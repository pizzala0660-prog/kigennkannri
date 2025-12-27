import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json

# ページ設定
st.set_page_config(page_title="接続検証", layout="wide")

st.title("💡 ステップ9：完全マニュアル認証（最終解決策）")

# --- 0. 秘密鍵の定義（あなたが提示した最新の鍵） ---
# 文字列の結合により、Base64の整合性と改行を完全に維持します
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
    "PQgu+zNf7nLTAlvZcNPf5JqtLsFX9CQMOlVxduXBQXcSfD+tSrMITIwgZ7VmBpul\nqQMs6AEIvwKBgGtW6wbwnPv7/oaDFznoLAgPnOYY4YaDhHxd/E8fHsTmEy3YPjwE\nUOZFhvQV9L8v4zgZtkTmYtG7LwB1TAnb5BnyCcMyBBnlHS5wcl0Ie/PzcwnUx3ch\n+4FumMOWpEeJweioYkBgewD/ePidbqDtTCCvwAS6s2ueSATDtRXSZHXhAoGAPLq0\n9m719fxfDlpCAoUsxCjoUX9Xv2b8rW3+e3jqr9DmKOKnEzNjHmHx844U/WDdIZXw\ndPeGoXZ3KcMpu3F3ss5623zpoHaNXKZFHGUmSSuYbpxusuk/qokQSyiQlIt/jrqN\n58jcPEWszKoh6GPldF6s7SLGG2c6JIo6jgGncxkCgYA6+Wjt/GjTRJ+MP5vCnA+Y\nuM3MM0RracL/NqjbOYQRGFlDZ40veLGfZHsJezTf/bfZ0Jdsebpd+USh+RIdniBO\nnxLQb5B1rL2jecx/n9q1LGw4zgY6zDl8afbo3Uj0mDSLxJLacfnwXf08qURbRnaPz\n6Tbf3QJFD+Oz5N2VPWexeQ==\n"
    "-----END PRIVATE KEY-----\n"
)

# サービスアカウント情報の構築（※キー名を変更して重複エラーを回避）
service_account_dict = {
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

spreadsheet_url = "https://docs.google.com/spreadsheets/d/10SPAlhEavpSZzHr2iCgu3U_gaaW6IHWgvjNTdvSWY9A/edit"

try:
    # --- 重要：不具合の多い st.connection をバイパスする ---
    # 空の状態でインスタンスを作成
    conn = GSheetsConnection(connection_name="gsheets")
    
    # 【解決策】内部変数を「辞書アンパック」せずに直接上書きします
    # これにより TypeError: got an unexpected keyword argument 'type' を物理的に回避します
    conn._service_account_info = service_account_dict
    
    # データの読み込み試行
    # service_account引数を渡さず、セットした内部情報を自動で使わせます
    df = conn.read(spreadsheet=spreadsheet_url, ttl=0)
    
    st.success("✅ 内部変数の直接注入により、全ての引数エラーを回避して接続に成功しました！")
    st.dataframe(df.head())

except Exception as e:
    st.error("❌ 最終解決策でも失敗しました")
    st.exception(e)
