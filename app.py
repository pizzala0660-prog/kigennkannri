import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date, datetime, timedelta
import io

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

# --- 2. データ操作関数 ---
def load_data(sheet_name):
    try:
        worksheet = sheet.worksheet(sheet_name)
        return pd.DataFrame(worksheet.get_all_records())
    except:
        return pd.DataFrame()

def save_data(df, sheet_name):
    try:
        try:
            worksheet = sheet.worksheet(sheet_name)
        except:
            worksheet = sheet.add_worksheet(title=sheet_name, rows="2000", cols="20")
        worksheet.clear()
        df_save = df.fillna("")
        worksheet.update([df_save.columns.values.tolist()] + df_save.values.tolist())
        return True
    except Exception as e:
        st.error(f"保存エラー: {e}")
        return False

# エクセル作成用関数
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

# --- 3. 認証・初期設定 ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'user_info': None})

# マスタに「アカウント情報」が必要なため初期化
def init_masters():
    masters = {
        "user_master": ["id", "password", "role", "target_id", "name"], # target_idは支部IDや店舗ID
        "expiry_records": ["id", "shop_id", "branch_id", "item_name", "expiry_date", "input_date"],
        "shop_master": ["shop_id", "branch_id", "shop_name"],
        "branch_master": ["branch_id", "branch_name"],
        "item_master": ["item_id", "item_name"]
    }
    for s, cols in masters.items():
        if load_data(s).empty:
            save_data(pd.DataFrame(columns=cols), s)
            if s == "user_master": # 初回マスターアカウント
                save_data(pd.DataFrame([{"id":"admin", "password":"admin", "role":"マスター", "target_id":"ALL", "name":"最高管理者"}]), s)

init_masters()

# --- 4. ログイン ---
if not st.session_state['logged_in']:
    st.title("🛡️ 期限管理システム ログイン")
    with st.form("login"):
        u_id = st.text_input("ユーザーID")
        u_pw = st.text_input("パスワード", type="password")
        if st.form_submit_button("ログイン"):
            users = load_data("user_master")
            user_row = users[(users['id'] == u_id) & (users['password'] == u_pw)]
            if not user_row.empty:
                st.session_state.update({'logged_in': True, 'role': user_row.iloc[0]['role'], 'user_info': user_row.iloc[0]})
                st.rerun()
            else:
                st.error("IDまたはパスワードが不正です")
    st.stop()

# --- 5. メインメニュー ---
role = st.session_state['role']
info = st.session_state['user_info']
st.sidebar.title(f"【{role}】")
st.sidebar.write(f"👤 {info['name']} 様")

# 権限別メニュー定義
if role == "マスター":
    menu = st.sidebar.radio("メニュー", ["期限確認", "支部/管轄登録", "商品マスタ", "全体集計"])
elif role == "支部":
    menu = st.sidebar.radio("メニュー", ["店舗マスタ登録", "期限確認(管轄)", "エクセル発行"])
else: # 店舗
    menu = st.sidebar.radio("メニュー", ["期限入力", "期限確認(自店)", "エクセル発行"])

if st.sidebar.button("ログアウト"):
    st.session_state.update({'logged_in': False, 'role': None})
    st.rerun()

# --- 6. 各機能実装 ---

# --- 【店舗】期限入力 ---
if menu == "期限入力":
    st.header("📝 期限登録")
    items = load_data("item_master")
    with st.form("entry"):
        item = st.selectbox("商品名", items["item_name"] if not items.empty else ["先にマスタ登録を"])
        exp = st.date_input("賞味/消費期限", date.today())
        if st.form_submit_button("登録"):
            df = load_data("expiry_records")
            new_row = pd.DataFrame([{
                "id": str(datetime.now().timestamp()),
                "shop_id": info['target_id'],
                "branch_id": info['id'].split('_')[0], # ID規則による
                "item_name": item,
                "expiry_date": str(exp),
                "input_date": str(date.today())
            }])
            save_data(pd.concat([df, new_row]), "expiry_records")
            st.success("登録しました")

