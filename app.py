import streamlit as st
import pandas as pd
import numpy as np
from utils import IsidoraReport, clean_headers, summarize_data, prepare_sostojba_na_hv
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import re

# --- Streamlit App Config ---
st.set_page_config(
    page_title="ИСИДОРА Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Helper: Load and clean data ---
@st.cache_data
def load_and_clean_data(uploaded_file, selected_sheet):
    df = pd.read_excel(uploaded_file, sheet_name=selected_sheet)
    df = clean_headers(df)
    # --- Robust normalization: lowercase, remove all spaces, unify naming ---
    def normalize_col(col):
        return re.sub(r'[^а-яa-z0-9]', '', col.lower().replace(' ', ''))
    norm_map = {normalize_col(col): col for col in df.columns}
    # Map for required columns
    required_norms = {
        'виднаизнос': None,
        'износвденари': None
    }
    for norm, orig in norm_map.items():
        if 'виднаизнос' in norm:
            required_norms['виднаизнос'] = orig
        if 'износвденари' in norm:
            required_norms['износвденари'] = orig
    # Rename columns in df for internal use
    rename_dict = {}
    if required_norms['виднаизнос']:
        rename_dict[required_norms['виднаизнос']] = 'Вид на износ'
    if required_norms['износвденари']:
        rename_dict[required_norms['износвденари']] = 'Износ во денари'
    df = df.rename(columns=rename_dict)
    return df

# --- Sidebar: Upload and Sheet Selection ---
st.sidebar.header("📊 Податоци")

uploaded_file = st.sidebar.file_uploader(
    "Прикачете Excel датотека",
    type=["xlsx"],
    help="Изберете Excel датотека со ИСИДОРА податоци"
)

selected_sheet = None
sheet_names = []
data_loaded = False

df = None
if uploaded_file:
    try:
        xls = pd.ExcelFile(uploaded_file)
        sheet_names = xls.sheet_names
        # Auto-select 'Примени податоци ' if present, else first sheet
        default_sheet = next((s for s in sheet_names if s.strip().lower() == "примени податоци".lower()), sheet_names[0])
        selected_sheet = st.sidebar.selectbox(
            "Изберете лист за анализа",
            sheet_names,
            index=sheet_names.index(default_sheet)
        )
        df = load_and_clean_data(uploaded_file, selected_sheet)
        data_loaded = True
        st.sidebar.success(f"Успешно вчитани податоци од листот: {selected_sheet}")
    except Exception as e:
        st.sidebar.error(f"Грешка при вчитување: {str(e)}")

# --- Main Area ---
st.title("ИСИДОРА Dashboard")
st.markdown("""
Оваа алатка овозможува анализа на податоци од ИСИДОРА системот за известување. 
**'Примени податоци '** е главниот лист за анализа. За другите листови, достапен е само табеларен приказ.
""")

if not data_loaded:
    st.info("📂 Прикачете .xlsx датотека за да започнете.")
    st.stop()

# --- If not 'Примени податоци ', show only table ---
if selected_sheet.strip().lower() != "примени податоци":
    st.subheader(f"Табеларен приказ за листот: {selected_sheet}")
    st.dataframe(df, use_container_width=True, height=500)
    st.info("За напредна анализа, изберете 'Примени податоци '")
    st.stop()

# --- Filters and Table for 'Прв Голем Пакет' ---
st.header("Прв Голем Пакет")
with st.expander("🔍 Филтри", expanded=True):
    # Date filter
    date_cols = [col for col in df.columns if 'датум' in str(col).lower()]
    date_range = None
    if date_cols:
        date_col = date_cols[0]
        try:
            min_date = pd.to_datetime(df[date_col].min())
            max_date = pd.to_datetime(df[date_col].max())
            date_range = st.date_input(
                "Период на известување",
                value=(min_date.date(), max_date.date()),
                min_value=min_date.date(),
                max_value=max_date.date()
            )
        except Exception as e:
            st.warning(f"Не може да се постави датумски филтер: {str(e)}")
            date_range = None
    # Reporter filter
    reporter_col = next((col for col in df.columns if 'известувач' in str(col).lower()), None)
    selected_reporter = None
    if reporter_col:
        reporter_names = sorted(df[reporter_col].dropna().unique())
        selected_reporter = st.selectbox(
            "Известувач",
            ["Сите"] + reporter_names
        )
    # Instrument type filter
    instrument_col = next((col for col in df.columns if 'вид' in str(col).lower() and 'х.в.' in str(col).lower()), None)
    selected_instrument = None
    if instrument_col:
        instrument_types = sorted(df[instrument_col].dropna().unique())
        selected_instrument = st.selectbox(
            "Тип на инструмент",
            ["Сите"] + instrument_types
        )
    # Paket filter
    paket_col = next((col for col in df.columns if 'пакет' in str(col).lower()), None)
    paket_types = sorted(df[paket_col].dropna().unique())
    selected_paket = st.multiselect("Пакет (избери еден или повеќе)", paket_types)
    # Средства/Обврска (A/L) rule filter
    sredstva_options = ["A", "L"]
    selected_sredstva = st.multiselect("Средства/Обврска (A/L)", sredstva_options)

# --- Apply filters ---
filtered_df = df.copy()
if date_range and len(date_range) == 2 and date_cols:
    filtered_df = filtered_df[(pd.to_datetime(filtered_df[date_col]) >= pd.Timestamp(date_range[0])) &
                             (pd.to_datetime(filtered_df[date_col]) <= pd.Timestamp(date_range[1]))]
if selected_reporter and selected_reporter != "Сите" and reporter_col:
    filtered_df = filtered_df[filtered_df[reporter_col] == selected_reporter]
if selected_instrument and selected_instrument != "Сите" and instrument_col:
    filtered_df = filtered_df[filtered_df[instrument_col] == selected_instrument]
if selected_paket:
    filtered_df = filtered_df[filtered_df[paket_col].isin(selected_paket)]
if selected_sredstva:
    filtered_df = filtered_df[
        filtered_df["Позиција"].astype(str).apply(
            lambda x: any(letter in x for letter in selected_sredstva)
        )
    ]

# --- Код (A/L) logic ---
def extract_code_from_position(pos):
    codes = []
    if pd.notna(pos):
        if "A" in str(pos):
            codes.append("A")
        if "L" in str(pos):
            codes.append("L")
    return ", ".join(codes) if codes else "-"
if "Позиција" in filtered_df.columns:
    filtered_df["Код (A/L)"] = filtered_df["Позиција"].apply(extract_code_from_position)

# --- Show the new clean table ---
st.subheader("📋 Табела: Прв Голем Пакет")

# Show active filters as hashtags
active_filters = []
if selected_paket:
    active_filters += [f"#{val}" for val in selected_paket]
if selected_sredstva:
    active_filters += [f"#{val}" for val in selected_sredstva]
if active_filters:
    st.markdown("**Активни филтри:** " + " ".join(active_filters))

st.dataframe(filtered_df, use_container_width=True, height=600)
