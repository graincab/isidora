import streamlit as st
import pandas as pd
import plotly.express as px
from utils import prepare_sostojba_na_hv, clean_headers

# --- Streamlit Page Config ---
st.set_page_config(page_title="ИСИДОРА Reporting Dashboard", layout="wide", initial_sidebar_state="collapsed")

# --- Session state to save file ---
if "uploaded_file" not in st.session_state:
    st.session_state.uploaded_file = None

# --- Landing Page ---
def landing_page():
    st.title("🖤 Добредојдовте во ISIDORA Dashboard")
    st.subheader("📊 Подгответе ги вашите извештаи брзо и професионално.")

    uploaded_file = st.file_uploader("📄 Прикачи Excel датотека (.xlsx)", type=["xlsx"])

    if uploaded_file:
        st.session_state.uploaded_file = uploaded_file
        st.success("✅ Датотеката е успешно прикачена!")

        if st.button("🚀 Продолжи кон Прв Тест Пакет"):
            st.session_state.page = "dashboard"

# --- Прв Тест Пакет Dashboard ---
def test_paket_page():
    st.title("🖤 ISIDORA - Прв Тест Пакет")

    try:
        df = pd.read_excel(st.session_state.uploaded_file, sheet_name="Примени податоци ")
        df = clean_headers(df)
        result = prepare_sostojba_na_hv(df)

        # --- Tabs Layout ---
        tab1, tab2, tab3 = st.tabs(["📊 Summary", "📈 Charts", "📋 Table"])

        with tab1:
            st.subheader("📊 Summary Metrics")
            col1, col2 = st.columns(2)
            with col1:
                st.metric(label="💰 Вкупен Износ", value=f"{int(result['sum_in_denars'])}")
            with col2:
                st.metric(label="📄 Број на Филтрирани Редови", value=f"{len(result['filtered_df'])}")

        with tab2:
            st.subheader("📈 Износ по Вид на Износ (DRVR, DSK, PRM, POBJ)")
            fig = px.bar(
                result["filtered_df"],
                x="Износ во денари",
                y="Вид на износ",
                orientation="h",
                color="Вид на износ",
                color_discrete_sequence=px.colors.qualitative.Safe,
                title="Анимиран Хоризонтален Бар Чарт",
            )
            st.plotly_chart(fig, use_container_width=True)

        with tab3:
            st.subheader("📋 Преглед на Прв Тест Пакет")

            table_data = {
                "Состојба на х.в на почеток на период (главнина)": [int(result["sum_in_denars"]), int(result["sum_in_denars"]), ", ".join(result["used_types"])],
                "Нето трансакции": ["⏳ Yet", "⏳ Yet", "⏳ Yet"],
                "Ценовни промени": ["⏳ Yet", "⏳ Yet", "⏳ Yet"],
                "Курсни разлики": ["⏳ Yet", "⏳ Yet", "⏳ Yet"],
                "Останати промени": ["⏳ Yet", "⏳ Yet", "⏳ Yet"],
                "Состојба на х.в на крај на период (главнина)": ["⏳ Yet", "⏳ Yet", "⏳ Yet"],
            }
            table_df = pd.DataFrame(table_data, index=["Rule", "Износ во денари", "Вид на износ"])
            st.dataframe(table_df, height=300, use_container_width=True)

            st.subheader("🔍 Филтрирани Редови (DRVR, DSK, PRM, POBJ)")
            st.dataframe(result["filtered_df"], height=400, use_container_width=True)

    except Exception as e:
        st.error(f"Грешка при вчитување или обработка на датотеката: {e}")

# --- Main Controller ---
def main():
    if "page" not in st.session_state:
        st.session_state.page = "landing"

    if st.session_state.page == "landing":
        landing_page()
    elif st.session_state.page == "dashboard":
        test_paket_page()

if __name__ == "__main__":
    main()
