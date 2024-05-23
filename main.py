#######################
# Import libraries
import streamlit as st
from streamlit_timeline import st_timeline
from streamlit_searchbox import st_searchbox
import pandas as pd
import altair as alt
import plotly.express as px
import plotly.graph_objects as go
import time
import os
import json
from datetime import datetime

#######################
# Page configuration
st.set_page_config(
    page_title="EMR Dashboard",
    page_icon="🏥",
    layout="centered",
    initial_sidebar_state="expanded")

alt.themes.enable("dark")


#######################
# Load data


@st.cache_data
def load_data() :
    with open('./icu_data.json', 'r') as json_file:
        accum_json = json.load(json_file)
    return accum_json

def vital_overview(dataset, selected_hadm_id) :
        hr_df = pd.DataFrame({'time': dataset['hadm_id'][selected_hadm_id]['vitals']['hr_time']
                                    , 'Purse (bpm)': dataset['hadm_id'][selected_hadm_id]['vitals']['hr']})
        bp_df = pd.DataFrame({'time': dataset['hadm_id'][selected_hadm_id]['vitals']['sbp_time']
                                    , 'sbp': dataset['hadm_id'][selected_hadm_id]['vitals']['sbp']
                                    , 'dbp': dataset['hadm_id'][selected_hadm_id]['vitals']['dbp']})
        os_df = pd.DataFrame({'time': dataset['hadm_id'][selected_hadm_id]['vitals']['os_time']
                                    , 'Oxygen (%)': dataset['hadm_id'][selected_hadm_id]['vitals']['os']})
        rp_df = pd.DataFrame({'time': dataset['hadm_id'][selected_hadm_id]['vitals']['rp_time']
                                    , 'Repos (insp/min)': dataset['hadm_id'][selected_hadm_id]['vitals']['rp']})
        temp_df = pd.DataFrame({'time': dataset['hadm_id'][selected_hadm_id]['vitals']['temp_time']
                                    , 'Body Temp (Cº)': dataset['hadm_id'][selected_hadm_id]['vitals']['temp']})

        dfs = [hr_df, bp_df, os_df, rp_df, temp_df]
        result_df = dfs[0]

        for df in dfs[1:]:
            result_df = pd.merge(result_df, df, on='time', how='outer')

        result_df.sort_values("time")

        result_df['time'] = pd.to_datetime(result_df['time'])

        # 30분 단위로 그룹화하고 각 그룹의 최대값 계산
        result_df = result_df.resample('60T', on='time').max().reset_index()

        df_melted = result_df.melt(id_vars=['time'], var_name='variable', value_name='value')

        def get_tile_color(value, variable):
            if pd.isna(value):
                return 'white'
            if variable == 'sbp' :
                return 'pink' if value < 90 else 'lightgreen'
            elif variable == 'dbp' :
                return 'pink' if value > 140 else 'lightgreen'
            elif variable == 'Body Temp (Cº)':
                return 'pink' if value >= 37.5 or value < 36 else 'lightgreen'
            elif variable == 'Purse (bpm)':
                return 'pink' if value < 50 or value > 100 else 'lightgreen'
            elif variable == 'Repos (insp/min)':
                return 'pink' if value < 12 or value > 20 else 'lightgreen'
            elif variable == 'Oxygen (%)':
                return 'pink' if value < 95 else 'lightgreen'
            return 'white'

        tile_colors = df_melted.apply(lambda row: get_tile_color(row['value'], row['variable']), axis=1).values
        df_melted['tile_color'] = tile_colors

        df_pivot = df_melted.pivot(index='time', columns='variable', values=['value', 'tile_color'])

        # sbp와 dbp를 결합하여 새로운 bp 컬럼 생성
        df_pivot['value', 'BP (mmHg)'] = df_pivot['value', 'sbp'].astype(str) + '/' + df_pivot['value', 'dbp'].astype(str)

        # 색상 결합 조건: 하나라도 pink이면 pink, 그렇지 않으면 lightgreen
        def combine_colors(row):
            if row['tile_color', 'sbp'] == 'pink' or row['tile_color', 'dbp'] == 'pink':
                return 'pink'
            return 'lightgreen'

        df_pivot['tile_color', 'BP (mmHg)'] = df_pivot.apply(combine_colors, axis=1)

        # 결합된 데이터프레임을 다시 풀어서 사용
        df_combined = df_pivot.stack().reset_index()

        # 필요한 열만 선택
        df_combined = df_combined[df_combined['variable'] == 'BP (mmHg)'][['time', 'variable', 'value', 'tile_color']]

        df_melted = df_melted.loc[(df_melted['variable']!='sbp' )&( df_melted['variable']!= 'dbp')]
        df_melted = pd.concat([df_melted, df_combined])

        sort_order = ['BP (mmHg)', 'Purse (bpm)', 'Repos (insp/min)', 'Body Temp (Cº)', 'Oxygen (%)']
        df_melted['variable'] = pd.Categorical(df_melted['variable'], categories=sort_order, ordered=True)
        df_melted = df_melted.sort_values(['variable', 'time'])
        # 히트맵을 그리기 위한 색상 매핑
        color_map = {'lightgreen': 1, 'pink': 2, 'white': 0}

        # 색상 값을 숫자로 변환
        df_melted['color_value'] = df_melted['tile_color'].map(color_map)

        # 히트맵 데이터 준비
        heatmap_data = df_melted.pivot(index='variable', columns='time', values='color_value').fillna(0)
        heatmap_text = df_melted.pivot(index='variable', columns='time', values='value')

        # 히트맵 생성
        fig = go.Figure(data=go.Heatmap(
            z=heatmap_data.values,
            x=heatmap_data.columns,
            y=heatmap_data.index,
            text=heatmap_text.values,
            colorscale=[(0, 'white'), (0.5, 'lightgreen'), (1, 'pink')],
            hovertemplate='Value: %{text}<extra></extra>',
            showscale=False
        ))

        fig.update_layout(
            xaxis_title='Chart Time',
            yaxis=dict(type='category')
        )
        # 범례 추가
        fig.add_trace(go.Scatter(
            x=[None],
            y=[None],
            mode='markers',
            marker=dict(size=10, color='white'),
            legendgroup='group',
            showlegend=True,
            name='No Data'
        ))

        fig.add_trace(go.Scatter(
            x=[None],
            y=[None],
            mode='markers',
            marker=dict(size=10, color='lightgreen'),
            legendgroup='group',
            showlegend=True,
            name='Normal'
        ))

        fig.add_trace(go.Scatter(
            x=[None],
            y=[None],
            mode='markers',
            marker=dict(size=10, color='pink'),
            legendgroup='group',
            showlegend=True,
            name='Danger'
        ))
    
        return fig


