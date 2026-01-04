import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date, datetime, timedelta
import calendar
import re

# --- 0. UIデザインの精密調整 (CSS) ---
st.set_page_config(page_title="賞味期限管理システム", layout="wide")
st.markdown("""
    <style>
    [data-testid="column"] { align-items: center; }
    div[data-testid="stButton"] button {
        height: 42px; width: 100%; border-radius: 5px;
    }
    /* テーブル風の表示を整える */
    .stTextInput input { height: 42px; }
    </style>
    """, unsafe_allow_html=True)

# --- 1. 接続・認証設定 ---
@st.cache_resource
def get_gspread_client():
    # secrets.tomlから情報を取得
    info = dict(st.secrets["gcp_service_account"])
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    return gspread.authorize(creds)

client = get_gspread_client()
spreadsheet_id = "10SPAlhEavpSZzHr2iCgu3U_gaaW6IHWgvjNTdvSWY9A"
sheet = client.open_by_key(spreadsheet_id)

# --- 2. データ操作基本関数 (ここが重要) ---
def load_data(sheet_name):
    """スプレッドシートからデータを読み込み、クレンジングする"""
    try:
        worksheet = sheet.worksheet(sheet_name)
        data = worksheet.get_all_values()
        if len(data) > 0:
            # 1行目をヘッダーとしてDF作成
            df = pd.DataFrame(data[1:], columns=[c.strip() for c in data[0]])
            # 全ての列を文字列として扱い、前後の空白を削除（スプレッドシート手入力対策）
            return df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        return pd.DataFrame()
    except Exception as e:
        st.error(f"シート {sheet_name} の読み込みに失敗しました: {e}")
        return pd.DataFrame()

def save_data(df, sheet_name):
    """DFをスプレッドシートに上書き保存する"""
    try:
        worksheet = sheet.worksheet(sheet_name)
        worksheet.clear()
        # NaNを空文字に変換
        df_save = df.fillna("")
        # ヘッダーと値をリスト形式で流し込む
        data_to_save = [df_save.columns.values.tolist()] + df_save.values.tolist()
        worksheet.update(data_to_save)
        return True
    except Exception as e:
        st.error(f"保存エラー ({sheet_name}): {e}")
        return False

def validate_input(s, fmt):
    """入力された日付文字列のバリデーション"""
    try:
        if fmt == "年月日":
            if not re.match(r"^\d{8}$", s): return False, "8桁（20250101等）で入力"
            dt = datetime.strptime(s, "%Y%m%d").date()
        else:
            if not re.match(r"^\d{6}$", s): return False, "6桁（202501等）で入力"
            y, m = int(s[:4]), int(s[4:])
            dt = date(y, m, calendar.monthrange(y, m)[1])
        # 過去日チェック（必要に応じて）
        # if dt < date.today(): return False, "過去の日付です"
        return True, dt
    except:
        return False, "有効な日付ではありません"

# --- 3. セッション管理 ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'user_info': None})

# --- 4. ログイン画面 ---
if not st.session_state['logged_in']:
    st.title("🛡️ 賞味期限管理システム")
    with st.form("login"):
        u_id = st.text_input("ID (数字4桁)", max_chars=4)
        u_pw = st.text_input("パスワード", type="password")
        if st.form_submit_button("ログイン"):
            users = load_data("user_master")
            if not users.empty:
                # 文字列として比較
                user_row = users[(users['id'] == u_id) & (users['password'] == u_pw)]
                if not user_row.empty:
                    st.session_state.update({
                        'logged_in': True, 
                        'role': user_row.iloc[0]['role'], 
                        'user_info': user_row.iloc[0].to_dict()
                    })
                    st.rerun()
                else: st.error("IDまたはパスワードが正しくありません")
    st.stop()

# --- 5. メインメニュー ---
role = st.session_state['role']
info = st.session_state['user_info']
st.sidebar.title(f"【{role}】")
st.sidebar.write(f"👤 {info['name']} 様")

