import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date, datetime, timedelta

# --- 0. スプレッドシート接続設定 ---
# Secretsから取得した情報を「修理」して認証を通します
s = st.secrets["connections"]["gsheets"]

# 鍵の改行コードを確実に復元
fixed_key = s["private_key"].replace("\\n", "\n")

# Googleが認める「サービスアカウント辞書」をコード内で強制的に再構築
creds_info = {
    "type": "service_account",
    "project_id": s["project_id"],
    "private_key_id": s["private_key_id"],
    "private_key": fixed_key,
    "client_email": s["client_email"],
    "client_id": s["client_id"],
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": s["client_x509_cert_url"],
    "universe_domain": "googleapis.com"
}

# 接続（service_account=引数を使うことで、閲覧専用モードを回避します）
conn = st.connection(
    "gsheets", 
    type=GSheetsConnection, 
    spreadsheet=s["spreadsheet"],
    service_account=creds_info
)

def load_data(sheet_name):
    try:
        return conn.read(worksheet=sheet_name, ttl=0)
    except Exception:
        return pd.DataFrame()

def save_data(df, sheet_name):
    try:
        conn.update(worksheet=sheet_name, data=df)
        st.cache_data.clear() 
    except Exception as e:
        st.error(f"保存エラー: {e}")

# 初期シート作成
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
        if df_check is None or df_check.empty or len(df_check.columns) == 0:
            save_data(pd.DataFrame(columns=cols), s_name)

init_spreadsheet()
# --- 1. ログイン画面 ---
st.title("期限管理システム")

try:
    # どこか一つのシートを読み込んでみる
    df = conn.read(worksheet="shop_master", ttl=0)
    st.success("スプレッドシートへの接続に成功しました！")
except Exception as e:
    st.warning("現在、接続設定を読み込み中です。設定が反映されるまでお待ちください。")

# ログイン画面
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    auth_id = st.text_input("IDを入力してください", type="password")
    if st.button("ログイン"):
        if auth_id == "9999": # テスト用ID
            st.session_state.logged_in = True
            st.rerun()
else:
    st.write("ログイン成功！システムを構築可能です。")












