import pandas as pd
import pyodbc
import streamlit as st

def process_excel_mapping(excel_file):
    """
    Match company names from main sheet with листа известувачи and get corresponding матичен број as integer.
    If mapping success is 100%, use Известувач as Назив на договорна страна.
    
    Args:
        excel_file: The uploaded Excel file containing both sheets
        
    Returns:
        DataFrame with matched матичен број values and company names
    """
    try:
        # Load both sheets
        main_df = pd.read_excel(excel_file, sheet_name='Примени податоци')
        reporters_df = pd.read_excel(excel_file, sheet_name='листа известувачи')
        
        # Clean and normalize company names for matching
        main_df['Известувач'] = main_df['Известувач'].astype(str).str.strip().str.upper()
        reporters_df['Опис МК'] = reporters_df['Опис МК'].astype(str).str.strip().str.upper()
        
        # Convert матичен број to integer, removing any decimals
        reporters_df['матичен број'] = pd.to_numeric(reporters_df['матичен број'], errors='coerce').fillna(0).astype(int)
        
        # Create mapping dictionary from cleaned names to integer матичен број
        opis_to_maticen = dict(zip(reporters_df['Опис МК'], reporters_df['матичен број']))
        
        # Map company names to get матичен број
        main_df['Матичен број на известувач'] = main_df['Известувач'].map(opis_to_maticen)
        
        # Calculate mapping success rate
        total_rows = len(main_df)
        mapped_rows = main_df['Матичен број на известувач'].notna().sum()
        mapping_percentage = (mapped_rows / total_rows) * 100 if total_rows > 0 else 0
        
        # If 100% mapping success, use Известувач as Назив на договорна страна
        if mapping_percentage == 100.0:
            main_df['Назив на договорна страна'] = main_df['Известувач']
            st.success("Using Известувач names directly (100% mapping success)")
        else:
            # Show missing mappings for debugging
            missing_mappings = main_df[main_df['Матичен број на известувач'].isna()]['Известувач'].unique()
            if len(missing_mappings) > 0:
                st.warning("Companies without matching матичен број:")
                st.write(missing_mappings)
                
                # Show available mappings for reference
                st.info("Available mappings in листа известувачи:")
                st.write(reporters_df[['Опис МК', 'матичен број']].head())
        
        return main_df
        
    except Exception as e:
        st.error(f"Error processing Excel mapping: {str(e)}")
        return pd.DataFrame()

def get_company_names_from_sql():
    """
    Retrieve company names from SQL database.
    
    Returns:
        dict: Mapping from матичен број (as integer) to full company name
    """
    conn_str = r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=isql2012;DATABASE=Sifri;Trusted_Connection=yes;'
    
    try:
        with pyodbc.connect(conn_str) as conn:
            query = 'SELECT [Matbr_stat], [Poln_naziv_DO] FROM [dbo].[vwDanocni_num]'
            danocni_df = pd.read_sql(query, conn)
            
            # Convert Matbr_stat to integer
            danocni_df['Matbr_stat'] = pd.to_numeric(danocni_df['Matbr_stat'], errors='coerce').fillna(0).astype(int)
            danocni_df['Poln_naziv_DO'] = danocni_df['Poln_naziv_DO'].astype(str).str.strip()
            
            # Create mapping dictionary with integer keys
            matbr_to_poln_naziv = dict(zip(danocni_df['Matbr_stat'], danocni_df['Poln_naziv_DO']))
            
            return matbr_to_poln_naziv
    except Exception as e:
        st.error(f"Error connecting to SQL database: {str(e)}")
        return {}

def display_mapping_preview(df):
    """
    Display a preview of the company mappings.
    
    Args:
        df: DataFrame containing mapped company data
    """
    try:
        st.subheader("Company Name Mapping Preview")
        
        # Show the mapping process
        preview_cols = ['Известувач', 'Матичен број на известувач', 'Назив на договорна страна']
        preview_df = df[preview_cols].head()
        
        # Format матичен број as integer
        preview_df['Матичен број на известувач'] = preview_df['Матичен број на известувач'].fillna(0).astype(int)
        
        st.dataframe(preview_df)
        
        # Show mapping statistics
        total_rows = len(df)
        mapped_rows = df['Матичен број на известувач'].notna().sum()
        mapping_percentage = (mapped_rows / total_rows) * 100 if total_rows > 0 else 0
        
        st.info(f"""
        Mapping Statistics:
        - Total rows: {total_rows}
        - Successfully mapped: {mapped_rows}
        - Mapping success rate: {mapping_percentage:.2f}%
        """)
        
    except Exception as e:
        st.error(f"Error displaying mapping preview: {str(e)}") 