import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import json

# Google Sheets authentication
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Open Google Sheet by spreadsheet ID
sheet_id = "1k4EPnA9cLXkaDWpJ7EJwIwKpXWoth9mOMlHbNsFs644"
sheet = client.open_by_key(sheet_id).sheet1

# Read data
data = sheet.get_all_records()
df = pd.DataFrame(data)

# Streamlit interface
st.title("🏠 租金管理系統")
st.subheader("📋 租客清單")
st.dataframe(df)

# Add tenant form
st.subheader("➕ 新增租客資料")
with st.form("add_form"):
    name = st.text_input("租客姓名")
    phone = st.text_input("電話")
    address = st.text_input("單位地址")
    rent = st.number_input("每月固定租金", min_value=0.0)

    # 水費選項
    use_fixed_water = st.checkbox("使用固定水費")
    if use_fixed_water:
        fixed_water = st.number_input("固定水費金額", min_value=0.0)
        water_rate = "N/A"
    else:
        water_rate = st.number_input("每度水費", min_value=0.0)

    # 電費選項
    use_fixed_electric = st.checkbox("使用固定電費")
    if use_fixed_electric:
        fixed_electric = st.number_input("固定電費金額", min_value=0.0)
        electric_rate = "N/A"
    else:
        electric_rate = st.number_input("每度電費", min_value=0.0)

    # 新增欄位：通訊語言
    language = st.selectbox("通訊語言", ["中文", "英文"])

    # 新增欄位：收租費
    management_fee = st.number_input("收租費（如有）", min_value=0.0, value=0.0)

    cutoff_day = st.text_input("截數日")
    submitted = st.form_submit_button("✅ 新增")

    if submitted:
        new_row = [name, phone, address, rent, water_rate, electric_rate, cutoff_day, language, management_fee]
        sheet.append_row(new_row)
        st.success(f"✅ 已新增租客：{name}")
        st.experimental_rerun()