#######################
# Sidebar
with st.sidebar:
    st.title('🏥 EMR Dashboard')

    dict_data = load_data()
    suggestions = list(dict_data.keys())

    # Function to search the suggestions
    def search_func(query):
        return [s for s in suggestions if query.lower() in s.lower()]

    # Use st_searchbox for text input with autocomplete
    user_input = st_searchbox(
        search_func,
        placeholder="ex) 10000032",
        label="Type Subject Id",
    )

    selected_id = user_input

    selected_hadm_id = None
    if selected_id :
        with st.spinner('Loading data...'):
            dict_data = dict_data[str(selected_id)]
            hadm_ids = []
            for i in dict_data['hadm_id'].keys() :
                if dict_data['hadm_id'][i]['admin_info']['is_icu'] == 'Y':
                    hadm_ids.append(i)
            selected_hadm_id = st.selectbox('Select hadm_id', hadm_ids)

main_placeholder = st.empty()
if not selected_id or not selected_hadm_id:
    main_placeholder.title('🏥Welcome to ICU EMR System')
    st.header('✅ You can check ...')
    st.markdown("- Basic Patients Information")
    st.markdown("- Planned Service")
    st.markdown("- Analyzed Results")

    


if selected_hadm_id:
    gender = dict_data['status']['gender']
    age = dict_data['status']['age']
    admission_dt = dict_data['hadm_id'][selected_hadm_id]['admin_info']['admittime'][:10]

    n_diagnois = dict_data['hadm_id'][selected_hadm_id]['diagnosis']['total_len']
    diagnosis =  dict_data['hadm_id'][selected_hadm_id]['diagnosis']['titles']
    race = dict_data['hadm_id'][selected_hadm_id]['admin_info']['race']
    insur = dict_data['hadm_id'][selected_hadm_id]['admin_info']['insurance']
    lang = dict_data['hadm_id'][selected_hadm_id]['admin_info']['language']
    martial = dict_data['hadm_id'][selected_hadm_id]['admin_info']['marital_status']
    icu_yn = dict_data['hadm_id'][selected_hadm_id]['admin_info']['is_icu']
    bmi = dict_data['hadm_id'][selected_hadm_id]['admin_info']['bmi']
    if icu_yn =="Y" :
        los = dict_data['hadm_id'][selected_hadm_id]['icu_stay']['los']
        caregivers = dict_data['hadm_id'][selected_hadm_id]['cargivers']

    tab1, tab2, tab3 = st.tabs(["Individual", "Overall", "Etc"])

    with tab1 :

        st.title(f'Subject_id: {selected_id}')
        st.text(f'Hadm_id: {selected_hadm_id}')

        cols = st.columns(2)
        with cols[0]:
            st.text(f"adm date: {str(admission_dt)}")
        if icu_yn == "Y":
            with cols[1]:
                st.text(f"LOS: {los}")

        second_row = st.columns(2)

        with second_row[0] :
            with st.popover(f"Number of Symptoms: {n_diagnois}"):
                for i in diagnosis :
                    st.markdown(f"- {i}")

        with second_row[1] :
            if icu_yn == "Y":
                current_cg = int(caregivers[-1]['caregiver_id'])
                caregivers_df = pd.DataFrame(columns=['Caregiver_id', 'Chart Start Time'])
                for i in caregivers:
                    new_row = pd.DataFrame({'Caregiver_id': [int(i['caregiver_id'])], 'Chart Start Time': [i['chartstart']]})
                    caregivers_df = pd.concat([caregivers_df, new_row], ignore_index=True)

                def highlight_last_row(y):
                    color = 'background-color: yellow'
                    df1 = pd.DataFrame('', index=y.index, columns=y.columns)
                    df1.iloc[-1, :] = color
                    return df1

                styled_df = caregivers_df.style.apply(highlight_last_row, axis=None)
                

                with st.popover(f"Current Caregiver: {current_cg}"):
                    st.dataframe(styled_df)


        third_row = st.columns(6) 

        # 각 컬럼에 정보 표시
        third_row[0].write(f"Age: {age}")
        third_row[1].write(f"Race: {race}")
        third_row[2].write(f"BMI: {bmi}")
        third_row[3].write(f"Language: {lang}")
        third_row[4].write(f"Insurance: {insur}")
        third_row[5].write(f"Martial Status: {martial}")

        if icu_yn =="Y" :
            hr = dict_data['hadm_id'][selected_hadm_id]['vitals']['hr']
            sbp = dict_data['hadm_id'][selected_hadm_id]['vitals']['sbp']
            dbp = dict_data['hadm_id'][selected_hadm_id]['vitals']['dbp']
            rp = dict_data['hadm_id'][selected_hadm_id]['vitals']['rp']
            oxy = dict_data['hadm_id'][selected_hadm_id]['vitals']['os']
            temp = dict_data['hadm_id'][selected_hadm_id]['vitals']['temp']

            # 조건에 따라 CSS 클래스 설정
            bp_class = "red" if sbp[-1] < 90 or dbp[-1] > 140 else "green"
            temp_class = "red" if temp[-1] >= 37.5 or temp[-1] < 36  else "green"
            pulse_class = "red" if hr[-1] < 50 or hr[-1] > 100 else "green"
            resp_class = "red" if rp[-1] < 12 or rp[-1] > 20 else "green"
            oxy_class = "red" if oxy[-1] < 95 else "green"

            # Schedule
            schedules = dict_data['hadm_id'][selected_hadm_id]['schedule']

            st.markdown('#### Vital Signs')

            st.markdown("""
            <style>
            .pink-background {background-color: #ffcccc;}
            .normal-background {background-color: #ccffcc;}
            </style>
            """, unsafe_allow_html=True)

            if temp_class != "green" or pulse_class != "green" or bp_class != "green" or resp_class != "green" or oxy_class != "green" :
                st.error('Check the vital signs', icon="⚠️")

            cols = st.columns(5)

            with cols[0]:
                st.markdown("**BP (mmHg)**")
                if bp_class == 'red' :
                    background = 'pink-background'
                else :        
                    background = 'normal-background'
                    
                st.markdown(f"<div class='{background}'><h3 style='text-align: center; color: {bp_class};'>{sbp[-1]}/{dbp[-1]}</h3>", unsafe_allow_html=True)
            

            with cols[1]:
                st.markdown("**Purse (bpm)**")
                if pulse_class == 'red' :
                    background = 'pink-background'
                else :        
                    background = 'normal-background'

                st.markdown(f"<div class='{background}'><h3 style='text-align: center; color: {pulse_class};'>{(hr[-1])}</h3>", unsafe_allow_html=True)

            with cols[2]:
                st.markdown("**Repos (insp/min)**")

                if resp_class == 'red' :
                    background = 'pink-background'
                else :        
                    background = 'normal-background'

                st.markdown(f"<div class='{background}'><h3 style='text-align: center; color: {resp_class};'>{rp[-1]}</h3>", unsafe_allow_html=True)


            with cols[3]:
                st.markdown("**Body Temp (Cº)**")
                if temp_class == 'red' :
                    background = 'pink-background'
                else :        
                    background = 'normal-background'

                st.markdown(f"<div class='{background}'><h3 style='text-align: center; color: {temp_class};'>{temp[-1]}</h3>", unsafe_allow_html=True)

            with cols[4]:
                st.markdown("**Oxygen (%)**")

                if oxy_class == 'red' :
                    background = 'pink-background'
                else :        
                    background = 'normal-background'

                st.markdown(f"<div class='{background}'><h3 style='text-align: center; color: {oxy_class};'>{oxy[-1]}</h3>", unsafe_allow_html=True)

            # 각 이벤트에 대한 데이터 리스트 생성

            fig = vital_overview(dict_data, selected_hadm_id)

            with st.expander("Overview of Vital Signs") :
                try :
                    st.plotly_chart(fig)
                except :
                    st.markdown("Not enough data.")




            try:
                timeline_data = []
                for entry in schedules:
                    charttime = datetime.strptime(entry['charttime'], '%Y-%m-%d %H:%M:%S')
                    timeline_data.append({
                        'start': charttime.strftime('%Y-%m-%d %H:%M:%S'),
                        'content': entry['category']
                    })

                # Timeline configuration
                options = {
                    "stack": True,
                    "showCurrentTime": True,
                    "zoomMin": 1000 * 60 * 10,   # 10 minutes in milliseconds
                    "zoom": 1000 * 60 * 15,  # Initial zoom level: 10 minutes
                }

                st.markdown('#### Schedule Checks')
                # Render the timeline in Streamlit
                st_timeline(timeline_data, options=options, height='250px')
            except:
                st.markdown('#### Schedule Checks')
                st.markdown('######## No Specific Schedule')

    with tab2:
        st.markdown('#### Overall Status')
        st.image("https://static.streamlit.io/examples/dog.jpg", width=200)
        


    with tab3:
        st.markdown('#### Etc')