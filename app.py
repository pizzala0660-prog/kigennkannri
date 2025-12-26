import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime
import calendar
import sqlite3
import re

# --- 0. データベース準備 ---
def init_db():
    conn = sqlite3.connect('zaiko.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS expiry_records
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, shop_id TEXT, category TEXT, item_name TEXT, expiry_date TEXT, input_date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS item_master
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT, item_name TEXT, input_type TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS shop_master
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, branch_id TEXT, shop_id TEXT, shop_name TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS branch_master
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, branch_id TEXT, branch_name TEXT)''')
    conn.commit()
    conn.close()

init_db()

CAT_OPTIONS = ["冷蔵食材", "冷凍食材", "常温食材", "ドリンク", "ピックアップ"]
TYPE_OPTIONS = ["年月日", "年月のみ"]

# --- 1. 共通関数 ---
ALL_ADMIN_ID = "9999"

def get_db_connection():
    return sqlite3.connect('zaiko.db')

def get_branch_info(uid):
    conn = get_db_connection()
    res = conn.execute("SELECT branch_name FROM branch_master WHERE branch_id = ?", (uid,)).fetchone()
    conn.close()
    return res[0] if res else None

def get_shop_info(uid):
    conn = get_db_connection()
    res = conn.execute("SELECT shop_name FROM shop_master WHERE shop_id = ?", (uid,)).fetchone()
    conn.close()
    return res[0] if res else None

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

# --- 2. ログイン管理 ---
if 'login_id' not in st.session_state:
    st.session_state.login_id = None

if st.session_state.login_id is None:
    st.title("賞味期限管理システム")
    u_id = st.text_input("IDを入力してください (数字4桁)", max_chars=4)
    if st.button("ログイン", use_container_width=True):
        if u_id.isdigit() and len(u_id) == 4:
            st.session_state.login_id = u_id
            st.rerun()
        else:
            st.error("IDは数字4桁で入力してください")
else:
    branch_name = get_branch_info(st.session_state.login_id)
    shop_name = get_shop_info(st.session_state.login_id)
    
    if st.sidebar.button("ログアウト"):
        st.session_state.login_id = None
        st.rerun()

    # --- A. 管理者画面 ---
    if st.session_state.login_id == ALL_ADMIN_ID or branch_name:
        st.title("⚙️ 管理者ページ")
        tabs_list = ["アイテム管理", "店舗管理", "集計表"]
        if st.session_state.login_id == ALL_ADMIN_ID: tabs_list.insert(0, "支部管理")
        selected_tabs = st.tabs(tabs_list)
        tab_offset = 1 if st.session_state.login_id == ALL_ADMIN_ID else 0

        # --- 支部管理 (全統括のみ) ---
        if st.session_state.login_id == ALL_ADMIN_ID:
            with selected_tabs[0]:
                st.subheader("支部ID登録")
                c1, c2 = st.columns(2)
                b_id = c1.text_input("支部ID(4桁)", max_chars=4, key="reg_b_id")
                b_name = c2.text_input("支部名", key="reg_b_name")
                if st.button("支部を登録"):
                    conn = get_db_connection()
                    conn.execute("INSERT INTO branch_master (branch_id, branch_name) VALUES (?, ?)", (b_id, b_name))
                    conn.commit()
                    conn.close()
                    st.rerun()
                st.divider()
                conn = get_db_connection()
                df_b = pd.read_sql_query("SELECT * FROM branch_master", conn)
                for i, row in df_b.iterrows():
                    cols = st.columns([1, 3, 1])
                    cols[0].write(row["branch_id"])
                    cols[1].write(row["branch_name"])
                    if cols[2].button("削除", key=f"del_b_{row['id']}"):
                        conn.execute("DELETE FROM branch_master WHERE id = ?", (row['id'],))
                        conn.commit()
                        st.rerun()
                conn.close()

        # --- アイテム管理 ---
        with selected_tabs[tab_offset]:
            st.subheader("アイテムの登録・編集")
            with st.expander("➕ 新規アイテム追加"):
                c1, c2, c3 = st.columns(3)
                i_cat = c1.selectbox("カテゴリ", CAT_OPTIONS, key="new_i_cat")
                i_name = c2.text_input("アイテム名", key="new_i_name")
                i_type = c3.radio("形式", TYPE_OPTIONS, key="new_i_type")
                if st.button("アイテムを保存", use_container_width=True):
                    conn = get_db_connection()
                    conn.execute("INSERT INTO item_master (category, item_name, input_type) VALUES (?, ?, ?)", (i_cat, i_name, i_type))
                    conn.commit()
                    conn.close()
                    st.rerun()
            st.write("---")
            conn = get_db_connection()
            items = pd.read_sql_query("SELECT * FROM item_master", conn)
            for _, row in items.iterrows():
                with st.container():
                    col1, col2, col3, col4, col5 = st.columns([1.5, 2, 1.2, 1, 1])
                    new_c = col1.selectbox("カテゴリ", CAT_OPTIONS, index=CAT_OPTIONS.index(row['category']) if row['category'] in CAT_OPTIONS else 0, key=f"ec_{row['id']}")
                    new_n = col2.text_input("名前", row['item_name'], key=f"en_{row['id']}")
                    new_t = col3.selectbox("形式", TYPE_OPTIONS, index=TYPE_OPTIONS.index(row['input_type']) if row['input_type'] in TYPE_OPTIONS else 0, key=f"et_{row['id']}")
                    if col4.button("更新", key=f"up_i_{row['id']}", use_container_width=True):
                        conn.execute("UPDATE item_master SET category=?, item_name=?, input_type=? WHERE id=?", (new_c, new_n, new_t, row['id']))
                        conn.commit()
                        st.rerun()
                    if col5.button("削除", key=f"dl_i_{row['id']}", use_container_width=True):
                        conn.execute("DELETE FROM item_master WHERE id=?", (row['id'],))
                        conn.commit()
                        st.rerun()
            conn.close()

        # --- 店舗管理 ---
        with selected_tabs[tab_offset + 1]:
            st.subheader("店舗の登録・編集")
            with st.expander("➕ 新規店舗追加"):
                if branch_name:
                    act_b_id = st.session_state.login_id
                    st.write(f"担当支部: **{branch_name}**")
                else:
                    conn = get_db_connection()
                    branches = pd.read_sql_query("SELECT * FROM branch_master", conn)
                    conn.close()
                    act_b_id = st.selectbox("登録先の支部", branches["branch_id"].tolist(), format_func=lambda x: branches[branches['branch_id']==x]['branch_name'].values[0]) if not branches.empty else None
                c1, c2 = st.columns(2)
                s_id = c1.text_input("店舗ID(4桁)", max_chars=4, key="reg_s_id")
                s_name = c2.text_input("店舗名", key="reg_s_name")
                if st.button("店舗を保存", use_container_width=True):
                    conn = get_db_connection()
                    conn.execute("INSERT INTO shop_master (branch_id, shop_id, shop_name) VALUES (?, ?, ?)", (act_b_id, s_id, s_name))
                    conn.commit()
                    conn.close()
                    st.rerun()
            st.write("---")
            conn = get_db_connection()
            if st.session_state.login_id == ALL_ADMIN_ID:
                df_s = pd.read_sql_query("SELECT * FROM shop_master", conn)
            else:
                df_s = pd.read_sql_query("SELECT * FROM shop_master WHERE branch_id = ?", conn, params=(st.session_state.login_id,))
            for _, row in df_s.iterrows():
                c1, c2, c3, c4, c5 = st.columns([1, 1, 3, 1, 1])
                new_bid = c1.text_input("支部ID", row['branch_id'], key=f"sb_{row['id']}")
                new_sid = c2.text_input("店舗ID", row['shop_id'], key=f"ss_{row['id']}")
                new_sn  = c3.text_input("店舗名", row['shop_name'], key=f"sn_{row['id']}")
                if c4.button("更新", key=f"up_s_{row['id']}", use_container_width=True):
                    conn.execute("UPDATE shop_master SET branch_id=?, shop_id=?, shop_name=? WHERE id=?", (new_bid, new_sid, new_sn, row['id']))
                    conn.commit()
                    st.rerun()
                if c5.button("削除", key=f"dl_s_{row['id']}", use_container_width=True):
                    conn.execute("DELETE FROM shop_master WHERE id=?", (row['id'],))
                    conn.commit()
                    st.rerun()
            conn.close()

        # --- 集計表 ---
        with selected_tabs[tab_offset + 2]:
            st.subheader("📊 集計一覧表")
            conn = get_db_connection()
            df_res = pd.read_sql_query("SELECT s.shop_name, r.item_name, r.expiry_date FROM expiry_records r LEFT JOIN shop_master s ON r.shop_id = s.shop_id", conn)
            if not df_res.empty:
                pivot = df_res.pivot_table(index='item_name', columns='shop_name', values='expiry_date', aggfunc='last')
                st.dataframe(pivot.fillna("-"), use_container_width=True)
                st.divider()
                st.subheader("📢 期限警告アラート")
                today = date.today()
                df_res['dt'] = pd.to_datetime(df_res['expiry_date']).dt.date
                for _, r in df_res.sort_values('expiry_date').iterrows():
                    diff = (r['dt'] - today).days
                    msg = f"{r['shop_name']} | {r['item_name']} ({r['expiry_date']})"
                    if diff <= 0: st.error(f"🚨 【期限切れ・本日】 {msg}")
                    elif diff <= 7: st.warning(f"⚠️ 【1週間以内】 {msg}")
                    elif diff <= 30: st.success(f"✅ 【1か月以内】 {msg}")
            conn.close()

    # --- B. 店舗用入力画面 (スマホ最適化) ---
    else:
        st.title(f"📦 {shop_name}")
        conn = get_db_connection()
        items = pd.read_sql_query("SELECT * FROM item_master", conn)
        conn.close()
        if not items.empty:
            final_data = {}
            all_valid = True
            for cat in items["category"].unique():
                st.markdown(f"### 📍 {cat}")
                for _, row in items[items["category"] == cat].iterrows():
                    with st.container():
                        st.write(f"**{row['item_name']}**")
                        placeholder = "20251231" if row['input_type']=="年月日" else "202512"
                        val_str = st.text_input(f"{row['input_type']}を入力", key=f"inp_{row['id']}", placeholder=placeholder)
                        if val_str:
                            valid, res = validate_input(val_str, row['input_type'])
                            if valid:
                                final_data[row['id']] = {"cat": row['category'], "name": row['item_name'], "date": res}
                                st.caption(f"✅ 登録予定: {res}")
                            else:
                                st.error(res)
                                all_valid = False
                st.write("")
            st.divider()
            if not all_valid:
                st.button("入力エラーがあります", disabled=True, use_container_width=True)
            else:
                if st.button("一括登録を確定する", type="primary", use_container_width=True):
                    if final_data:
                        conn = get_db_connection()
                        for k, v in final_data.items():
                            conn.execute("INSERT INTO expiry_records (shop_id, category, item_name, expiry_date, input_date) VALUES (?, ?, ?, ?, ?)",
                                         (st.session_state.login_id, v["cat"], v["name"], str(v["date"]), date.today().isoformat()))
                        conn.commit()
                        conn.close()
                        st.success("全てのアイテムを登録しました！")
                        st.balloons()