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
    # st.write("欄位清單:", tenant_df.columns.tolist())
    st.subheader("📋 租客資料")
    st.dataframe(tenant_df, use_container_width=True)

elif mode == "📆 租金處理進度":
    rentflow_data = sheet_rentflow.get_all_records()
    rentflow_df = pd.DataFrame(rentflow_data)
    rentflow_df.columns = rentflow_df.columns.str.strip()
    # st.write("欄位清單:", rentflow_df.columns.tolist())
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
    st.subheader("📆 租金收取／入帳狀態")

    flow_df = pd.DataFrame(sheet_rentflow.get_all_records())
    flow_df.columns = flow_df.columns.str.strip()
    flow_df["年度"]  = flow_df["年度"].astype(int)
    flow_df["月份"]  = flow_df["月份"].astype(int)
    st.dataframe(flow_df, use_container_width=True, height=350)

    tenants = ["全部"] + sorted(flow_df["租客姓名"].unique().tolist())
    sel_tenant = st.selectbox("🔍 篩選租客", tenants, index=0)

    if sel_tenant != "全部":
        sel_df = flow_df[flow_df["租客姓名"] == sel_tenant]
        st.markdown(f"### {sel_tenant} 的所有紀錄")
        st.dataframe(sel_df, use_container_width=True)
    else:
        sel_df = flow_df   # 之後「修改」表單仍需要用到

    st.divider()

    # ────────────────── ➕ 新增紀錄 ──────────────────
    st.markdown("## ➕ 新增月度紀錄（補建 / 預先建）")
    with st.form("add_flow"):
        col1, col2, col3 = st.columns(3)
        with col1:
            add_name = st.selectbox("租客姓名", sorted(sheet_tenants.col_values(1)[1:]))  # 假設 A 欄是姓名
        with col2:
            add_year  = st.number_input("年度", min_value=2020, max_value=2100, value=pd.Timestamp.today().year)
        with col3:
            add_month = st.selectbox("月份", list(range(1, 13)), index=pd.Timestamp.today().month - 1)

        if st.form_submit_button("✅ 新增紀錄"):
            # 防重複：若已存在同人同年月 → 給提醒
            dup = flow_df[
                (flow_df["租客姓名"] == add_name) &
                (flow_df["年度"] == add_year) &
                (flow_df["月份"] == add_month)
            ]
            if not dup.empty:
                st.warning("⚠️ 這筆月份紀錄已存在，不可重複新增。")
            else:
                sheet_rentflow.append_row([
                    sheet_tenants.find(add_name).offset(0, 1).value,  # 租客電話
                    add_name, add_year, add_month,
                    "", False, "", False
                ])
                st.success("✅ 已新增！")
                st.rerun()

    st.divider()

    # ────────────────── ✏️ 修改既有紀錄 ──────────────────
    st.markdown("## ✏️ 修改租金流程紀錄")
    # 先讓使用者選要改哪一列（用「租客｜年度-月份」當選項）
    sel_df = sel_df.sort_values(["租客姓名", "年度", "月份"], ascending=[True, False, False])
    display_opt = sel_df["租客姓名"] + "｜" + sel_df["年度"].astype(str) + "-" + sel_df["月份"].astype(str).str.zfill(2)
    choice = st.selectbox("選擇要修改的紀錄", display_opt)

    # 找到 Google Sheets 的實際列號
    idx = display_opt.tolist().index(choice)
    gs_row = sel_df.index[idx] + 2   # +2 因第 1 列標題, DataFrame index 從 0

    record = sel_df.iloc[idx]

    with st.form("edit_flow"):
        c1, c2 = st.columns(2)

        # —— 步驟 1：收租 —— #
        with c1:
            r_done = st.checkbox("✅ 已收租", value=record["已收取租金"])
            r_date = st.date_input(
                "收租日期",
                value = pd.to_datetime(record["收取租金日期"]).date()
                        if record["收取租金日期"] else pd.Timestamp.today().date(),
                disabled = not r_done,
                format="YYYY-MM-DD"
            )

        # —— 步驟 2：入帳 —— #
        with c2:
            d_done = st.checkbox("🏦 已入帳", value=record["已存入租金"])
            d_date = st.date_input(
                "入帳日期",
                value = pd.to_datetime(record["存入租金日期"]).date()
                        if record["存入租金日期"] else pd.Timestamp.today().date(),
                disabled = not d_done,
                format="YYYY-MM-DD"
            )

        if st.form_submit_button("💾 儲存修改"):
            # 若 checkbox 未勾則清空日期
            r_date_str = r_date.strftime("%Y-%m-%d") if r_done else ""
            d_date_str = d_date.strftime("%Y-%m-%d") if d_done else ""

            sheet_rentflow.update(
                f"E{gs_row}:H{gs_row}",
                [[r_date_str, str(r_done).upper(), d_date_str, str(d_done).upper()]]
            )
            st.success("✅ 已更新！")
            st.rerun()