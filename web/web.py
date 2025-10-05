Python

Copy
import streamlit as st
from core.pdf_tool import extract_text
from core.analyzer import analyze
from core.doc_generator import build
from core.kb_search import find_answer
import tempfile, os

st.set_page_config(page_title="LegalAideIP", layout="centered")
st.title("⚖️ LegalAide – помощник ИП")

menu = st.sidebar.radio("Раздел", ["Анализ PDF", "Создать договор", "Вопрос-ответ"])

if menu == "Анализ PDF":
    f = st.file_uploader("Загрузите договор (PDF)", type="pdf")
    if f:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(f.read())
            text = extract_text(tmp.name)
            os.unlink(tmp.name)
            for line in analyze(text):
                st.write(line)

elif menu == "Создать договор":
    with st.form("contract"):
        city = st.text_input("Город")
        landlord = st.text_input("Арендодатель (ФИО)")
        tenant = st.text_input("Арендатор (ФИО)")
        prop = st.text_area("Описание помещения")
        rent = st.text_input("Сумма аренды, руб/мес.")
        submitted = st.form_submit_button("Сформировать DOCX")
        if submitted:
            data = {"city": city, "landlord": landlord, "tenant": tenant,
                    "property": prop, "rent": rent,
                    "day": "01", "month": "января", "year": "2025",
                    "landlord_passport": "серия 1234 №567890",
                    "tenant_passport":  "серия 9876 №543210"}
            out = build(data, "договор_аренды_ИП.docx")
            with open(out, "rb") as f:
                st.download_button("Скачать", f, file_name=out.name)

elif menu == "Вопрос-ответ":
    q = st.text_input("Ваш вопрос:")
    if q:
        st.info(find_answer(q))
