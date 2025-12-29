import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date, datetime, timedelta
import calendar
import re
import io

# --- 0. UIデザインの微調整 (CSS) ---
# ボタンの配置を数ピクセル下げて入力枠と高さを揃え、全体のフォントサイズを最適化します
st.markdown("""
    <style>
    /* ボタンの上下位置調整 */
    div[data-testid="stButton"] button {
        margin-top: 24px; 
    }
    /* 入力枠のラベルを非表示にした際の余白調整 */
    div[data-testid="stTextInput"] label, div[data-testid="stSelectbox"] label {
        display: none;
    }
    /* 列の中央揃え */
    [data-testid="column"] {
        display: flex;
        align-items: center;
    }
    </style>
    """, unsafe_allow_html=True)

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

# --- 2. データ操作基本関数 ---
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

# --- 4. ログイン画面 ---
if not st.session_state['logged_in']:
    st.title("🛡️ 賞味期限管理システム")
    with st.form("login"):
        u_id = st.text_input("IDを入力してください (数字4桁)", max_chars=4)
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

# --- 5. メインメニュー ---
role = st.session_state['role']
info = st.session_state['user_info']
st.sidebar.title(f"【{role}】")
st.sidebar.write(f"👤 {info['name']} 様")

if role == "マスター":
    menu = st.sidebar.radio("メニュー", ["期限確認", "支部登録", "アイテム管理"])
elif role == "支部":
    menu = st.sidebar.radio("メニュー", ["期限確認", "店舗管理", "管轄者管理", "アイテム管理", "パスワード変更"])
elif role == "管轄者":
    menu = st.sidebar.radio("メニュー", ["期限確認", "パスワード変更"])
elif role == "店舗":
    menu = st.sidebar.radio("メニュー", ["期限入力", "期限一覧・編集", "エクセル発行", "パスワード変更"])

if st.sidebar.button("ログアウト"):
    st.session_state.update({'logged_in': False, 'role': None})
    st.rerun()

# --- 6. 各機能の実装 ---

# --- A. 期限確認・編集 ---
if "期限確認" in menu or "期限一覧" in menu:
    st.header(f"🔍 {menu}")
    df = load_data("expiry_records")
    if role == "店舗":
        df = df[df["shop_id"] == info["name"]]
    elif role == "管轄者":
        my_shops = info["target_id"].split(",")
        df = df[df["shop_id"].isin(my_shops)]
    elif role == "支部":
        s_master = load_data("shop_master")
        my_s_names = s_master[s_master["branch_id"] == info["id"]]["shop_name"].tolist()
        df = df[df["shop_id"].isin(my_s_names)]

    if not df.empty:
        st.subheader("📋 登録済みデータ（行ごとに操作）")
        h_cols = st.columns([1, 2, 2, 0.5, 0.5])
        h_cols[0].caption("店舗名")
        h_cols[1].caption("商品名")
        h_cols[2].caption("期限日")
        
        for idx, row in df.iterrows():
            with st.container():
                c = st.columns([1, 2, 2, 0.5, 0.5])
                c[0].write(row["shop_id"])
                new_inm = c[1].text_input("商品名", value=row["item_name"], key=f"rec_nm_{idx}")
                new_exp = c[2].text_input("期限", value=row["expiry_date"], key=f"rec_dt_{idx}")
                
                if c[3].button("🆙", key=f"rec_upd_{idx}", help="更新"):
                    all_df = load_data("expiry_records")
                    all_df.loc[all_df["id"] == row["id"], ["item_name", "expiry_date"]] = [new_inm, new_exp]
                    save_data(all_df, "expiry_records")
                    st.success("更新完了"); st.rerun()
                
                if c[4].button("🗑️", key=f"rec_del_{idx}", help="削除"):
                    all_df = load_data("expiry_records")
                    save_data(all_df[all_df["id"] != row["id"]], "expiry_records")
                    st.warning("削除完了"); st.rerun()
    else:
        st.info("データがありません。")

