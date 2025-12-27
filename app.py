import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json

# ページ設定
st.set_page_config(page_title="期限管理システム", layout="wide")

# --- 0. スプレッドシート接続設定 ---
# Secretsに保存した「1行のJSON」を読み込みます
json_str = st.secrets["connections"]["gsheets"]["json_base64"]

# 文字列をPythonの辞書形式に変換します
creds_dict = json.loads(json_str)

# 秘密鍵（private_key）の中にある「\n」という文字を、本物の改行コードに変換します
if "private_key" in creds_dict:
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

# 修理した設定を使って接続を確立します
conn = st.connection("gsheets", type=GSheetsConnection, **creds_dict)

# --- 1. データ読み込み・保存用関数 ---
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

# (以下、以前の init_spreadsheet() やログイン処理へ続く)
# 接続が確立してから実行
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





