import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date, datetime, timedelta
import calendar
import re
import io

# ページ設定
st.set_page_config(page_title="期限管理システム", layout="wide")

# --- 0. スプレッドシート接続設定 ---
# 最もシンプルな接続方法に戻します
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name):
    try:
        # ttl=0 でキャッシュを無効化し、常に最新のデータを読み込む
        return conn.read(worksheet=sheet_name, ttl=0)
    except Exception:
        return pd.DataFrame()

def save_data(df, sheet_name):
    try:
        conn.update(worksheet=sheet_name, data=df)
        st.cache_data.clear() # 更新後にキャッシュをクリア
    except Exception as e:
        st.error(f"保存エラー: {e}")

# 初期シート作成（データが空の場合にヘッダーを作成）
def init_spreadsheet():
    sheets = {
        "expiry_records": ["id", "shop_id", "category", "item_name", "expiry_date", "input_date"],
        "item_master": ["id", "category", "item_name", "input_type"],
        "shop_master": ["id", "branch_id", "shop_id", "shop_name"],
        "branch_master": ["id", "branch_id", "branch_name"],
        "manager_shop_link": ["branch_id", "shop_id"]
    }
    for s, cols in sheets.items():
        df = load_data(s)
        if df is None or df.empty or len(df.columns) == 0:
            save_data(pd.DataFrame(columns=cols), s)

init_spreadsheet()

# --- 以降のコード（ログイン画面など）は以前と同じです ---
st.title("期限管理システム")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    auth_id = st.text_input("IDを入力してください", type="password")
    if st.button("ログイン"):
        if auth_id:
            st.session_state.logged_in = True
            st.session_state.auth_id = auth_id
            st.rerun()
else:
    st.write(f"ログイン中: {st.session_state.auth_id}")
    if st.button("ログアウト"):
        st.session_state.logged_in = False
        st.rerun()
    
    # ここにメイン機能を記述
