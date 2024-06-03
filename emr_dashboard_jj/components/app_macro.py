import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from scipy.stats import gaussian_kde

def component_macro(total_data) :
    # Streamlit 앱 시작
    st.title('Hospital Admission Analysis')

    data, data_pat = total_data

    col1, col2 = st.columns(2)

    # 1-1. 입원 유형별 환자 수
    with col1:
        st.header('Admission Type Counts')
        admission_type_counts = data['admission_type'].value_counts().reset_index()
        admission_type_counts.columns = ['admission_type', 'count']
        
        fig1 = px.bar(admission_type_counts, x='admission_type', y='count', title='Admissions by Type',
                    labels={'admission_type': 'Admission Type', 'count': 'Number of Admissions'},
                    color='admission_type')
        
        st.plotly_chart(fig1)

    # 1-2. 성별별 환자 수
    with col2:
        st.header('Gender Type Counts')
        gender_counts = data_pat['gender'].value_counts().reset_index()
        gender_counts.columns = ['gender', 'count']
        
        fig2 = px.bar(gender_counts, x='gender', y='count', title='Gender Distribution',
                    labels={'gender': 'Gender', 'count': 'Count'},
                    color='gender')
        
        st.plotly_chart(fig2)

    # 1-3. 연령대별 환자 수
    st.header('Age Type Counts')
    data_pat['anchor_age_dec'] = (data_pat['anchor_age'] // 10) * 10
    age_dec_counts = data_pat['anchor_age_dec'].value_counts().reset_index()
    age_dec_counts.columns = ['age_decade', 'count']
    
    fig3 = px.bar(age_dec_counts, x='age_decade', y='count', title='Age Distribution by Decade',
                labels={'age_decade': 'Age Decade', 'count': 'Count'},
                color='age_decade')
    
    st.plotly_chart(fig3)


    # 2. 병원 사망률
    st.header('Hospital Death Rate')
    death_rate = data['hospital_expire_flag'].mean() * 100
    # Create a gauge chart
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=death_rate,
        title={'text': "Hospital Death Rate"},
        gauge={'axis': {'range': [0, 100]},
            'bar': {'color': "red"},
            'steps': [
                {'range': [0, 50], 'color': "lightgray"},
                {'range': [50, 100], 'color': "gray"}]}))

    # Customize the layout
    fig.update_layout(
        title_font_size=20,
        title_x=0.5,  # Centers the title
        template='plotly_white'  # Uses a white theme
    )

    # Display the figure in Streamlit
    st.header('Hospital Death Rate')
    st.plotly_chart(fig)

    # 3-1. 평균 입원 기간
    average_length_of_stay = data['length_of_stay'].mean()

    # Create a horizontal bar chart
    fig = px.bar(
        x=[average_length_of_stay],
        y=["Average Length of Stay"],
        orientation='h',
        title='Average Length of Stay',
        labels={'x': 'Days', 'y': ''},
        text=[f'{average_length_of_stay:.2f} days']
    )

    # Customize the layout
    fig.update_layout(
        xaxis_title='Days',
        yaxis_title='',
        title_font_size=20,
        title_x=0.5,  # Centers the title
        template='plotly_white',  # Uses a white theme
        showlegend=False  # Hides the legend
    )

    fig.update_traces(textposition='outside')

    # Display the figure in Streamlit
    st.header('Average Length of Stay')
    st.plotly_chart(fig)

    # 3-2. 평균 입원 기간
    fig = px.histogram(
        data_frame=data,
        x='length_of_stay',
        nbins=30,
        title='Length of Stay Distribution',
        labels={'length_of_stay': 'Length of Stay (days)'},
        marginal='rug',  # Adds a rug plot
        opacity=0.75,  # Adjusts the opacity of the bars
        histnorm='',
    )

    # Add KDE line
    fig.add_trace(
        go.Scatter(
            x=np.linspace(data['length_of_stay'].min(), data['length_of_stay'].max(), 1000),
            y=gaussian_kde(data['length_of_stay'].dropna())(np.linspace(data['length_of_stay'].min(), data['length_of_stay'].max(), 1000)) * len(data),
            mode='lines',
            line=dict(color='royalblue'),
            name='KDE'
        )
    )

    # Customize the layout for a better appearance
    fig.update_layout(
        xaxis_title='Length of Stay (days)',
        yaxis_title='Frequency',
        title_font_size=20,
        title_x=0.5,  # Centers the title
        template='plotly_white',  # Uses a white theme
    )

    # Display the figure in Streamlit
    st.header('Length of Stay Distribution')
    st.plotly_chart(fig)

    # 4. 보험 유형별 입원 패턴
    st.header('Insurance Type and Length of Stay')
    insurance_stay_pattern = data.groupby('insurance')['length_of_stay'].mean().reset_index()

    # Create the bar chart
    fig = px.bar(
        insurance_stay_pattern,
        x='insurance',
        y='length_of_stay',
        title='Average Stay by Insurance Type',
        labels={'insurance': 'Insurance Type', 'length_of_stay': 'Average Length of Stay (days)'},
        color='insurance'
    )

    # Customize the layout for a better appearance
    fig.update_layout(
        yaxis_title='Average Length of Stay (days)',
        xaxis_title='Insurance Type',
        title_font_size=20,
        title_x=0.5,  # Centers the title
        template='plotly_white',  # Uses a white theme
    )

    # Display the figure in Streamlit
    st.plotly_chart(fig)

    # 5. 응급실 이용 시간
    average_er_stay = data['er_stay_length'].mean()

    # Create a horizontal bar chart
    fig = px.bar(
        x=[average_er_stay],
        y=["Average ER Stay Length"],
        orientation='h',
        title='Average ER Stay Length',
        labels={'x': 'Hours', 'y': ''},
        text=[f'{average_er_stay:.2f} hours']
    )

    # Customize the layout
    fig.update_layout(
        xaxis_title='Hours',
        yaxis_title='',
        title_font_size=20,
        title_x=0.5,  # Centers the title
        template='plotly_white',  # Uses a white theme
        showlegend=False  # Hides the legend
    )

    fig.update_traces(textposition='outside')

    # Display the figure in Streamlit
    st.header('Average ER Stay Length')
    st.plotly_chart(fig)

    # 앱을 실행하기 위해 streamlit run your_script_name.py 명령을 사용하세요.
