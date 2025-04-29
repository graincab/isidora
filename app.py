import streamlit as st
import pandas as pd
import numpy as np
from utils import IsidoraReport, clean_headers, summarize_data, prepare_sostojba_na_hv
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Конфигурација на страницата
st.set_page_config(
    page_title="ИСИДОРА Алатка за Известување",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Наслов и опис
st.title("ИСИДОРА Алатка за Известување")
st.markdown("""
    Оваа алатка овозможува анализа на податоци од ИСИДОРА системот за известување.
    Моментално поддржува анализа на пакетот ХВ (хартии од вредност).
""")

# Иницијализација на сесиски променливи
if 'isidora_report' not in st.session_state:
    st.session_state.isidora_report = IsidoraReport()

# --- Caching for performance ---
@st.cache_data
def load_and_clean_data(uploaded_file, selected_sheet):
    df = pd.read_excel(uploaded_file, sheet_name=selected_sheet)
    return clean_headers(df)

@st.cache_data
def prepare_sostojba_na_hv_cached(df):
    return prepare_sostojba_na_hv(df)

# Страничен панел за контроли
with st.sidebar:
    st.header("📊 Контроли")
    
    # Прикачување на датотека
    uploaded_file = st.file_uploader(
        "Прикачете Excel датотека",
        type=["xlsx"],
        help="Изберете Excel датотека со ИСИДОРА податоци"
    )

    if uploaded_file:
        try:
            # Вчитување на листови
            xls = pd.ExcelFile(uploaded_file)
            sheet_names = xls.sheet_names
            
            # Избор на лист
            selected_sheet = st.selectbox(
                "Изберете лист за анализа",
                sheet_names,
                help="Изберете кој лист од Excel датотеката сакате да го анализирате"
            )
            
            # Вчитување на податоци (cached)
            st.session_state.isidora_report.data = load_and_clean_data(uploaded_file, selected_sheet)
            st.success(f"Успешно вчитани податоци од листот {selected_sheet}")
            
            # Филтри
            st.subheader("🔍 Филтри")
            
            # Датумски филтер
            date_cols = [col for col in st.session_state.isidora_report.data.columns 
                        if 'датум' in str(col).lower()]
            if date_cols:
                try:
                    date_col = date_cols[0]
                    min_date = pd.to_datetime(st.session_state.isidora_report.data[date_col].min())
                    max_date = pd.to_datetime(st.session_state.isidora_report.data[date_col].max())
                    
                    date_range = st.date_input(
                        "Период на известување",
                        value=(min_date.date(), max_date.date()),
                        min_value=min_date.date(),
                        max_value=max_date.date()
                    )
                except Exception as e:
                    st.warning(f"Не може да се постави датумски филтер: {str(e)}")
                    date_range = None
            
            # Филтер за известувач
            reporter_col = next((col for col in st.session_state.isidora_report.data.columns 
                               if 'известувач' in str(col).lower()), None)
            if reporter_col:
                reporter_names = sorted(st.session_state.isidora_report.data[reporter_col].dropna().unique())
                selected_reporter = st.selectbox(
                    "Известувач",
                    ["Сите"] + reporter_names
                )
            
            # Филтер за тип на инструмент
            instrument_col = next((col for col in st.session_state.isidora_report.data.columns 
                                 if 'вид' in str(col).lower() and 'х.в.' in str(col).lower()), None)
            if instrument_col:
                instrument_types = sorted(st.session_state.isidora_report.data[instrument_col].dropna().unique())
                selected_instrument = st.selectbox(
                    "Тип на инструмент",
                    ["Сите"] + instrument_types
                )
            
            # Копче за извоз
            if st.button("📥 Извези во Excel"):
                try:
                    filtered_data = st.session_state.isidora_report.data.copy()
                    if 'date_range' in locals() and date_range and len(date_range) == 2:
                        filtered_data = st.session_state.isidora_report.filter_by_date(
                            pd.Timestamp(date_range[0]),
                            pd.Timestamp(date_range[1])
                        )
                    if 'selected_reporter' in locals() and selected_reporter != "Сите":
                        filtered_data = st.session_state.isidora_report.filter_by_reporter(selected_reporter)
                    
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    export_filename = f"isidora_извештај_{timestamp}.xlsx"
                    st.session_state.isidora_report.export_report(export_filename)
                    st.success(f"Извештајот е зачуван како {export_filename}")
                except Exception as e:
                    st.error(f"Грешка при извоз на податоците: {str(e)}")
            
        except Exception as e:
            st.error(f"Грешка при вчитување на податоците: {str(e)}")

# Главен панел за визуелизација
if hasattr(st.session_state, 'isidora_report') and st.session_state.isidora_report.data is not None:
    try:
        # Применување на филтри
        filtered_data = st.session_state.isidora_report.data.copy()
        
        # Креирање на две колони за визуелизации
        col1, col2 = st.columns(2)
        
        with col1:
            # Дистрибуција по тип на инструмент
            instrument_col = next((col for col in filtered_data.columns 
                                 if 'вид' in str(col).lower() and 'х.в.' in str(col).lower()), None)
            if instrument_col:
                st.subheader("📊 Дистрибуција по тип на инструмент")
                instrument_counts = filtered_data[instrument_col].value_counts()
                if not instrument_counts.empty:
                    fig = px.pie(
                        values=instrument_counts.values,
                        names=instrument_counts.index.astype(str),
                        title='Дистрибуција на хартии од вредност по тип'
                    )
                    st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Топ известувачи
            reporter_col = next((col for col in filtered_data.columns 
                               if 'известувач' in str(col).lower()), None)
            if reporter_col:
                st.subheader("📈 Топ известувачи")
                # Чистење и подготовка на податоците за известувачи
                reporter_data = filtered_data[reporter_col].dropna()
                if not reporter_data.empty:
                    reporter_counts = reporter_data.value_counts().head(10)
                    reporter_df = pd.DataFrame({
                        'Известувач': reporter_counts.index.astype(str),
                        'Број': reporter_counts.values
                    })
                    
                    fig = px.bar(
                        reporter_df,
                        x='Број',
                        y='Известувач',
                        orientation='h',
                        title='Топ 10 известувачи по број на инструменти'
                    )
                    fig.update_layout(
                        yaxis={'categoryorder': 'total ascending'},
                        showlegend=False
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Нема податоци за известувачи за приказ")
        
        # Табела со податоци
        st.subheader("📋 Детален преглед на податоци")
        
        # Избор на колони за приказ
        all_columns = list(filtered_data.columns)
        selected_columns = st.multiselect(
            "Изберете колони за приказ:",
            all_columns,
            default=all_columns[:5] if len(all_columns) > 5 else all_columns
        )
        
        if selected_columns:
            st.dataframe(
                filtered_data[selected_columns],
                height=400,
                use_container_width=True
            )
        
        # Сумарна статистика
        st.subheader("📊 Сумарна статистика")
        try:
            summary = summarize_data(filtered_data)
            
            # Прикажување на статистиката во три колони
            summary_col1, summary_col2, summary_col3 = st.columns(3)
            
            with summary_col1:
                st.metric("Вкупно записи", f"{summary.get('вкупно_записи', 0):,}")
            
            with summary_col2:
                st.metric("Број на известувачи", f"{summary.get('број_известувачи', 0):,}")
            
            with summary_col3:
                st.metric("Број на инструменти", f"{summary.get('број_инструменти', 0):,}")
        except Exception as e:
            st.error(f"Грешка при пресметување на статистиката: {str(e)}")

        # Прв Тест Пакет секција (само за листот 'Примени податоци')
        if 'selected_sheet' in locals() and selected_sheet.strip() == 'Примени податоци':
            if st.button("Прв Тест Пакет"):
                st.subheader("📦 Прв Тест Пакет (Табела)")

                try:
                    result = prepare_sostojba_na_hv(filtered_data)
                    calculated_sum = f"{result['sum_in_denars']:,} денари"
                    used_types = ", ".join(result['used_types'])
                except Exception as e:
                    calculated_sum = used_types = "❌ Error"
                    result = {"filtered_df": pd.DataFrame()}

                placeholder = "⏳ Yet"

                # Build the main table
                table = pd.DataFrame({
                    "Состојба на х.в на почеток на период (главнина)": [calculated_sum, calculated_sum, used_types],
                    "Нето трансакции": [placeholder, placeholder, placeholder],
                    "Ценовни промени": [placeholder, placeholder, placeholder],
                    "Курсни разлики": [placeholder, placeholder, placeholder],
                    "Останати промени": [placeholder, placeholder, placeholder],
                    "Состојба на х.в на крај на период (главнина)": [placeholder, placeholder, placeholder],
                }, index=["Rule", "Износ во денари", "Вид на износ"])

                st.table(table)

                # Verification table: Show filtered rows
                st.subheader("🔎 Филтрирани редови за проверка (DRVR, DSK, PRM, POBJ)")
                st.dataframe(result["filtered_df"])

                # Optional: add a count sanity check
                st.success(f"✅ Филтрирани {len(result['filtered_df'])} редови вкупно за пресметка.")

                # Optional: breakdown by type
                st.subheader("📈 Поделба по Вид на Износ")
                breakdown = result["filtered_df"].groupby("Вид на износ").agg(
                    Број_на_редови=("Вид на износ", "count"),
                    Вкупно_износ_во_денари=("Износ во денари", "sum")
                ).reset_index()
                breakdown["Вкупно_износ_во_денари"] = breakdown["Вкупно_износ_во_денари"].map('{:,.0f} денари'.format)
                st.dataframe(breakdown)
    
    except Exception as e:
        st.error(f"Грешка при прикажување на податоците: {str(e)}")
