import pandas as pd
import numpy as np

def prepare_sostojba_na_hv(df_received):
    required_cols = ["Вид на износ", "Износ во денари", "Износводенари"]
    if not any(col in df_received.columns for col in required_cols):
        raise ValueError("Missing required columns for calculation.")

    df = df_received.copy()

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
