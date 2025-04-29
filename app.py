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
        # --- Debug: Show columns to user (after all cleaning) ---
        st.sidebar.write('🛠️ Колони во табелата:', df.columns.tolist())
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

# --- Filters for 'Примени податоци ' ---
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

# --- Apply filters ---
filtered_df = df.copy()
if date_range and len(date_range) == 2 and date_cols:
    filtered_df = filtered_df[(pd.to_datetime(filtered_df[date_col]) >= pd.Timestamp(date_range[0])) &
                             (pd.to_datetime(filtered_df[date_col]) <= pd.Timestamp(date_range[1]))]
if selected_reporter and selected_reporter != "Сите" and reporter_col:
    filtered_df = filtered_df[filtered_df[reporter_col] == selected_reporter]
if selected_instrument and selected_instrument != "Сите" and instrument_col:
    filtered_df = filtered_df[filtered_df[instrument_col] == selected_instrument]

# --- Tabs for Dashboard ---
tab_summary, tab_charts, tab_table, tab_debug = st.tabs([
    "📊 Summary", "📈 Charts", "📋 Table", "🐞 Debug"
])

with tab_summary:
    st.subheader("📊 Клучни Метрики")
    try:
        result = prepare_sostojba_na_hv(filtered_df)
        sum_in_denars = int(result["sum_in_denars"])
        filtered_count = len(result["filtered_df"])
        st.metric("💰 Вкупен Износ (денари)", f"{sum_in_denars}")
        st.metric("📄 Број на Филтрирани Редови", f"{filtered_count}")
    except Exception as e:
        st.error(f"Грешка при пресметка: {str(e)}")

with tab_charts:
    st.subheader("📈 Визуелизации")
    try:
        # Animated horizontal bar chart by 'Вид на износ'
        if "Вид на износ" in filtered_df.columns and "Износ во денари" in filtered_df.columns:
            chart_df = filtered_df.copy()
            chart_df["Износ во денари"] = pd.to_numeric(chart_df["Износ во денари"], errors="coerce")
            chart_df = chart_df[chart_df["Износ во денари"].notna()]
            fig = px.bar(
                chart_df,
                x="Износ во денари",
                y="Вид на износ",
                orientation="h",
                color="Вид на износ",
                color_discrete_sequence=px.colors.qualitative.Safe,
                title="Анимиран Хоризонтален Бар Чарт",
                animation_frame=None
            )
            st.plotly_chart(fig, use_container_width=True)
        # Pie chart by instrument type
        if instrument_col:
            inst_counts = filtered_df[instrument_col].value_counts()
            if not inst_counts.empty:
                fig2 = px.pie(
                    values=inst_counts.values,
                    names=inst_counts.index.astype(str),
                    title='Дистрибуција на хартии од вредност по тип'
                )
                st.plotly_chart(fig2, use_container_width=True)
    except Exception as e:
        st.error(f"Грешка при визуелизација: {str(e)}")

with tab_table:
    st.subheader("📋 Преглед на Прв Тест Пакет")
    try:
        result = prepare_sostojba_na_hv(filtered_df)
        calculated_sum = f"{result['sum_in_denars']} денари"
        used_types = ", ".join(result['used_types'])
        placeholder = "⏳ Yet"
        table = pd.DataFrame({
            "Состојба на х.в на почеток на период (главнина)": [calculated_sum, calculated_sum, used_types],
            "Нето трансакции": [placeholder, placeholder, placeholder],
            "Ценовни промени": [placeholder, placeholder, placeholder],
            "Курсни разлики": [placeholder, placeholder, placeholder],
            "Останати промени": [placeholder, placeholder, placeholder],
            "Состојба на х.в на крај на период (главнина)": [placeholder, placeholder, placeholder],
        }, index=["Rule", "Износ во денари", "Вид на износ"])
        st.table(table)
        st.subheader("🔎 Филтрирани редови за проверка (DRVR, DSK, PRM, POBJ)")
        st.dataframe(result["filtered_df"], use_container_width=True, height=400)
        st.success(f"✅ Филтрирани {len(result['filtered_df'])} редови вкупно за пресметка.")
        # Breakdown by type
        st.subheader("📈 Поделба по Вид на Износ")
        breakdown = result["filtered_df"].groupby("Вид на износ").agg(
            Број_на_редови=("Вид на износ", "count"),
            Вкупно_износ_во_денари=("Износ во денари", "sum")
        ).reset_index()
        breakdown["Вкупно_износ_во_денари"] = breakdown["Вкупно_износ_во_денари"].map('{:,.0f} денари'.format)
        st.dataframe(breakdown, use_container_width=True)
    except Exception as e:
        st.error(f"Грешка при табеларен приказ: {str(e)}")

with tab_debug:
    st.subheader("🐞 DRVR Debugging")
    try:
        result = prepare_sostojba_na_hv(filtered_df)
        drvr_df = result["filtered_df"][result["filtered_df"]["Вид на износ"] == "DRVR"]
        st.write("Non-numeric or NaN rows in DRVR:", drvr_df[drvr_df["Износ во денари"].isna()])
        st.write("Sample DRVR values:", drvr_df["Износ во денари"].head(20))
        st.write("DRVR min/max:", drvr_df["Износ во денари"].min(), drvr_df["Износ во денари"].max())
        st.write("DRVR duplicates:", drvr_df.duplicated().sum())
    except Exception as e:
        st.error(f"Грешка при DRVR debugging: {str(e)}")