# ロール別メニュー設定
menus = {
    "マスター": ["期限確認", "支部登録", "アイテム管理"],
    "支部": ["期限確認", "店舗管理", "管轄者管理", "アイテム管理", "パスワード変更"],
    "管轄者": ["期限確認", "パスワード変更"],
    "店舗": ["期限入力", "期限一覧・編集", "エクセル発行", "パスワード変更"]
}
menu = st.sidebar.radio("メニュー", menus.get(role, ["期限確認"]))

if st.sidebar.button("ログアウト"):
    st.session_state.update({'logged_in': False, 'role': None})
    st.rerun()

# --- 6. 各機能の実装 ---

# --- 【店舗管理】 ---
if menu == "店舗管理":
    st.header("🏪 店舗マスタ管理")
    s_all = load_data("shop_master")
    b_all = load_data("branch_master")
    u_all = load_data("user_master")
    
    # ログインしている支部の店舗のみ表示
    my_s_list = s_all[s_all["branch_id"] == info["id"]]

    with st.expander("➕ 新規店舗登録"):
        with st.form("reg_shop"):
            c1, c2, c3 = st.columns(3)
            new_sid = c1.text_input("店舗ID(4桁)", max_chars=4)
            new_snm = c2.text_input("店舗名")
            new_spw = c3.text_input("初期パスワード")
            if st.form_submit_button("登録"):
                if new_sid and new_snm:
                    new_user = pd.DataFrame([{"id": new_sid, "password": new_spw, "role":"店舗", "target_id": new_snm, "name": new_snm}])
                    new_shop = pd.DataFrame([{"shop_id": new_sid, "branch_id": info["id"], "shop_name": new_snm}])
                    save_data(pd.concat([u_all, new_user]), "user_master")
                    save_data(pd.concat([s_all, new_shop]), "shop_master")
                    st.success("登録しました"); st.rerun()

    st.subheader("📋 店舗一覧（編集・削除）")
    if not my_s_list.empty:
        # 見出し
        h = st.columns([1, 2, 1, 1, 0.5, 0.5])
        h[0].caption("ID"); h[1].caption("店舗名"); h[2].caption("PW")
        
        for idx, row in my_s_list.iterrows():
            c = st.columns([1, 2, 1, 1, 0.5, 0.5])
            # ID編集
            edit_id = c[0].text_input("ID", row["shop_id"], key=f"sid_{idx}", label_visibility="collapsed")
            # 店名編集
            edit_nm = c[1].text_input("店名", row["shop_name"], key=f"snm_{idx}", label_visibility="collapsed")
            # ユーザーマスタからPW取得
            u_entry = u_all[u_all["id"] == row["shop_id"]]
            curr_pw = u_entry.iloc[0]["password"] if not u_entry.empty else ""
            edit_pw = c[2].text_input("PW", curr_pw, key=f"spw_{idx}", label_visibility="collapsed")
            
            if c[4].button("🆙", key=f"sup_{idx}"):
                # shop_master更新
                s_all.at[idx, "shop_id"] = edit_id
                s_all.at[idx, "shop_name"] = edit_nm
                # user_masterも連動更新
                u_all.loc[u_all["id"] == row["shop_id"], ["id", "password", "target_id", "name"]] = [edit_id, edit_pw, edit_nm, edit_nm]
                save_data(s_all, "shop_master")
                save_data(u_all, "user_master")
                st.success("更新完了"); st.rerun()
                
            if c[5].button("🗑️", key=f"sdel_{idx}"):
                save_data(s_all.drop(idx), "shop_master")
                save_data(u_all[u_all["id"] != row["shop_id"]], "user_master")
                st.warning("削除しました"); st.rerun()

