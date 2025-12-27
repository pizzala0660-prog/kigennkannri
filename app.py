import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# ページ設定
st.set_page_config(page_title="接続テスト", layout="wide")

# --- 0. スプレッドシート接続設定 ---
conn = st.connection("gsheets", type=GSheetsConnection)

# テスト用のデータ読み込み（エラーが出なければ接続成功）
st.title("期限管理システム - 接続テスト")

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
