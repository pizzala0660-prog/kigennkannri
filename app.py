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
        data = worksheet.get_all_values()
        if len(data) > 0:
            # 列名の前後の空白を自動削除してDataFrame化
            cols = [c.strip() for c in data[0]]
            return pd.DataFrame(data[1:], columns=cols)
        return pd.DataFrame()
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

def validate_input(s, fmt):
    try:
        if fmt == "年月日":
            if not re.match(r"^\d{8}$", s): return False, "8桁の数字で入力してください"
            dt = datetime.strptime(s, "%Y%m%d").date()
        else:
            if not re.match(r"^\d{6}$", s): return False, "6桁の数字で入力してください"
            y, m = int(s[:4]), int(s[4:])
            if not (1 <= m <= 12): return False, "月が不正です"
            dt = date(y, m, calendar.monthrange(y, m)[1])
        if dt < date.today(): return False, "過去の日付は登録できません"
        return True, dt
    except:
        return False, "正しい日付を入力してください"

# --- 3. セッション管理 ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'user_info': None})

# --- ログイン ---
if not st.session_state['logged_in']:
    st.title("賞味期限管理システム")
    with st.form("login"):
        u_id = st.text_input("ID (数字4桁)", max_chars=4)
        u_pw = st.text_input("パスワード", type="password")
        if st.form_submit_button("ログイン", use_container_width=True):
            users = load_data("user_master")
            if not users.empty:
                users['id'] = users['id'].astype(str).str.strip()
                users['password'] = users['password'].astype(str).str.strip()
                user_row = users[(users['id'] == str(u_id).strip()) & (users['password'] == str(u_pw).strip())]
                if not user_row.empty:
                    st.session_state.update({'logged_in': True, 'role': user_row.iloc[0]['role'], 'user_info': user_row.iloc[0].to_dict()})
                    st.rerun()
                else: st.error("IDまたはパスワードが不正です")
    st.stop()

# --- 4. メインメニュー ---
role = st.session_state['role']
info = st.session_state['user_info']
st.sidebar.title(f"【{role}】")
st.sidebar.write(f"👤 {info['name']} 様")

if st.sidebar.button("ログアウト"):
    st.session_state.update({'logged_in': False, 'role': None})
    st.rerun()

# --- 5. 機能実装 ---

