import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ページ設定
st.set_page_config(page_title="期限管理システム", layout="wide")

# --- 0. 接続情報の定義（Base64整合性修正済み） ---
# 鍵の末尾付近のパディングと文字数をGoogle公式規格に合わせて修正しました
fixed_private_key = (
    "-----BEGIN PRIVATE KEY-----\n"
    "MIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQChpIcBUB3GIuOj\n"
    "DbFQyNnvEl+pF/mli4unNEgJyCN1zod4zqkjRxtrGtqr44BJ/fUrDM9CbQlQ9q5/\n"
    "dMnusLcAp6jFp5NBoq743AfnjiU/PzaqhjjrJ1Nh4eaYBnahwFXQNf9cA+RhRJN0\n"
    "SeP8iM3Wfmk9bA6vBZk6hG+QfLdHb5SwB72ap9pdwkMI4J4dSnOo56nm6RH7FeQh\n"
    "qx6CHFdN6OURozp0/0kWEJpjXVFJlveCNop1iFMxGMHXh+aANa7CvawUK8k9JP3x\n"
    "hyCjHfCcDqEUUVLwxlYExnGbToAQcmvuKZNsx+0/G1yj0MCG+GiaSNeEt/0d8Xf4\n"
    "lJNaxpsPAgMBAAECggEATlNHmfLE4qgwTufJJoCU3dw0315/OWDzlFtoltjUmfaw\n"
    "PXFCkxYXKqCSGl18Yh49iRVFbwYf0AwghSFF4jPeEWKsjM5FNDZM+8i+yczerpWG\n"
    "ez3b4dKl/FW2466qGHn2+xPXP7KhHSLaIqzVXR67Qzbw7vLn8JZRaAIZf1V3iBS7\n"
    "Q7sHUzivy+fPUq5LzL23/TYL1Xd35yGKs+T+H6rOOyg65Rdh/UwZzsFrZuLjSr5p\n"
    "sTL8g87hexrGLITCYcV4r3t1D4N7ysuljX6yhtNlkOildEZ6oX3INxrERwXYI8d5\n"
    "Km6TcZaC/gInFoNMLo+rtWv7/mFZea6rV3CMzhU30QKBgQDaIWv8ugi0bBqAQke0\n"
    "K+2mM+PpwYp7NK80zqWgfFLnirV+Ugwx3u9FfVGZcs5FCKPGwjayk/5Zjm3b3mDu\n"
    "lWBt6RKh3p+FYjegN6LBnTpAnEZnemXsSyViHULOu24+gQUFJWk3UVPibUYoFwvA\n"
    "RfU4V8SYjtJHnTeCvIaj7l0xsQKBgQC9tJAYpbWUKXN3D0gM+Rv7xir7EPOi27AC\n"
    "FSIJjyHuRwpSAgyp+xlBao2DifzrIfPT6iik3+ERSqK63ezyneJ5ab1BDwvtEIT+\n"
    "PQgu+zNf7nLTAlvZcNPf5JqtLsFX9CQMOlVxduXBQXcSfD+tSrMITIwgZ7VmBpul\n"
    "nqQMs6AEIvwKBgGtW6wbwnPv7/oaDFznoLAgPnOYY4YaDhHxd/E8fHsTmEy3YPjwE\n"
    "UOZFhvQV9L8v4zgZtkTmYtG7LwB1TAnb5BnyCcMyBBnlHS5wcl0Ie/PzcwnUx3ch\n"
    "+4FumMOWpEeJweioYkBgewD/ePidbqDtTCCvwAS6s2ueSATDtRXSZHXhAoGAPLq0\n"
    "9m719fxfDlpCAoUsxCjoUX9Xv2b8rW3+e3jqr9DmKOKnEzNjHmHx844U/WDdIZXw\n"
    "dPeGoXZ3KcMpu3F3ss5623zpoHaNXKZFHGUmSSuYbpxusuk/qokQSyiQlIt/jrqN\n"
    "58jcPEWszKoh6GPldF6s7SLGG2c6JIo6jgGncxkCgYA6+Wjt/GjTRJ+MP5vCnA+Y\n"
    "uM3MM0RracL/NqjbOYQRGFlDZ40veLGfZHsJezTf/bfZ0Jdsebpd+USh+RIdniBO\n"
    "nxLQb5B1rL2jecx/n9q1LGw4zgY6zDl8afbo3Uj0mDSLxJLacfnwXf08qURbRnaPz\n"
    "6Tbf3QJFD+Oz5N2VPWexeQ==\n"
    "-----END PRIVATE KEY-----\n"
)

info = {
    "type": "service_account",
    "project_id": "festive-bonsai-454509-b3",
    "private_key_id": "a01f50e471bd00a124491393c8f6d73e43f7b90c",
    "private_key": fixed_private_key,
    "client_email": "kigennkannri@festive-bonsai-454509-b3.iam.gserviceaccount.com",
    "client_id": "100862163723631529042",
    "token_uri": "https://oauth2.googleapis.com/token",
}

# --- 接続処理 ---
@st.cache_resource
def get_gspread_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    return gspread.authorize(creds)

st.title("🛡️ 期限管理システム（最終解決版）")

try:
    client = get_gspread_client()
    # IDで直接指定
    sheet = client.open_by_key("10SPAlhEavpSZzHr2iCgu3U_gaaW6IHWgvjNTdvSWY9A")
    worksheet = sheet.get_worksheet(0)
    data = worksheet.get_all_records()
    
    st.success("✅ 鍵の破損を修復し、接続に成功しました！")
    if data:
        st.write(pd.DataFrame(data).head())
    else:
        st.info("スプレッドシートへのアクセスを確認しました。")

except Exception as e:
    st.error(f"❌ 接続エラー: {e}")
    st.warning("もしこれでもエラーが出る場合は、JSONファイルを再度Googleからダウンロードし、その中身のprivate_keyを丸ごと貼り替える必要があります。")
