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
main_mode = st.radio("📂 功能類別", ["👥 租客資料管理", "📆 租金處理進度"], horizontal=True)

tenant_data = sheet_tenants.get_all_records()
tenant_df = pd.DataFrame(tenant_data)
rentflow_data = sheet_rentflow.get_all_records()
rentflow_df = pd.DataFrame(rentflow_data)
for col in ["固定水費", "固定電費", "每度水費", "每度電費"]:
    if col in tenant_df.columns:
        tenant_df[col] = tenant_df[col].astype(str)

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

            if st.form_submit_button("✅ 新增"):
                new_row = [name, phone, address, rent, fix_water_fee, fix_electric_fee, water_fee, electric_fee,
                        cutoff_day, language, management_fee]
                sheet_tenants.append_row(new_row)
                st.success(f"✅ 已新增租客：{name}")
                st.rerun()

    # ────────────────── 更改 ──────────────────
    elif sub_mode == "✏️ 更改租客資料":
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
            with st.form("edit_tenant_form"):
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
    st.subheader("📋 租金流程")
    st.dataframe(rentflow_df, use_container_width=True)
    sub_mode = st.radio("🧾 租金紀錄操作", ["➕ 新增租金紀錄", "✏️ 更改租金紀錄"], horizontal=True)
    if sub_mode == "➕ 新增租金紀錄":
        st.subheader("➕ 新增租金紀錄")

        receive_done  = st.checkbox("✅ 已收租", key="receive_done_out")
        deposit_done  = st.checkbox("🏦 已入帳", key="deposit_done_out")

        with st.form("add_rentflow_form"):
            # selector = tenant_df["租客姓名"] + "｜" + tenant_df["單位地址"]
            # name = st.selectbox("租客姓名", selector)
            # phone = st.text_input("租客電話").strip().lstrip("'")

            # 1️⃣ 讓使用者挑租客（含單位地址，方便辨識）
            selector = tenant_df["租客姓名"] + "｜" + tenant_df["單位地址"]
            sel_opt = st.selectbox("租客", selector)

            # 2️⃣ 根據選項，自動抓該列電話
            #    取得對應 index，再取 tenant_df.iloc[idx]["電話"]
            idx = selector.tolist().index(sel_opt)
            default_phone = str(tenant_df.iloc[idx]["電話"]).lstrip("'").strip()

            # 3️⃣ 把 phone 欄預填，並設成 disabled (唯讀)
            phone = st.text_input("租客電話", value=default_phone, disabled=True)
            name = sel_opt.split("｜")[0]
            
            year = st.number_input("年度", min_value=2000, max_value=2100, value=pd.Timestamp.now().year)
            month = st.selectbox("月份", list(range(1, 13)), index=pd.Timestamp.now().month - 1)

            if receive_done:
                receive_date = st.date_input("📅 收租日期", value=pd.Timestamp.now().date(), key="receive_date_in")
            else:
                receive_date = ""
            if deposit_done:
                deposit_date = st.date_input("📅 過數日期", value=pd.Timestamp.now().date(), key="deposit_date_in")
            else:
                deposit_date = ""

            if st.form_submit_button("✅ 新增"):
                exists = rentflow_df[
                    (rentflow_df["租客姓名"] == name) &
                    (rentflow_df["年度"] == year) &
                    (rentflow_df["月份"] == month)
                ]
                if not exists.empty:
                    st.warning("⚠️ 此租客該月份的紀錄已存在！")
                else:
                    row = [
                        phone, name, year, month,
                        str(receive_date) if receive_done else "",
                        receive_done,
                        str(deposit_date) if deposit_done else "",
                        deposit_done
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

            with st.form("edit_rentflow_form"):
                receive_done = st.checkbox("✅ 已收租", value=row_data["已收取租金"])
                if receive_done:
                    r_date = row_data["收取租金日期"]
                    receive_date = st.date_input("收租日期", value=pd.to_datetime(r_date).date() if r_date else pd.Timestamp.now().date())
                else:
                    receive_date = ""

                deposit_done = st.checkbox("🏦 已入帳", value=row_data["已存入租金"])
                if deposit_done:
                    d_date = row_data["存入租金日期"]
                    deposit_date = st.date_input("過數日期", value=pd.to_datetime(d_date).date() if d_date else pd.Timestamp.now().date())
                else:
                    deposit_date = ""

                if st.form_submit_button("💾 儲存修改"):
                    sheet_rentflow.update(f"E{gs_row}:H{gs_row}", [[
                        str(receive_date) if receive_done else "",
                        str(receive_done).upper(),
                        str(deposit_date) if deposit_done else "",
                        str(deposit_done).upper()
                    ]])
                    st.success("✅ 已成功修改紀錄")
                    st.rerun()