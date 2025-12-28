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

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

# --- 3. 認証・初期設定 ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'user_info': None})

def init_masters():
    masters = {
        "user_master": ["id", "password", "role", "target_id", "name"],
        "expiry_records": ["id", "shop_id", "branch_id", "item_name", "expiry_date", "input_date"],
        "shop_master": ["shop_id", "branch_id", "shop_name"],
        "branch_master": ["branch_id", "branch_name"],
        "item_master": ["item_id", "item_name"]
    }
    for s, cols in masters.items():
        if load_data(s).empty:
            save_data(pd.DataFrame(columns=cols), s)
            if s == "user_master":
                save_data(pd.DataFrame([{"id":"admin", "password":"admin", "role":"マスター", "target_id":"ALL", "name":"最高管理者"}]), s)

init_masters()

# --- 4. ログイン ---
if not st.session_state['logged_in']:
    st.title("🔐 期限管理システム ログイン")
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

if role == "マスター":
    menu = st.sidebar.radio("メニュー", ["期限確認", "支部/店舗登録", "商品マスタ", "全体集計"])
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
    items_df = load_data("item_master")
    
    with st.form("entry"):
        if items_df.empty:
            st.warning("商品マスタが登録されていません。マスターに連絡してください。")
            item = ""
        else:
            item = st.selectbox("商品名", ["選択してください"] + items_df["item_name"].tolist())
        
        exp = st.date_input("賞味/消費期限", date.today(), min_value=date.today()) # 過去日付入力不可
        
        if st.form_submit_button("登録"):
            if item == "選択してください" or not item:
                st.error("❌ 商品名を選択してください。")
            else:
                df = load_data("expiry_records")
                new_row = pd.DataFrame([{
                    "id": str(datetime.now().strftime('%Y%m%d%H%M%S')),
                    "shop_id": info['target_id'],
                    "branch_id": info['id'].split('_')[0],
                    "item_name": item,
                    "expiry_date": str(exp),
                    "input_date": str(date.today())
                }])
                save_data(pd.concat([df, new_row]), "expiry_records")
                st.success("✅ 登録しました")

# --- 期限確認・編集・削除機能 ---
elif "期限確認" in menu:
    st.header(f"🔍 {menu}")
    df = load_data("expiry_records")
    
    if role == "店舗":
        df = df[df["shop_id"] == info["target_id"]]
    elif role == "支部":
        shops = load_data("shop_master")
        my_shops = shops[shops["branch_id"] == info["target_id"]]["shop_name"].tolist()
        df = df[df["shop_id"].isin(my_shops)]
    
    if df.empty:
        st.info("表示するデータがありません。")
    else:
        # 編集・削除セクション
        st.subheader("データの編集・削除")
        selected_id = st.selectbox("操作するデータのIDを選択", df["id"].tolist())
        target_row = df[df["id"] == selected_id].iloc[0]
        
        col1, col2 = st.columns(2)
        with col1:
            new_item_name = st.text_input("編集：商品名", value=target_row["item_name"])
            new_exp_date = st.date_input("編集：期限日", value=datetime.strptime(target_row["expiry_date"], '%Y-%m-%d').date(), min_value=date.today())
        
        with col2:
            st.write("---")
            if st.button("🆙 変更を保存"):
                df.loc[df["id"] == selected_id, ["item_name", "expiry_date"]] = [new_item_name, str(new_exp_date)]
                save_data(df, "expiry_records")
                st.success("更新しました")
                st.rerun()
            
            if st.button("🗑️ データを削除"):
                df = df[df["id"] != selected_id]
                save_data(df, "expiry_records")
                st.warning("削除しました")
                st.rerun()
        
        st.divider()
        st.dataframe(df, use_container_width=True)

# --- エクセル発行 ---
elif menu == "エクセル発行":
    st.header("📊 エクセルレポート出力")
    df = load_data("expiry_records")
    today = date.today()
    
    if role == "支部":
        df_filtered = df # 支部ロジックは必要に応じて
    else:
        # 店舗別ロジック
        next_m = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
        after_next_m = (next_m + timedelta(days=32)).replace(day=7)
        df_filtered = df[(pd.to_datetime(df["expiry_date"]).dt.date >= next_m) & (pd.to_datetime(df["expiry_date"]).dt.date <= after_next_m)]
    
    st.download_button("📥 Excelダウンロード", to_excel(df_filtered), f"report_{today}.xlsx")

# --- マスタ登録 (ID+名前の登録) ---
elif "登録" in menu or "マスタ" in menu:
    st.header(f"⚙️ {menu}")
    
    if role == "マスター":
        st.subheader("支部IDと支部名の登録")
        with st.form("branch_reg"):
            b_id = st.text_input("支部ID")
            b_name = st.text_input("支部名")
            b_pw = st.text_input("パスワード")
            if st.form_submit_button("登録"):
                u_df = load_data("user_master")
                new_u = pd.DataFrame([{"id": b_id, "password": b_pw, "role":"支部", "target_id": b_id, "name": b_name}])
                save_data(pd.concat([u_df, new_u]), "user_master")
                # 支部マスタへも登録
                br_df = load_data("branch_master")
                save_data(pd.concat([br_df, pd.DataFrame([{"branch_id":b_id, "branch_name":b_name}])]), "branch_master")
                st.success("支部マスタを更新しました")

    elif role == "支部":
        st.subheader("店舗IDと店舗名の登録・更新")
        with st.form("shop_reg"):
            s_id = st.text_input("店舗ID")
            s_name = st.text_input("店舗名")
            s_pw = st.text_input("パスワード(リセット兼用)")
            if st.form_submit_button("登録/リセット"):
                # ユーザーマスタ更新
                u_df = load_data("user_master")
                u_df = u_df[u_df["id"] != s_id]
                new_u = pd.DataFrame([{"id": s_id, "password": s_pw, "role":"店舗", "target_id": s_name, "name": s_name}])
                save_data(pd.concat([u_df, new_u]), "user_master")
                # 店舗マスタ更新
                s_df = load_data("shop_master")
                s_df = s_df[s_df["shop_id"] != s_id]
                new_s = pd.DataFrame([{"shop_id": s_id, "branch_id": info["target_id"], "shop_name": s_name}])
                save_data(pd.concat([s_df, new_s]), "shop_master")
                st.success("店舗情報を同期しました")

    if "商品マスタ" in menu:
        st.subheader("商品マスタ登録")
        item_n = st.text_input("商品名を入力")
        if st.button("保存") and item_n:
            idf = load_data("item_master")
            save_data(pd.concat([idf, pd.DataFrame([{"item_id":len(idf)+1, "item_name":item_n}])]), "item_master")
            st.rerun()
