import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date, datetime

# ページ設定
st.set_page_config(page_title="期限管理システム", layout="wide")

# --- 1. 接続・認証設定 ---
@st.cache_resource
def get_gspread_client():
    # Secretsから認証情報を取得
    info = dict(st.secrets["gcp_service_account"])
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    return gspread.authorize(creds)

# 共通接続オブジェクトの取得
client = get_gspread_client()
spreadsheet_id = "10SPAlhEavpSZzHr2iCgu3U_gaaW6IHWgvjNTdvSWY9A"
sheet = client.open_by_key(spreadsheet_id)

# --- 2. データ操作用関数 ---
def load_data(sheet_name):
    try:
        worksheet = sheet.worksheet(sheet_name)
        return pd.DataFrame(worksheet.get_all_records())
    except gspread.exceptions.WorksheetNotFound:
        return pd.DataFrame()

def save_data(df, sheet_name):
    try:
        # シートがなければ作成、あれば取得
        try:
            worksheet = sheet.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = sheet.add_worksheet(title=sheet_name, rows="100", cols="20")
        
        # データの書き込み（ヘッダー付き）
        worksheet.clear()
        worksheet.update([df.columns.values.tolist()] + df.values.tolist())
        return True
    except Exception as e:
        st.error(f"保存エラー: {e}")
        return False

# 初期シート作成機能（システム起動時に必要な表を準備）
def init_spreadsheet():
    target_sheets = {
        "expiry_records": ["id", "shop_id", "category", "item_name", "expiry_date", "input_date"],
        "item_master": ["id", "category", "item_name", "input_type"],
        "shop_master": ["id", "branch_id", "shop_id", "shop_name"],
        "branch_master": ["id", "branch_id", "branch_name"],
        "manager_shop_link": ["branch_id", "shop_id"]
    }
    for s_name, cols in target_sheets.items():
        df_check = load_data(s_name)
        if df_check.empty:
            save_data(pd.DataFrame(columns=cols), s_name)

# 起動時に一度だけ実行
if 'initialized' not in st.session_state:
    init_spreadsheet()
    st.session_state['initialized'] = True

# --- 3. ログイン画面 ---
st.title("🛡️ 期限管理システム")

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    with st.form("login_form"):
        st.subheader("ログイン")
        user_id = st.text_input("ユーザーID")
        password = st.text_input("パスワード", type="password")
        submit = st.form_submit_button("ログイン")
        
        if submit:
            # 簡易認証（必要に応じてスプレッドシート管理に変更可能）
            if user_id == "admin" and password == "1234":
                st.session_state['logged_in'] = True
                st.rerun()
            else:
                st.error("IDまたはパスワードが違います")
else:
    st.sidebar.success(f"ログイン中: {user_id if 'user_id' in locals() else '管理者'}")
    if st.sidebar.button("ログアウト"):
        st.session_state['logged_in'] = False
        st.rerun()

    # --- メインコンテンツ ---
    st.write("### システムメニュー")
    # ここに各機能（期限入力、マスタ管理など）を実装していきます
    st.info("スプレッドシートに初期シートを作成しました。確認してください。")
