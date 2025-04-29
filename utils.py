import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional

# --- Clean Headers ---
def detect_header_row(df: pd.DataFrame) -> int:
    keywords = ['Назив на известувач', 'матичен број', 'ISIN', 'Вид на х.в.']
    for idx in range(min(10, len(df))):
        row = df.iloc[idx].astype(str)
        if any(keyword.lower() in ' '.join(row).lower() for keyword in keywords):
            return idx
    return 0

def clean_headers(df: pd.DataFrame) -> pd.DataFrame:
    header_row = detect_header_row(df)
    if header_row > 0:
        df.columns = df.iloc[header_row]
        df = df.iloc[header_row + 1:].reset_index(drop=True)
    df.columns = df.columns.astype(str).str.strip()
    df.columns = [f'Колона_{i+1}' if pd.isna(col) or col == '' else col for i, col in enumerate(df.columns)]
    return df

# --- Прв Тест Пакет Processing ---
def prepare_sostojba_na_hv(df_received):
    required_cols = ["Вид на износ", "Износ во денари", "Износводенари"]
    if not any(col in df_received.columns for col in required_cols):
        raise ValueError("Недостасуваат задолжителни колони за калкулација.")

    df = df_received.copy()

    # Correct wrong column if needed
    if "Износводенари" in df.columns and "Износ во денари" not in df.columns:
        df = df.rename(columns={"Износводенари": "Износ во денари"})

    valid_types = ["DRVR", "DSK", "PRM", "POBJ"]
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
