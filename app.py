import streamlit as st
import pandas as pd
import numpy as np
from utils import clean_headers
import plotly.express as px
import plotly.graph_objects as go

# Increase the file size limit to 1000MB (1GB)
st.set_page_config(page_title="ISIDORA Reporting Tool", layout="wide")
st.title("ISIDORA Reporting Tool")

def analyze_relationships(df_main, df_reporters, df_securities, df_received):
    # Analyze relationships and data patterns
    summary = {}
    
    # Check Reporter relationships
    reporters_in_main = set(df_main['Матичен број на известувач'].unique())
    reporters_in_list = set(df_reporters['матичен број'].unique())
    summary['reporters_match'] = len(reporters_in_main.intersection(reporters_in_list))
    
    # Analyze securities types
    securities_types = df_main['Вид на х.в. (ЕСА2010)'].unique()
    valid_types = df_securities['Вид на ХВ'].unique()
    summary['securities_types'] = len(set(securities_types).intersection(set(valid_types)))
    
    return summary

def load_and_analyze_data(excel_file):
    # Initialize variables
    main_data = None
    reporters = None
    securities = None
    received = None
    
    # First, let's see what sheets are actually in the file
    xls = pd.ExcelFile(excel_file)
    available_sheets = xls.sheet_names
    st.write("Available sheets in the file:", available_sheets)
    
    # Load each sheet if available
    if "БАЗА ИСИДОРА ХВ" in available_sheets:
        main_data = pd.read_excel(excel_file, sheet_name="БАЗА ИСИДОРА ХВ", header=5)
        st.write("Successfully loaded БАЗА ИСИДОРА ХВ")
    
    if "листа известувачи" in available_sheets:
        reporters = pd.read_excel(excel_file, sheet_name="листа известувачи", header=0)
        st.write("Successfully loaded листа известувачи")
    
    if "Вид на ХВ" in available_sheets:
        securities = pd.read_excel(excel_file, sheet_name="Вид на ХВ", header=0)
        st.write("Successfully loaded Вид на ХВ")
    
    # Fix: Look for sheet name with or without trailing space
    received_sheet = next((s for s in available_sheets if s.strip() == "Примени податоци"), None)
    if received_sheet:
        received = pd.read_excel(excel_file, sheet_name=received_sheet, header=0)
        st.write(f"Successfully loaded {received_sheet}")
    
    # Only analyze relationships if all required sheets are present
    if all([main_data is not None, reporters is not None, securities is not None, received is not None]):
        relationships = analyze_relationships(main_data, reporters, securities, received)
        
        # Display enriched main data
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
        st.error(f"Missing sheets: {', '.join(missing_sheets)}")
        return None, None

def load_sheet_with_correct_headers(excel_file, sheet_name):
    if sheet_name == "БАЗА ИСИДОРА ХВ":
        # Headers are in row 6 (index 5)
        df = pd.read_excel(excel_file, sheet_name=sheet_name, header=5)
    elif sheet_name == "Примени податоци":
        # Headers are in row 1 (index 0)
        df = pd.read_excel(excel_file, sheet_name=sheet_name, header=0)
    elif sheet_name in ["Вид на ХВ", "листа известувачи"]:
        # Headers are in row 1 (index 0)
        df = pd.read_excel(excel_file, sheet_name=sheet_name, header=0)
    elif sheet_name == "курсни разлики":
        # This sheet contains only formulas, load as is
        df = pd.read_excel(excel_file, sheet_name=sheet_name)
    else:
        # Default behavior
        df = pd.read_excel(excel_file, sheet_name=sheet_name)
    return df

