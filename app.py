import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import pytz

# ────────────────── 🔒 密碼登入驗證 ──────────────────
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_name = ""

# 字體控制功能
if "font_size" not in st.session_state:
    st.session_state.font_size = 16
col_font1, col_font2 = st.columns([1, 1])
with col_font1:
    if st.button("🔍 放大字體"):
        st.session_state.font_size = min(st.session_state.font_size + 2, 32)
with col_font2:
    if st.button("🔎 縮小字體"):
        st.session_state.font_size = max(st.session_state.font_size - 2, 6)
st.markdown(f"""
    <style>
    html, body, [class*="css"]  {{
        font-size: {st.session_state.font_size}px !important;
    }}
    .stDataFrame div[data-testid="stDataFrame"] .ag-cell,
    .stDataEditor div[data-testid="stDataEditor"] .ag-cell {{
        font-size: {st.session_state.font_size}px !important;
    }}
    </style>
""", unsafe_allow_html=True)
# 主選單開始

if not st.session_state.authenticated:
    st.title("🏠 公司管理系統")
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
sheet_listings  = client.open_by_key(sheet_id).worksheet("租賃盤源")  # 租金流程表

# ────────────────── 版頭 & 功能選單 ──────────────────
st.title("🏠 公司管理系統")
main_mode = st.radio("📂 功能類別", ["👥 租客資料管理", "📆 租金處理進度", "🏢 租賃盤源管理"], horizontal=True)

tenant_data   = sheet_tenants.get_all_records()
tenant_df     = pd.DataFrame(tenant_data)
rentflow_data = sheet_rentflow.get_all_records()
rentflow_df   = pd.DataFrame(rentflow_data)
listing_data  = sheet_listings.get_all_records()
listing_df    = pd.DataFrame(listing_data)
for col in ["租客姓名", "單位地址", "租客電話", "固定水費", "固定電費", "每度水費", "每度電費", "起始水錶度數", "起始電錶度數"]:
    if col in tenant_df.columns:
        tenant_df[col] = tenant_df[col].astype(str)
for col in ["本月水錶度數", "上月水錶度數", "本月水費", "本月電錶度數", "上月電錶度數", "本月電費"]:
    if col in rentflow_df.columns:
        rentflow_df[col] = rentflow_df[col].astype(str)
for col in ["收租金額", "過戶金額"]:
    if col in rentflow_df.columns:
        rentflow_df[col] = pd.to_numeric(rentflow_df[col], errors="coerce")
for col in ["建築面積", "租金要求"]:
    if col in listing_df.columns:
        listing_df[col] = pd.to_numeric(listing_df[col], errors="coerce")
for col in ["最多人數限制", "業主電話"]:
    if col in listing_df.columns:
        listing_df[col] = listing_df[col].astype(str)

tenant_df["起始水錶度數"] = pd.to_numeric(tenant_df["起始水錶度數"].replace(['N/A', '', None], 0), errors="coerce").fillna(0.0)
tenant_df["起始電錶度數"] = pd.to_numeric(tenant_df["起始電錶度數"].replace(['N/A', '', None], 0), errors="coerce").fillna(0.0)

rentflow_df["本月水錶度數"] = pd.to_numeric(rentflow_df["本月水錶度數"].replace(['N/A', '', None], 0), errors="coerce").fillna(0.0)
rentflow_df["本月電錶度數"] = pd.to_numeric(rentflow_df["本月電錶度數"].replace(['N/A', '', None], 0), errors="coerce").fillna(0.0)

