import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ページ設定
st.set_page_config(page_title="期限管理システム", layout="wide")

# --- 接続処理 ---
@st.cache_resource
def get_gspread_client():
    # Streamlit Secretsから安全に情報を取得
    info = dict(st.secrets["gcp_service_account"])
    
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    # Secretsの情報から直接認証を作成
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    return gspread.authorize(creds)

st.title("🛡️ 期限管理システム（セキュア接続版）")

try:
    client = get_gspread_client()
    
    # スプレッドシートID
    spreadsheet_id = "10SPAlhEavpSZzHr2iCgu3U_gaaW6IHWgvjNTdvSWY9A"
    sheet = client.open_by_key(spreadsheet_id)
    
    # 接続テスト（最初のシートを読み込み）
    worksheet = sheet.get_worksheet(0)
    data = worksheet.get_all_records()
    
    st.success("✅ Secrets経由で安全に接続に成功しました！")
    
    if data:
        st.dataframe(pd.DataFrame(data).head())
    else:
        st.info("接続は正常です。スプレッドシートが空のためデータはありません。")

except Exception as e:
    st.error(f"❌ 接続エラー: {e}")
    st.info("新しい鍵を発行し、StreamlitのSecretsに正しく貼り付けたか確認してください。")