# --- 【期限入力 (店舗用)】 ---
elif menu == "期限入力":
    st.header(f"📦 {info['name']} - 期限入力")
    items = load_data("item_master")
    if not items.empty:
        final_data = []
        for cat in items["category"].unique():
            st.markdown(f"#### 📍 {cat}")
            cat_items = items[items["category"] == cat]
            for _, i_row in cat_items.iterrows():
                with st.container(border=True):
                    col1, col2 = st.columns([2, 1])
                    col1.write(f"**{i_row['item_name']}**")
                    ph = "20251231" if i_row['input_type']=="年月日" else "202512"
                    val = col2.text_input("期限", key=f"inp_{i_row['item_id']}", placeholder=ph, label_visibility="collapsed")
                    if val:
                        is_ok, res = validate_input(val, i_row['input_type'])
                        if is_ok:
                            final_data.append({
                                "id": datetime.now().strftime('%Y%m%d%H%M%S') + str(i_row['item_id']),
                                "shop_id": info['name'],
                                "category": i_row['category'],
                                "item_name": i_row['item_name'],
                                "expiry_date": str(res),
                                "input_date": str(date.today())
                            })
                        else:
                            st.error(f"{i_row['item_name']}: {res}")

        if st.button("一括登録", type="primary", use_container_width=True):
            if final_data:
                old_df = load_data("expiry_records")
                save_data(pd.concat([old_df, pd.DataFrame(final_data)]), "expiry_records")
                st.success("全ての期限を登録しました！")
                st.balloons()
            else:
                st.warning("入力データがありません")

# --- 【期限確認 / 一覧】 ---
elif menu in ["期限確認", "期限一覧・編集"]:
    st.header(f"🔍 {menu}")
    df = load_data("expiry_records")
    
    # 権限によるフィルタリング
    if role == "店舗":
        df = df[df["shop_id"] == info["name"]]
    elif role == "支部":
        s_master = load_data("shop_master")
        my_shops = s_master[s_master["branch_id"] == info["id"]]["shop_name"].tolist()
        df = df[df["shop_id"].isin(my_shops)]
    # ...他ロールも同様

    if not df.empty:
        # 日付順にソート
        df = df.sort_values("expiry_date")
        for idx, row in df.iterrows():
            with st.container(border=True):
                c = st.columns([1, 2, 2, 0.5, 0.5])
                c[0].info(row["shop_id"])
                new_inm = c[1].text_input("商品名", row["item_name"], key=f"enm_{idx}")
                new_exp = c[2].text_input("期限", row["expiry_date"], key=f"edt_{idx}")
                if c[3].button("🆙", key=f"eup_{idx}"):
                    all_rec = load_data("expiry_records")
                    all_rec.loc[all_rec["id"] == row["id"], ["item_name", "expiry_date"]] = [new_inm, new_exp]
                    save_data(all_rec, "expiry_records")
                    st.rerun()
                if c[4].button("🗑️", key=f"edel_{idx}"):
                    all_rec = load_data("expiry_records")
                    save_data(all_rec[all_rec["id"] != row["id"]], "expiry_records")
                    st.rerun()
    else:
        st.write("該当するデータはありません。")

# --- 【アイテム管理】 ---
elif menu == "アイテム管理":
    st.header("⚙️ アイテムマスタ管理")
    i_all = load_data("item_master")
    
    with st.expander("➕ 新規アイテム追加"):
        with st.form("add_i"):
            c1, c2, c3 = st.columns(3)
            ni_cat = c1.selectbox("カテゴリ", ["冷蔵食材", "冷凍食材", "常温食材", "ドリンク", "備品"])
            ni_nm = c2.text_input("アイテム名")
            ni_tp = c3.selectbox("入力形式", ["年月日", "年月のみ"])
            if st.form_submit_button("追加"):
                new_i = pd.DataFrame([{"item_id": str(len(i_all)+1), "category": ni_cat, "item_name": ni_nm, "input_type": ni_tp}])
                save_data(pd.concat([i_all, new_i]), "item_master")
                st.rerun()

    for idx, row in i_all.iterrows():
        c = st.columns([1, 2, 1, 0.5, 0.5])
        c[0].write(row["category"])
        edit_inm = c[1].text_input("名", row["item_name"], key=f"inm_{idx}", label_visibility="collapsed")
        c[2].caption(row["input_type"])
        if c[3].button("🆙", key=f"iup_{idx}"):
            i_all.at[idx, "item_name"] = edit_inm
            save_data(i_all, "item_master"); st.rerun()
        if c[4].button("🗑️", key=f"idel_{idx}"):
            save_data(i_all.drop(idx), "item_master"); st.rerun()

# (パスワード変更などの他メニューは元のロジックを維持して実装)
