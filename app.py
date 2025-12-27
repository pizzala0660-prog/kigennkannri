import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date, datetime, timedelta

# ページ設定
st.set_page_config(page_title="接続検証", layout="wide")

st.title("💡 ステップ7：内部クラス直接呼び出し検証")

# --- 0. 認証情報の定義（あなたが提示した新しい鍵を直接組み込み） ---
fixed_private_key = "-----BEGIN PRIVATE KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQChpIcBUB3GIuOj\nDbFQyNnvEl+pF/mli4unNEgJyCN1zod4zqkjRxtrGtqr44BJ/fUrDM9CbQlQ9q5/\ndMnusLcAp6jFp5NBoq743AfnjiU/PzaqhjjrJ1Nh4eaYBnahwFXQNf9cA+RhRJN0\nSeP8iM3Wfmk9bA6vBZk6hG+QfLdHb5SwB72ap9pdwkMI4J4dSnOo56nm6RH7FeQh\nqx6CHFdN6OURozp0/0kWEJpjXVFJlveCNop1iFMxGMHXh+aANa7CvawUK8k9JP3x\nhyCjHfCcDqEUUVLwxlYExnGbToAQcmvuKZNsx+0/G1yj0MCG+GiaSNeEt/0d8Xf4\nlJNaxpsPAgMBAAECggEATlNHmfLE4qgwTufJJoCU3dw0315/OWDzlFtoltjUmfaw\nPXFCkxYXKqCSGl18Yh49iRVFbwYf0AwghSFF4jPeEWKsjM5FNDZM+8i+yczerpWG\nez3b4dKl/FW2466qGHn2+xPXP7KhHSLaIqzVXR67Qzbw7vLn8JZRaAIZf1V3iBS7\nQ7sHUzivy+fPUq5LzL23/TYL1Xd35yGKs+T+H6rOOyg65Rdh/UwZzsFrZuLjSr5p\nsTL8g87hexrGLITCYcV4r3t1D4N7ysuljX6yhtNlkOildEZ6oX3INxrERwXYI8d5\nKm6TcZaC/gInFoNMLo+rtWv7/mFZea6rV3CMzhU30QKBgQDaIWv8ugi0bBqAQke0\nK+2mM+PpwYp7NK80zqWgfFLnirV+Ugwx3u9FfVGZcs5FCKPGwjayk/5Zjm3b3mDu\nlWBt6RKh3p+FYjegN6LBnTpAnEZnemXsSyViHULOu24+gQUFJWk3UVPibUYoFwvA\nRfU4V8SYjtJHnTeCvIaj7l0xsQKBgQC9tJAYpbWUKXN3D0gM+Rv7xir7EPOi27AC\nFSIJjyHuRwpSAgyp+xlBao2DifzrIfPT6iik3+ERSqK63ezyneJ5ab1BDwvtEIT+\nPQgu+zNf7nLTAlvZcNPf5JqtLsFX9CQMOlVxduXBQXcSfD+tSrMITIwgZ7VmBpul\nqQMs6AEIvwKBgGtW6wbwnPv7/oaDFznoLAgPnOYY4YaDhHxd/E8fHsTmEy3YPjwE\nUOZFhvQV9L8v4zgZtkTmYtG7LwB1TAnb5BnyCcMyBBnlHS5wcl0Ie/PzcwnUx3ch\n+4FumMOWpEeJweioYkBgewD/ePidbqDtTCCvwAS6s2ueSATDtRXSZHXhAoGAPLq0\n9m719fxfDlpCAoUsxCjoUX9Xv2b8rW3+e3jqr9DmKOKnEzNjHmHx844U/WDdIZXw\ndPeGoXZ3KcMpu3F3ss5623zpoHaNXKZFHGUmSSuYbpxusuk/qokQSyiQlIt/jrqN\n58jcPEWszKoh6GPldF6s7SLGG2c6JIo6jgGncxkCgYA6+Wjt/GjTRJ+MP5vCnA+Y\nuM3MM0RracL/NqjbOYQRGFlDZ40veLGfZHsJezTf/bfZ0Jdsebpd+USh+RIdniBO\nnxLQb5B1rL2jecx/n9q1LGw4zgY6zDl8afbo3Uj0mDSLxJLacfnwXf08qURbRnaPz\n6Tbf3QJFD+Oz5N2VPWexeQ==\n-----END PRIVATE KEY-----\n".replace("\\n", "\n")

# Googleが求める形式に辞書を組み立てます
creds_dict = {
    "type": "service_account",
    "project_id": "festive-bonsai-454509-b3",
    "private_key_id": "a01f50e471bd00a124491393c8f6d73e43f7b90c",
    "private_key": fixed_private_key,
    "client_email": "kigennkannri@festive-bonsai-454509-b3.iam.gserviceaccount.com",
    "client_id": "100862163723631529042",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/kigennkannri%40festive-bonsai-454509-b3.iam.gserviceaccount.com"
}

# 接続先URL
url = "https://docs.google.com/spreadsheets/d/10SPAlhEavpSZzHr2iCgu3U_gaaW6IHWgvjNTdvSWY9A/edit"

try:
    # --- 1. st.connectionを介さず、直接インスタンスを作成する ---
    # これにより TypeError("Secrets does not support item assignment") を回避します
    conn = GSheetsConnection(connection_name="gsheets")
    
    # 内部の認証情報を自作の辞書で上書き（このクラスの内部変数 _secrets を利用）
    conn._secrets = {"connections": {"gsheets": creds_dict}}
    
    # 読み込みテスト
    df = conn.read(spreadsheet=url, ttl=0)
    
    st.success("✅ 内部クラスの直接操作により接続に成功しました！")
    st.dataframe(df.head())

except Exception as e:
    st.error("❌ 内部操作でも失敗しました")
    st.exception(e)
