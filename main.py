import pandas as pd

def load_excel(file_path):
    # Load all sheets as a dictionary
    xls = pd.read_excel(file_path, sheet_name=None)
    return xls

def show_sheet_summary(data):
    for sheet, df in data.items():
        print(f"--- {sheet} ---")
        print(f"Rows: {df.shape[0]} | Columns: {df.shape[1]}")
        print(f"Headers: {list(df.columns[:5])}...\n")

if __name__ == "__main__":
    file_path = "data/Paket HV.xlsx"
    data = load_excel(file_path)
    show_sheet_summary(data)
