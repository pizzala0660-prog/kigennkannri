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
    # Streamlit Secretsから認証情報を取得
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
        return pd.DataFrame(worksheet.get_all_records())
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

# --- 3. バリデーション関数 (SQLite版のロジックを継承) ---
def validate_input(s, fmt):
    try:
        if fmt == "年月日":
            if not re.match(r"^\d{8}$", s): return False, "8桁の数字で入力してください"
            dt = datetime.strptime(s, "%Y%m%d").date()
        else: # 年月のみ
            if not re.match(r"^\d{6}$", s): return False, "6桁の数字で入力してください"
            y, m = int(s[:4]), int(s[4:])
            if not (1 <= m <= 12): return False, "月が不正です"
            dt = date(y, m, calendar.monthrange(y, m)[1])
        if dt < date.today(): return False, "過去の日付は登録できません"
        return True, dt
    except:
        return False, "正しい日付を入力してください"

# --- 4. 初期設定・ログイン管理 ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'user_info': None})

def init_system():
    # 必要なマスタ構成
    masters = {
        "user_master": ["id", "password", "role", "target_id", "name"],
        "expiry_records": ["id", "shop_id", "branch_id", "category", "item_name", "expiry_date", "input_date"],
        "shop_master": ["shop_id", "branch_id", "shop_name"],
        "branch_master": ["branch_id", "branch_name"],
        "item_master": ["item_id", "category", "item_name", "input_type"]
    }
    for s, cols in masters.items():
        df = load_data(s)
        if df.empty:
            save_data(pd.DataFrame(columns=cols), s)
    
    # マスターアカウント(9999)の強制確認
    users = load_data("user_master")
    if users.empty or "9999" not in users["id"].astype(str).values:
        admin_data = pd.DataFrame([{"id": "9999", "password": "admin", "role": "マスター", "target_id": "ALL", "name": "最高管理者"}])
        save_data(pd.concat([users, admin_data], ignore_index=True), "user_master")

init_system()

# --- ログイン画面 ---
if not st.session_state['logged_in']:
    st.title("🛡️ 賞味期限管理システム")
    st.info("初期ログイン ID: 9999 / PW: admin")
    with st.form("login"):
        u_id = st.text_input("ID (数字4桁)", max_chars=4)
        u_pw = st.text_input("パスワード", type="password")
        if st.form_submit_button("ログイン", use_container_width=True):
            users = load_data("user_master")
            # 型変換を行い確実に比較
            user_row = users[(users['id'].astype(str) == str(u_id)) & (users['password'].astype(str) == str(u_pw))]
            if not user_row.empty:
                st.session_state.update({'logged_in': True, 'role': user_row.iloc[0]['role'], 'user_info': user_row.iloc[0]})
                st.rerun()
            else:
                st.error("IDまたはパスワードが不正です")
    st.stop()

# --- 5. メインメニュー（ログイン後） ---
role = st.session_state['role']
info = st.session_state['user_info']
st.sidebar.title(f"【{role}】")
st.sidebar.write(f"👤 {info['name']} 様")

if st.sidebar.button("ログアウト"):
    st.session_state.update({'logged_in': False, 'role': None})
    st.rerun()

# --- A. 管理者ページ（マスター・支部共通） ---
if role in ["マスター", "支部"]:
    st.title("⚙️ 管理者ページ")
    tabs_list = ["アイテム管理", "店舗管理", "集計・警告"]
    if role == "マスター": tabs_list.insert(0, "支部・管轄者登録")
    selected_tabs = st.tabs(tabs_list)
    offset = 1 if role == "マスター" else 0

    # 支部・管轄者登録（マスターのみ）
    if role == "マスター":
        with selected_tabs[0]:
            st.subheader("支部IDおよび管轄責任者の登録")
            with st.form("reg_b"):
                c1, c2, c3 = st.columns(3)
                b_id = c1.text_input("支部ID(4桁)", max_chars=4)
                b_name = c2.text_input("管轄責任者名")
                b_pw = c3.text_input("初期PW")
                if st.form_submit_button("支部を登録"):
                    u_df = load_data("user_master")
                    new_u = pd.DataFrame([{"id": b_id, "password": b_pw, "role":"支部", "target_id": b_id, "name": b_name}])
                    save_data(pd.concat([u_df, new_u]), "user_master")
                    br_df = load_data("branch_master")
                    save_data(pd.concat([br_df, pd.DataFrame([{"branch_id":b_id, "branch_name":b_name}])]), "branch_master")
                    st.success("支部情報を登録しました")

    # アイテム管理
    with selected_tabs[offset]:
        st.subheader("アイテム管理")
        with st.expander("➕ 新規アイテム追加"):
            c1, c2, c3 = st.columns(3)
            i_cat = c1.selectbox("カテゴリ", ["冷蔵食材", "冷凍食材", "常温食材", "ドリンク", "ピック
