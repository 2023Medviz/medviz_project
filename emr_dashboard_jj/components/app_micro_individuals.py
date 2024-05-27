#######################
# Import libraries
import streamlit as st
from streamlit_timeline import st_timeline
from streamlit_searchbox import st_searchbox
import pandas as pd
import altair as alt
import plotly.express as px
import plotly.graph_objects as go
import plotly.colors
import time
import os
import json
from datetime import datetime, timedelta


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



def component_indiviual(dict_data, selected_id, selected_hadm_id):
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
            caregivers_df = caregivers_df.tail(10) ##마지막 10개만
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
            task = []
            label = []
            start = []
            finish = []
            cv = []
            for entry in schedules:
                    cv.append(str(int(entry['caregiver_id'])))
                    start_time = datetime.strptime(entry['charttime'], '%Y-%m-%d %H:%M:%S')
                    start.append(start_time)
                    finish_time = start_time + timedelta(minutes=20)
                    finish.append(finish_time)
                    task.append(entry["category"])
                    label.append(entry["label"])

            data = {"Care Giver": cv,
                    "Start": start,
                    "Finish": finish,
                    "Task": task,
                    "Detail": label}
            df = pd.DataFrame(data)

            # Gantt 차트 생성


            # Streamlit을 사용하여 차트 표시
            st.markdown("#### Treatment and Care Plans")

            task_options = df['Detail'].unique().tolist()
            cols = st.columns(2)
            with cols[0] :
                with st.popover(f"Filter Option"):
                    selected_tasks = st.multiselect("Select Tasks", task_options, default=task_options)
            with cols[1] :
                with st.popover("Display Option"):
                    display_option = st.selectbox("Select Display Option", ["Plot", "DataFrame", "Both"])

            # 선택한 Task로 데이터 필터링
            filtered_df = df[df['Detail'].isin(selected_tasks)]

            # Care Giver 컬럼의 유니크 값에 대해 색상 매핑
            unique_care_givers = filtered_df['Care Giver'].unique()
            color_map = {care_giver: color for care_giver, color in zip(unique_care_givers, plotly.colors.qualitative.Plotly)}



            def highlight_care_giver(data):
                df1 = pd.DataFrame('', index=data.index, columns=data.columns)
                for idx, row in data.iterrows():
                    color = color_map[row['Care Giver']]
                    df1.loc[idx, :] = f'background-color: {color}'
                return df1

            # DataFrame을 스타일링하여 표시
            def display_styled_dataframe(data):
                return data.style.apply(highlight_care_giver, axis=None)

            if display_option == "DataFrame":
                st.dataframe(display_styled_dataframe(filtered_df))

            elif display_option == "Plot":
                fig = px.timeline(filtered_df, x_start='Start', x_end='Finish', y='Task', hover_data=['Start', 'Detail']
                                  , color='Care Giver', color_discrete_map=color_map)
                fig.update_yaxes(categoryorder='total ascending')
                st.plotly_chart(fig)
                
            elif display_option == "Both":
                st.dataframe(display_styled_dataframe(filtered_df))
                fig = px.timeline(filtered_df, x_start='Start', x_end='Finish', y='Task', hover_data=['Start', 'Detail']
                                  , color='Care Giver', color_discrete_map=color_map,)
                fig.update_yaxes(categoryorder='total ascending')
                st.plotly_chart(fig)

        except:
            st.markdown('#### Schedule Checks')
            st.markdown('######## No Specific Schedule')


