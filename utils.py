def clean_headers(df):
    for i, row in df.iterrows():
        if "Назив на известувач" in row.values:
            df.columns = row
            return df[i+1:].reset_index(drop=True)
    return df
