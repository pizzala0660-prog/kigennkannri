import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# ページ設定
st.set_page_config(page_title="接続検証", layout="wide")

st.title("💡 ステップ3：自動認識検証（フルコード）")
st.write("Secretsの [connections.gsheets] セクションから情報を自動読み込みします。")

try:
    # ライブラリの標準機能に任せるため、引数は最小限にします
    # これにより TypeError: got an unexpected keyword argument を回避します
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # データの読み込み試行
    # シートが空の場合は EmptyDataError になりますが、接続自体が成功していればOKです
    df = conn.read(ttl=0)
    
    st.success("✅ スプレッドシートの接続・読み込みに成功しました！")
    st.dataframe(df.head())

except Exception as e:
    st.error("❌ 接続または読み込みに失敗しました")
    st.exception(e)

st.info("これが成功すれば、次は元のシステムのログイン機能を合体させます。")
