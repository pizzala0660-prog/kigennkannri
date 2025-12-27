import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json

# ページ設定
st.set_page_config(page_title="接続検証", layout="wide")

st.title("💡 ステップ10：完全手動・接続オブジェクト構築")

# --- 0. 認証情報の定義 ---
# 文字列結合によりBase64の整合性を完全に維持
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
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/kigennkannri%40festive-bonsai-454509-b3.iam.gserviceaccount.com",
    "universe_domain": "googleapis.com"
}

spreadsheet_url = "https://docs.google.com/spreadsheets/d/10SPAlhEavpSZzHr2iCgu3U_gaaW6IHWgvjNTdvSWY9A/edit"

try:
    # --- 重要：不具合の多い st.connection をバイパス ---
    # 1. まず「空」の状態の接続クラスを作成（__init__を飛ばすためのハック）
    conn = GSheetsConnection.__new__(GSheetsConnection)
    
    # 2. 必要な内部変数を直接セット
    # これにより初期化時の自動認証（MalformedError）を回避します
    conn._connection_name = "gsheets"
    conn._kwargs = {"spreadsheet": spreadsheet_url}
    
    # 3. 認証情報を直接セット（これが最重要）
    # ライブラリの内部変数に直接鍵を叩き込みます
    conn._service_account_info = service_account_dict
    
    # 4. データの読み込み試行
    df = conn.read(spreadsheet=spreadsheet_url, ttl=0)
    
    st.success("✅ 手動オブジェクト構築により接続に成功しました！")
    st.dataframe(df.head())

except Exception as e:
    st.error("❌ この究極の手段でも失敗しました")
    st.exception(e)
