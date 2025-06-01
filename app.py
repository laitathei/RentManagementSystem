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
    water_rate = st.number_input("每度水費", min_value=0.0)
    electric_rate = st.number_input("每度電費", min_value=0.0)
    cutoff_day = st.text_input("截數日")
    submitted = st.form_submit_button("✅ 新增")
    
    if submitted:
        new_row = [name, phone, address, rent, water_rate, electric_rate, cutoff_day]
        sheet.append_row(new_row)
        st.success(f"✅ 已新增租客：{name}")
        st.experimental_rerun()
