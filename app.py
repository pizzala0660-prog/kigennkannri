import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date, datetime, timedelta

# ページ設定
st.set_page_config(page_title="期限管理システム", layout="wide")

# --- 0. スプレッドシート接続設定 ---
# Secretsから取得した情報を一度辞書(creds)にコピーします
creds = dict(st.secrets["connections"]["gsheets"])

# 【重要】秘密鍵のゴミ掃除
# コピペ時に混じった「スペース」や「改行の化け」をプログラムで強制的に直します
if "private_key" in creds:
    # 1. 誤って混じった半角・全角スペースをすべて消去
    creds["private_key"] = creds["private_key"].replace(" ", "").replace("　", "")
    # 2. 文字列としての「\n」を、本物の改行コードに変換
    creds["private_key"] = creds["private_key"].replace("\\n", "\n")
    # 3. 繋がってしまったヘッダー部分などを正規の形に復元（保険的処理）
    if "-----BEGINPRIVATEKEY-----" in creds["private_key"]:
        creds["private_key"] = creds["private_key"].replace("-----BEGINPRIVATEKEY-----", "-----BEGIN PRIVATE KEY-----\n")
    if "-----ENDPRIVATEKEY-----" in creds["private_key"]:
        creds["private_key"] = creds["private_key"].replace("-----ENDPRIVATEKEY-----", "\n-----END PRIVATE KEY-----")

# 掃除した後のcredsを使って接続
conn = st.connection("gsheets", type=GSheetsConnection, **creds)

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







