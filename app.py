import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date, datetime, timedelta
import calendar
import re
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

# --- 3. バリデーション関数 (ご提示のロジックを継承) ---
def validate_input(s, fmt):
    try:
        if fmt == "年月日":
            if not re.match(r"^\d{8}$", s): return False, "8桁の数字で入力してください"
            dt = datetime.strptime(s, "%Y%m%d").date()
        else: # 年月のみ
            if not re.match(r"^\d{6}$", s): return False, "6桁の数字で入力してください"
            y, m = int(s[:4]), int(s[4:])
            if not (1 <= m <= 12): return False, "月が不正です"
            dt = date(y, m, calendar.monthrange(y, m)[1])
        if dt < date.today(): return False, "過去の日付は登録できません"
        return True, dt
    except:
        return False, "正しい日付を入力してください"

# --- 4. 初期設定・ログイン管理 ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'user_info': None})

def init_masters():
    masters = {
        "user_master": ["id", "password", "role", "target_id", "name"],
        "expiry_records": ["id", "shop_id", "branch_id", "category", "item_name", "expiry_date", "input_date"],
        "shop_master": ["shop_id", "branch_id", "shop_name"],
        "branch_master": ["branch_id", "branch_name"],
        "item_master": ["item_id", "category", "item_name", "input_type"]
    }
    for s, cols in masters.items():
        if load_data(s).empty:
            save_data(pd.DataFrame(columns=cols), s)
            if s == "user_master":
                save_data(pd.DataFrame([{"id":"9999", "password":"admin", "role":"マスター", "target_id":"ALL", "name":"最高管理者"}]), s)

init_masters()

# --- ログイン ---
if not st.session_state['logged_in']:
    st.title("賞味期限管理システム")
    with st.form("login"):
        u_id = st.text_input("IDを入力してください (数字4桁)", max_chars=4)
        u_pw = st.text_input("パスワード", type="password")
        if st.form_submit_button("ログイン", use_container_width=True):
            users = load_data("user_master")
            user_row = users[(users['id'] == u_id) & (users['password'] == u_pw)]
            if not user_row.empty:
                st.session_state.update({'logged_in': True, 'role': user_row.iloc[0]['role'], 'user_info': user_row.iloc[0]})
                st.rerun()
            else:
                st.error("IDまたはパスワードが不正です")
    st.stop()

# --- 5. メインメニューとUIレイアウト ---
role = st.session_state['role']
info = st.session_state['user_info']
st.sidebar.title(f"【{role}】")
st.sidebar.write(f"👤 {info['name']} 様")

if st.sidebar.button("ログアウト"):
    st.session_state.update({'logged_in': False, 'role': None})
    st.rerun()

