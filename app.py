import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date, datetime

# --- 1. 接続・認証設定 ---
@st.cache_resource
def get_gspread_client():
    info = dict(st.secrets["gcp_service_account"])
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    return gspread.authorize(creds)

client = get_gspread_client()
spreadsheet_id = "10SPAlhEavpSZzHr2iCgu3U_gaaW6IHWgvjNTdvSWY9A"
sheet = client.open_by_key(spreadsheet_id)

# --- 2. データ操作用関数 ---
def load_data(sheet_name):
    try:
        worksheet = sheet.worksheet(sheet_name)
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

def save_data(df, sheet_name):
    try:
        try:
            worksheet = sheet.worksheet(sheet_name)
        except:
            worksheet = sheet.add_worksheet(title=sheet_name, rows="1000", cols="20")
        worksheet.clear()
        # NaNを空文字に変換してエラーを防止
        df_to_save = df.fillna("")
        worksheet.update([df_to_save.columns.values.tolist()] + df_to_save.values.tolist())
        return True
    except Exception as e:
        st.error(f"保存失敗: {e}")
        return False

# --- 3. セッション管理 ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# --- 4. ログイン画面 ---
if not st.session_state['logged_in']:
    st.title("🔐 期限管理システム ログイン")
    with st.form("login"):
        user_id = st.text_input("ユーザーID")
        password = st.text_input("パスワード", type="password")
        if st.form_submit_button("ログイン"):
            # ここでID/PWを検証
            if user_id == "admin" and password == "1234":
                st.session_state['logged_in'] = True
                st.session_state['user_id'] = user_id
                st.rerun()
            else:
                st.error("IDまたはパスワードが正しくありません")
    st.stop()

# --- 5. メインメニュー（ログイン後） ---
st.sidebar.title(f"👤 {st.session_state['user_id']} 様")
menu = st.sidebar.radio("メニュー", ["期限登録", "期限一覧", "マスタ管理"])

if st.sidebar.button("ログアウト"):
    st.session_state['logged_in'] = False
    st.rerun()

# --- 機能実装 ---

# A. 期限登録
if menu == "期限登録":
    st.header("🛒 商品期限登録")
    # マスタ読み込み
    shop_df = load_data("shop_master")
    item_df = load_data("item_master")
    
    if shop_df.empty or item_df.empty:
        st.warning("先にマスタ管理で店舗と商品を登録してください。")
    else:
        with st.form("input_form"):
            selected_shop = st.selectbox("店舗", shop_df["shop_name"])
            selected_item = st.selectbox("商品", item_df["item_name"])
            expiry_date = st.date_input("期限日", date.today())
            
            if st.form_submit_button("登録"):
                new_data = pd.DataFrame([{
                    "id": str(datetime.now().timestamp()),
                    "shop_id": selected_shop,
                    "item_name": selected_item,
                    "expiry_date": str(expiry_date),
                    "input_date": str(date.today())
                }])
                current_df = load_data("expiry_records")
                updated_df = pd.concat([current_df, new_data], ignore_index=True)
                if save_data(updated_df, "expiry_records"):
                    st.success("登録完了！")

# B. 期限一覧
elif menu == "期限一覧":
    st.header("📋 期限一覧・検索")
    df = load_data("expiry_records")
    if not df.empty:
        # 近い期限を赤く表示するなどの処理も可能
        st.dataframe(df, use_container_width=True)
        if st.button("全データ削除（リセット）"):
            save_data(pd.DataFrame(columns=df.columns), "expiry_records")
            st.rerun()
    else:
        st.info("登録データがありません。")

# C. マスタ管理
elif menu == "マスタ管理":
    st.header("⚙️ マスタ管理")
    tab1, tab2 = st.tabs(["店舗マスタ", "商品マスタ"])
    
    with tab1:
        st.subheader("店舗登録")
        shop_name = st.text_input("新しい店舗名")
        if st.button("店舗を追加"):
            df = load_data("shop_master")
            new_shop = pd.DataFrame([{"id": len(df)+1, "shop_name": shop_name}])
            if save_data(pd.concat([df, new_shop], ignore_index=True), "shop_master"):
                st.success(f"{shop_name} を登録しました")
        st.write("現在の店舗一覧", load_data("shop_master"))

    with tab2:
        st.subheader("商品登録")
        item_name = st.text_input("新しい商品名")
        if st.button("商品を追加"):
            df = load_data("item_master")
            new_item = pd.DataFrame([{"id": len(df)+1, "item_name": item_name}])
            if save_data(pd.concat([df, new_item], ignore_index=True), "item_master"):
                st.success(f"{item_name} を登録しました")
        st.write("現在の商品一覧", load_data("item_master"))
