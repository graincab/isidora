import streamlit as st
import pandas as pd
import numpy as np
from utils import clean_headers
import plotly.express as px
import plotly.graph_objects as go

# Зголемување на ограничувањето на големината на датотеката на 1000MB (1GB)
st.set_page_config(page_title="ИСИДОРА Алатка за Известување", layout="wide")
st.title("ИСИДОРА Алатка за Известување")

def analyze_relationships(df_main, df_reporters, df_securities, df_received):
    # Анализа на врски и шаблони на податоци
    summary = {}
    
    # Проверка на врските на известувачите
    reporters_in_main = set(df_main['Матичен број на известувач'].unique())
    reporters_in_list = set(df_reporters['матичен број'].unique())
    summary['reporters_match'] = len(reporters_in_main.intersection(reporters_in_list))
    
    # Анализа на видовите на хартии од вредност
    securities_types = df_main['Вид на х.в. (ЕСА2010)'].unique()
    valid_types = df_securities['Вид на ХВ'].unique()
    summary['securities_types'] = len(set(securities_types).intersection(set(valid_types)))
    
    return summary

def load_and_analyze_data(excel_file):
    # Иницијализација на променливи
    main_data = None
    reporters = None
    securities = None
    received = None
    
    # Прво, да видиме кои листови се достапни во датотеката
    xls = pd.ExcelFile(excel_file)
    available_sheets = xls.sheet_names
    st.write("Достапни листови во датотеката:", available_sheets)
    
    # Вчитување на секој лист ако е достапен
    if "БАЗА ИСИДОРА ХВ" in available_sheets:
        main_data = pd.read_excel(excel_file, sheet_name="БАЗА ИСИДОРА ХВ", header=5)
        st.write("Успешно вчитан БАЗА ИСИДОРА ХВ")
    
    if "листа известувачи" in available_sheets:
        reporters = pd.read_excel(excel_file, sheet_name="листа известувачи", header=0)
        st.write("Успешно вчитана листа известувачи")
    
    if "Вид на ХВ" in available_sheets:
        securities = pd.read_excel(excel_file, sheet_name="Вид на ХВ", header=0)
        st.write("Успешно вчитан Вид на ХВ")
    
    received_sheet = next((s for s in available_sheets if s.strip() == "Примени податоци"), None)
    if received_sheet:
        received = pd.read_excel(excel_file, sheet_name=received_sheet, header=0)
        st.write(f"Успешно вчитани {received_sheet}")
    
    # Анализа на врските само ако сите потребни листови се присутни
    if all([main_data is not None, reporters is not None, securities is not None, received is not None]):
        relationships = analyze_relationships(main_data, reporters, securities, received)
        
        # Прикажување на збогатени главни податоци
        enriched_data = main_data.merge(
            reporters,
            left_on='Матичен број на известувач',
            right_on='матичен број',
            how='left'
        )
        
        return enriched_data, relationships
    else:
        missing_sheets = []
        if main_data is None: missing_sheets.append("БАЗА ИСИДОРА ХВ")
        if reporters is None: missing_sheets.append("листа известувачи")
        if securities is None: missing_sheets.append("Вид на ХВ")
        if received is None: missing_sheets.append("Примени податоци")
        st.error(f"Недостасуваат листови: {', '.join(missing_sheets)}")
        return None, None

def load_sheet_with_correct_headers(excel_file, sheet_name):
    if sheet_name == "БАЗА ИСИДОРА ХВ":
        df = pd.read_excel(excel_file, sheet_name=sheet_name, header=5)
    elif sheet_name == "Примени податоци":
        df = pd.read_excel(excel_file, sheet_name=sheet_name, header=0)
    elif sheet_name in ["Вид на ХВ", "листа известувачи"]:
        df = pd.read_excel(excel_file, sheet_name=sheet_name, header=0)
    elif sheet_name == "курсни разлики":
        df = pd.read_excel(excel_file, sheet_name=sheet_name)
    else:
        df = pd.read_excel(excel_file, sheet_name=sheet_name)
    return df

