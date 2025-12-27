import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json

st.title("💡 ステップ2：書き込み権限検証")

# 1. JSONファイルの読み込み
json_path = "festive-bonsai-454509-b3-a01f50e471bd.json"
spreadsheet_url = "https://docs.google.com/spreadsheets/d/10SPAlhEavpSZzHr2iCgu3U_gaaW6IHWgvjNTdvSWY9A/edit"

try:
    with open(json_path, "r") as f:
        creds_info = json.load(f)
    
    # 2. 接続設定（辞書形式で渡す）
    conn = st.connection(
        "gsheets",
        type=GSheetsConnection,
        service_account=creds_info
    )

    # 3. テストデータの作成
    test_df = pd.DataFrame({"検証結果": ["成功"], "日時": [pd.Timestamp.now()]})

    # 4. 書き込み実行
    # 「test_sheet」という名前のシートを作成/更新しようとします
    conn.update(spreadsheet=spreadsheet_url, worksheet="test_sheet", data=test_df)
    
    st.success("✅ スプレッドシートへの書き込みに成功しました！")
    st.write("スプレッドシートを確認してください。'test_sheet' というシートができているはずです。")

except Exception as e:
    st.error("❌ 書き込みに失敗しました")
    st.exception(e)







