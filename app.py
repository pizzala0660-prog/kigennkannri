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

def convert_df(df):
    return df.to_csv(index=False).encode('utf_8_sig')

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

if role == "マスター":
    menu = st.sidebar.radio("メニュー", ["期限確認", "支部登録", "アイテム管理"])
elif role == "支部":
    menu = st.sidebar.radio("メニュー", ["期限確認", "店舗管理", "管轄者割り当て", "アイテム管理", "パスワード変更"])
elif role == "管轄者":
    menu = st.sidebar.radio("メニュー", ["期限確認", "パスワード変更"])
elif role == "店舗":
    menu = st.sidebar.radio("メニュー", ["期限入力", "期限一覧・編集", "エクセル発行", "パスワード変更"])

if st.sidebar.button("ログアウト"):
    st.session_state.update({'logged_in': False, 'role': None})
    st.rerun()

# --- 5. 機能実装 ---

# --- A. 期限確認・一覧 (共通) ---
if "期限" in menu:
    st.header(f"🔍 {menu}")
    df = load_data("expiry_records")
    if role == "店舗":
        df = df[df["shop_id"] == info["name"]]
    elif role == "管轄者":
        my_shops = info["target_id"].split(",")
        df = df[df["shop_id"].isin(my_shops)]
    elif role == "支部":
        # 支部所属の店舗のみ
        s_master = load_data("shop_master")
        my_s_names = s_master[s_master["branch_id"] == info["id"]]["shop_name"].tolist()
        df = df[df["shop_id"].isin(my_s_names)]

    if not df.empty:
        st.subheader("データ選択 (編集・削除)")
        target_id = st.selectbox("操作するIDを選択", df["id"].tolist())
        t_row = df[df["id"] == target_id].iloc[0]
        
        with st.expander("📝 選択した項目を編集/削除"):
            new_item = st.text_input("商品名", value=t_row["item_name"])
            new_date = st.text_input("期限日 (YYYY-MM-DD)", value=t_row["expiry_date"])
            
            c_a, c_b = st.columns(2)
            if c_a.button("🆙 更新保存", use_container_width=True):
                all_df = load_data("expiry_records")
                all_df.loc[all_df["id"] == target_id, ["item_name", "expiry_date"]] = [new_item, new_date]
                save_data(all_df, "expiry_records")
                st.success("更新完了")
                st.rerun()
            if c_b.button("🗑️ 削除実行", use_container_width=True):
                all_df = load_data("expiry_records")
                all_df = all_df[all_df["id"] != target_id]
                save_data(all_df, "expiry_records")
                st.warning("削除完了")
                st.rerun()
        st.divider()
        st.dataframe(df, use_container_width=True)
    else:
        st.info("データがありません。")

# --- B. 店舗管理 (支部用) ---
elif menu == "店舗管理":
    st.header("🏪 店舗管理")
    # 新規登録
    with st.expander("➕ 新規店舗を登録する"):
        with st.form("reg_shop"):
            s_id = st.text_input("店舗ID (4桁)", max_chars=4)
            s_name = st.text_input("店舗名")
            s_pw = st.text_input("初期パスワード")
            if st.form_submit_button("登録実行"):
                u_df = load_data("user_master")
                s_df = load_data("shop_master")
                new_u = pd.DataFrame([{"id": s_id, "password": s_pw, "role":"店舗", "target_id": s_name, "name": s_name}])
                new_s = pd.DataFrame([{"shop_id": s_id, "branch_id": info["id"], "shop_name": s_name}])
                save_data(pd.concat([u_df, new_u]), "user_master")
                save_data(pd.concat([s_df, new_s]), "shop_master")
                st.success(f"{s_name} を登録しました")
                st.rerun()

    # 一覧・編集・削除
    s_master = load_data("shop_master")
    my_shops = s_master[s_master["branch_id"] == info["id"]]
    if not my_shops.empty:
        st.subheader("登録済み店舗一覧 (選択して編集/削除)")
        sel_s_id = st.selectbox("店舗を選択", my_shops["shop_id"].tolist())
        s_info = my_shops[my_shops["shop_id"] == sel_s_id].iloc[0]
        
        with st.expander("📝 店舗情報の修正/削除"):
            new_s_name = st.text_input("店舗名修正", value=s_info["shop_name"])
            c_a, c_b = st.columns(2)
            if c_a.button("🆙 名称変更保存"):
                u_df = load_data("user_master")
                s_df = load_data("shop_master")
                s_df.loc[s_df["shop_id"] == sel_s_id, "shop_name"] = new_s_name
                u_df.loc[u_df["id"] == sel_s_id, ["target_id", "name"]] = [new_s_name, new_s_name]
                save_data(s_df, "shop_master")
                save_data(u_df, "user_master")
                st.rerun()
            if c_b.button("🗑️ この店舗を削除"):
                u_df = load_data("user_master")
                s_df = load_data("shop_master")
                save_data(u_df[u_df["id"] != sel_s_id], "user_master")
                save_data(s_df[s_df["shop_id"] != sel_s_id], "shop_master")
                st.rerun()
        st.dataframe(my_shops, use_container_width=True)

