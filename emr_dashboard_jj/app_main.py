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
from utils.data_processing import split_read
from components.app_micro_individuals import component_indiviual
from components.app_macro import component_macro
from components.app_micro_analysis import component_analysis

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
def load_data_indiviual() :
    with open('./data/icu_data.json', 'r') as json_file:
        accum_json = json.load(json_file)
    return accum_json


@st.cache_data
def load_data_macro() :
    base_df = split_read('./data/icustays.csv.gz')

    condition = 'subject_id in ['
    for i in list(base_df['subject_id'].unique()[:1000]) :
        condition += str(i)
        condition += ', '
    condition += ']'

    tmp_data = split_read('./data/patients.csv.gz', condition = condition)

    tmp_data['anchor_age_dec'] = (tmp_data['anchor_age'] // 10) * 10
    
    data = split_read('./data/admissions.csv.gz', condition = condition)

    data['admittime'] = pd.to_datetime(data['admittime'])
    data['dischtime'] = pd.to_datetime(data['dischtime'])
    data['edregtime'] = pd.to_datetime(data['edregtime'])
    data['edouttime'] = pd.to_datetime(data['edouttime'])
    data['length_of_stay'] = (data['dischtime'] - data['admittime']).dt.total_seconds() / (24 * 3600)
    data['er_stay_length'] = (data['edouttime'] - data['edregtime']).dt.total_seconds() / 3600

    return [data, tmp_data]

@st.cache_data
def load_data_analysis() :
    with open('./data/accumulated_data.json', 'r') as json_file:
        accum_json = json.load(json_file)
    return accum_json

#######################
# Sidebar
with st.sidebar:
    st.title('🏥 EMR Dashboard')
    dict_data = load_data_indiviual()
    admin_data = load_data_macro()      ###macro
    analysis_data = load_data_analysis()

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


#######################
# Main Part

##Empty
main_placeholder = st.empty()
if not selected_id or not selected_hadm_id:
    main_placeholder.title('🏥Welcome to ICU EMR System')
    st.header('✅ You can check ...')
    st.markdown("- Basic Patients Information")
    st.markdown("- Planned Service")
    st.markdown("- Analyzed Results")

    
##Data Implemented
if selected_hadm_id:

    tab1, tab2, tab3 = st.tabs(["Admission", "Ward-Wide Statistics", "Individual"])

    with tab1 :
        component_indiviual(dict_data, selected_id, selected_hadm_id)

    with tab2:
        component_macro(admin_data)
        
    with tab3:
        component_analysis(analysis_data, selected_id)
