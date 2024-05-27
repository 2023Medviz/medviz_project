import pandas as pd
import os
import json


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




def to_json(path) :
    # 현재 노트북 파일의 디렉토리를 가져옵니다.
    current_directory = os.getcwd()
    relative_folder_path = "../2.2/"

    base_df = split_read(os.path.join(current_directory, relative_folder_path, "icu/icustays.csv.gz"))

    condition = 'subject_id in ['
    for i in list(base_df['subject_id'].unique()[:1000]) :
        condition += str(i)
        condition += ', '
    condition += ']'


    admissions_df = split_read(os.path.join(current_directory, relative_folder_path, "hosp/admissions.csv.gz"), condition = condition)
    patients_df = split_read(os.path.join(current_directory, relative_folder_path, "hosp/patients.csv.gz"), condition = condition)
    omr_df = split_read(os.path.join(current_directory, relative_folder_path, "hosp/omr.csv.gz"), condition = condition)
    omr_df = omr_df.drop_duplicates(subset=['subject_id','chartdate', 'result_name'], keep='last')


    diagnois_df = split_read(os.path.join(current_directory, relative_folder_path, "hosp/diagnoses_icd.csv.gz"), condition = condition)
    d_diagnois_df = split_read(os.path.join(current_directory, relative_folder_path, "hosp/d_icd_diagnoses.csv.gz"))
    diagnois_df = pd.merge(diagnois_df, d_diagnois_df, on = ['icd_code', 'icd_version'], how = 'left')

    transfers_df = split_read(os.path.join(current_directory, relative_folder_path, "hosp/transfers.csv.gz"), condition = condition)

    icust_df = split_read(os.path.join(current_directory, relative_folder_path, "icu/icustays.csv.gz"), condition = condition)
    datetimeevents_df = split_read(os.path.join(current_directory, relative_folder_path, "icu/datetimeevents.csv.gz"), condition = condition)
    d_items_df = split_read(os.path.join(current_directory, relative_folder_path, "icu/d_items.csv.gz")) 
    datetimeevents_df = pd.merge(datetimeevents_df, d_items_df, on = 'itemid', how = 'left')

    chartevents_df = pd.read_csv(os.path.join(current_directory, relative_folder_path, "icu/chartevents.csv.gz"), compression='gzip', nrows=1000000)
    chartevents_df = chartevents_df[chartevents_df['subject_id'].isin(base_df['subject_id'].unique()[:1000])]
    chartevents_df = pd.merge(chartevents_df, d_items_df, on = 'itemid', how = 'left')
    chartevents_df = chartevents_df.sort_values('charttime')
    accum_json = {}
    for subject_id in [int(i) for i in patients_df['subject_id'].unique()] :
        accum_json[subject_id] = {}
        accum_json[subject_id]['status'] = {}
        t_patient = patients_df.loc[patients_df['subject_id']==subject_id]
        accum_json[subject_id]['status']['gender'] = t_patient['gender'].iloc[0]
        accum_json[subject_id]['status']['age'] = int(t_patient['anchor_age'].iloc[0])
        accum_json[subject_id]['hadm_id'] = {}
        for hadm_id in [int(j) for j in admissions_df.loc[admissions_df['subject_id']==subject_id]['hadm_id'].unique()] :
            accum_json[subject_id]['hadm_id'][hadm_id] = {}

            #######################환자 기본 상태 관련
            #####Admission 당시 정보 모음
            accum_json[subject_id]['hadm_id'][hadm_id]['admin_info'] = {}
            if chartevents_df.loc[(chartevents_df['subject_id']==subject_id) & (chartevents_df['hadm_id']==hadm_id)].sort_values("charttime").empty :
                accum_json[subject_id]['hadm_id'][hadm_id]['admin_info']['is_icu'] = 'N'
            else :
                accum_json[subject_id]['hadm_id'][hadm_id]['admin_info']['is_icu'] = 'Y'
            t_admission = admissions_df.loc[(admissions_df['subject_id']==subject_id) & (admissions_df['hadm_id']==hadm_id)]
            accum_json[subject_id]['hadm_id'][hadm_id]['admin_info']['admittime'] = t_admission['admittime'].iloc[0]
            accum_json[subject_id]['hadm_id'][hadm_id]['admin_info']['dischtime'] = t_admission['dischtime'].iloc[0]

            t_omr = omr_df.loc[(omr_df['subject_id']==subject_id) & (omr_df['chartdate'] <= accum_json[subject_id]['hadm_id'][hadm_id]['admin_info']['dischtime'][:10])]
            if len(t_omr) == 0 :
                t_omr = omr_df.loc[(omr_df['subject_id']==subject_id)]
            
            try :
                accum_json[subject_id]['hadm_id'][hadm_id]['admin_info']['bp'] = t_omr.loc[t_omr['result_name']=='Blood Pressure'].tail(1)['result_value'].iloc[0]
            except : 
                accum_json[subject_id]['hadm_id'][hadm_id]['admin_info']['bp'] = ' '

            try :
                accum_json[subject_id]['hadm_id'][hadm_id]['admin_info']['weight'] = t_omr.loc[t_omr['result_name']=='Weight (Lbs)'].tail(1)['result_value'].iloc[0]
            except : 
                accum_json[subject_id]['hadm_id'][hadm_id]['admin_info']['weight'] = ' '

            try :
                accum_json[subject_id]['hadm_id'][hadm_id]['admin_info']['bmi'] = t_omr.loc[t_omr['result_name']=='BMI (kg/m2)'].tail(1)['result_value'].iloc[0]
            except : 
                accum_json[subject_id]['hadm_id'][hadm_id]['admin_info']['bmi'] = ' '

            try :
                accum_json[subject_id]['hadm_id'][hadm_id]['admin_info']['height'] = t_omr.loc[t_omr['result_name']=='Height (Inches)'].tail(1)['result_value'].iloc[0]
            except : 
                accum_json[subject_id]['hadm_id'][hadm_id]['admin_info']['height'] = ' '


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
                #t_schedule['charttime'] = pd.to_datetime(t_schedule['charttime'])
                accum_json[subject_id]['hadm_id'][hadm_id]['schedule'] = []
                for it, row in t_schedule.iterrows() :
                    if row['category'] == "Alarms" or row['category'] == "Treatments" or row['category'] == "Care Plans" : 
                        new_schedule = {}
                        new_schedule['caregiver_id'] = row['caregiver_id']
                        new_schedule['charttime'] = row['charttime']
                        new_schedule['category'] = row['category'] + " - " + row['label']
                        accum_json[subject_id]['hadm_id'][hadm_id]['schedule'].append(new_schedule)

                ######
                

            
def load_data_indiviual(path) :
    with open(path, 'r') as json_file:
        accum_json = json.load(json_file)
    return accum_json


def load_data_macro(path) :
    data = pd.read_csv(r"your_data_path.csv")

    data['admittime'] = pd.to_datetime(data['admittime'])
    data['dischtime'] = pd.to_datetime(data['dischtime'])
    data['edregtime'] = pd.to_datetime(data['edregtime'])
    data['edouttime'] = pd.to_datetime(data['edouttime'])
    data['length_of_stay'] = (data['dischtime'] - data['admittime']).dt.total_seconds() / (24 * 3600)
    data['er_stay_length'] = (data['edouttime'] - data['edregtime']).dt.total_seconds() / 3600

    return data