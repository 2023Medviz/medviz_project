#######################
# Import libraries
import streamlit as st
from streamlit_timeline import st_timeline
import pandas as pd
import altair as alt
import plotly.express as px
import plotly.graph_objects as go
import time
import os

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


# csv.gz 파일을 chunk 단위로 읽어옵니다.
def split_read(path, chunksize=100000, condition="") :
    #chunksize = 100000  # 원하는 chunk 사이즈를 설정합니다.
    #condition = '특정열 == "조건"'  # 필터링할 조건을 설정합니다.
    filtered_df = pd.DataFrame() 
    for chunk in pd.read_csv(path, compression='gzip', chunksize=chunksize):
        # 조건에 맞는 행들만 선택하여 필터링합니다.
        if condition == "":
            filtered_df = pd.concat([filtered_df, chunk], ignore_index=True)
        else :
            filtered_chunk = chunk.query(condition)
            filtered_df = pd.concat([filtered_df, filtered_chunk], ignore_index=True)
        # 필터링된 chunk를 처리합니다.
        # 예를 들어, 이 부분에 필터링된 chunk를 다른 데이터프레임에 추가하거나
        # 원하는 작업을 수행할 수 있습니다.
    return filtered_df

@st.cache_data
def load_data() :
    # 현재 노트북 파일의 디렉토리를 가져옵니다.
    current_directory = os.getcwd()
    relative_folder_path = "../2.2/"

    admissions_df = split_read(os.path.join(current_directory, relative_folder_path, "hosp/admissions.csv.gz"), condition = 'subject_id == 10000032')
    patients_df = split_read(os.path.join(current_directory, relative_folder_path, "hosp/patients.csv.gz"), condition = 'subject_id == 10000032')
    omr_df = split_read(os.path.join(current_directory, relative_folder_path, "hosp/omr.csv.gz"), condition = 'subject_id == 10000032')
    omr_df = omr_df.drop_duplicates(subset=['subject_id','chartdate', 'result_name'], keep='last')


    diagnois_df = split_read(os.path.join(current_directory, relative_folder_path, "hosp/diagnoses_icd.csv.gz"), condition = 'subject_id == 10000032')
    d_diagnois_df = split_read(os.path.join(current_directory, relative_folder_path, "hosp/d_icd_diagnoses.csv.gz"))
    diagnois_df = pd.merge(diagnois_df, d_diagnois_df, on = ['icd_code', 'icd_version'], how = 'left')

    transfers_df = split_read(os.path.join(current_directory, relative_folder_path, "hosp/transfers.csv.gz"), condition = 'subject_id == 10000032')

    icust_df = split_read(os.path.join(current_directory, relative_folder_path, "icu/icustays.csv.gz"), condition = 'subject_id == 10000032')
    datetimeevents_df = split_read(os.path.join(current_directory, relative_folder_path, "icu/datetimeevents.csv.gz"), condition = 'subject_id == 10000032')
    d_items_df = split_read(os.path.join(current_directory, relative_folder_path, "icu/d_items.csv.gz"))
    datetimeevents_df = pd.merge(datetimeevents_df, d_items_df, on = 'itemid', how = 'left')

    procedureevents_df = split_read(os.path.join(current_directory, relative_folder_path, "icu/procedureevents.csv.gz"), condition = 'subject_id == 10000032')
    chartevents_df = pd.read_csv(os.path.join(current_directory, relative_folder_path, "icu/chartevents.csv.gz"), compression='gzip', nrows=100000)
    chartevents_df = chartevents_df.loc[chartevents_df['subject_id']==10000032]
    chartevents_df = pd.merge(chartevents_df, d_items_df, on = 'itemid', how = 'left')
    chartevents_df = chartevents_df.sort_values('charttime')

    accum_json = {}
    for subject_id in patients_df['subject_id'].unique() :
        accum_json[subject_id] = {}
        accum_json[subject_id]['status'] = {}
        t_patient = patients_df.loc[patients_df['subject_id']==subject_id]
        accum_json[subject_id]['status']['gender'] = t_patient['gender'].iloc[0]
        accum_json[subject_id]['status']['age'] = t_patient['anchor_age'].iloc[0]
        accum_json[subject_id]['hadm_id'] = {}
        for hadm_id in admissions_df.loc[admissions_df['subject_id']==subject_id]['hadm_id'].unique() :
            accum_json[subject_id]['hadm_id'][hadm_id] = {}

            #######################환자 기본 상태 관련
            #####Admission 당시 정보 모음
            accum_json[subject_id]['hadm_id'][hadm_id]['admin_info'] = {}
            if icust_df.loc[(icust_df['subject_id']==subject_id) & (icust_df['hadm_id']==hadm_id)].empty :
                accum_json[subject_id]['hadm_id'][hadm_id]['admin_info']['is_icu'] = 'N'
            else :
                accum_json[subject_id]['hadm_id'][hadm_id]['admin_info']['is_icu'] = 'Y'
            t_admission = admissions_df.loc[(admissions_df['subject_id']==subject_id) & (admissions_df['hadm_id']==hadm_id)]
            accum_json[subject_id]['hadm_id'][hadm_id]['admin_info']['admittime'] = t_admission['admittime'].iloc[0]
            accum_json[subject_id]['hadm_id'][hadm_id]['admin_info']['dischtime'] = t_admission['dischtime'].iloc[0]

            t_omr = omr_df.loc[(omr_df['subject_id']==subject_id) & (omr_df['chartdate'] <= accum_json[subject_id]['hadm_id'][hadm_id]['admin_info']['dischtime'][:10])]
            accum_json[subject_id]['hadm_id'][hadm_id]['admin_info']['bp'] = t_omr.loc[t_omr['result_name']=='Blood Pressure'].tail(1)['result_value'].iloc[0]
            accum_json[subject_id]['hadm_id'][hadm_id]['admin_info']['weight'] = t_omr.loc[t_omr['result_name']=='Weight (Lbs)'].tail(1)['result_value'].iloc[0]
            accum_json[subject_id]['hadm_id'][hadm_id]['admin_info']['bmi'] = t_omr.loc[t_omr['result_name']=='BMI (kg/m2)'].tail(1)['result_value'].iloc[0]
            accum_json[subject_id]['hadm_id'][hadm_id]['admin_info']['height'] = t_omr.loc[t_omr['result_name']=='Height (Inches)'].tail(1)['result_value'].iloc[0]

            accum_json[subject_id]['hadm_id'][hadm_id]['admin_info']['insurance'] = t_admission['insurance'].iloc[0]
            accum_json[subject_id]['hadm_id'][hadm_id]['admin_info']['language'] = t_admission['language'].iloc[0]
            accum_json[subject_id]['hadm_id'][hadm_id]['admin_info']['marital_status'] = t_admission['marital_status'].iloc[0]
            accum_json[subject_id]['hadm_id'][hadm_id]['admin_info']['race'] = t_admission['race'].iloc[0]

            ######진단 관련 정보
            accum_json[subject_id]['hadm_id'][hadm_id]['diagnosis'] = {}
            t_diagnosis = diagnois_df.loc[(diagnois_df['subject_id']==subject_id) & (diagnois_df['hadm_id']==hadm_id)]
            accum_json[subject_id]['hadm_id'][hadm_id]['diagnosis']['total_len'] = len(t_diagnosis)
            accum_json[subject_id]['hadm_id'][hadm_id]['diagnosis']['titles'] = []
            for it, row in t_diagnosis.iterrows() :
                accum_json[subject_id]['hadm_id'][hadm_id]['diagnosis']['titles'].append(row['long_title'])
            
            #########################ICU
            if accum_json[subject_id]['hadm_id'][hadm_id]['admin_info']['is_icu'] == 'Y' :
                t_icustay = icust_df[(icust_df['subject_id']==subject_id) & (icust_df['hadm_id']==hadm_id)]
                accum_json[subject_id]['hadm_id'][hadm_id]['icu_stay'] = {}
                accum_json[subject_id]['hadm_id'][hadm_id]['icu_stay']['los'] = t_icustay['los'].iloc[0]
                ######Vital Signs
                t_chartevent = chartevents_df.loc[(chartevents_df['subject_id']==subject_id) & (chartevents_df['hadm_id']==hadm_id)].sort_values("charttime")
                accum_json[subject_id]['hadm_id'][hadm_id]['vitals'] = {}

                ###맥박 bpm
                accum_json[subject_id]['hadm_id'][hadm_id]['vitals']['hr'] = []
                accum_json[subject_id]['hadm_id'][hadm_id]['vitals']['hr_time'] = []
                t_vt = t_chartevent.loc[t_chartevent['itemid']==220045]
                for it, row in t_vt.iterrows() :
                    accum_json[subject_id]['hadm_id'][hadm_id]['vitals']['hr'].append(row['valuenum'])
                    accum_json[subject_id]['hadm_id'][hadm_id]['vitals']['hr_time'].append(row['charttime'])

                ###수축기 혈압 mmHg
                accum_json[subject_id]['hadm_id'][hadm_id]['vitals']['sbp'] = []
                accum_json[subject_id]['hadm_id'][hadm_id]['vitals']['sbp_time'] = []
                t_vt = t_chartevent.loc[t_chartevent['itemid']==220179]
                for it, row in t_vt.iterrows() :
                    accum_json[subject_id]['hadm_id'][hadm_id]['vitals']['sbp'].append(row['valuenum'])
                    accum_json[subject_id]['hadm_id'][hadm_id]['vitals']['sbp_time'].append(row['charttime'])

                ###이완기 혈압 mmHg
                accum_json[subject_id]['hadm_id'][hadm_id]['vitals']['dbp'] = []
                accum_json[subject_id]['hadm_id'][hadm_id]['vitals']['dbp_time'] = []
                t_vt = t_chartevent.loc[t_chartevent['itemid']==220180]
                for it, row in t_vt.iterrows() :
                    accum_json[subject_id]['hadm_id'][hadm_id]['vitals']['dbp'].append(row['valuenum'])
                    accum_json[subject_id]['hadm_id'][hadm_id]['vitals']['dbp_time'].append(row['charttime'])

                ###호흡 insp/min
                accum_json[subject_id]['hadm_id'][hadm_id]['vitals']['rp'] = []
                accum_json[subject_id]['hadm_id'][hadm_id]['vitals']['rp_time'] = []
                t_vt = t_chartevent.loc[t_chartevent['itemid']==220210]
                for it, row in t_vt.iterrows() :
                    accum_json[subject_id]['hadm_id'][hadm_id]['vitals']['rp'].append(row['valuenum'])
                    accum_json[subject_id]['hadm_id'][hadm_id]['vitals']['rp_time'].append(row['charttime'])

                ###산소 포화도 %
                accum_json[subject_id]['hadm_id'][hadm_id]['vitals']['os'] = []
                accum_json[subject_id]['hadm_id'][hadm_id]['vitals']['os_time'] = []
                t_vt = t_chartevent.loc[t_chartevent['itemid']==220277]
                for it, row in t_vt.iterrows() :
                    accum_json[subject_id]['hadm_id'][hadm_id]['vitals']['os'].append(row['valuenum'])
                    accum_json[subject_id]['hadm_id'][hadm_id]['vitals']['os_time'].append(row['charttime'])

                ###체온 섭씨
                accum_json[subject_id]['hadm_id'][hadm_id]['vitals']['temp'] = []
                accum_json[subject_id]['hadm_id'][hadm_id]['vitals']['temp_time'] = []
                t_vt = t_chartevent.loc[t_chartevent['itemid']==223761]
                for it, row in t_vt.iterrows() :
                    accum_json[subject_id]['hadm_id'][hadm_id]['vitals']['temp'].append(round((row['valuenum'] - 32) * 5/9, 2))
                    accum_json[subject_id]['hadm_id'][hadm_id]['vitals']['temp_time'].append(row['charttime'])


                ######최근 근무자
                t_caregivers = t_chartevent.loc[t_chartevent['caregiver_id'].notna()]
                t_caregivers['next_caregiver'] = t_caregivers['caregiver_id'].shift(1, fill_value=0)
                t_caregivers = t_caregivers.loc[t_caregivers['caregiver_id']!=t_caregivers['next_caregiver']]
                accum_json[subject_id]['hadm_id'][hadm_id]['cargivers'] = []
                for it, row in t_caregivers.iterrows() :
                    new_giver = {}
                    new_giver['caregiver_id'] = row['caregiver_id']
                    new_giver['chartstart'] = row['charttime']
                    accum_json[subject_id]['hadm_id'][hadm_id]['cargivers'].append(new_giver)

            #####################################################
                #########일정 관련
                t_schedule = t_chartevent.drop_duplicates(subset= ["charttime", "category"]).drop_duplicates(subset= ["charttime", "category"])[['caregiver_id', 'charttime', 'category', 'label']]
                t_schedule = t_schedule.loc[t_schedule['caregiver_id'].notna()]
                t_schedule['charttime'] = pd.to_datetime(t_schedule['charttime'])
                accum_json[subject_id]['hadm_id'][hadm_id]['schedule'] = []
                for it, row in t_schedule.iterrows() :
                    if row['category'] == "Alarms" or row['category'] == "Treatments" or row['category'] == "Care Plans" : 
                        new_schedule = {}
                        new_schedule['caregiver_id'] = row['caregiver_id']
                        new_schedule['charttime'] = row['charttime']
                        new_schedule['category'] = row['category'] + " - " + row['label']
                        accum_json[subject_id]['hadm_id'][hadm_id]['schedule'].append(new_schedule)


                ######
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
    selected_id = st.text_input('Type the subject_id', placeholder = 'ex) 10000032')
    selected_hadm_id = None
    if selected_id :
        with st.spinner('Loading data...'):
            dict_data = load_data()
            dict_data = dict_data[int(selected_id)]
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

    st.title(f'Subject_id: {selected_id}')
    st.text(f'Hadm_id: {selected_hadm_id}')

    st.text(f"adm date: {str(admission_dt)}")
    if icu_yn == "Y":
        st.text(f"LOS: {los}")

    second_row = st.columns(2)

    with second_row[0] :
        with st.popover(f"Number of Symptoms: {n_diagnois}"):
            for i in diagnosis :
                st.markdown(f"- {i}")

    with second_row[1] :
        if icu_yn == "Y":
            with st.popover(f"Caregivers : Time"):
                for i in caregivers :
                    st.markdown(f"- {i['caregiver_id']} : {i['chartstart']}")

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

        if temp_class != "green" or pulse_class != "green" or bp_class != "green" or resp_class != "green" or resp_class != "green" :
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
            st.plotly_chart(fig)




        timeline_data = []
        for entry in schedules:
            timeline_data.append({
                'start': entry['charttime'].strftime('%Y-%m-%d %H:%M:%S'),
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




    cols = st.columns(2)

    with cols[0]:
        st.markdown('#### 세부주제 1')

    with cols[1]:
        st.markdown('#### 세부주제 2')



    cols = st.columns(2)

    with cols[0]:
        st.markdown('#### 세부주제 3')

    with cols[1]:
        st.markdown('#### 세부주제 4')