# --- C. 管轄者割り当て (支部用) ---
elif menu == "管轄者割り当て":
    st.header("👥 管轄者(マネージャー)管理")
    s_master = load_data("shop_master")
    my_shops = s_master[s_master["branch_id"] == info["id"]]
    
    with st.expander("➕ 新規管轄者を登録する"):
        with st.form("reg_mgr"):
            m_id = st.text_input("管轄者ID (4桁)", max_chars=4)
            m_name = st.text_input("管轄者名")
            m_pw = st.text_input("パスワード")
            sel_list = st.multiselect("担当店舗を選択", my_shops["shop_name"].tolist())
            if st.form_submit_button("登録"):
                u_df = load_data("user_master")
                new_u = pd.DataFrame([{"id": m_id, "password": m_pw, "role":"管轄者", "target_id": ",".join(sel_list), "name": m_name}])
                save_data(pd.concat([u_df, new_u]), "user_master")
                st.success("管轄者を登録しました")
                st.rerun()

    u_all = load_data("user_master")
    # 簡易的に管轄者のみ抽出（本来は所属も見るべきですがID体系で運用）
    m_list = u_all[u_all["role"] == "管轄者"]
    if not m_list.empty:
        st.subheader("管轄者一覧")
        sel_m_id = st.selectbox("管轄者を選択", m_list["id"].tolist())
        if st.button("🗑️ 選択した管轄者を削除"):
            save_data(u_all[u_all["id"] != sel_m_id], "user_master")
            st.rerun()
        st.dataframe(m_list, use_container_width=True)

# --- D. アイテム管理 (支部・マスター用) ---
elif menu == "アイテム管理":
    st.header("📦 アイテムマスタ管理")
    with st.expander("➕ 新規アイテム追加"):
        with st.form("reg_item"):
            cat = st.selectbox("カテゴリ", ["冷蔵食材", "冷凍食材", "常温食材", "ドリンク", "ピックアップ"])
            nm = st.text_input("アイテム名")
            tp = st.radio("形式", ["年月日", "年月のみ"])
            if st.form_submit_button("追加"):
                idf = load_data("item_master")
                new_i = pd.DataFrame([{"item_id": str(len(idf)+1), "category": cat, "item_name": nm, "input_type": tp}])
                save_data(pd.concat([idf, new_i]), "item_master")
                st.rerun()
    
    i_df = load_data("item_master")
    if not i_df.empty:
        sel_i = st.selectbox("アイテムを選択して削除", i_df["item_name"].tolist())
        if st.button("🗑️ 削除実行"):
            save_data(i_df[i_df["item_name"] != sel_i], "item_master")
            st.rerun()
        st.dataframe(i_df, use_container_width=True)

# --- E. エクセル発行 (店舗専用) ---
elif menu == "エクセル発行":
    st.header("📊 エクセルレポート発行")
    df = load_data("expiry_records")
    df = df[df["shop_id"] == info["name"]]
    today = date.today()
    start_date = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
    end_date = (start_date + timedelta(days=32)).replace(day=7)
    st.write(f"抽出範囲: **{start_date}** ～ **{end_date}**")
    df['exp_dt'] = pd.to_datetime(df['expiry_date']).dt.date
    filtered_df = df[(df['exp_dt'] >= start_date) & (df['exp_dt'] <= end_date)]
    if not filtered_df.empty:
        st.download_button("📥 Excel(CSV)を発行する", data=convert_df(filtered_df), file_name=f"expiry_report.csv")
        st.dataframe(filtered_df.drop(columns=['exp_dt']), use_container_width=True)

# --- F. パスワード変更 ---
elif menu == "パスワード変更":
    st.header("🔑 パスワード変更")
    with st.form("pw_f"):
        new_pw = st.text_input("新パスワード", type="password")
        if st.form_submit_button("更新"):
            u_df = load_data("user_master")
            u_df.loc[u_df["id"] == info["id"], "password"] = new_pw
            save_data(u_df, "user_master")
            st.success("更新しました。")

# --- G. 期限入力 (店舗用) ---
elif menu == "期限入力":
    st.header(f"📦 {info['name']} - 期限入力")
    items = load_data("item_master")
    if not items.empty:
        final_data = {}
        for cat in items["category"].unique():
            st.markdown(f"### 📍 {cat}")
            for _, row in items[items["category"] == cat].iterrows():
                with st.container(border=True):
                    st.write(f"**{row['item_name']}**")
                    ph = "20251231" if row['input_type']=="年月日" else "202512"
                    val_str = st.text_input(f"期限", key=f"inp_{row['item_id']}", placeholder=ph)
                    if val_str:
                        v, r = validate_input(val_str, row['input_type'])
                        if v: final_data[row['item_id']] = {"cat": row['category'], "name": row['item_name'], "date": r}
                        else: st.error(r)
        if st.button("一括登録", type="primary", use_container_width=True):
            if final_data:
                df = load_data("expiry_records")
                new_recs = []
                for k, v in final_data.items():
                    new_recs.append({"id": datetime.now().strftime('%Y%m%d%H%M%S')+str(k), "shop_id": info['name'], "category": v["cat"], "item_name": v["name"], "expiry_date": str(v["date"]), "input_date": str(date.today())})
                save_data(pd.concat([df, pd.DataFrame(new_recs)]), "expiry_records")
                st.success("完了！")
