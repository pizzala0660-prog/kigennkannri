import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date, datetime, timedelta
import calendar
import re
import io

# --- 0. UIデザインの精密調整 (CSS) ---
# テキスト入力、セレクトボックス、ボタンの垂直位置を完全に一致させます
st.markdown("""
    <style>
    /* 全体の入力フォームの高さを統一し、ボタンとのズレを解消 */
    [data-testid="column"] {
        display: flex;
        align-items: center; /* 垂直方向中央揃え */
        justify-content: center;
    }
    /* ボタン専用の微調整：入力欄と高さを揃えるためマージンをリセット */
    div[data-testid="stButton"] {
        display: flex;
        align-items: center;
        margin-top: 0px !important;
    }
    div[data-testid="stButton"] button {
        height: 42px; /* 入力枠の標準的な高さに固定 */
        padding-top: 0px !important;
        padding-bottom: 0px !important;
        margin-top: 0px !important;
    }
    /* 入力枠の下の不要な余白を削除 */
    div[data-testid="stTextInput"], div[data-testid="stSelectbox"] {
        margin-bottom: 0px !important;
    }

    /* --- サイドバー最下段固定（更新/ログアウトを下に寄せる） --- */
    section[data-testid="stSidebar"] > div:first-child {
        display: flex;
        flex-direction: column;
        height: 100vh;
    }
    .sidebar-footer {
        margin-top: auto;
        padding-top: 10px;
        padding-bottom: 10px;
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

# --- ★追加：DB用スプレッドシートから同期する関数 ---
def sync_from_database_sheet():
    """
    DB用スプレッドシートが別にある場合に、
    DB側の指定ワークシートをこの運用スプレッドシートへ上書き同期します。

    secrets.toml に以下を入れると有効化：
      db_spreadsheet_id = "（DB用スプレッドシートID）"

    未設定の場合は「同期スキップ（再読込のみ）」になります。
    """
    try:
        db_id = st.secrets.get("db_spreadsheet_id", "")
        if not db_id:
            return False, "db_spreadsheet_id が未設定のため同期はスキップしました（再読込のみ）。"

        db_sheet = client.open_by_key(db_id)

        # 同期対象（必要に応じて増減OK）
        targets = ["user_master", "branch_master", "shop_master", "item_master"]

        for ws_name in targets:
            try:
                db_ws = db_sheet.worksheet(ws_name)
                values = db_ws.get_all_values()
                if not values:
                    save_data(pd.DataFrame(), ws_name)
                    continue

                cols = [c.strip() for c in values[0]]
                df_db = pd.DataFrame(values[1:], columns=cols)
                save_data(df_db, ws_name)

            except Exception as e:
                # 1シート失敗しても他を続行
                st.warning(f"同期スキップ: {ws_name}（{e}）")

        return True, "DBシートからマスタを同期しました。"

    except Exception as e:
        return False, f"DB同期エラー: {e}"

# --- 3. セッション管理 ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'user_info': None})

# --- 4. ログイン画面 ---
if not st.session_state['logged_in']:
    st.title("🛡️ 賞味期限管理システム")
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
                else:
                    st.error("IDまたはパスワードが不正です")
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

# ログアウトはそのまま
if st.sidebar.button("ログアウト"):
    st.session_state.update({'logged_in': False, 'role': None})
    st.rerun()

# --- ★追加：サイドバー最下段に「更新」ボタン ---
with st.sidebar.container():
    st.markdown('<div class="sidebar-footer">', unsafe_allow_html=True)

    if st.button("🔄 更新（DB同期/再読込）", use_container_width=True):
        # 1) DBがあれば同期（secretsにdb_spreadsheet_idがある場合だけ）
        ok, msg = sync_from_database_sheet()
        if ok:
            st.success(msg)
        else:
            st.info(msg)

        # 2) キャッシュをクリアして必ず最新を取り直す
        st.cache_data.clear()
        st.cache_resource.clear()

        # 3) 再実行
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# --- 6. 各機能の実装 ---

# --- 【店舗管理・垂直位置修正版】 ---
if menu == "店舗管理":
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
                save_data(pd.concat([u_all, nu]), "us_]()_
