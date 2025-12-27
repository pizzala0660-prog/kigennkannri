import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# ページ設定
st.set_page_config(page_title="期限管理システム", layout="wide")

# --- 0. スプレッドシート接続設定 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name):
    try:
        return conn.read(worksheet=sheet_name, ttl=0)
    except Exception:
        return pd.DataFrame()

def save_data(df, sheet_name):
    try:
        conn.update(worksheet=sheet_name, data=df)
        st.cache_data.clear() # 更新後にキャッシュをクリア
    except Exception as e:
        st.error(f"保存エラー: {e}")

# 初期シート作成
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

# --- ログイン画面 ---
st.title("期限管理システム")
# (以下、以前と同じログイン処理を続けてください)