# --- B. 店舗管理 (レイアウト修正版) ---
elif menu == "店舗管理":
    st.header("🏪 店舗マスタ管理")
    s_all = load_data("shop_master")
    b_all = load_data("branch_master")
    u_all = load_data("user_master")
    my_s_list = s_all[s_all["branch_id"] == info["id"]]

    with st.expander("➕ 新規店舗登録"):
        with st.form("reg_shop"):
            sc1, sc2, sc3 = st.columns(3)
            new_sid = sc1.text_input("店舗ID(4桁)", max_chars=4)
            new_snm = sc2.text_input("店舗名")
            new_spw = sc3.text_input("パスワード")
            if st.form_submit_button("登録"):
                nu = pd.DataFrame([{"id": new_sid, "password": new_spw, "role":"店舗", "target_id": new_snm, "name": new_snm}])
                ns = pd.DataFrame([{"shop_id": new_sid, "branch_id": info["id"], "shop_name": new_snm}])
                save_data(pd.concat([u_all, nu]), "user_master")
                save_data(pd.concat([s_all, ns]), "shop_master")
                st.success("登録完了"); st.rerun()

    st.subheader("📋 店舗一覧・一括編集")
    if not my_s_list.empty:
        mgrs = u_all[u_all["role"] == "管轄者"]
        mgr_names = ["未割当"] + mgrs["name"].tolist()
        branch_map = b_all.set_index("branch_id")["branch_name"].to_dict()
        branch_names = b_all["branch_name"].tolist()

        # レイアウト比率調整 (IDを0.8に広げ、ボタンを0.5に固定)
        col_ratios = [0.8, 1.2, 1.5, 0.8, 1.5, 0.5, 0.5]
        h = st.columns(col_ratios)
        h[0].caption("ID")
        h[1].caption("店舗名")
        h[2].caption("支部名")
        h[3].caption("PW")
        h[4].caption("管轄者")

        for idx, row in my_s_list.iterrows():
            with st.container():
                c = st.columns(col_ratios)
                
                e_sid = c[0].text_input("ID", row["shop_id"], key=f"s_id_{idx}")
                e_snm = c[1].text_input("店名", row["shop_name"], key=f"s_nm_{idx}")
                
                curr_b = branch_map.get(row["branch_id"], "不明")
                def_b_idx = branch_names.index(curr_b) if curr_b in branch_names else 0
                e_bnm = c[2].selectbox("支部", branch_names, index=def_b_idx, key=f"s_bn_{idx}")
                
                u_row = u_all[u_all["id"] == row["shop_id"]]
                curr_pw = u_row.iloc[0]["password"] if not u_row.empty else ""
                e_pw = c[3].text_input("PW", curr_pw, key=f"s_pw_{idx}")
                
                curr_mgr = mgrs[mgrs["target_id"].str.contains(row["shop_name"], na=False)]
                def_m_idx = mgr_names.index(curr_mgr.iloc[0]["name"]) if not curr_mgr.empty else 0
                e_mgr = c[4].selectbox("管轄者", mgr_names, index=def_m_idx, key=f"s_mg_{idx}")

                if c[5].button("🆙", key=f"s_up_{idx}", help="更新"):
                    new_b_id = b_all[b_all["branch_name"] == e_bnm].iloc[0]["branch_id"]
                    s_all.at[idx, ["shop_id", "shop_name", "branch_id"]] = [e_sid, e_snm, new_b_id]
                    u_all.loc[u_all["id"] == row["shop_id"], ["id", "password", "target_id", "name"]] = [e_sid, e_pw, e_snm, e_snm]
                    save_data(s_all, "shop_master"); save_data(u_all, "user_master")
                    st.success("更新完了"); st.rerun()
                
                if c[6].button("🗑️", key=f"s_de_{idx}", help="削除"):
                    save_data(s_all.drop(idx), "shop_master")
                    save_data(u_all[u_all["id"] != row["shop_id"]], "user_master")
                    st.warning("削除完了"); st.rerun()
    else:
        st.info("店舗が登録されていません。")

# --- C. エクセル発行 ---
elif menu == "エクセル発行":
    st.header("📊 エクセルレポート発行")
    df = load_data("expiry_records")
    df = df[df["shop_id"] == info["name"]]
    today = date.today()
    start_date = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
    end_date = (start_date + timedelta(days=32)).replace(day=7)
    
    st.write(f"抽出範囲: **{start_date}** ～ **{end_date}**")
    df['exp_dt'] = pd.to_datetime(df['expiry_date']).dt.date
    f_df = df[(df['exp_dt'] >= start_date) & (df['exp_dt'] <= end_date)]
    
    if not f_df.empty:
        st.download_button("📥 Excel(CSV)を発行する", data=convert_df(f_df), file_name=f"expiry_report_{info['id']}.csv")
        st.dataframe(f_df.drop(columns=['exp_dt']), use_container_width=True)
    else:
        st.warning("対象期間のデータがありません。")

