import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import json

# ────────────────── 🔒 密碼登入驗證 ──────────────────
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🏠 代收租金管理系統")
    st.subheader("🔐 請輸入密碼登入")

    with st.form("login_form"):
        pw = st.text_input("密碼", type="password")
        login_btn = st.form_submit_button("🔓 登入")
    
        if login_btn:
            if pw == st.secrets["ADMIN_PASSWORD"]:
                st.session_state.authenticated = True
                st.success("✅ 登入成功，正在載入系統...")
                st.rerun()
            else:
                st.error("❌ 密碼錯誤，請再試一次。")
    st.stop()  # ❗停止頁面，防止其他內容顯示

# ────────────────── Google Sheets 認證 ──────────────────
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

sheet_id = "1k4EPnA9cLXkaDWpJ7EJwIwKpXWoth9mOMlHbNsFs644"
sheet_tenants   = client.open_by_key(sheet_id).worksheet("租客資料")  # 租客資料表
sheet_rentflow  = client.open_by_key(sheet_id).worksheet("租金流程")  # 租金流程表

# ────────────────── 版頭 & 功能選單 ──────────────────
st.title("🏠 代收租金管理系統")
mode = st.radio(
    "請選擇操作：",
    ["➕ 新增租客資料", "✏️ 更改租客資料", "🗑️ 刪除租客資料", "📆 租金處理進度"],
    horizontal=True
)

if mode in ["➕ 新增租客資料", "✏️ 更改租客資料", "🗑️ 刪除租客資料"]:
    # 讀取資料
    tenant_data = sheet_tenants.get_all_records()
    tenant_df = pd.DataFrame(tenant_data)
    tenant_df.columns = tenant_df.columns.str.strip()
    st.write("欄位清單:", tenant_df.columns.tolist())
    st.subheader("📋 租客資料")
    st.dataframe(tenant_df, use_container_width=True)

elif mode == "📆 租金處理進度":
    rentflow_data = sheet_rentflow.get_all_records()
    rentflow_df = pd.DataFrame(rentflow_data)
    rentflow_df.columns = rentflow_df.columns.str.strip()
    st.write("欄位清單:", rentflow_df.columns.tolist())
    st.subheader("📋 租金流程")
    st.dataframe(rentflow_df, use_container_width=True)

# ────────────────── 新增 ──────────────────
if mode == "➕ 新增租客資料":
    st.subheader("➕ 新增租客資料")
    water_mode = st.radio("💧 水費收費方式", ["每度計算", "固定金額", "不代收"], horizontal=True)
    electric_mode = st.radio("⚡ 電費收費方式", ["每度計算", "固定金額", "不代收"], horizontal=True)
    with st.form("add_form"):
        name = st.text_input("租客姓名")
        phone = st.text_input("電話")
        address = st.text_input("單位地址")
        rent = st.number_input("每月固定租金", min_value=0.0)

        # 水費
        water_box = st.empty()
        if water_mode == "每度計算":
            water_fee = st.number_input("每度水費", min_value=0.0, key="water_per_unit_add")
            fix_water_fee = "N/A"
        elif water_mode == "固定金額":
            fix_water_fee = st.number_input("固定水費金額", min_value=0.0, key="water_fixed_add")
            water_fee = "N/A"
        else:
            water_fee = fix_water_fee = "N/A"

        # 電費
        electric_box = st.empty()
        if electric_mode == "每度計算":
            electric_fee = st.number_input("每度電費", min_value=0.0, key="electric_per_unit_add")
            fix_electric_fee = "N/A"
        elif electric_mode == "固定金額":
            fix_electric_fee = st.number_input("固定電費金額", min_value=0.0, key="electric_fixed_add")
            electric_fee = "N/A"
        else:
            electric_fee = fix_electric_fee = "N/A"
        
        language = st.selectbox("通訊語言", ["中文", "英文"])
        management_fee = st.number_input("收租費", min_value=0.0, value=0.0)
        cutoff_day = st.selectbox("截數日（每月）", list(range(1, 32)))

        if st.form_submit_button("✅ 新增"):
            new_row = [name, phone, address, rent, fix_water_fee, fix_electric_fee, water_fee, electric_fee,
                       cutoff_day, language, management_fee]
            sheet_tenants.append_row(new_row)
            st.success(f"✅ 已新增租客：{name}")
            st.rerun()

