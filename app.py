import streamlit as st
import pandas as pd
from utils import clean_headers
from data_processing import process_first_packet

# --- Streamlit App Config ---
st.set_page_config(
    page_title="ИСИДОРА Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Helper: Simple initial load ---
@st.cache_data
def load_data(uploaded_file, selected_sheet):
    return pd.read_excel(uploaded_file, sheet_name=selected_sheet)

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
        default_sheet = next((s for s in sheet_names if s.strip().lower() == "примени податоци".lower()), sheet_names[0])
        selected_sheet = st.sidebar.selectbox(
            "Изберете лист за анализа",
            sheet_names,
            index=sheet_names.index(default_sheet)
        )
        df = load_data(uploaded_file, selected_sheet)
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

# Show raw data initially
st.subheader("📋 Податоци")
st.dataframe(df, use_container_width=True, height=400)

# --- First Packet Button ---
if st.button("First Packet"):
    try:
        processed_df = process_first_packet(uploaded_file)
        if processed_df is not None:
            st.subheader("📋 First Packet")
            st.dataframe(processed_df, use_container_width=True, height=600)
    except Exception as e:
        st.error(f"Error processing First Packet: {str(e)}")
