import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date, datetime, timedelta
import calendar
import re
import io

# --- 1. 接続・認証設定 ---
@st.cache_resource
def get_gspread_client():
    info = dict(st.secrets["gcp_service_account"])
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    return gspread.authorize(creds)

client = get_gspread_client()
spreadsheet_id = "10SPAlhEavpSZzHr2iCgu3U_gaaW6IHWgvjNTdvSWY9A"
sheet = client.open_by_key(spreadsheet_id)

# --- 2. データ操作関数 ---
def load_data(sheet_name):
    try:
        worksheet = sheet.worksheet(sheet_name)
        data = worksheet.get_all_values()
        if len(data) > 0:
            cols = [c.strip() for c in data[0]]
            return pd.DataFrame(data[1:], columns=cols)
        return pd.DataFrame()
    except:
        return pd.DataFrame()

def save_data(df, sheet_name):
    try:
        try:
            worksheet = sheet.worksheet(sheet_name)
        except:
            worksheet = sheet.add_worksheet(title=sheet_name, rows="2000", cols="20")
        worksheet.clear()
        df_save = df.fillna("")
        worksheet.update([df_save.columns.values.tolist()] + df_save.values.tolist())
        return True
    except Exception as e:
        st.error(f"保存エラー: {e}")
        return False

def validate_input(s, fmt):
    try:
        if fmt == "年月日":
            if not re.match(r"^\d{8}$", s): return False, "8桁の数字で入力してください"
            dt = datetime.strptime(s, "%Y%m%d").date()
        else:
            if not re.match(r"^\d{6}$", s): return False, "6桁の数字で入力してください"
            y, m = int(s[:4]), int(s[4:])
            if not (1 <= m <= 12): return False, "月が不正です"
            dt = date(y, m, calendar.monthrange(y, m)[1])
        if dt < date.today(): return False, "過去の日付は登録できません"
        return True, dt
    except:
        return False, "正しい日付を入力してください"

# CSV変換用関数
def convert_df(df):
    return df.to_csv(index=False).encode('utf_8_sig')

# --- 3. セッション管理 ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'user_info': None})

# --- ログイン ---
if not st.session_state['logged_in']:
    st.title("賞味期限管理システム")
    with st.form("login"):
        u_id = st.text_input("ID (数字4桁)", max_chars=4)
        u_pw = st.text_input("パスワード", type="password")
        if st.form_submit_button("ログイン", use_container_width=True):
            users = load_data("user_master")
            if not users.empty:
                users['id'] = users['id'].astype(str).str.strip()
                users['password'] = users['password'].astype(str).str.strip()
                user_row = users[(users['id'] == str(u_id).strip()) & (users['password'] == str(u_pw).strip())]
                if not user_row.empty:
                    st.session_state.update({'logged_in': True, 'role': user_row.iloc[0]['role'], 'user_info': user_row.iloc[0].to_dict()})
                    st.rerun()
                else: st.error("IDまたはパスワードが不正です")
    st.stop()

# --- 4. メインメニュー ---
role = st.session_state['role']
info = st.session_state['user_info']
st.sidebar.title(f"【{role}】")
st.sidebar.write(f"👤 {info['name']} 様")

if st.sidebar.button("ログアウト"):
    st.session_state.update({'logged_in': False, 'role': None})
    st.rerun()

# --- 5. 機能実装 ---