# --- 期限確認・検索機能 ---
elif "期限確認" in menu:
    st.header(f"🔍 {menu}")
    df = load_data("expiry_records")
    # 権限フィルタ
    if role == "店舗":
        df = df[df["shop_id"] == info["target_id"]]
    elif role == "支部":
        shops = load_data("shop_master")
        my_shops = shops[shops["branch_id"] == info["target_id"]]["shop_name"].tolist()
        df = df[df["shop_id"].isin(my_shops)]
    
    st.dataframe(df, use_container_width=True)

# --- エクセル発行 (支部・店舗別ロジック) ---
elif menu == "エクセル発行":
    st.header("📊 エクセルレポート出力")
    df = load_data("expiry_records")
    today = date.today()
    
    if role == "支部":
        period = st.multiselect("抽出期間", ["1週間以内", "1か月以内"], default=["1週間以内"])
        mask = pd.Series([False] * len(df))
        if "1週間以内" in period:
            mask |= (pd.to_datetime(df["expiry_date"]).dt.date <= today + timedelta(days=7))
        if "1か月以内" in period:
            mask |= (pd.to_datetime(df["expiry_date"]).dt.date <= today + timedelta(days=30))
        filtered_df = df[mask]
    else: # 店舗
        st.write("翌月1日〜翌々月第1週目までの期限切れを出力します")
        next_month_start = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
        after_next_month_end = (next_month_start + timedelta(days=32)).replace(day=7)
        filtered_df = df[(pd.to_datetime(df["expiry_date"]).dt.date >= next_month_start) & 
                         (pd.to_datetime(df["expiry_date"]).dt.date <= after_next_month_end)]
    
    if st.button("Excelファイルを生成"):
        excel_data = to_excel(filtered_df)
        st.download_button("📥 ダウンロード", excel_data, f"expiry_report_{today}.xlsx")

# --- マスタ管理 (マスター・支部) ---
elif "登録" in menu or "マスタ" in menu:
    st.header(f"⚙️ {menu}")
    if role == "マスター":
        st.subheader("支部アカウント発行")
        with st.form("branch_add"):
            b_id = st.text_input("支部ID(半角英数)")
            b_name = st.text_input("支部名")
            b_pw = st.text_input("初期パスワード")
            if st.form_submit_button("支部を登録"):
                users = load_data("user_master")
                new_u = pd.DataFrame([{"id": b_id, "password": b_pw, "role":"支部", "target_id": b_id, "name": b_name}])
                save_data(pd.concat([users, new_u]), "user_master")
                st.success(f"{b_name} を発行しました")
                
    elif role == "支部":
        st.subheader("店舗アカウント発行・パスワードリセット")
        with st.form("shop_add"):
            s_id = st.text_input("店舗ID(半角英数)")
            s_name = st.text_input("店舗名")
            s_pw = st.text_input("パスワード(リセット時もここに入力)")
            if st.form_submit_button("店舗情報を保存/更新"):
                users = load_data("user_master")
                # 既存なら削除して更新（リセット）
                users = users[users["id"] != s_id]
                new_u = pd.DataFrame([{"id": s_id, "password": s_pw, "role":"店舗", "target_id": s_name, "name": s_name}])
                save_data(pd.concat([users, new_u]), "user_master")
                
                # 店舗マスタも更新
                shops = load_data("shop_master")
                shops = shops[shops["shop_id"] != s_id]
                new_s = pd.DataFrame([{"shop_id": s_id, "branch_id": info["target_id"], "shop_name": s_name}])
                save_data(pd.concat([shops, new_s]), "shop_master")
                st.success("店舗アカウントを更新しました")
                
    if "商品マスタ" in menu:
        st.subheader("共通商品登録")
        new_item = st.text_input("商品名")
        if st.button("追加"):
            idf = load_data("item_master")
            save_data(pd.concat([idf, pd.DataFrame([{"item_id":len(idf)+1, "item_name":new_item}])]), "item_master")
            st.rerun()
