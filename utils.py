def clean_headers(df):
    for i, row in df.iterrows():
        if "Назив на известувач" in row.values:
            df.columns = row
            return df[i+1:].reset_index(drop=True)
    return df

def prepare_sostojba_na_hv(df_received):
    required_cols = ["Вид на износ", "Износ во денари"]
    if not all(col in df_received.columns for col in required_cols):
        raise ValueError(f"Missing required columns: {required_cols}")
    
    valid_types = ["DRVR", "DSK", "PRM", "POBJ"]
    filtered_df = df_received[df_received["Вид на износ"].isin(valid_types)]
    total_sum = filtered_df["Износ во денари"].sum()
    
    return {
        "umbrella_header": "Состојба на х.в на почеток на период (главнина)",
        "rule": (
            "Состојба од претходен известувачки период (t-1) да се направи збир на износи "
            "според сите критериуми за линијата, се собираат износи од колона 'Износ во денари' "
            "за кои во 'Вид на износ' се обележани 'DRVR', 'DSK', 'PRM', 'POBJ'."
        ),
        "sum_in_denars": total_sum,
        "used_types": valid_types
    }