# --- D. 期限入力 ---
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
        if st.button("一括登録を確定", type="primary", use_container_width=True):
            if final_data:
                df = load_data("expiry_records")
                s_master = load_data("shop_master")
                b_id = s_master[s_master["shop_name"] == info['name']]["branch_id"].values[0]
                new_recs = []
                for k, v in final_data.items():
                    new_recs.append({"id": datetime.now().strftime('%Y%m%d%H%M%S')+str(k), "shop_id": info['name'], "branch_id": b_id, "category": v["cat"], "item_name": v["name"], "expiry_date": str(v["date"]), "input_date": str(date.today())})
                save_data(pd.concat([df, pd.DataFrame(new_recs)]), "expiry_records")
                st.success("登録完了！"); st.balloons()

# --- E. パスワード変更 ---
elif menu == "パスワード変更":
    st.header("🔑 パスワード変更")
    with st.form("pw_f"):
        new_pw = st.text_input("新しいパスワード", type="password")
        if st.form_submit_button("パスワードを更新"):
            u_df = load_data("user_master")
            u_df.loc[u_df["id"] == info["id"], "password"] = new_pw
            save_data(u_df, "user_master")
            st.success("更新しました。")

# --- F. 管轄者・アイテム・支部管理 ---
elif menu in ["管轄者管理", "アイテム管理", "支部登録"]:
    st.header(f"⚙️ {menu}")
    if menu == "支部登録":
        b_all = load_data("branch_master")
        u_all = load_data("user_master")
        with st.form("reg_b"):
            c1, c2, c3 = st.columns(3)
            b_id = c1.text_input("支部ID(4桁)")
            b_name = c2.text_input("支部名")
            b_pw = c3.text_input("PW")
            if st.form_submit_button("登録"):
                save_data(pd.concat([u_all, pd.DataFrame([{"id":b_id, "password":b_pw, "role":"支部", "target_id":b_id, "name":b_name}])]), "user_master")
                save_data(pd.concat([b_all, pd.DataFrame([{"branch_id":b_id, "branch_name":b_name}])]), "branch_master")
                st.success("登録完了"); st.rerun()
    
    elif menu == "アイテム管理":
        i_all = load_data("item_master")
        with st.expander("➕ 新規アイテム追加"):
            with st.form("reg_i"):
                c1, c2, c3 = st.columns(3)
                cat = c1.selectbox("カテゴリ", ["冷蔵食材", "冷凍食材", "常温食材", "ドリンク", "ピックアップ"])
                nm = c2.text_input("アイテム名")
                tp = c3.radio("形式", ["年月日", "年月のみ"])
                if st.form_submit_button("保存"):
                    new_i = pd.DataFrame([{"item_id": str(len(i_all)+1), "category": cat, "item_name": nm, "input_type": tp}])
                    save_data(pd.concat([i_all, new_i]), "item_master"); st.rerun()
        
        st.subheader("📋 アイテム一覧・操作")
        for idx, row in i_all.iterrows():
            c = st.columns([1, 2, 1, 1])
            c[0].write(row["category"])
            new_nm = c[1].text_input("名前", row["item_name"], key=f"i_nm_{idx}")
            if c[2].button("🆙", key=f"i_up_{idx}"):
                i_all.at[idx, "item_name"] = new_nm
                save_data(i_all, "item_master"); st.rerun()
            if c[3].button("🗑️", key=f"i_de_{idx}"):
                save_data(i_all.drop(idx), "item_master"); st.rerun()

    elif menu == "管轄者管理":
        u_all = load_data("user_master")
        s_all = load_data("shop_master")
        my_shops = s_all[s_all["branch_id"] == info["id"]]
        with st.expander("➕ 新規管轄者登録"):
            with st.form("reg_mgr"):
                m_id = st.text_input("管轄者ID(4桁)", max_chars=4)
                m_name = st.text_input("管轄者名")
                m_pw = st.text_input("パスワード")
                sels = st.multiselect("担当店舗を選択", my_shops["shop_name"].tolist())
                if st.form_submit_button("登録"):
                    new_u = pd.DataFrame([{"id": m_id, "password": m_pw, "role":"管轄者", "target_id": ",".join(sels), "name": m_name}])
                    save_data(pd.concat([u_all, new_u]), "user_master")
                    st.success("登録完了"); st.rerun()
        m_list = u_all[u_all["role"] == "管轄者"]
        if not m_list.empty:
            for idx, row in m_list.iterrows():
                c = st.columns([1, 1, 2, 0.5])
                c[0].write(row["id"])
                c[1].write(row["name"])
                c[2].write(row["target_id"])
                if c[3].button("🗑️", key=f"m_de_{idx}"):
                    save_data(u_all.drop(idx), "user_master"); st.rerun()