# ────────────────── 更改 ──────────────────
elif mode == "✏️ 更改租客資料":
    st.subheader("✏️ 更改租客資料")
    water_mode = st.radio("💧 水費收費方式", ["每度計算", "固定金額", "不代收"], horizontal=True)
    electric_mode = st.radio("⚡ 電費收費方式", ["每度計算", "固定金額", "不代收"], horizontal=True)
    if tenant_df.empty:
        st.info("目前沒有資料可修改。")
    else:
        selector = tenant_df["租客姓名"] + "｜" + tenant_df["單位地址"]
        choice = st.selectbox("選擇欲修改的租客", selector)
        idx = selector.tolist().index(choice)
        sheet_row = idx + 2  # Sheet 2-based

        row = tenant_df.iloc[idx]
        with st.form("edit_form"):
            name = st.text_input("租客姓名", value=row.get("租客姓名", ""))
            phone = st.text_input("電話", value=row.get("電話", ""))
            address = st.text_input("單位地址", value=row.get("單位地址", ""))
            rent = st.number_input("每月固定租金", value=float(row.get("每月固定租金", 0)))

            # 水費
            water_box = st.empty()
            if water_mode == "每度計算":
                water_fee = st.number_input("每度水費", min_value=0.0, key="water_per_unit_add")
                fix_water_fee = "N/A"
            elif water_mode == "固定金額":
                fix_water_fee = st.number_input("固定水費金額", min_value=0.0, key="water_fixed_add")
                water_fee = "N/A"
            else:
                water_fee = fix_water_fee = "N/A"
        
            # 電費
            electric_box = st.empty()
            if electric_mode == "每度計算":
                electric_fee = st.number_input("每度電費", min_value=0.0, key="electric_per_unit_add")
                fix_electric_fee = "N/A"
            elif electric_mode == "固定金額":
                fix_electric_fee = st.number_input("固定電費金額", min_value=0.0, key="electric_fixed_add")
                electric_fee = "N/A"
            else:
                electric_fee = fix_electric_fee = "N/A"
        
            language = st.selectbox("通訊語言", ["中文", "英文"],
                                    index=0 if row["通訊語言"]=="中文" else 1)
            management_fee = st.number_input("收租費", min_value=0.0, value=float(row["收租費"]))
            cutoff_day = st.selectbox("截數日（每月）", list(range(1, 32)),
                                      index=int(row["截數日"])-1)

            if st.form_submit_button("💾 儲存修改"):
                new_row = [name, phone, address, rent, fix_water_fee, fix_electric_fee, water_fee, electric_fee,
                           cutoff_day, language, management_fee]
                sheet_tenants.update(f"A{sheet_row}:I{sheet_row}", [new_row])
                st.success("✅ 已更新！")
                st.rerun()

# ────────────────── 刪除 ──────────────────
elif mode == "🗑️ 刪除租客資料":
    st.subheader("🗑️ 刪除租客資料")
    if tenant_df.empty:
        st.info("目前沒有資料可刪除。")
    else:
        selector = tenant_df["租客姓名"] + "｜" + tenant_df["單位地址"]
        choice = st.selectbox("選擇欲刪除的租客", selector)
        idx = selector.tolist().index(choice)
        sheet_row = idx + 2  # Sheet 2-based

        if st.button("⚠️ 確認刪除"):
            sheet_tenants.delete_rows(sheet_row)
            st.warning(f"已刪除：{choice}")
            st.rerun()

elif mode == "📆 租金處理進度":
    st.subheader("📆 本月租金收取／入帳狀態")

    # 1. 讀取 RentFlow
    flow_df = pd.DataFrame(sheet_rentflow.get_all_records())
    flow_df.columns = flow_df.columns.str.strip()

    # 2. 只顯示本月資料
    today = pd.Timestamp.today()
    yy, mm = today.year, today.month
    this_month = flow_df[(flow_df["年度"] == yy) & (flow_df["月份"] == mm)]

    if this_month.empty:
        st.info("📭 本月尚未建立任何租金紀錄。")
    else:
        for i, row in this_month.reset_index(drop=True).iterrows():
            st.markdown(f"---\n#### 👤 {row['租客姓名']}（{row['租客電話']}）")

            col1, col2 = st.columns(2)
            # ── 收租 ──
            with col1:
                r_done = st.checkbox("✅ 已收租", value=row["已收取租金"], key=f"r{i}")
                r_date = row["收取租金日期"]
                if r_done and not r_date:
                    r_date = today.strftime("%Y-%m-%d")
            # ── 入帳 ──
            with col2:
                d_done = st.checkbox("🏦 已入帳", value=row["已存入租金"], key=f"d{i}")
                d_date = row["存入租金日期"]
                if d_done and not d_date:
                    d_date = today.strftime("%Y-%m-%d")

            if st.button("💾 儲存", key=f"s{i}"):
                # 找到 Google Sheet 中的實際列號：i（0-base）+2（標題列+1）
                row_num = i + 2
                # 只更新 E~H 4 欄：收租日期 / 收租勾 / 入帳日期 / 入帳勾
                sheet_rentflow.update(
                    f"E{row_num}:H{row_num}",
                    [[r_date, str(r_done).upper(), d_date, str(d_done).upper()]]
                )
                st.success("✅ 已更新")
                st.rerun()
