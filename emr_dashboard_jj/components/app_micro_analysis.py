#######################
# Import libraries
import streamlit as st
# from streamlit_timeline import timeline
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


def plot_prescriptions(analysis_data, subject_id):
    patient_data = pd.DataFrame(analysis_data[subject_id]['prescriptions'])
    patient_data['date'] = pd.to_datetime(patient_data['date'])
    patient_data['hour'] = pd.to_numeric(patient_data['hour'])
    
    fig = px.scatter(patient_data, x='date', y='hour',
                     size='formulary_drug_cd',
                     color='formulary_drug_cd',
                     hover_data=['drug_info'],
                     labels={
                         "date": "Date",
                         "hour": "Hour of Day",
                         "formulary_drug_cd": "Total Drugs Administered",
                         "drug_info": "Drugs and Routes Administered"
                     },
                     title=f'Grouped Drug Administration Details for Subject ID {subject_id}')

    fig.update_layout(
        xaxis_title='Date',
        yaxis_title='Hour of Day',
        legend_title='Drug Details',
        legend=dict(orientation="h", xanchor="center", x=0.5, yanchor="bottom", y=-0.3)
    )

    return fig

# 감염 분석 플롯 생성
def plot_infection_analysis(analysis_data, subject_id):
    micro_data = pd.DataFrame(analysis_data[subject_id]['detailed_infection_analysis'])
    micro_data['chartdate'] = pd.to_datetime(micro_data['chartdate'])

    fig = px.scatter(micro_data, x='chartdate', y='org_name', color='interpretation',
                     title=f'Detailed Infection Analysis for Subject ID {subject_id}',
                     labels={'chartdate': 'Date of Sample', 'org_name': 'Organism', 'interpretation': 'Test Result'},
                     hover_data=['spec_type_desc', 'test_name', 'interpretation', 'quantity', 'comments'])

    fig.update_traces(marker=dict(size=15, line=dict(width=1, color='DarkSlateGrey')))
    return fig

# 약물 투여 기록 플롯 생성
def plot_medication_administration(analysis_data, subject_id):
    combined_data = pd.DataFrame(analysis_data[subject_id]['medication_administration_details'])
    combined_data['charttime'] = pd.to_datetime(combined_data['charttime'])
    
    fig = px.scatter(combined_data, x='charttime', y='medication', color='dose_given',
                     size='dose_given',
                     title=f'Medication Administration Details for Subject ID {subject_id}',
                     labels={'charttime': 'Time of Administration', 'medication': 'Medication', 'dose_given': 'Dose Given'},
                     hover_data=['administration_type', 'route', 'product_description', 'infusion_rate'])

    fig.update_traces(marker=dict(line=dict(width=1, color='DarkSlateGrey')))
    return fig

# ICU 투입 및 배출 이벤트 플롯 생성
def plot_icu_events(analysis_data, subject_id):
    combined_data = pd.DataFrame(analysis_data[subject_id]['icu_input_output_events'])
    combined_data['charttime'] = pd.to_datetime(combined_data['charttime'])

    fig = px.scatter(combined_data, x='charttime', y='category', color='amount',
                     size='amount',
                     title=f'ICU Input and Output Events for Subject ID {subject_id}',
                     labels={'charttime': 'Time', 'amount': 'Amount', 'category': 'Category', 'event': 'Event Type'},
                     hover_data=['itemid', 'label', 'event'])

    fig.update_traces(marker=dict(line=dict(width=1, color='DarkSlateGrey')))
    return fig



def component_analysis(analysis_data, selected_id):
    st.title('Patient Data Visualization')

    # 처방 정보 플롯
    st.markdown('### Grouped Drug Administration Details')
    prescriptions_fig = plot_prescriptions(analysis_data, selected_id)
    st.plotly_chart(prescriptions_fig)

    # 감염 분석 플롯
    st.markdown('### Detailed Infection Analysis')
    infection_fig = plot_infection_analysis(analysis_data, selected_id)
    st.plotly_chart(infection_fig)

    # 약물 투여 기록 플롯
    st.markdown('### Medication Administration Details')
    medication_fig = plot_medication_administration(analysis_data, selected_id)
    st.plotly_chart(medication_fig)

    # ICU 투입 및 배출 이벤트 플롯
    st.markdown('### ICU Input and Output Events')
    icu_fig = plot_icu_events(analysis_data, selected_id)
    st.plotly_chart(icu_fig)