if role in ["マスター", "支部", "管轄者"]:
    st.title("⚙️ 管理パネル")
    tabs = ["期限確認", "アイテム管理", "店舗管理"]
    if role == "マスター": tabs.insert(0, "支部登録")
    if role == "支部": tabs.insert(1, "管轄者割り当て")
    
    selected_tabs = st.tabs(tabs)
    
    # --- 期限確認 (ダウンロード機能付) ---
    with selected_tabs[tabs.index("期限確認")]:
        st.subheader("📊 期限アラート・集計")
        recs = load_data("expiry_records")
        if not recs.empty:
            st.download_button("Excel(CSV)をダウンロード", data=convert_df(recs), file_name=f"expiry_report_{date.today()}.csv", mime='text/csv')
            recs['dt'] = pd.to_datetime(recs['expiry_date']).dt.date
            today = date.today()
            for _, r in recs.sort_values('expiry_date').iterrows():
                diff = (r['dt'] - today).days
                msg = f"{r['shop_id']} | {r['item_name']} ({r['expiry_date']})"
                if diff <= 0: st.error(f"🚨 【期限切れ】 {msg}")
                elif diff <= 7: st.warning(f"⚠️ 【1週間以内】 {msg}")
                elif diff <= 30: st.success(f"✅ 【1か月以内】 {msg}")

    # --- マスター：支部登録 ---
    if role == "マスター":
        with selected_tabs[0]:
            st.subheader("支部の管理")
            with st.expander("➕ 新規支部登録"):
                with st.form("reg_b"):
                    b_id = st.text_input("支部ID(4桁)", max_chars=4)
                    b_name = st.text_input("支部名")
                    b_pw = st.text_input("パスワード")
                    if st.form_submit_button("登録"):
                        u_df = load_data("user_master")
                        new_u = pd.DataFrame([{"id": b_id, "password": b_pw, "role":"支部", "target_id": b_id, "name": b_name}])
                        save_data(pd.concat([u_df, new_u]), "user_master")
                        st.success(f"支部 {b_name} を登録しました")
                        st.rerun()
            
            st.write("---")
            st.subheader("登録済み支部一覧")
            u_all = load_data("user_master")
            b_list = u_all[u_all["role"] == "支部"]
            for _, row in b_list.iterrows():
                col1, col2, col3 = st.columns([1, 2, 1])
                col1.write(row["id"])
                col2.write(row["name"])
                if col3.button("削除", key=f"del_b_{row['id']}"):
                    u_all = u_all[u_all["id"] != row["id"]]
                    save_data(u_all, "user_master")
                    st.rerun()

    # --- 支部：管轄者割り当て (複数選択対応・一覧表示) ---
    if "管轄者割り当て" in tabs:
        with selected_tabs[tabs.index("管轄者割り当て")]:
            st.subheader("管轄者の管理")
            shops_df = load_data("shop_master")
            my_shops = shops_df[shops_df["branch_id"] == info["id"]]
            
            with st.expander("➕ 管轄者の新規登録"):
                with st.form("reg_mgr"):
                    m_id = st.text_input("管轄者ID(4桁)", max_chars=4)
                    m_name = st.text_input("管轄者名")
                    m_pw = st.text_input("パスワード")
                    selected_shops = st.multiselect("担当店舗を選択 (複数可)", my_shops["shop_name"].tolist())
                    if st.form_submit_button("登録"):
                        u_df = load_data("user_master")
                        new_u = pd.DataFrame([{"id": m_id, "password": m_pw, "role":"管轄者", "target_id": ",".join(selected_shops), "name": m_name}])
                        save_data(pd.concat([u_df, new_u]), "user_master")
                        st.success(f"管轄者 {m_name} を登録しました")
                        st.rerun()
            
            st.write("---")
            st.subheader("登録済み管轄者一覧")
            u_all = load_data("user_master")
            m_list = u_all[u_all["role"] == "管轄者"]
            for _, row in m_list.iterrows():
                col1, col2, col3, col4 = st.columns([1, 1, 2, 1])
                col1.write(row["id"])
                col2.write(row["name"])
                col3.write(f"担当: {row['target_id']}")
                if col4.button("削除", key=f"del_m_{row['id']}"):
                    u_all = u_all[u_all["id"] != row["id"]]
                    save_data(u_all, "user_master")
                    st.rerun()

    # --- 店舗管理 (支部：店舗一覧・削除) ---
    if "店舗管理" in tabs:
        with selected_tabs[tabs.index("店舗管理")]:
            st.subheader("店舗の管理")
            if role == "支部":
                with st.expander("➕ 新規店舗追加"):
                    with st.form("reg_s"):
                        s_id = st.text_input("店舗ID(4桁)", max_chars=4)
                        s_name = st.text_input("店舗名")
                        s_pw = st.text_input("パスワード")
                        if st.form_submit_button("登録"):
                            u_df = load_data("user_master")
                            new_u = pd.DataFrame([{"id": s_id, "password": s_pw, "role":"店舗", "target_id": s_name, "name": s_name}])
                            save_data(pd.concat([u_df, new_u]), "user_master")
                            s_df = load_data("shop_master")
                            new_s = pd.DataFrame([{"shop_id": s_id, "branch_id": info["id"], "shop_name": s_name}])
                            save_data(pd.concat([s_df, new_s]), "shop_master")
                            st.success(f"店舗 {s_name} を登録しました")
                            st.rerun()
                
                st.write("---")
                st.subheader("管轄店舗一覧")
                s_all = load_data("shop_master")
                u_all = load_data("user_master")
                my_s_list = s_all[s_all["branch_id"] == info["id"]]
                st.download_button("店舗リストをダウンロード", data=convert_df(my_s_list), file_name="shops.csv")
                for _, row in my_s_list.iterrows():
                    col1, col2, col3 = st.columns([1, 2, 1])
                    col1.write(row["shop_id"])
                    col2.write(row["shop_name"])
                    if col3.button("削除", key=f"del_s_{row['shop_id']}"):
                        s_all = s_all[s_all["shop_id"] != row["shop_id"]]
                        u_all = u_all[u_all["id"] != row["shop_id"]]
                        save_data(s_all, "shop_master")
                        save_data(u_all, "user_master")
                        st.rerun()

    # --- アイテム管理 ---
    if "アイテム管理" in tabs:
        with selected_tabs[tabs.index("アイテム管理")]:
            st.subheader("アイテム管理")
            with st.expander("➕ アイテム追加"):
                with st.form("reg_i"):
                    c1, c2, c3 = st.columns(3)
                    i_cat = c1.selectbox("カテゴリ", ["冷蔵食材", "冷凍食材", "常温食材", "ドリンク", "ピックアップ"])
                    i_name = c2.text_input("アイテム名")
                    i_type = c3.radio("形式", ["年月日", "年月のみ"])
                    if st.form_submit_button("保存"):
                        idf = load_data("item_master")
                        new_i = pd.DataFrame([{"item_id": str(len(idf)+1), "category": i_cat, "item_name": i_name, "input_type": i_type}])
                        save_data(pd.concat([idf, new_i]), "item_master")
                        st.rerun()
            
            i_all = load_data("item_master")
            st.dataframe(i_all, use_container_width=True)
            if not i_all.empty:
                st.download_button("アイテムリストをダウンロード", data=convert_df(i_all), file_name="items.csv")
                target_del = st.selectbox("削除するアイテムを選択", i_all["item_name"].tolist())
                if st.button("選択したアイテムを削除"):
                    i_all = i_all[i_all["item_name"] != target_del]
                    save_data(i_all, "item_master")
                    st.rerun()