# --- A. マスター/管理者権限 ---
if role in ["マスター", "支部"]:
    st.title("⚙️ 管理者ページ")
    
    tabs = ["アイテム管理", "店舗管理", "集計・アラート"]
    if role == "マスター": tabs.insert(0, "支部・管轄管理")
    
    selected_tabs = st.tabs(tabs)
    offset = 1 if role == "マスター" else 0

    if role == "マスター":
        with selected_tabs[0]:
            st.subheader("支部IDおよび管轄者登録")
            with st.form("reg_branch"):
                c1, c2, c3 = st.columns(3)
                b_id = c1.text_input("支部ID(4桁)", max_chars=4)
                b_name = c2.text_input("支部/管轄者名")
                b_pw = c3.text_input("初期パスワード")
                if st.form_submit_button("登録実行"):
                    u_df = load_data("user_master")
                    new_u = pd.DataFrame([{"id": b_id, "password": b_pw, "role":"支部", "target_id": b_id, "name": b_name}])
                    save_data(pd.concat([u_df, new_u]), "user_master")
                    br_df = load_data("branch_master")
                    save_data(pd.concat([br_df, pd.DataFrame([{"branch_id":b_id, "branch_name":b_name}])]), "branch_master")
                    st.success("支部と管轄ユーザーを登録しました")
                    st.rerun()

    with selected_tabs[offset]:
        st.subheader("アイテム管理")
        with st.expander("➕ 新規アイテム追加"):
            c1, c2, c3 = st.columns(3)
            i_cat = c1.selectbox("カテゴリ", ["冷蔵食材", "冷凍食材", "常温食材", "ドリンク", "ピックアップ"])
            i_name = c2.text_input("アイテム名")
            i_type = c3.radio("形式", ["年月日", "年月のみ"])
            if st.button("アイテムを保存"):
                df = load_data("item_master")
                new_i = pd.DataFrame([{"item_id": len(df)+1, "category": i_cat, "item_name": i_name, "input_type": i_type}])
                save_data(pd.concat([df, new_i]), "item_master")
                st.rerun()
        # アイテム一覧表示 (更新・削除機能付)
        items_df = load_data("item_master")
        st.dataframe(items_df, use_container_width=True)

    with selected_tabs[offset + 1]:
        st.subheader("店舗管理")
        with st.expander("➕ 管轄店舗の新規登録"):
            b_id_list = load_data("branch_master")
            target_b = st.selectbox("担当支部", b_id_list["branch_id"].tolist()) if role == "マスター" else info["id"]
            c1, c2, c3 = st.columns(3)
            s_id = c1.text_input("店舗ID(4桁)", max_chars=4)
            s_name = c2.text_input("店舗名")
            s_pw = c3.text_input("店舗パスワード")
            if st.button("店舗を保存"):
                u_df = load_data("user_master")
                new_u = pd.DataFrame([{"id": s_id, "password": s_pw, "role":"店舗", "target_id": s_name, "name": s_name}])
                save_data(pd.concat([u_df, new_u]), "user_master")
                s_df = load_data("shop_master")
                new_s = pd.DataFrame([{"shop_id": s_id, "branch_id": target_b, "shop_name": s_name}])
                save_data(pd.concat([s_df, new_s]), "shop_master")
                st.success("店舗を登録しました")
                st.rerun()

    with selected_tabs[offset + 2]:
        st.subheader("📊 期限警告アラート")
        records = load_data("expiry_records")
        if not records.empty:
            today = date.today()
            records['dt'] = pd.to_datetime(records['expiry_date']).dt.date
            for _, r in records.sort_values('expiry_date').iterrows():
                diff = (r['dt'] - today).days
                msg = f"{r['shop_id']} | {r['item_name']} ({r['expiry_date']})"
                if diff <= 0: st.error(f"🚨 【期限切れ】 {msg}")
                elif diff <= 7: st.warning(f"⚠️ 【1週間以内】 {msg}")
                elif diff <= 30: st.success(f"✅ 【1か月以内】 {msg}")

# --- B. 店舗用入力画面 (スマホ最適化レイアウト) ---
else:
    st.title(f"📦 {info['name']}")
    items = load_data("item_master")
    final_data = {}
    
    if not items.empty:
        for cat in items["category"].unique():
            st.markdown(f"### 📍 {cat}")
            for _, row in items[items["category"] == cat].iterrows():
                with st.container(border=True):
                    st.write(f"**{row['item_name']}**")
                    ph = "20251231" if row['input_type']=="年月日" else "202512"
                    val_str = st.text_input(f"{row['input_type']}を入力", key=f"inp_{row['item_id']}", placeholder=ph)
                    if val_str:
                        valid, res = validate_input(val_str, row['input_type'])
                        if valid:
                            final_data[row['item_id']] = {"cat": row['category'], "name": row['item_name'], "date": res}
                            st.caption(f"✅ 登録予定: {res}")
                        else:
                            st.error(res)

        if st.button("一括登録を確定する", type="primary", use_container_width=True):
            if final_data:
                df = load_data("expiry_records")
                # 自身の支部IDを取得
                shops_m = load_data("shop_master")
                b_id = shops_m[shops_m["shop_id"] == info['id']]["branch_id"].values[0]
                
                new_rows = []
                for k, v in final_data.items():
                    new_rows.append({
                        "id": str(datetime.now().strftime('%Y%m%d%H%M%S')) + str(k),
                        "shop_id": info['name'],
                        "branch_id": b_id,
                        "category": v["cat"],
                        "item_name": v["name"],
                        "expiry_date": str(v["date"]),
                        "input_date": str(date.today())
                    })
                save_data(pd.concat([df, pd.DataFrame(new_rows)]), "expiry_records")
                st.success("一括登録完了！")
                st.balloons()
