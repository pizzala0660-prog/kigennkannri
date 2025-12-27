import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json

# --- 0. スプレッドシート接続設定 ---
# Secretsから取得した生データを辞書形式に変換します
s = st.secrets["connections"]["gsheets"]

# 秘密鍵（private_key）に含まれる「\\n」という文字を「本物の改行コード」に復元します
# これにより、Googleが正しい鍵として認識できるようになります
fixed_private_key = s["private_key"].replace("\\n", "\n")

# Streamlitの内部ライブラリが「サービスアカウント」として認識するための辞書を再構築します
service_account_info = {
    "type": s["type"],
    "project_id": s["project_id"],
    "private_key_id": s["private_key_id"],
    "private_key": fixed_private_key,
    "client_email": s["client_email"],
    "client_id": s["client_id"],
    "auth_uri": s["auth_uri"],
    "token_uri": s["token_uri"],
    "auth_provider_x509_cert_url": s["auth_provider_x509_cert_url"],
    "client_x509_cert_url": s["client_x509_cert_url"],
    "universe_domain": s.get("universe_domain", "googleapis.com")
}

# 【重要】service_account引数に上記の辞書を直接渡します
# これにより「Public Spreadsheet（公開用）」ではなく「CRUD（編集権限あり）」として接続されます
conn = st.connection(
    "gsheets",
    type=GSheetsConnection,
    spreadsheet=s["spreadsheet"],
    service_account=service_account_info
)

def save_data(df, sheet_name):
    try:
        # スプレッドシートへデータを保存し、キャッシュをクリアします
        conn.update(worksheet=sheet_name, data=df)
        st.cache_data.clear() 
    except Exception as e:
        st.error(f"保存エラー: {e}")

# 初期シート作成（データが空の場合に表の見出しを作成）
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

# 接続を確立し、初期設定を実行
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









