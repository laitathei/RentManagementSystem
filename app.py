import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import json

# ────────────────── 🔒 密碼登入驗證 ──────────────────
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_name = ""

if not st.session_state.authenticated:
    st.title("🏠 代收租金管理系統")
    st.subheader("🔐 請輸入密碼登入")

    with st.form("login_form"):
        pw = st.text_input("密碼", type="password")
        login_btn = st.form_submit_button("🔓 登入")
        if login_btn:
            pw2user = {v: k for k, v in st.secrets["USERS"].items()}   # 反轉成 {密碼:名字}
            if pw in pw2user:
                st.session_state.authenticated = True
                st.session_state.user_name = pw2user[pw]               # 記下誰登入
                st.success(f"✅ 歡迎 {st.session_state.user_name}！")
                st.rerun()
            else:
                st.error("❌ 密碼錯誤，請再試一次。")
    st.stop()  # ❗停止頁面，防止其他內容顯示

# ────────────────── Google Sheets 認證 ──────────────────
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
# creds_dict = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"])
creds_dict = dict(st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

sheet_id = "1k4EPnA9cLXkaDWpJ7EJwIwKpXWoth9mOMlHbNsFs644"
sheet_tenants   = client.open_by_key(sheet_id).worksheet("租客資料")  # 租客資料表
sheet_rentflow  = client.open_by_key(sheet_id).worksheet("租金流程")  # 租金流程表

# ────────────────── 版頭 & 功能選單 ──────────────────
st.title("🏠 代收租金管理系統")
main_mode = st.radio("📂 功能類別", ["👥 租客資料管理", "📆 租金處理進度"], horizontal=True)

tenant_data = sheet_tenants.get_all_records()
tenant_df = pd.DataFrame(tenant_data)
rentflow_data = sheet_rentflow.get_all_records()
rentflow_df = pd.DataFrame(rentflow_data)
for col in ["租客姓名", "單位地址", "租客電話", "固定水費", "固定電費", "每度水費", "每度電費"]:
    if col in tenant_df.columns:
        tenant_df[col] = tenant_df[col].astype(str)
for col in ["收租金額", "過戶金額"]:
    if col in rentflow_df.columns:
        rentflow_df[col] = pd.to_numeric(rentflow_df[col], errors="coerce")

if main_mode == "👥 租客資料管理":
    # 讀取資料
    st.subheader("📋 租客資料")
    st.dataframe(tenant_df, use_container_width=True)
    sub_mode = st.radio("📋 租客操作選項", ["➕ 新增租客資料", "✏️ 更改租客資料", "🗑️ 刪除租客資料"], horizontal=True)

    # ────────────────── 新增 ──────────────────
    if sub_mode == "➕ 新增租客資料":
        st.subheader("➕ 新增租客資料")
        water_mode = st.radio("💧 水費收費方式", ["每度計算", "固定金額", "不代收"], horizontal=True)
        electric_mode = st.radio("⚡ 電費收費方式", ["每度計算", "固定金額", "不代收"], horizontal=True)
        with st.form("add_tenant_form"):
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
            lease_start = st.date_input("租約開始日", key="lease_start", value=pd.Timestamp.now().date())
            lease_end   = st.date_input("租約結束日", key="lease_end", value=pd.Timestamp.now().date() + pd.DateOffset(years=1))

            if st.form_submit_button("✅ 新增"):
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                who = st.session_state.get("user_name", "unknown")
                exists = rentflow_df[
                    (tenant_df["租客姓名"] == name.strip()) &
                    (tenant_df["單位地址"] == address.strip())
                ]
                if not exists.empty:
                    st.warning("⚠️ 已存在相同租客姓名與單位地址的紀錄，請確認是否重覆輸入。")
                else:
                    new_row = [name, phone, address, rent, fix_water_fee, fix_electric_fee, water_fee, electric_fee,
                            cutoff_day, language, management_fee, str(lease_start), str(lease_end), ts, who]
                    sheet_tenants.append_row(new_row)
                    st.success(f"✅ 已新增租客：{name}")
                    st.rerun()

    # ────────────────── 更改 ──────────────────
    elif sub_mode == "✏️ 更改租客資料":
        st.subheader("✏️ 更改租客資料")
        if tenant_df.empty:
            st.info("目前沒有資料可修改。")
        else:
            selector = tenant_df["租客姓名"] + "｜" + tenant_df["單位地址"]
            choice = st.selectbox("選擇欲修改的租客", selector)
            idx = selector.tolist().index(choice)
            sheet_row = idx + 2  # Sheet 2-based
            row      = tenant_df.iloc[idx]

            water_mode_options    = ["每度計算", "固定金額", "不代收"]
            electric_mode_options = ["每度計算", "固定金額", "不代收"]

            if str(row["每度水費"]).upper() != "N/A" and str(row["每度水費"]) != "":
                water_mode_idx   = water_mode_options.index("每度計算")
            elif str(row["固定水費"]).upper() != "N/A" and str(row["固定水費"]) != "":
                water_mode_idx   = water_mode_options.index("固定金額")
            else:
                water_mode_idx   = water_mode_options.index("不代收")


            if str(row["每度電費"]).upper() != "N/A" and str(row["每度電費"]) != "":
                electric_mode_idx   = electric_mode_options.index("每度計算")
            elif str(row["固定電費"]).upper() != "N/A" and str(row["固定電費"]) != "":
                electric_mode_idx   = electric_mode_options.index("固定金額")
            else:
                electric_mode_idx   = electric_mode_options.index("不代收")

            water_mode = st.radio("💧 水費收費方式", water_mode_options, index=water_mode_idx, horizontal=True)
            electric_mode = st.radio("⚡ 電費收費方式", electric_mode_options, index=electric_mode_idx, horizontal=True)
        
            row = tenant_df.iloc[idx]
            with st.form("edit_tenant_form"):
                name    = st.text_input("租客姓名",  value=row["租客姓名"])
                phone   = st.text_input("電話",      value=str(row["租客電話"]))
                address = st.text_input("單位地址",  value=row["單位地址"])
                rent    = st.number_input("每月固定租金", value=float(row["每月固定租金"]))

                # 水費
                water_box = st.empty()
                if water_mode == "每度計算":
                    water_fee = st.number_input("每度水費", min_value=0.0, 
                                                value=float(row["每度水費"]) if str(row["每度水費"]).replace('.', '', 1).isdigit() else 0.0,
                                                key="water_per_unit_add")
                    fix_water_fee = "N/A"
                elif water_mode == "固定金額":
                    fix_water_fee = st.number_input("固定水費金額", min_value=0.0, 
                                                    value=float(row["固定水費"]) if str(row["固定水費"]).replace('.', '', 1).isdigit() else 0.0,
                                                    key="water_fixed_add")
                    water_fee = "N/A"
                else:
                    water_fee = fix_water_fee = "N/A"
            
                # 電費
                electric_box = st.empty()
                if electric_mode == "每度計算":
                    electric_fee = st.number_input("每度電費", min_value=0.0, 
                                                   value=float(row["每度電費"]) if str(row["每度電費"]).replace('.', '', 1).isdigit() else 0.0,
                                                   key="electric_per_unit_add")
                    fix_electric_fee = "N/A"
                elif electric_mode == "固定金額":
                    fix_electric_fee = st.number_input("固定電費金額", min_value=0.0, 
                                                       value=float(row["固定電費"]) if str(row["固定電費"]).replace('.', '', 1).isdigit() else 0.0,
                                                       key="electric_fixed_add")
                    electric_fee = "N/A"
                else:
                    electric_fee = fix_electric_fee = "N/A"
            
                language = st.selectbox("通訊語言", ["中文", "英文"],
                                        index=0 if row["通訊語言"]=="中文" else 1)
                management_fee = st.number_input("收租費", min_value=0.0, value=float(row["收租費"]))
                cutoff_day = st.selectbox("截數日（每月）", list(range(1, 32)),
                                        index=int(row["截數日"])-1)
                
                lease_start = st.date_input("租約開始日", value=pd.to_datetime(row["租約開始日"]) if "租約開始日" in row and row["租約開始日"] else pd.Timestamp.now().date())
                lease_end   = st.date_input("租約結束日", value=pd.to_datetime(row["租約結束日"]) if "租約結束日" in row and row["租約結束日"] else pd.Timestamp.now().date() + pd.DateOffset(years=1))

                if st.form_submit_button("💾 儲存修改"):
                    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    who = st.session_state.get("user_name", "unknown")
                    new_row = [name, phone, address, rent, 
                               fix_water_fee, fix_electric_fee, 
                               water_fee, electric_fee,
                               cutoff_day, language, management_fee,
                               str(lease_start), str(lease_end),
                               ts, who]
                    sheet_tenants.update(f"A{sheet_row}:M{sheet_row}", [new_row])
                    st.success("✅ 已更新！")
                    st.rerun()

    # ────────────────── 刪除 ──────────────────
    elif sub_mode == "🗑️ 刪除租客資料":
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

elif main_mode == "📆 租金處理進度":
    st.markdown("### 🔍 指定月份查詢")
    now = datetime.now()
    all_years  = sorted(set(rentflow_df["年度"].unique().tolist() + [now.year]), reverse=True)
    all_months = sorted(set(rentflow_df["月份"].unique().tolist() + [now.month]))
    selected_year  = st.selectbox("選擇年份", all_years, index=0)
    selected_month = st.selectbox("選擇月份", all_months, index=all_months.index(now.month))
    filtered_df = rentflow_df[
        (rentflow_df["年度"] == selected_year) &
        (rentflow_df["月份"] == selected_month)
    ]

    st.markdown(f"### 📋 {selected_year} 年 {selected_month} 月租金流程")
    tenant_df["key"]   = tenant_df["租客姓名"] + "｜" + tenant_df["單位地址"].astype(str)
    filtered_df["key"] = filtered_df["租客姓名"] + "｜" + filtered_df["單位地址"].astype(str)
    
    paid_df   = filtered_df[filtered_df["已收取租金"].astype(str).str.upper() == "TRUE"]
    paid_rooms = len(paid_df)                         # ← 行數就是房間數
    paid_keys  = set(paid_df["key"])                  # ← 用來做未交租比對
    total_rooms  = len(tenant_df)                     # 全部房間
    unpaid_rooms = total_rooms - paid_rooms           # 未交租房間數
    unpaid_df = tenant_df[~tenant_df["key"].isin(paid_keys)]
    

    col1, col2, col3 = st.columns(3)
    col1.metric("📋 總租客數", total_rooms)
    col2.metric("✅ 已交租", paid_rooms)
    col3.metric("⚠️ 未交租", unpaid_rooms)
    st.dataframe(filtered_df.drop(columns=["key"]), use_container_width=True)

    if unpaid_rooms > 0:
        st.markdown("### ❌ 未交租租客名單")
        show_cols = [c for c in ["租客姓名", "租客電話", "單位地址", "每月固定租金"] if c in unpaid_df.columns]
        view_df = unpaid_df[show_cols].copy()
        view_df = view_df.rename(columns={"每月固定租金": "應付租金"})
        st.dataframe(view_df, use_container_width=True)
    else:
        st.success(f"🥳 所有租客都已繳交{selected_year} 年 {selected_month} 月月租金")

    sub_mode = st.radio("🧾 租金紀錄操作", ["➕ 新增租金紀錄", "✏️ 更改租金紀錄"], horizontal=True)
    if sub_mode == "➕ 新增租金紀錄":
        st.subheader("➕ 新增租金紀錄")
        
        selector = tenant_df["租客姓名"] + "｜" + tenant_df["單位地址"]
        sel_opt = st.selectbox("租客", selector)
        idx = selector.tolist().index(sel_opt)
        default_phone = str(tenant_df.iloc[idx]["租客電話"]).lstrip("'").strip()
        name = sel_opt.split("｜")[0]
        address = tenant_df.iloc[idx]["單位地址"]
        default_rent = float(tenant_df.iloc[idx]["每月固定租金"])

        receive_done  = st.checkbox("✅ 已收租", key="receive_done_out")
        deposit_done  = st.checkbox("🏦 已入帳", key="deposit_done_out")

        with st.form("add_rentflow_form"):
            phone = st.text_input("租客電話", value=default_phone, disabled=True)

            year = st.number_input("年度", min_value=2000, max_value=2100, value=pd.Timestamp.now().year)
            month = st.selectbox("月份", list(range(1, 13)), index=pd.Timestamp.now().month - 1)

            if receive_done:
                receive_date = st.date_input("📅 收租日期", value=pd.Timestamp.now().date(), key="receive_date_in")
                receive_amt  = st.number_input("💰 收租金額", min_value=0.0, value=default_rent, key="receive_amt")
            else:
                receive_date = ""
                receive_amt = ""
            if deposit_done:
                deposit_date = st.date_input("📅 過數日期", value=pd.Timestamp.now().date(), key="deposit_date_in")
                deposit_amt  = st.number_input("💰 過戶金額", min_value=0.0, value=default_rent, key="deposit_amt")
            else:
                deposit_date = ""
                deposit_amt = ""

            if st.form_submit_button("✅ 新增"):
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                who = st.session_state.get("user_name", "unknown")
                exists = rentflow_df[
                    (rentflow_df["租客姓名"] == name) &
                    (rentflow_df["年度"] == year) &
                    (rentflow_df["月份"] == month)
                ]
                if not exists.empty:
                    st.warning(f"⚠️ 此租客{selected_year} 年 {selected_month} 月的租金流程紀錄已存在！")
                else:
                    row = [
                        phone, name, address, year, month,
                        str(receive_date) if receive_done else "",
                        receive_done,
                        receive_amt  if receive_done  else "",
                        str(deposit_date) if deposit_done else "",
                        deposit_done,
                        deposit_amt  if deposit_done else "",
                        ts, who
                    ]
                    sheet_rentflow.append_row(row, value_input_option="RAW")
                    st.success("✅ 已成功新增租金紀錄")
                    st.rerun()

    elif sub_mode == "✏️ 更改租金紀錄":
        st.subheader("✏️ 更改租金紀錄")
        if rentflow_df.empty:
            st.info("目前尚無紀錄可修改")
        else:
            rentflow_df["選項"] = rentflow_df["租客姓名"] + "｜" + rentflow_df["年度"].astype(str) + "-" + rentflow_df["月份"].astype(str).str.zfill(2)
            choice = st.selectbox("選擇要修改的紀錄", rentflow_df["選項"].tolist())
            idx = rentflow_df[rentflow_df["選項"] == choice].index[0]
            row_data = rentflow_df.loc[idx]
            gs_row = idx + 2  # Google Sheets 的列數（從第2列開始）

            receive_done = st.checkbox("✅ 已收租", value=str(row_data["已收取租金"]).upper() == "TRUE")
            deposit_done = st.checkbox("🏦 已入帳", value=str(row_data["已存入租金"]).upper() == "TRUE")

            with st.form("edit_rentflow_form"):
                if receive_done:
                    receive_date = st.date_input("📅 收租日期", value=pd.to_datetime(row_data["收取租金日期"]).date() if row_data["收取租金日期"] else pd.Timestamp.now().date(), key="receive_date_in")
                    receive_amt  = st.number_input("💰 收租金額", min_value=0.0, value=float(row_data["收租金額"]) if row_data["收租金額"] else 0.0, key="receive_amt")
                else:
                    receive_date = ""
                    receive_amt = ""
                if deposit_done:
                    deposit_date = st.date_input("📅 過數日期", value=pd.to_datetime(row_data["存入租金日期"]).date() if row_data["存入租金日期"] else pd.Timestamp.now().date(), key="deposit_date_in")
                    deposit_amt  = st.number_input("💰 過戶金額", min_value=0.0, value=float(row_data["過戶金額"]) if row_data["過戶金額"] else 0.0, key="deposit_amt")
                else:
                    deposit_date = ""
                    deposit_amt = ""

                if st.form_submit_button("💾 儲存修改"):
                    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    who = st.session_state.get("user_name", "unknown")
                    sheet_rentflow.update(f"F{gs_row}:M{gs_row}", [[
                        str(receive_date) if receive_done else "",
                        str(receive_done).upper(),
                        receive_amt if receive_done else "",
                        str(deposit_date) if deposit_done else "",
                        str(deposit_done).upper(),
                        deposit_amt if deposit_done else "",
                        ts, who
                    ]])
                    st.success("✅ 已成功修改紀錄")
                    st.rerun()