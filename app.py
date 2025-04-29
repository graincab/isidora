import streamlit as st
import pandas as pd
import plotly.express as px
from utils import prepare_sostojba_na_hv, clean_headers

# --- Streamlit App Config ---
st.set_page_config(page_title="ИСИДОРА Прв Тест Пакет", layout="wide", initial_sidebar_state="collapsed")

# --- Page Title ---
st.title("🖤 ИСИДОРА - Прв Тест Пакет (Dark Dashboard)")

# --- File Upload ---
uploaded_file = st.file_uploader("📄 Прикачи Excel датотека", type=["xlsx"])

if uploaded_file:
    try:
        # Auto-load 'Примени податоци ' sheet
        df = pd.read_excel(uploaded_file, sheet_name="Примени податоци ")
        df = clean_headers(df)

        st.success("✅ Податоците се успешно вчитани.")

        # --- Прв Тест Пакет Button ---
        if st.button("🚀 Генерирај Прв Тест Пакет"):
            result = prepare_sostojba_na_hv(df)

            # --- TABS Layout ---
            tab1, tab2, tab3 = st.tabs(["📊 Summary", "📈 Charts", "📋 Table"])

            # --- Summary Tab ---
            with tab1:
                st.subheader("📊 Summary Metrics")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric(label="💰 Вкупен Износ (денари)", value=f"{int(result['sum_in_denars'])}")
                with col2:
                    st.metric(label="📄 Број на Филтрирани Редови", value=f"{len(result['filtered_df'])}")

            # --- Charts Tab ---
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

            # --- Table Tab ---
            with tab3:
                st.subheader("📋 Преглед на Прв Тест Пакет")
                
                # Main Table
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

                # Filtered raw data
                st.subheader("🔍 Филтрирани Редови (DRVR, DSK, PRM, POBJ)")
                st.dataframe(result["filtered_df"], height=400, use_container_width=True)

    except Exception as e:
        st.error(f"Грешка при вчитување на датотеката: {e}")

else:
    st.info("📂 Прикачете .xlsx датотека за да започнете.")