# --- B. 店舗：期限入力 ---
else:
    st.title(f"📦 {info['name']}")
    items = load_data("item_master")
    
    if not items.empty and "category" in items.columns:
        final_data = {}
        for cat in items["category"].unique():
            st.markdown(f"### 📍 {cat}")
            for _, row in items[items["category"] == cat].iterrows():
                with st.container(border=True):
                    st.write(f"**{row['item_name']}**")
                    ph = "20251231" if row['input_type']=="年月日" else "202512"
                    val_str = st.text_input(f"期限入力", key=f"inp_{row['item_id']}", placeholder=ph)
                    if val_str:
                        valid, res = validate_input(val_str, row['input_type'])
                        if valid:
                            final_data[row['item_id']] = {"cat": row['category'], "name": row['item_name'], "date": res}
                            st.caption(f"✅ 登録予定: {res}")
                        else: st.error(res)

        if st.button("一括登録を確定", type="primary", use_container_width=True):
            if final_data:
                df = load_data("expiry_records")
                new_recs = []
                for k, v in final_data.items():
                    new_recs.append({"id": datetime.now().strftime('%Y%m%d%H%M%S')+str(k), "shop_id": info['name'], "category": v["cat"], "item_name": v["name"], "expiry_date": str(v["date"]), "input_date": str(date.today())})
                save_data(pd.concat([df, pd.DataFrame(new_recs)]), "expiry_records")
                st.success("登録完了！")
                st.balloons()