def analyze_primeni_podatoci(df):
    st.header("Анализа на Примени податоци")
    
    # Креирање на странична лента за филтри
    st.sidebar.header("📊 Филтри")
    
    # Прикажување на сите колони и овозможување на корисникот да избере кои да ги филтрира
    all_columns = list(df.columns)
    selected_columns = st.sidebar.multiselect(
        "Изберете колони за филтрирање:",
        all_columns,
        default=[]
    )
    
    # Креирање на динамички филтри врз основа на избраните колони
    filtered_df = df.copy()
    for column in selected_columns:
        if pd.api.types.is_datetime64_any_dtype(df[column]):
            # Филтер за датумски опсег
            min_date = df[column].min()
            max_date = df[column].max()
            date_range = st.sidebar.date_input(
                f"Филтрирај {column}",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
            if len(date_range) == 2:
                filtered_df = filtered_df[
                    (filtered_df[column].dt.date >= date_range[0]) &
                    (filtered_df[column].dt.date <= date_range[1])
                ]
        elif pd.api.types.is_numeric_dtype(df[column]):
            # Филтер за нумерички опсег
            min_val = float(df[column].min())
            max_val = float(df[column].max())
            value_range = st.sidebar.slider(
                f"Филтрирај {column}",
                min_val, max_val,
                (min_val, max_val)
            )
            filtered_df = filtered_df[
                (filtered_df[column] >= value_range[0]) &
                (filtered_df[column] <= value_range[1])
            ]
        else:
            # Категориски филтер
            unique_values = sorted(df[column].unique())
            selected_values = st.sidebar.multiselect(
                f"Филтрирај {column}",
                unique_values,
                default=list(unique_values)
            )
            filtered_df = filtered_df[filtered_df[column].isin(selected_values)]
    
    # Функционалност за пребарување
    st.sidebar.header("🔍 Пребарување")
    search_term = st.sidebar.text_input("Пребарувај во сите колони:")
    if search_term:
        mask = np.column_stack([filtered_df[col].astype(str).str.contains(search_term, case=False, na=False) 
                              for col in filtered_df.columns])
        filtered_df = filtered_df[mask.any(axis=1)]
    
    # Прикажување на бројот на филтрирани резултати
    st.sidebar.metric("Филтрирани редови", f"{len(filtered_df):,}")
    
    # Креирање на две колони за визуелизации
    col1, col2 = st.columns(2)
    
    with col1:
        # Дистрибуција на статус
        status_cols = [col for col in filtered_df.columns if 'статус' in col.lower()]
        if status_cols:
            status_col = status_cols[0]
            st.subheader("📊 Дистрибуција на статус")
            status_counts = filtered_df[status_col].value_counts()
            fig = px.pie(values=status_counts.values, 
                        names=status_counts.index,
                        title='Дистрибуција на статус на поднесување',
                        color_discrete_sequence=px.colors.qualitative.Set3)
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Активност на известувачи
        reporter_cols = [col for col in filtered_df.columns if 'назив' in col.lower()]
        if reporter_cols:
            st.subheader("📈 Активност на известувачи")
            reporter_col = reporter_cols[0]
            reporter_data = filtered_df[reporter_col].value_counts().reset_index()
            reporter_data.columns = ['Известувач', 'Број']
            fig = px.bar(reporter_data.head(10), 
                        x='Број',
                        y='Известувач',
                        orientation='h',
                        title='Топ 10 најактивни известувачи')
            st.plotly_chart(fig, use_container_width=True)
    
    # Временска анализа
    date_cols = [col for col in filtered_df.columns if 'датум' in col.lower()]
    if date_cols:
        st.subheader("📅 Временска линија на поднесувања")
        date_col = date_cols[0]
        timeline = filtered_df.groupby(date_col).size().reset_index(name='Број')
        fig = px.line(timeline, 
                     x=date_col, 
                     y='Број',
                     title='Поднесувања низ време')
        fig.update_traces(line_color='#2E86C1')
        st.plotly_chart(fig, use_container_width=True)
    
    # Табела со податоци со сортирање и филтрирање
    st.subheader("📋 Детален преглед на податоци")
    
    # Избирач на колони за табелата
    selected_table_columns = st.multiselect(
        "Изберете колони за приказ:",
        all_columns,
        default=all_columns[:5]
    )
    
    # Прикажување на филтрираната табела
    if selected_table_columns:
        st.dataframe(
            filtered_df[selected_table_columns],
            height=400,
            use_container_width=True
        )

def load_and_display_sheet(excel_file, sheet_name):
    if sheet_name == "БАЗА ИСИДОРА ХВ":
        df = pd.read_excel(excel_file, sheet_name=sheet_name, header=5)
        st.dataframe(df.head(100))
    elif sheet_name == "Примени податоци ":
        df = pd.read_excel(excel_file, sheet_name=sheet_name, header=0)
        analyze_primeni_podatoci(df)
    else:
        df = pd.read_excel(excel_file, sheet_name=sheet_name, header=0)
        st.dataframe(df.head(100))

# Прикачување на датотека
uploaded_file = st.file_uploader("Прикачете Excel датотека", type=["xlsx"])
if uploaded_file:
    # Добивање листа на листови
    xls = pd.ExcelFile(uploaded_file)
    sheet_names = xls.sheet_names
    
    # Избирач на лист
    selected_sheet = st.selectbox("Изберете лист за анализа", sheet_names)
    
    try:
        load_and_display_sheet(uploaded_file, selected_sheet)
    except Exception as e:
        st.error(f"Грешка при вчитување на листот: {str(e)}")
