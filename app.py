import streamlit as st
import pandas as pd
import plotly.express as px
from utils import IsidoraReport, clean_headers, prepare_sostojba_na_hv
from datetime import datetime

st.set_page_config(
    page_title="Примени Податоци - ИСИДОРА",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("ИСИДОРА - Примени Податоци")

# Upload and load data
with st.sidebar:
    st.header("🚀 Прикачи податоци")
    uploaded_file = st.file_uploader("Прикачете Excel (.xlsx)", type=["xlsx"])

if 'isidora_report' not in st.session_state:
    st.session_state.isidora_report = IsidoraReport()

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)
    sheet_names = xls.sheet_names
    selected_sheet = st.selectbox("Одбери лист", sheet_names)

    df = pd.read_excel(uploaded_file, sheet_name=selected_sheet)
    df = clean_headers(df)
    st.session_state.isidora_report.data = df

    st.success("✅ Податоците се вчитани успешно!")

    # Filters
    with st.expander("🎯 Филтри"):
        date_cols = [col for col in df.columns if 'датум' in str(col).lower()]
        reporter_col = next((col for col in df.columns if 'известувач' in str(col).lower()), None)
        instrument_col = next((col for col in df.columns if 'вид' in str(col).lower() and 'х.в.' in str(col).lower()), None)

        if date_cols:
            min_date = pd.to_datetime(df[date_cols[0]].min())
            max_date = pd.to_datetime(df[date_cols[0]].max())
            date_range = st.date_input("Избери период", (min_date, max_date))

        if reporter_col:
            reporter_filter = st.multiselect("Филтрирај по Известувач", df[reporter_col].dropna().unique())

        if instrument_col:
            instrument_filter = st.multiselect("Филтрирај по Тип на инструмент", df[instrument_col].dropna().unique())

    # Apply filters
    filtered_df = df.copy()
    if date_cols and date_range:
        filtered_df = filtered_df[(pd.to_datetime(filtered_df[date_cols[0]]) >= pd.to_datetime(date_range[0])) &
                                  (pd.to_datetime(filtered_df[date_cols[0]]) <= pd.to_datetime(date_range[1]))]
    if reporter_col and reporter_filter:
        filtered_df = filtered_df[filtered_df[reporter_col].isin(reporter_filter)]
    if instrument_col and instrument_filter:
        filtered_df = filtered_df[filtered_df[instrument_col].isin(instrument_filter)]

    # Main Analysis Section
    st.subheader("📊 Главен Преглед на Примени Податоци")

    # Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Број на Записи", f"{len(filtered_df):,}")
    if reporter_col:
        col2.metric("Број на Известувачи", f"{filtered_df[reporter_col].nunique():,}")
    if instrument_col:
        col3.metric("Број на Типови на Инструменти", f"{filtered_df[instrument_col].nunique():,}")

    # Chart 1 - Distribution by Instrument Type
    if instrument_col:
        with st.expander("📈 Дистрибуција по Тип на Инструмент"):
            fig = px.pie(filtered_df, names=instrument_col, title="Типови на Инструменти")
            st.plotly_chart(fig, use_container_width=True)

    # Chart 2 - Top Reporters
    if reporter_col:
        with st.expander("🏆 Топ Известувачи"):
            reporter_counts = filtered_df[reporter_col].value_counts().head(10)
            fig = px.bar(x=reporter_counts.values, y=reporter_counts.index, orientation='h', labels={'x': 'Број', 'y': 'Известувач'})
            st.plotly_chart(fig, use_container_width=True)

    # Data Table
    st.subheader("🗂️ Детална Табела")
    st.dataframe(filtered_df, use_container_width=True, height=500)

    # Export Button
    st.download_button("📥 Превземи ја Табелата", data=filtered_df.to_csv(index=False).encode('utf-8-sig'), file_name="primeni_podatoci.csv")

    # Advanced Calculation: Прв Тест Пакет
    if selected_sheet.strip() == 'Примени податоци':
        st.subheader("📦 Пресметка на Прв Тест Пакет")
        result = prepare_sostojba_na_hv(filtered_df)
        st.metric("Сума на Главнина", f"{result['sum_in_denars']:,.0f} денари")
        st.write("Користени типови на износ:", ", ".join(result['used_types']))
        st.dataframe(result['filtered_df'], use_container_width=True)

else:
    st.info("📄 Прикачете Excel датотека за почеток.")