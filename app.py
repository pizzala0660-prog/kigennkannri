import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json

# ページ設定
st.set_page_config(page_title="期限管理システム", layout="wide")

# --- 接続処理 ---
@st.cache_resource
def get_gspread_client():
    # GitHubにアップロードしたJSONファイル名を正確に指定
    json_file = "festive-bonsai-454509-b3-a01f50e471bd.json"
    
    # 権限範囲（スコープ）の設定
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    # JSONファイルを直接読み込んで認証
    # これにより、Base64の文字数エラーを物理的に回避します
    creds = Credentials.from_service_account_file(json_file, scopes=scopes)
    return gspread.authorize(creds)

st.title("🛡️ 期限管理システム（ファイル直結版）")

try:
    # 認証実行
    client = get_gspread_client()
    
    # スプレッドシートID（URLの中にある文字列）で開く
    spreadsheet_id = "10SPAlhEavpSZzHr2iCgu3U_gaaW6IHWgvjNTdvSWY9A"
    sheet = client.open_by_key(spreadsheet_id)
    
    # テスト読み込み（最初のシート）
    worksheet = sheet.get_worksheet(0)
    data = worksheet.get_all_records()
    
    st.success("✅ JSONファイルの直接読み込みにより、接続に成功しました！")
    
    if data:
        st.write("現在のデータサンプル:")
        st.dataframe(pd.DataFrame(data).head())
    else:
        st.info("スプレッドシートは正常に接続されました（データは空です）。")

except FileNotFoundError:
    st.error(f"❌ エラー: JSONファイルが見つかりません。GitHubにファイルがあるか確認してください。")
except Exception as e:
    st.error(f"❌ 接続エラー: {e}")

st.divider()
st.caption("この方式は、人間によるコピペミスを介さないため、最も安定しています。")
