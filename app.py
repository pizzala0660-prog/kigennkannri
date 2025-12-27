import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json

# ページ設定
st.set_page_config(page_title="接続検証", layout="wide")

st.title("💡 ステップ8：完全手動認証初期化")

# --- 0. 秘密鍵の定義（改行コードを確実に含む形式） ---
# ここで定義する鍵は、Pythonが直接読み込むためブラウザの干渉を受けません
private_key_content = (
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
    "qQMs6AEIvwKBgGtW6wbwnPv7/oaDFznoLAgPnOYY4YaDhHxd/E8fHsTmEy3YPjwE\n"
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

# サービスアカウント情報の構築
creds_dict = {
    "connections": {
        "gsheets": {
            "type": "service_account",
            "project_id": "festive-bonsai-454509-b3",
            "private_key_id": "a01f50e471bd00a124491393c8f6d73e43f7b90c",
            "private_key": private_key_content,
            "client_email": "kigennkannri@festive-bonsai-454509-b3.iam.gserviceaccount.com",
            "client_id": "100862163723631529042",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/kigennkannri%40festive-bonsai-454509-b3.iam.gserviceaccount.com"
        }
    }
}

spreadsheet_url = "https://docs.google.com/spreadsheets/d/10SPAlhEavpSZzHr2iCgu3U_gaaW6IHWgvjNTdvSWY9A/edit"

try:
    # 接続をインスタンス化する前に、秘密鍵を含んだ「正しい辞書」を渡す方法に変更します
    # st.connectionは使わず、GSheetsConnectionを直接初期化します
    conn = GSheetsConnection(
        connection_name="gsheets",
        **creds_dict["connections"]["gsheets"]
    )
    
    # データの読み込み試行
    df = conn.read(spreadsheet=spreadsheet_url, ttl=0)
    
    st.success("✅ 手動認証による接続に完全成功しました！")
    st.dataframe(df.head())

except Exception as e:
    st.error("❌ 認証情報の直接投入でも失敗しました")
    st.exception(e)
