import streamlit as st
import pandas as pd
import numpy as np
from utils import IsidoraReport, clean_headers, summarize_data
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
        # Вчитување на листови
        xls = pd.ExcelFile(uploaded_file)
        sheet_names = xls.sheet_names
        
        # Избор на лист
        selected_sheet = st.selectbox(
            "Изберете лист за анализа",
            sheet_names,
            help="Изберете кој лист од Excel датотеката сакате да го анализирате"
        )
        
        try:
            # Вчитување на податоци
            st.session_state.isidora_report.load_data(uploaded_file, selected_sheet)
            st.success(f"Успешно вчитани податоци од листот {selected_sheet}")
            
            # Филтри
            st.subheader("🔍 Филтри")
            
            # Датумски филтер
            if any('датум' in col.lower() for col in st.session_state.isidora_report.data.columns):
                date_col = next(col for col in st.session_state.isidora_report.data.columns if 'датум' in col.lower())
                min_date = st.session_state.isidora_report.data[date_col].min()
                max_date = st.session_state.isidora_report.data[date_col].max()
                
                date_range = st.date_input(
                    "Период на известување",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date
                )
            
            # Филтер за известувач
            reporter_names = st.session_state.isidora_report.data['Назив на известувач'].unique() if 'Назив на известувач' in st.session_state.isidora_report.data.columns else []
            selected_reporter = st.selectbox(
                "Известувач",
                ["Сите"] + list(reporter_names)
            )
            
            # Филтер за тип на инструмент
            if 'Вид на х.в. (ЕСА2010)' in st.session_state.isidora_report.data.columns:
                instrument_types = st.session_state.isidora_report.data['Вид на х.в. (ЕСА2010)'].unique()
                selected_instrument = st.selectbox(
                    "Тип на инструмент",
                    ["Сите"] + list(instrument_types)
                )
            
            # Копче за извоз
            if st.button("📥 Извези во Excel"):
                filtered_data = st.session_state.isidora_report.data
                if len(date_range) == 2:
                    filtered_data = st.session_state.isidora_report.filter_by_date(date_range[0], date_range[1])
                if selected_reporter != "Сите":
                    filtered_data = st.session_state.isidora_report.filter_by_reporter(selected_reporter)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                export_filename = f"isidora_извештај_{timestamp}.xlsx"
                st.session_state.isidora_report.export_report(export_filename)
                st.success(f"Извештајот е зачуван како {export_filename}")
            
        except Exception as e:
            st.error(f"Грешка при вчитување на податоците: {str(e)}")

# Главен панел за визуелизација
if hasattr(st.session_state, 'isidora_report') and st.session_state.isidora_report.data is not None:
    # Применување на филтри
    filtered_data = st.session_state.isidora_report.data
    
    # Креирање на две колони за визуелизации
    col1, col2 = st.columns(2)
    
    with col1:
        # Дистрибуција по тип на инструмент
        if 'Вид на х.в. (ЕСА2010)' in filtered_data.columns:
            st.subheader("📊 Дистрибуција по тип на инструмент")
            instrument_counts = filtered_data['Вид на х.в. (ЕСА2010)'].value_counts()
            fig = px.pie(
                values=instrument_counts.values,
                names=instrument_counts.index,
                title='Дистрибуција на хартии од вредност по тип'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Топ известувачи
        if 'Назив на известувач' in filtered_data.columns:
            st.subheader("📈 Топ известувачи")
            reporter_counts = filtered_data['Назив на известувач'].value_counts().head(10)
            fig = px.bar(
                x=reporter_counts.values,
                y=reporter_counts.index,
                orientation='h',
                title='Топ 10 известувачи по број на инструменти'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Табела со податоци
    st.subheader("📋 Детален преглед на податоци")
    
    # Избор на колони за приказ
    all_columns = list(filtered_data.columns)
    selected_columns = st.multiselect(
        "Изберете колони за приказ:",
        all_columns,
        default=all_columns[:5]
    )
    
    if selected_columns:
        st.dataframe(
            filtered_data[selected_columns],
            height=400,
            use_container_width=True
        )
    
    # Сумарна статистика
    st.subheader("📊 Сумарна статистика")
    summary = summarize_data(filtered_data)
    
    # Прикажување на статистиката во три колони
    summary_col1, summary_col2, summary_col3 = st.columns(3)
    
    with summary_col1:
        st.metric("Вкупно записи", f"{summary['вкупно_записи']:,}")
    
    with summary_col2:
        st.metric("Број на известувачи", f"{summary['број_известувачи']:,}")
    
    with summary_col3:
        st.metric("Број на инструменти", f"{summary['број_инструменти']:,}")