# A. 管理者ページ（マスター・支部・管轄者）
if role in ["マスター", "支部", "管轄者"]:
    st.title("⚙️ 管理パネル")
    tabs = ["期限確認", "アイテム管理", "店舗管理"]
    if role == "マスター": tabs.insert(0, "支部登録")
    if role == "支部": tabs.insert(0, "管轄者割り当て")
    
    selected_tabs = st.tabs(tabs)
    
    # --- マスター：支部登録 ---
    if role == "マスター":
        with selected_tabs[0]:
            st.subheader("支部の新規登録")
            with st.form("reg_b"):
                c1, c2, c3 = st.columns(3)
                b_id = c1.text_input("支部ID(4桁)", max_chars=4)
                b_name = c2.text_input("支部名")
                b_pw = c3.text_input("パスワード")
                if st.form_submit_button("登録"):
                    u_df = load_data("user_master")
                    new_u = pd.DataFrame([{"id": b_id, "password": b_pw, "role":"支部", "target_id": b_id, "name": b_name}])
                    save_data(pd.concat([u_df, new_u]), "user_master")
                    st.success(f"支部 {b_name} を登録しました")

    # --- 支部：管轄者割り当て ---
    if role == "支部":
        with selected_tabs[0]:
            st.subheader("管轄者の登録と店舗割り当て")
            shops_df = load_data("shop_master")
            my_shops = shops_df[shops_df["branch_id"] == info["id"]]
            
            with st.form("reg_mgr"):
                m_id = st.text_input("管轄者ID(4桁)", max_chars=4)
                m_name = st.text_input("管轄者名")
                m_pw = st.text_input("パスワード")
                # 自身の支部の店舗から選択
                selected_shops = st.multiselect("担当店舗を選択", my_shops["shop_name"].tolist())
                if st.form_submit_button("管轄者を登録"):
                    u_df = load_data("user_master")
                    new_u = pd.DataFrame([{"id": m_id, "password": m_pw, "role":"管轄者", "target_id": ",".join(selected_shops), "name": m_name}])
                    save_data(pd.concat([u_df, new_u]), "user_master")
                    st.success(f"管轄者 {m_name} を登録しました")

    # --- 店舗管理 (支部が店舗を登録) ---
    if "店舗管理" in tabs:
        with selected_tabs[tabs.index("店舗管理")]:
            if role == "支部":
                st.subheader("店舗IDと店舗名の登録")
                with st.form("reg_s"):
                    s_id = st.text_input("店舗ID(4桁)", max_chars=4)
                    s_name = st.text_input("店舗名")
                    s_pw = st.text_input("パスワード")
                    if st.form_submit_button("店舗登録"):
                        u_df = load_data("user_master")
                        new_u = pd.DataFrame([{"id": s_id, "password": s_pw, "role":"店舗", "target_id": s_name, "name": s_name}])
                        save_data(pd.concat([u_df, new_u]), "user_master")
                        s_df = load_data("shop_master")
                        new_s = pd.DataFrame([{"shop_id": s_id, "branch_id": info["id"], "shop_name": s_name}])
                        save_data(pd.concat([s_df, new_s]), "shop_master")
                        st.success(f"店舗 {s_name} を登録しました")

    # --- アイテム管理 ---
    if "アイテム管理" in tabs:
        with selected_tabs[tabs.index("アイテム管理")]:
            st.subheader("アイテム登録")
            with st.form("reg_i"):
                c1, c2, c3 = st.columns(3)
                i_cat = c1.selectbox("カテゴリ", ["冷蔵食材", "冷凍食材", "常温食材", "ドリンク", "ピックアップ"])
                i_name = c2.text_input("アイテム名")
                i_type = c3.radio("形式", ["年月日", "年月のみ"])
                if st.form_submit_button("保存"):
                    idf = load_data("item_master")
                    new_i = pd.DataFrame([{"item_id": len(idf)+1, "category": i_cat, "item_name": i_name, "input_type": i_type}])
                    save_data(pd.concat([idf, new_i]), "item_master")
                    st.rerun()
            st.dataframe(load_data("item_master"), use_container_width=True)

# --- B. 店舗：期限入力 ---
else:
    st.title(f"📦 {info['name']}")
    items = load_data("item_master")
    
    # 列名の存在確認をしてエラーを回避
    if not items.empty and "category" in items.columns:
        final_data = {}
        for cat in items["category"].unique():
            st.markdown(f"### 📍 {cat}")
            for _, row in items[items["category"] == cat].iterrows():
                with st.container(border=True):
                    st.write(f"**{row['item_name']}**")
                    ph = "20251231" if row['input_type']=="年月日" else "202512"
                    val_str = st.text_input(f"期限入力", key=f"inp_{row['item_id']}", placeholder=ph)
                    if val_str:
                        valid, res = validate_input(val_str, row['input_type'])
                        if valid:
                            final_data[row['item_id']] = {"cat": row['category'], "name": row['item_name'], "date": res}
                            st.caption(f"✅ 登録予定: {res}")
                        else: st.error(res)

        if st.button("一括登録を確定", type="primary", use_container_width=True):
            if final_data:
                df = load_data("expiry_records")
                new_recs = []
                for k, v in final_data.items():
                    new_recs.append({"id": datetime.now().strftime('%Y%m%d%H%M%S')+str(k), "shop_id": info['name'], "category": v["cat"], "item_name": v["name"], "expiry_date": str(v["date"]), "input_date": str(date.today())})
                save_data(pd.concat([df, pd.DataFrame(new_recs)]), "expiry_records")
                st.success("登録完了！")
                st.balloons()
    else:
        st.warning("アイテムマスタに 'category' 列が見つかりません。スプレッドシートを確認してください。")
