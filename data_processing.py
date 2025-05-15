import pandas as pd
import pyodbc
import streamlit as st
from typing import Dict, Tuple, Optional
import numpy as np

REQUIRED_COLUMNS = [
    'Известувач', 'Вид на износ', 'Износ во денари', 'Пакет',
    'Извештаен датум', 'Позиција', 'Идентификатор на хартија од вредност',
    'Алфанумеричка ознака на хартија од вредност', 'Котација'
]

def get_sql_connection() -> pyodbc.Connection:
    """Get SQL Server connection."""
    return pyodbc.connect(
        r'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=isql2012;DATABASE=Sifri;Trusted_Connection=yes;'
    )

@st.cache_data
def load_sql_mappings() -> Dict[int, str]:
    """Load only required company mappings from SQL database."""
    try:
        with get_sql_connection() as conn:
            # Load only company names mapping
            company_query = 'SELECT [Matbr_stat], [Poln_naziv_DO] FROM [dbo].[vwDanocni_num]'
            company_df = pd.read_sql(company_query, conn)
            company_df['Matbr_stat'] = pd.to_numeric(company_df['Matbr_stat'], errors='coerce').fillna(0).astype(int)
            return dict(zip(company_df['Matbr_stat'], company_df['Poln_naziv_DO']))
    except Exception as e:
        st.error(f"Error loading SQL mappings: {str(e)}")
        return {}

@st.cache_data
def load_excel_mappings(excel_file) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """Load only required Excel mappings efficiently."""
    try:
        # Load main sheet with only required columns
        main_df = pd.read_excel(
            excel_file, 
            sheet_name='Примени податоци',
            usecols=REQUIRED_COLUMNS
        )
        
        # Load only needed columns from листа известувачи
        reporters_df = pd.read_excel(
            excel_file, 
            sheet_name='листа известувачи',
            usecols=['Опис МК', 'матичен број']
        )
        
        # Clean and normalize company names
        main_df['Известувач'] = main_df['Известувач'].astype(str).str.strip().str.upper()
        reporters_df['Опис МК'] = reporters_df['Опис МК'].astype(str).str.strip().str.upper()
        reporters_df['матичен број'] = pd.to_numeric(reporters_df['матичен број'], errors='coerce').fillna(0).astype(int)
        
        # Create mapping dictionary
        opis_to_maticen = dict(zip(reporters_df['Опис МК'], reporters_df['матичен број']))
        
        return main_df, opis_to_maticen
    except Exception as e:
        st.error(f"Error loading Excel mappings: {str(e)}")
        return pd.DataFrame(), {}

def process_first_packet(excel_file) -> pd.DataFrame:
    """Process First Packet data efficiently."""
    try:
        # Load main data with required columns
        df = pd.read_excel(excel_file, sheet_name='Примени податоци', usecols=REQUIRED_COLUMNS)
        reporters_df = pd.read_excel(excel_file, sheet_name='листа известувачи', usecols=['Опис МК', 'матичен број'])
        
        # Clean company names
        df['Известувач'] = df['Известувач'].astype(str).str.strip().str.upper()
        reporters_df['Опис МК'] = reporters_df['Опис МК'].astype(str).str.strip().str.upper()
        reporters_df['матичен број'] = pd.to_numeric(reporters_df['матичен број'], errors='coerce').fillna(0).astype(int)
        
        # Get company mapping
        opis_to_maticen = dict(zip(reporters_df['Опис МК'], reporters_df['матичен број']))
        
        # Get SQL mapping
        conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=isql2012;DATABASE=Sifri;Trusted_Connection=yes;')
        company_df = pd.read_sql('SELECT [Matbr_stat], [Poln_naziv_DO] FROM [dbo].[vwDanocni_num]', conn)
        company_df['Matbr_stat'] = pd.to_numeric(company_df['Matbr_stat'], errors='coerce').fillna(0).astype(int)
        company_mapping = dict(zip(company_df['Matbr_stat'], company_df['Poln_naziv_DO']))
        
        # Apply mappings
        df['Матичен број на известувач'] = df['Известувач'].map(opis_to_maticen)
        df['Назив на договорна страна'] = df['Матичен број на известувач'].map(company_mapping)
        
        # Process dates and codes
        df['Датум'] = pd.to_datetime(df['Извештаен датум'], errors='coerce').dt.date
        df['Година'] = pd.to_datetime(df['Извештаен датум'], errors='coerce').dt.year
        df['Код (A/L)'] = df['Позиција'].apply(
            lambda pos: ', '.join([l for l in ['A', 'L'] if pd.notna(pos) and l in str(pos)]) 
            if pd.notna(pos) and any(l in str(pos) for l in ['A', 'L']) else '-'
        )
        
        # Process securities identifiers
        conditions = [
            (df['Идентификатор на хартија од вредност'].str.strip().str.upper() == 'ISIN'),
            (
                (df['Идентификатор на хартија од вредност'].str.strip().str.upper() == 'OTID') & 
                (df['Котација'].str.strip().str.upper() == 'KT')
            )
        ]
        choices = [df['Алфанумеричка ознака на хартија од вредност']] * 2
        
        df['Ознака на х.в. (ИСИН)'] = np.select(conditions, choices, default='')
        df['Ознака на х.в. (тикер)'] = np.select([conditions[1]], [choices[0]], default='')
        
        # Filter for PHoV and AHoV
        if 'Пакет' in df.columns:
            df = df[df['Пакет'].isin(['PHoV', 'AHoV'])]
        
        return df
        
    except Exception as e:
        st.error(f"Error in First Packet processing: {str(e)}")
        return pd.DataFrame()

def display_debug_info(df: pd.DataFrame) -> None:
    """Display debug information about the processed data."""
    try:
        st.subheader("Debug Information")
        
        # Mapping statistics
        total_rows = len(df)
        mapped_rows = df['Матичен број на известувач'].notna().sum()
        mapping_percentage = (mapped_rows / total_rows) * 100 if total_rows > 0 else 0
        
        st.info(f"""
        Data Processing Statistics:
        - Total rows: {total_rows:,}
        - Successfully mapped companies: {mapped_rows:,} ({mapping_percentage:.2f}%)
        """)
        
        # Show missing mappings if any
        missing_mappings = df[df['Матичен број на известувач'].isna()]['Известувач'].unique()
        if len(missing_mappings) > 0:
            st.warning("Companies without matching матичен број:")
            st.write(missing_mappings)
        
        # Preview of mapped data
        st.subheader("Data Preview")
        preview_cols = ['Известувач', 'Назив на договорна страна']
        st.dataframe(df[preview_cols].head(), use_container_width=True)
        
    except Exception as e:
        st.error(f"Error displaying debug information: {str(e)}") 