if main_mode == "👥 租客資料管理":
    # 讀取資料
    st.subheader("📋 租客資料")
    st.data_editor(tenant_df.set_index(pd.RangeIndex(start=1, stop=len(tenant_df)+1)), use_container_width=True, disabled=True)
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
            
            init_water_units = st.number_input("起始水錶度數", min_value=0.0, key="init_water_units")
            init_elec_units = st.number_input("起始電錶度數", min_value=0.0, key="init_elec_units")

            language = st.selectbox("通訊語言", ["中文", "英文"])
            management_fee = st.number_input("收租費", min_value=0.0, value=0.0)
            cutoff_day = st.selectbox("截數日（每月）", list(range(1, 32)))
            lease_type = st.selectbox("租約狀態", ["新租", "續租"], index=0)
            lease_start = st.date_input("租約開始日", key="lease_start", value=pd.Timestamp.now().date())
            lease_end   = st.date_input("租約結束日", key="lease_end", value=pd.Timestamp.now().date() + pd.DateOffset(years=2))

            if st.form_submit_button("✅ 新增"):
                tz_hk = pytz.timezone("Asia/Hong_Kong")
                ts = datetime.now(tz_hk).strftime("%Y-%m-%d %H:%M:%S")
                who = st.session_state.get("user_name", "unknown")
                exists = rentflow_df[
                    (tenant_df["租客姓名"] == name.strip()) &
                    (tenant_df["單位地址"] == address.strip())
                ]
                if not exists.empty:
                    st.warning("⚠️ 已存在相同租客姓名與單位地址的紀錄，請確認是否重覆輸入。")
                else:
                    new_row = [name, phone, address, rent, fix_water_fee, fix_electric_fee, water_fee, electric_fee, init_water_units, init_elec_units,
                            cutoff_day, language, management_fee, lease_type, str(lease_start), str(lease_end), ts, who]
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
            row = tenant_df.iloc[idx]

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
    
                init_water_units = st.number_input("起始水錶度數", min_value=0.0, value=float(row["起始水錶度數"]), key="init_water_units")
                init_elec_units = st.number_input("起始電錶度數", min_value=0.0, value=float(row["起始電錶度數"]), key="init_elec_units")

                language = st.selectbox("通訊語言", ["中文", "英文"], index=0 if row["通訊語言"]=="中文" else 1)
                management_fee = st.number_input("收租費", min_value=0.0, value=float(row["收租費"]))
                cutoff_day = st.selectbox("截數日（每月）", list(range(1, 32)), index=int(row["截數日"])-1)
                lease_type = st.selectbox("租約狀態", ["新租", "續租"], index = 0 if row["租約狀態"] != "續租" else 1)
                lease_start = st.date_input("租約開始日", value=pd.to_datetime(row["租約開始日"]) if "租約開始日" in row and row["租約開始日"] else pd.Timestamp.now().date())
                lease_end   = st.date_input("租約結束日", value=pd.to_datetime(row["租約結束日"]) if "租約結束日" in row and row["租約結束日"] else pd.Timestamp.now().date() + pd.DateOffset(years=2))

                if st.form_submit_button("💾 儲存修改"):
                    tz_hk = pytz.timezone("Asia/Hong_Kong")
                    ts = datetime.now(tz_hk).strftime("%Y-%m-%d %H:%M:%S")
                    who = st.session_state.get("user_name", "unknown")
                    new_row = [name, phone, address, rent, 
                               fix_water_fee, fix_electric_fee, 
                               water_fee, electric_fee,
                               cutoff_day, language, management_fee, lease_type,
                               str(lease_start), str(lease_end),
                               ts, who]
                    sheet_tenants.update(f"A{sheet_row}:O{sheet_row}", [new_row])
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
    month_start = pd.Timestamp(selected_year, selected_month, 1)
    filtered_df = rentflow_df[
        (rentflow_df["年度"] == selected_year) &
        (rentflow_df["月份"] == selected_month)
    ]

    # ────── ❷ 將租約日期欄位轉為 datetime，方便比對 ──────
    tenant_df["租約開始日"] = pd.to_datetime(tenant_df["租約開始日"], errors="coerce")
    tenant_df["租約結束日"] = pd.to_datetime(tenant_df["租約結束日"], errors="coerce")

    # ────── ❸ 只挑出「本月需要交租」的租客 (= 已開始且未退租) ──────
    active_df = tenant_df[
        pd.to_datetime(tenant_df["租約開始日"], errors="coerce") < month_start
    ].copy()

    # 續租 = 一律要收
    cond_renew = tenant_df["租約狀態"] == "續租"

    # 新租 = 起租日在本月 1 號「之前」才要收(即首租期由下一月開始)
    cond_new   = (
        (tenant_df["租約狀態"] != "續租") &            # 空白或「新租」
        (tenant_df["租約開始日"] < month_start)        # 嚴格 < 本月 1 日
    )

    active_df = tenant_df[cond_renew | cond_new].copy()

    st.markdown(f"### 📋 {selected_year} 年 {selected_month} 月租金流程")
    active_df["key"]   = active_df["租客姓名"] + "｜" + active_df["單位地址"].astype(str)
    filtered_df["key"] = filtered_df["租客姓名"] + "｜" + filtered_df["單位地址"].astype(str)
    
    paid_df   = filtered_df[filtered_df["已收取租金"].astype(str).str.upper() == "TRUE"]
    paid_rooms = len(paid_df)                         # ← 行數就是房間數
    paid_keys  = set(paid_df["key"])                  # ← 用來做未交租比對
    total_rooms  = len(active_df)                     # 全部房間
    unpaid_df = active_df[~active_df["key"].isin(paid_keys)]
    unpaid_rooms = len(unpaid_df)           # 未交租房間數
    
    received_not_deposited_df = filtered_df[
        (filtered_df["已收取租金"].astype(str).str.upper() == "TRUE") &
        (filtered_df["已存入租金"].astype(str).str.upper() != "TRUE")
    ]
    received_not_deposited_count = len(received_not_deposited_df)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📋 總租客數", total_rooms)
    col2.metric("✅ 已交租", paid_rooms)
    col3.metric("⚠️ 未交租", unpaid_rooms)
    col4.metric("🏦 待入帳", received_not_deposited_count)
    st.data_editor(filtered_df.drop(columns=["key"]).set_index(pd.RangeIndex(start=1, stop=len(filtered_df.drop(columns=["key"]))+1)), use_container_width=True, disabled=True)

    # ❶ 顯示未交租租客
    if not unpaid_df.empty:
        st.markdown("### ❌ 未交租租客名單")
        show_cols = [c for c in ["租客姓名", "租客電話", "單位地址", "每月固定租金"] if c in unpaid_df.columns]
        view_df = unpaid_df[show_cols].rename(columns={"每月固定租金": "應付租金"})
        st.data_editor(view_df.set_index(view_df.index + 2), use_container_width=True, disabled=True)
    else:
        st.success(f"🥳 所有{selected_year} 年 {selected_month} 月租客都已完成收租")

    # ❷ 顯示已收租但未入帳租客
    if filtered_df[filtered_df["已收取租金"].astype(str).str.upper() == "TRUE"].empty:
        st.info(f"尚未有 {selected_year} 年 {selected_month} 月的收租紀錄")
    elif not received_not_deposited_df.empty:
        st.markdown("### 🏦 已收租但尚未過戶名單")
        show_cols = [c for c in ["租客姓名", "租客電話", "單位地址", "收租金額", "收取租金日期"] if c in received_not_deposited_df.columns]
        view_df2 = received_not_deposited_df[show_cols]
        st.data_editor(view_df2.set_index(view_df2.index + 1), use_container_width=True, disabled=True)
    else:
        st.success(f"🥳 所有{selected_year} 年 {selected_month} 月已收租紀錄皆已完成過戶")

    sub_mode = st.radio("🧾 租金紀錄操作", ["➕ 新增租金紀錄", "✏️ 更改租金紀錄", "🗑️ 刪除租金紀錄"], horizontal=True)
    if sub_mode == "➕ 新增租金紀錄":
        st.subheader("➕ 新增租金紀錄")
        
        # tenant_df["key"] = tenant_df["租客姓名"] + "｜" + tenant_df["單位地址"]
        # filtered_df["key"] = filtered_df["租客姓名"] + "｜" + filtered_df["單位地址"]

        # # 取得該月份的第一天
        # month_start = pd.Timestamp(selected_year, selected_month, 1)

        # # 只選擇租期已生效，且未到期的租客
        # tenant_df["租約開始日"] = pd.to_datetime(tenant_df["租約開始日"], errors="coerce")
        # tenant_df["租約結束日"] = pd.to_datetime(tenant_df["租約結束日"], errors="coerce")
        # tenant_df["key"] = tenant_df["租客姓名"] + "｜" + tenant_df["單位地址"]

        # cond_renew = (
        #     (tenant_df["租約狀態"] == "續租") &
        #     (tenant_df["租約開始日"] < month_start) &                # 已開始
        #     (
        #         tenant_df["租約結束日"].isna() |                      # 沒有結束日
        #         (tenant_df["租約結束日"] >= month_start)              # 或尚未到期
        #     )
        # )

        # cond_new = (
        #     (tenant_df["租約狀態"] != "續租") &
        #     (tenant_df["租約開始日"] < month_start)
        # )

        # active_df = tenant_df[cond_renew | cond_new].copy()

        # active_df = tenant_df[
        #     (tenant_df["租約開始日"] < month_start) &
        #     ((tenant_df["租約結束日"].isna()) | (tenant_df["租約狀態"] == "續租") | (tenant_df["租約結束日"] >= month_start))
        # ]

        # # 計算已交租租客 key
        # filtered_df["key"] = filtered_df["租客姓名"] + "｜" + filtered_df["單位地址"]
        # paid_keys = set(filtered_df[filtered_df["已收取租金"].astype(str).str.upper() == "TRUE"]["key"])

        # # 從應收租的租客中，排除已交租的，得到「應收但未交」
        # unpaid_df = active_df[~active_df["key"].isin(paid_keys)]

        if unpaid_df.empty:
            st.info("🥳 所有租客都已繳交該月份租金，無需新增紀錄。")
            st.stop()

        selector = unpaid_df["租客姓名"] + "｜" + unpaid_df["單位地址"]
        sel_opt = st.selectbox("租客", selector)

        idx = selector.tolist().index(sel_opt)
        default_phone = str(unpaid_df.iloc[idx]["租客電話"]).lstrip("'").strip()
        name = sel_opt.split("｜")[0]
        address = unpaid_df.iloc[idx]["單位地址"]
        default_rent = float(unpaid_df.iloc[idx]["每月固定租金"])

        calculate_done  = st.checkbox("🧮 已計算費用", key="calculate_done_out")
        receive_done  = st.checkbox("✅ 已收租", key="receive_done_out")
        deposit_done  = st.checkbox("🏦 已入帳", key="deposit_done_out")

        with st.form("add_rentflow_form"):
            phone = st.text_input("租客電話", value=default_phone, disabled=True)

            year = st.number_input("年度", min_value=2000, max_value=2100, value=pd.Timestamp.now().year)
            month = st.selectbox("月份", list(range(1, 13)), index=pd.Timestamp.now().month - 1)

            trow = unpaid_df.iloc[idx]                        # 取得該租客在 tenant_df 的資料
            prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
            matching_prev = rentflow_df[
                (rentflow_df["租客姓名"] == name) &
                (rentflow_df["單位地址"] == address) &
                (rentflow_df["年度"] == prev_year) &
                (rentflow_df["月份"] == prev_month)
            ]

            if not matching_prev.empty:
                prev_row = matching_prev.iloc[0]
                prev_water_units = float(prev_row["本月水錶度數"]) if str(prev_row["本月水錶度數"]).replace('.', '', 1).isdigit() else float(trow["起始水錶度數"])
                prev_elec_units  = float(prev_row["本月電錶度數"]) if str(prev_row["本月電錶度數"]).replace('.', '', 1).isdigit() else float(trow["起始電錶度數"])
            else:
                prev_water_units = float(trow["起始水錶度數"]) if str(trow["起始水錶度數"]).replace('.', '', 1).isdigit() else 0
                prev_elec_units  = float(trow["起始電錶度數"]) if str(trow["起始電錶度數"]).replace('.', '', 1).isdigit() else 0

            if calculate_done:
                curr_water_units = st.number_input("💧 本月水錶度數", min_value=0.0, step=0.1, value=0.0)
                curr_elec_units  = st.number_input("⚡ 本月電錶度數", min_value=0.0, step=0.1, value=0.0)
                water_units = max(0, round(float(curr_water_units) - float(prev_water_units)))
                elec_units  = max(0, round(float(curr_elec_units)  - float(prev_elec_units)))

                # ② 計算水費
                if str(trow["每度水費"]).upper() != "N/A" and water_units:
                    water_fee = water_units * float(trow["每度水費"])
                elif str(trow["固定水費"]).upper() != "N/A":
                    water_fee = float(trow["固定水費"])
                else:
                    water_fee = 0

                # ③ 計算電費
                if str(trow["每度電費"]).upper() != "N/A" and elec_units:
                    elec_fee = elec_units * float(trow["每度電費"])
                elif str(trow["固定電費"]).upper() != "N/A":
                    elec_fee = float(trow["固定電費"])
                else:
                    elec_fee = 0

                calculate_amt = default_rent + water_fee + elec_fee
                water_elec_fee = water_fee + elec_fee
                calculate_date = st.date_input("📅 計算日期", value=pd.Timestamp.now().date(), key="calculated_date_in")
                st.info(f"💧 水費: HK$ {water_fee:,.0f}")
                st.info(f"⚡ 電費: HK$ {elec_fee:,.0f}")
                st.info(f"💰 租金:HK$ {default_rent:,.0f}")
                st.info(f"🔢 合共: HK$ {calculate_amt:,.0f}")
            else:
                water_fee = ""
                elec_fee = ""
                water_elec_fee = ""
                calculate_date = ""
                calculate_amt = ""

            if receive_done:
                receive_date = st.date_input("📅 收租日期", value=pd.Timestamp.now().date(), key="receive_date_in")
                receive_amt  = st.number_input("💰 收租金額", min_value=0.0, value=default_rent, key="receive_amt")
            else:
                receive_date = ""
                receive_amt = ""
            if deposit_done:
                deposit_date = st.date_input("📅 過數日期", value=pd.Timestamp.now().date(), key="deposit_date_in")
                deposit_amt  = st.number_input("💰 過戶金額", min_value=0.0, value=calculate_amt, key="deposit_amt")
            else:
                deposit_date = ""
                deposit_amt = ""

            if st.form_submit_button("✅ 新增"):
                tz_hk = pytz.timezone("Asia/Hong_Kong")
                ts = datetime.now(tz_hk).strftime("%Y-%m-%d %H:%M:%S")
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
                        str(calculate_date) if calculate_done else "",
                        calculate_done,
                        water_elec_fee  if calculate_done  else "",
                        str(receive_date) if receive_done else "",
                        receive_done,
                        receive_amt  if receive_done  else "",
                        str(deposit_date) if deposit_done else "",
                        deposit_done,
                        deposit_amt  if deposit_done else "",
                        water_units, prev_water_units, water_fee,
                        elec_units, prev_elec_units, elec_fee,
                        calculate_amt,
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
            rentflow_df["選項"] = (
                rentflow_df["租客姓名"] + "｜" +
                rentflow_df["單位地址"] + "｜" +
                rentflow_df["年度"].astype(str) + "-" + rentflow_df["月份"].astype(str).str.zfill(2)
            )
            choice = st.selectbox("選擇要修改的紀錄", rentflow_df["選項"].tolist())
            idx = rentflow_df[rentflow_df["選項"] == choice].index[0]
            row_data = rentflow_df.loc[idx]
            gs_row = idx + 2  # Google Sheets 的列數（從第2列開始）

            calculate_done  = st.checkbox("🧮 已計算費用", value=str(row_data["應付金額"]).upper() == "TRUE")
            receive_done = st.checkbox("✅ 已收租", value=str(row_data["已收取租金"]).upper() == "TRUE")
            deposit_done = st.checkbox("🏦 已入帳", value=str(row_data["已存入租金"]).upper() == "TRUE")

            with st.form("edit_rentflow_form"):
                if calculate_done:
                    calculate_date = st.date_input("📅 計算日期", value=pd.to_datetime(row_data["計算費用日期"]).date() if row_data["計算費用日期"] else pd.Timestamp.now().date(), key="calculate_date_in")
                    calculate_amt  = st.number_input("💰 計算金額", min_value=0.0, value=float(row_data["應付金額"]) if row_data["應付金額"] else 0.0, key="calculate_amt")
                else:
                    calculate_date = ""
                    calculate_amt = ""
                if receive_done:
                    receive_date = st.date_input("📅 收租日期", value=pd.to_datetime(row_data["收取租金日期"]).date() if row_data["收取租金日期"] else pd.Timestamp.now().date(), key="receive_date_in")
                    receive_amt  = st.number_input("💰 收租金額", min_value=0.0, value=float(row_data["收租金額"]) if row_data["收租金額"] else 0.0, key="receive_amt")
                else:
                    receive_date = ""
                    receive_amt = ""
                if deposit_done:
                    deposit_date = st.date_input("📅 過數日期", value=pd.to_datetime(row_data["存入租金日期"]).date() if row_data["存入租金日期"] else pd.Timestamp.now().date(), key="deposit_date_in")
                    deposit_amt  = st.number_input("💰 過戶金額", min_value=0.0, value=float(row_data["收租金額"]) if row_data["收租金額"] else 0.0, key="deposit_amt") # 理論上收租金額=過戶金額
                else:
                    deposit_date = ""
                    deposit_amt = ""

                if st.form_submit_button("💾 儲存修改"):
                    tz_hk = pytz.timezone("Asia/Hong_Kong")
                    ts = datetime.now(tz_hk).strftime("%Y-%m-%d %H:%M:%S")
                    who = st.session_state.get("user_name", "unknown")
                    sheet_rentflow.update(f"F{gs_row}:M{gs_row}", [[
                        str(calculate_date) if calculate_done else "",
                        calculate_done,
                        calculate_amt  if calculate_done  else "",
                        str(receive_date) if receive_done else "",
                        str(receive_done).upper(),
                        receive_amt if receive_done else "",
                        str(deposit_date) if deposit_done else "",
                        str(deposit_done).upper(),
                        deposit_amt if deposit_done else "",
                        calculate_amt, 
                        ts, who
                    ]])
                    st.success("✅ 已成功修改紀錄")
                    st.rerun()

    elif sub_mode == "🗑️ 刪除租金紀錄":
        st.subheader("🗑️ 刪除租金紀錄")
        if rentflow_df.empty:
            st.info("目前尚無紀錄可刪除")
        else:
            selector = (
                rentflow_df["租客姓名"] + "｜" +
                rentflow_df["單位地址"] + "｜" +
                rentflow_df["年度"].astype(str) + "-" + rentflow_df["月份"].astype(str).str.zfill(2)
            )
            choice    = st.selectbox("選擇要刪除的紀錄", selector)
            idx       = selector.tolist().index(choice)
            sheet_row = idx + 2  # Google Sheets 的列數（從第2列開始）

            if st.button("⚠️ 確認刪除"):
                sheet_rentflow.delete_rows(sheet_row)
                st.warning(f"✅ 已刪除：{choice}")
                st.rerun()