def analyze_primeni_podatoci(df):
    st.header("Analysis of Примени податоци")
    
    # First, let's create a sidebar for filters
    st.sidebar.header("📊 Filters")
    
    # Show all columns and let user select which ones to filter
    all_columns = list(df.columns)
    selected_columns = st.sidebar.multiselect(
        "Select columns to filter by:",
        all_columns,
        default=[]
    )
    
    # Create dynamic filters based on selected columns
    filtered_df = df.copy()
    for column in selected_columns:
        if pd.api.types.is_datetime64_any_dtype(df[column]):
            # Date range filter
            min_date = df[column].min()
            max_date = df[column].max()
            date_range = st.sidebar.date_input(
                f"Filter {column}",
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
            # Numeric range filter
            min_val = float(df[column].min())
            max_val = float(df[column].max())
            value_range = st.sidebar.slider(
                f"Filter {column}",
                min_val, max_val,
                (min_val, max_val)
            )
            filtered_df = filtered_df[
                (filtered_df[column] >= value_range[0]) &
                (filtered_df[column] <= value_range[1])
            ]
        else:
            # Categorical filter
            unique_values = sorted(df[column].unique())
            selected_values = st.sidebar.multiselect(
                f"Filter {column}",
                unique_values,
                default=list(unique_values)
            )
            filtered_df = filtered_df[filtered_df[column].isin(selected_values)]
    
    # Search functionality
    st.sidebar.header("🔍 Search")
    search_term = st.sidebar.text_input("Search in any column:")
    if search_term:
        mask = np.column_stack([filtered_df[col].astype(str).str.contains(search_term, case=False, na=False) 
                              for col in filtered_df.columns])
        filtered_df = filtered_df[mask.any(axis=1)]
    
    # Show number of filtered results
    st.sidebar.metric("Filtered Rows", f"{len(filtered_df):,}")
    
    # Create two columns for visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        # Status Distribution (if status column exists)
        status_cols = [col for col in filtered_df.columns if 'статус' in col.lower()]
        if status_cols:
            status_col = status_cols[0]
            st.subheader("📊 Status Distribution")
            status_counts = filtered_df[status_col].value_counts()
            fig = px.pie(values=status_counts.values, 
                        names=status_counts.index,
                        title='Distribution of Submission Status',
                        color_discrete_sequence=px.colors.qualitative.Set3)
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Reporter Activity (if reporter column exists)
        reporter_cols = [col for col in filtered_df.columns if 'назив' in col.lower()]
        if reporter_cols:
            st.subheader("📈 Reporter Activity")
            reporter_col = reporter_cols[0]
            reporter_data = filtered_df[reporter_col].value_counts().reset_index()
            reporter_data.columns = ['Reporter', 'Count']
            fig = px.bar(reporter_data.head(10), 
                        x='Count',
                        y='Reporter',
                        orientation='h',
                        title='Top 10 Most Active Reporters')
            st.plotly_chart(fig, use_container_width=True)
    
    # Timeline Analysis (if date column exists)
    date_cols = [col for col in filtered_df.columns if 'датум' in col.lower()]
    if date_cols:
        st.subheader("📅 Submission Timeline")
        date_col = date_cols[0]
        timeline = filtered_df.groupby(date_col).size().reset_index(name='Count')
        fig = px.line(timeline, 
                     x=date_col, 
                     y='Count',
                     title='Submissions Over Time')
        fig.update_traces(line_color='#2E86C1')
        st.plotly_chart(fig, use_container_width=True)
    
    # Data table with sorting and filtering
    st.subheader("📋 Detailed Data View")
    
    # Column selector for table
    selected_table_columns = st.multiselect(
        "Select columns to display:",
        all_columns,
        default=all_columns[:5]  # Default to first 5 columns
    )
    
    # Show the filtered dataframe
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
    elif sheet_name == "Примени податоци ":  # Note the space after податоци
        df = pd.read_excel(excel_file, sheet_name=sheet_name, header=0)
        analyze_primeni_podatoci(df)
    else:
        df = pd.read_excel(excel_file, sheet_name=sheet_name, header=0)
        st.dataframe(df.head(100))

# File uploader
uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])
if uploaded_file:
    # Get list of sheets
    xls = pd.ExcelFile(uploaded_file)
    sheet_names = xls.sheet_names
    
    # Sheet selector
    selected_sheet = st.selectbox("Select Sheet to Analyze", sheet_names)
    
    try:
        load_and_display_sheet(uploaded_file, selected_sheet)
    except Exception as e:
        st.error(f"Error loading sheet: {str(e)}")
