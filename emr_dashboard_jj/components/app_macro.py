import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# 데이터 불러오기 (이 부분은 로컬 데이터 경로로 변경해야 함)

def component_macro(data) :
    # Streamlit 앱 시작
    st.title('Hospital Admission Analysis')

    # 1. 입원 유형별 환자 수
    st.header('Admission Type Counts')
    admission_type_counts = data['admission_type'].value_counts()
    fig, ax = plt.subplots()
    admission_type_counts.plot(kind='bar', ax=ax)
    ax.set_ylabel('Number of Admissions')
    ax.set_title('Admissions by Type')
    st.pyplot(fig)

    # 2. 병원 사망률
    st.header('Hospital Death Rate')
    death_rate = data['hospital_expire_flag'].mean() * 100
    st.write(f'Hospital Death Rate: {death_rate:.2f}%')

    # 3. 평균 입원 기간
    st.header('Average Length of Stay')
    average_stay = data['length_of_stay'].mean()
    st.write(f'Average Length of Stay: {average_stay:.2f} days')

    # 4. 보험 유형별 입원 패턴
    st.header('Insurance Type and Length of Stay')
    insurance_stay_pattern = data.groupby('insurance')['length_of_stay'].mean()
    fig, ax = plt.subplots()
    insurance_stay_pattern.plot(kind='bar', ax=ax)
    ax.set_ylabel('Average Length of Stay (days)')
    ax.set_title('Average Stay by Insurance Type')
    st.pyplot(fig)

    # 5. 응급실 이용 시간
    st.header('Average ER Stay Length')
    average_er_stay = data['er_stay_length'].mean()
    st.write(f'Average ER Stay Length: {average_er_stay:.2f} hours')

    # 앱을 실행하기 위해 streamlit run your_script_name.py 명령을 사용하세요.