elif main_mode == "🏢 租賃盤源管理":
    st.markdown("### 🔍 查詢間隔類型的盤源")
    layout_options = sorted(listing_df["間隔"].dropna().unique())
    layout_options.insert(0, "所有類型")  # 插入「全部」在最前面
    layout_selected = st.selectbox("📐 選擇間隔類型", layout_options)

    if layout_selected == "所有類型":
        filtered_listing = listing_df
    else:
        filtered_listing = listing_df[listing_df["間隔"] == layout_selected]
    st.write(f"共找到{len(filtered_listing)}個{layout_selected}盤源")
    st.markdown(f"### 🏢 {layout_selected}盤源一覽")
    st.data_editor(filtered_listing.set_index(pd.RangeIndex(start=1, stop=len(filtered_listing)+1)), use_container_width=True, disabled=True)
    
    sub_mode = st.radio("📋 盤源操作選項", ["➕ 新增盤源", "✏️ 更改盤源", "🗑️ 刪除盤源"], horizontal=True)
    if sub_mode == "➕ 新增盤源":
        with st.form("add_listing_form"):
            address   = st.text_input("🏠 物業地址")
            unit_type = st.selectbox("🏢 單位類型", ["劏房", "分契樓", "獨立單位"])
            layout    = st.selectbox("🛏️ 間隔", ["開放式", "套房", "一房一廳", "兩房一廳", "三房一廳"])
            gross     = st.number_input("📏 建築面積 (呎)", min_value=0.0)
            rent_amt  = st.number_input("💰 租金要求 (HKD)", min_value=0.0)
            bld_type  = st.selectbox("🏗️ 物業類型", ["唐樓", "居屋", "洋樓"])
            src_type  = st.selectbox("📌 盤源權限", ["獨家", "合作", "自己盤"])
            owner     = st.text_input("👤 業主姓名")
            owner_tel = st.text_input("📱 業主電話")
            nation    = st.selectbox("🌏 預期租客國籍", ["中國", "無限制", "外國"])
            max_occ   = st.number_input("👥 最多人數限制", min_value=1, step=1, value=1)
            remark    = st.text_area("📝 備註")
            date      = st.date_input("📅 上架日期", value=pd.Timestamp.now().date())

            if st.form_submit_button("✅ 新增"):
                dup = listing_df[(listing_df["物業地址"] == address.strip())]
                if not dup.empty:
                    st.warning("⚠️ 此地址已存在盤源，請確認是否重覆。")
                else:
                    tz_hk = pytz.timezone("Asia/Hong_Kong")
                    ts = datetime.now(tz_hk).strftime("%Y-%m-%d %H:%M:%S")
                    who = st.session_state.get("user_name", "unknown")
                    sheet_listings.append_row([
                        address, unit_type, layout, gross, rent_amt, bld_type,
                        src_type, owner, owner_tel, nation, 
                        max_occ, remark, date.strftime("%Y-%m-%d"), ts, who
                    ], value_input_option="RAW")
                    st.success("✅ 盤源已新增")
                    st.rerun()

    # ─────────────── ➋ 更改盤源 ───────────────
    elif sub_mode == "✏️ 更改盤源":
        if listing_df.empty:
            st.info("目前沒有盤源可修改。")
        else:
            selector = listing_df["物業地址"]
            choice   = st.selectbox("選擇盤源", selector)
            idx      = selector.tolist().index(choice)
            sheet_row = idx + 2
            row      = listing_df.iloc[idx]

            with st.form("edit_listing_form"):
                address   = st.text_input("🏠 物業地址", row["物業地址"])
                unit_type = st.selectbox("🏢 單位類型", ["劏房", "分契樓", "獨立單位"], index=["劏房", "分契樓", "獨立單位"].index(row["單位類型"]))
                layout    = st.selectbox("🛏️ 間隔", ["開放式", "套房", "一房一廳", "兩房一廳", "三房一廳"], index=["開放式", "套房", "一房一廳", "兩房一廳", "三房一廳"].index(row["間隔"]))
                gross     = st.number_input("📏 建築面積 (呎)", min_value=0.0, value=float(row["建築面積(呎)"]))
                rent_amt  = st.number_input("💰 租金要求 (HKD)", min_value=0.0, value=float(row["租金要求"]))
                bld_type  = st.selectbox("🏗️ 物業類型", ["唐樓", "居屋", "洋樓"],
                                         index=["唐樓", "居屋", "洋樓"].index(row["物業類型"]))
                src_type  = st.selectbox("📌 盤源權限", ["獨家", "合作", "自己盤"],
                                         index=["獨家", "合作", "自己盤"].index(row["盤源權限"]))
                owner     = st.text_input("👤 業主姓名", row["業主姓名"])
                owner_tel = st.text_input("📱 業主電話", row["業主電話"])
                nation    = st.selectbox("🌏 預期租客國籍", ["中國", "無限制", "外國"],
                                         index=["中國", "無限制", "外國"].index(row["預期租客國籍"]))
                max_occ   = st.number_input("👥 最多人數限制", min_value=1, step=1, value=1 if str(row["最多人數限制"])=="N/A" else int(row["最多人數限制"]))
                remark    = st.text_area("📝 備註", row["備註"])

                if st.form_submit_button("💾 儲存修改"):
                    tz_hk = pytz.timezone("Asia/Hong_Kong")
                    ts = datetime.now(tz_hk).strftime("%Y-%m-%d %H:%M:%S")
                    who = st.session_state.get("user_name", "unknown")
                    sheet_listings.update(
                        f"A{sheet_row}:O{sheet_row}",
                        [[address, unit_type, layout, gross, rent_amt, bld_type, 
                          src_type, owner, owner_tel, nation,
                          max_occ, remark, str(row["上架日期"]), ts, who]], value_input_option="RAW"
                    )
                    st.success("✅ 已成功更改盤源")
                    st.rerun()

    # ─────────────── ➌ 刪除盤源 ───────────────
    elif sub_mode == "🗑️ 刪除盤源":
        if listing_df.empty:
            st.info("目前沒有盤源可刪除。")
        else:
            selector = listing_df["物業地址"]
            choice   = st.selectbox("選擇盤源", selector)
            idx      = selector.tolist().index(choice)
            sheet_row = idx + 2
            if st.button("⚠️ 確認刪除"):
                sheet_listings.delete_rows(sheet_row)
                st.warning(f"已刪除：{choice}")
                st.rerun()