import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional

def detect_header_row(df: pd.DataFrame) -> int:
    """
    Детектира го редот со заглавја во DataFrame преку барање на специфични клучни зборови.
    """
    keywords = ['Назив на известувач', 'матичен број', 'ISIN', 'Вид на х.в.']
    
    for idx in range(min(10, len(df))):  # Проверка на првите 10 реда
        row = df.iloc[idx].astype(str)
        if any(keyword.lower() in ' '.join(row).lower() for keyword in keywords):
            return idx
    return 0

def clean_headers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Чисти и стандардизира имиња на колони.
    """
    header_row = detect_header_row(df)
    if header_row > 0:
        df.columns = df.iloc[header_row]
        df = df.iloc[header_row + 1:].reset_index(drop=True)
    
    # Отстранување на празни простори и специјални знаци
    df.columns = df.columns.astype(str).str.strip()
    
    # Замена на NaN вредности со описни имиња
    df.columns = [f'Колона_{i+1}' if pd.isna(col) or col == '' else col 
                 for i, col in enumerate(df.columns)]
    
    return df

def safe_str_operation(value: any) -> str:
    """
    Безбедно конвертирање на вредност во string.
    """
    if pd.isna(value):
        return ''
    return str(value).lower()

def filter_data(df: pd.DataFrame, 
                date_range: Optional[Tuple[str, str]] = None,
                reporter: Optional[str] = None,
                instrument_type: Optional[str] = None) -> pd.DataFrame:
    """
    Филтрира податоци според датум, известувач и тип на инструмент.
    """
    filtered_df = df.copy()
    
    if date_range:
        date_cols = [col for col in df.columns if 'датум' in safe_str_operation(col)]
        if date_cols:
            filtered_df = filtered_df[
                (filtered_df[date_cols[0]] >= date_range[0]) &
                (filtered_df[date_cols[0]] <= date_range[1])
            ]
    
    if reporter:
        reporter_cols = [col for col in df.columns if 'известувач' in safe_str_operation(col)]
        if reporter_cols:
            filtered_df = filtered_df[filtered_df[reporter_cols[0]].astype(str).str.contains(reporter, na=False)]
    
    if instrument_type:
        instrument_cols = [col for col in df.columns 
                         if 'вид' in safe_str_operation(col) and 'х.в.' in safe_str_operation(col)]
        if instrument_cols:
            filtered_df = filtered_df[filtered_df[instrument_cols[0]] == instrument_type]
    
    return filtered_df

def summarize_data(df: pd.DataFrame) -> Dict:
    """
    Креира сумарна статистика за податоците.
    """
    summary = {
        'вкупно_записи': len(df)
    }
    
    # Безбедно додавање на статистики само ако постојат соодветните колони
    if 'Матичен број на известувач' in df.columns:
        summary['број_известувачи'] = df['Матичен број на известувач'].nunique()
    
    if 'Вид на х.в. (ЕСА2010)' in df.columns:
        summary['број_инструменти'] = df['Вид на х.в. (ЕСА2010)'].nunique()
    
    # Додавање на агрегации по вредност ако постојат соодветни колони
    value_cols = [col for col in df.columns 
                 if any(term in safe_str_operation(col) for term in ['вредност', 'износ'])]
    
    for col in value_cols:
        try:
            summary[f'вкупна_{col}'] = pd.to_numeric(df[col], errors='coerce').sum()
        except:
            continue
    
    return summary

def export_to_excel(df: pd.DataFrame, filename: str) -> None:
    """
    Извезува DataFrame во Excel со соодветно форматирање.
    """
    writer = pd.ExcelWriter(filename, engine='openpyxl')
    df.to_excel(writer, index=False, sheet_name='Извештај')
    
    # Форматирање на колоните
    for column in df.columns:
        column_width = max(df[column].astype(str).map(len).max(), len(str(column)))
        col_idx = df.columns.get_loc(column)
        writer.sheets['Извештај'].column_dimensions[chr(65 + col_idx)].width = column_width + 2
    
    writer.close()

class IsidoraReport:
    def __init__(self):
        self.data = None
        self.metadata = {}
    
    def load_data(self, excel_file: str, sheet_name: str) -> None:
        """
        Вчитува податоци од Excel датотека.
        """
        try:
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
            self.data = clean_headers(df)
            self.metadata = {
                'извор': excel_file,
                'лист': sheet_name,
                'датум_на_вчитување': pd.Timestamp.now()
            }
        except Exception as e:
            raise Exception(f"Грешка при вчитување на податоците: {str(e)}")
    
    def filter_by_date(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Филтрира податоци по датум.
        """
        return filter_data(self.data, date_range=(start_date, end_date))
    
    def filter_by_reporter(self, reporter: str) -> pd.DataFrame:
        """
        Филтрира податоци по известувач.
        """
        return filter_data(self.data, reporter=reporter)
    
    def summarize_by_instrument(self) -> Dict:
        """
        Креира сумарна статистика по инструмент.
        """
        if 'Вид на х.в. (ЕСА2010)' not in self.data.columns:
            return {}
        
        try:
            summary = self.data.groupby('Вид на х.в. (ЕСА2010)').agg({
                'Матичен број на известувач': 'nunique',
                'ISIN': 'count'
            }).rename(columns={
                'Матичен број на известувач': 'број_известувачи',
                'ISIN': 'број_инструменти'
            })
            
            return summary.to_dict('index')
        except:
            return {}
    
    def export_report(self, filename: str) -> None:
        """
        Извезува извештај во Excel.
        """
        if self.data is not None:
            export_to_excel(self.data, filename)

def prepare_sostojba_na_hv(df_received):
    """
    Prepares the correct sum for 'Состојба на х.в на почеток на период (главнина)',
    filtering strictly Вид на износ as DRVR, DSK, PRM, POBJ.
    """
    required_cols = ["Вид на износ", "Износ во денари"]
    if not all(col in df_received.columns for col in required_cols):
        raise ValueError(f"Missing required columns: {required_cols}")

    valid_types = ["DRVR", "DSK", "PRM", "POBJ"]

    df = df_received.copy()
    df["Вид на износ"] = df["Вид на износ"].astype(str).str.strip().str.upper()
    df["Износ во денари"] = pd.to_numeric(df["Износ во денари"], errors="coerce")

    filtered_df = df[df["Вид на износ"].isin(valid_types)]
    filtered_df = filtered_df.drop_duplicates()
    filtered_df = filtered_df[filtered_df["Износ во денари"].notna()]

    total_sum = filtered_df["Износ во денари"].sum()

    return {
        "sum_in_denars": total_sum,
        "used_types": valid_types,
        "filtered_df": filtered_df
    }