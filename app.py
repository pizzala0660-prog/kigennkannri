import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# ページ設定
st.set_page_config(page_title="接続検証", layout="wide")

st.title("💡 ステップ1：公開読み込み検証")
st.write("このテストでは、サービスアカウントを使わずにスプレッドシートにアクセスできるかを確認します。")

# 接続先URL
spreadsheet_url = "https://docs.google.com/spreadsheets/d/10SPAlhEavpSZzHr2iCgu3U_gaaW6IHWgvjNTdvSWY9A/edit"

try:
    # 認証情報なしで接続を初期化
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # データの読み込み試行（url引数を使用）
    df = conn.read(spreadsheet=spreadsheet_url, ttl=0)
    
    st.success("✅ スプレッドシートの読み込みに成功しました！")
    st.write("スプレッドシートの内容（最初の5行）:")
    st.dataframe(df.head())

except Exception as e:
    st.error("❌ 読み込みに失敗しました")
    st.exception(e)

st.info("これが成功したら、次は『JSONファイルを使った認証』のテストに進みます。")








