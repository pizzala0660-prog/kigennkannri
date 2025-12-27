import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date, datetime, timedelta
import calendar
import re
import io

# --- 0. スプレッドシート接続設定 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name):
    try:
        # ttl=0 でキャッシュを無効化し、常に最新のスプレッドシートを読み込む
        return conn.read(worksheet=sheet_name, ttl=0)
    except:
        return pd.DataFrame()

def save_data(df, sheet_name):
    # スプレッドシートを更新
    conn.update(worksheet=sheet_name, data=df)

# 初期シート作成（データが空の場合にヘッダーを作成）
def init_spreadsheet():
    sheets = {
        "expiry_records": ["id", "shop_id", "category", "item_name", "expiry_date", "input_date"],
        "item_master": ["id", "category", "item_name", "input_type"],
        "shop_master": ["id", "branch_id", "shop_id", "shop_name"],
        "branch_master": ["id", "branch_id", "branch_name"],
        "manager_shop_link": ["branch_id", "shop_id"] # 紐付け用新シート
    }
    for s, cols in sheets.items():
        df = load_data(s)
        if df.empty or len(df.columns) == 0:
            save_data(pd.DataFrame(columns=cols), s)

init_spreadsheet()

CAT_OPTIONS = ["冷蔵食材", "冷凍食材", "常温食材", "ドリンク", "ピックアップ"]
TYPE_OPTIONS = ["年月日", "年月のみ"]
ALL_ADMIN_ID = "9999"

# --- 1. 共通関数 ---
def validate_input(s, fmt):
    try:
        if fmt == "年月日":
            if not re.match(r"^\d{8}$", s): return False, "8桁の数字で入力してください"
            dt = datetime.strptime(s, "%Y%m%d").date()
        else: # 年月のみ
            if not re.match(r"^\d{6}$", s): return False, "6桁の数字で入力してください"
            y, m = int(s[:4]), int(s[4:])
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
    # データの読み込み
    df_branch = load_data("branch_master")
    df_shop = load_data("shop_master")
    df_item = load_data("item_master")
    df_link = load_data("manager_shop_link")
    df_records = load_data("expiry_records")
    
    # 権限判定
    branch_info = df_branch[df_branch['branch_id'] == st.session_state.login_id]
    shop_info = df_shop[df_shop['shop_id'] == st.session_state.login_id]
    
    is_all_admin = (st.session_state.login_id == ALL_ADMIN_ID)
    is_manager = not branch_info.empty
    
    branch_name = branch_info.iloc[0]['branch_name'] if is_manager else None
    shop_name = shop_info.iloc[0]['shop_name'] if not shop_info.empty else None

    if st.sidebar.button("ログアウト"):
        st.session_state.login_id = None
        st.rerun()

    # --- A. 管理者・管轄者画面 ---
    if is_all_admin or is_manager:
        st.title(f"⚙️ {'全権管理者' if is_all_admin else branch_name + ' 管轄者'} ページ")
        
        # 管轄者が担当する店舗のIDリストを取得
        managed_shop_ids = []
        if is_manager:
            managed_shop_ids = df_link[df_link['branch_id'] == st.session_state.login_id]['shop_id'].tolist()

        tabs = st.tabs(["集計・Excel出力", "店舗紐付け管理", "マスタ登録"])
        
        # --- タブ1: 集計・Excel出力 ---
        with tabs[0]:
            st.subheader("📊 期限一覧・抽出")
            
            # データの絞り込み（管轄者の場合は自分の担当店舗のみ）
            display_df = df_records.copy()
            if is_manager:
                display_df = display_df[display_df['shop_id'].isin(managed_shop_ids)]
            
            # 店舗名を表示するために結合
            if not display_df.empty and not df_shop.empty:
                display_df = pd.merge(display_df, df_shop[['shop_id', 'shop_name']], on='shop_id', how='left')

            # 抽出条件
            st.write("▼ 条件を選択してください（複数選択可）")
            c1, c2 = st.columns(2)
            f_1w = c1.checkbox("1週間以内")
            f_1m = c2.checkbox("1か月以内")
            
            if not display_df.empty:
                # 日付型に変換してフィルタリング
                display_df['expiry_date_dt'] = pd.to_datetime(display_df['expiry_date']).dt.date
                today = date.today()
                
                conditions = []
                if f_1w: conditions.append(display_df['expiry_date_dt'] <= today + timedelta(days=7))
                if f_1m: conditions.append(display_df['expiry_date_dt'] <= today + timedelta(days=30))
                
                if conditions:
                    # 複数条件のいずれかに合致するものを抽出
                    display_df = display_df[pd.concat(conditions, axis=1).any(axis=1)]

                st.dataframe(display_df.drop(columns=['expiry_date_dt']), use_container_width=True)
                
                # Excel出力
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    display_df.to_excel(writer, index=False, sheet_name='Sheet1')
                
                st.download_button(
                    label="📥 表示中のリストをExcelで保存",
                    data=output.getvalue(),
                    file_name=f"expiry_report_{today}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            else:
                st.info("表示できるデータがありません。")

        # --- タブ2: 店舗紐付け管理 ---
        with tabs[1]:
            st.subheader("🔗 管轄店舗の紐付け設定")
            
            # 全権管理者の場合は操作対象の管轄者を選択
            if is_all_admin:
                if not df_branch.empty:
                    target_branch = st.selectbox("設定する管轄者を選択", df_branch['branch_id'].tolist(), 
                                               format_func=lambda x: f"{x}: {df_branch[df_branch['branch_id']==x]['branch_name'].values[0]}")
                else:
                    st.warning("先に支部を登録してください")
                    target_branch = None
            else:
                target_branch = st.session_state.login_id
            
            if target_branch:
                # 現在の紐付けを表示
                current_links = df_link[df_link['branch_id'] == target_branch]
                st.write(f"現在の担当店舗一覧:")
                
                for idx, row in current_links.iterrows():
                    col_name, col_btn = st.columns([4, 1])
                    s_name = df_shop[df_shop['shop_id'] == row['shop_id']]['shop_name'].values[0] if row['shop_id'] in df_shop['shop_id'].values else "未登録店舗"
                    col_name.write(f"🏢 {row['shop_id']} : {s_name}")
                    if col_btn.button("解除", key=f"unlink_{idx}"):
                        new_df = df_link.drop(idx)
                        save_data(new_df, "manager_shop_link")
                        st.rerun()
                
                st.divider()
                # 新規追加用
                st.write("➕ 新しい担当店舗を追加")
                available_shops = df_shop[~df_shop['shop_id'].isin(current_links['shop_id'])]
                if not available_shops.empty:
                    new_shop = st.selectbox("店舗を選択", available_shops['shop_id'].tolist(),
                                           format_func=lambda x: f"{x}: {df_shop[df_shop['shop_id']==x]['shop_name'].values[0]}")
                    if st.button("担当として追加登録する", use_container_width=True):
                        new_row = pd.DataFrame([{"branch_id": target_branch, "shop_id": new_shop}])
                        save_data(pd.concat([df_link, new_row], ignore_index=True), "manager_shop_link")
                        st.rerun()
                else:
                    st.write("追加できる未担当の店舗はありません。")

        # --- タブ3: マスタ登録 ---
        with tabs[2]:
            st.subheader("各種情報の登録・編集")
            
            # 支部登録
            with st.expander("支部（管轄者）の登録"):
                c1, c2 = st.columns(2)
                nb_id = c1.text_input("支部ID(4桁)", max_chars=4, key="nbid")
                nb_name = c2.text_input("支部名", key="nbname")
                if st.button("支部を保存"):
                    new_b = pd.DataFrame([{"id": len(df_branch)+1, "branch_id": nb_id, "branch_name": nb_name}])
                    save_data(pd.concat([df_branch, new_b], ignore_index=True), "branch_master")
                    st.rerun()
                st.table(df_branch)

            # 店舗登録
            with st.expander("店舗の登録"):
                c1, c2, c3 = st.columns(3)
                ns_bid = c1.text_input("所属支部ID", key="nsbid")
                ns_sid = c2.text_input("店舗ID(4桁)", max_chars=4, key="nssid")
                ns_name = c3.text_input("店舗名", key="nsname")
                if st.button("店舗を保存"):
                    new_s = pd.DataFrame([{"id": len(df_shop)+1, "branch_id": ns_bid, "shop_id": ns_sid, "shop_name": ns_name}])
                    save_data(pd.concat([df_shop, new_s], ignore_index=True), "shop_master")
                    st.rerun()
                st.table(df_shop)

            # アイテム登録
            with st.expander("アイテムの登録"):
                c1, c2, c3 = st.columns(3)
                ni_cat = c1.selectbox("カテゴリ", CAT_OPTIONS, key="nicat")
                ni_name = c2.text_input("アイテム名", key="niname")
                ni_type = c3.radio("形式", TYPE_OPTIONS, key="nitype")
                if st.button("アイテムを保存"):
                    new_i = pd.DataFrame([{"id": len(df_item)+1, "category": ni_cat, "item_name": ni_name, "input_type": ni_type}])
                    save_data(pd.concat([df_item, new_i], ignore_index=True), "item_master")
                    st.rerun()
                st.table(df_item)

    # --- B. 店舗用入力画面 ---
    elif shop_name:
        st.title(f"📋 店舗入力: {shop_name}")
        st.caption("賞味期限を入力してください（過去日は登録できません）")
        
        if not df_item.empty:
            final_inputs = []
            for i, row in df_item.iterrows():
                st.write(f"---")
                st.markdown(f"**{row['item_name']}** ({row['category']})")
                ph = "20251231" if row['input_type']=="年月日" else "202512"
                val = st.text_input(f"{row['input_type']}形式で入力", key=f"shop_in_{i}", placeholder=ph)
                
                if val:
                    ok, res = validate_input(val, row['input_type'])
                    if ok:
                        st.success(f"確認: {res}")
                        final_inputs.append({
                            "id": len(df_records) + len(final_inputs) + 1,
                            "shop_id": st.session_state.login_id,
                            "category": row['category'],
                            "item_name": row['item_name'],
                            "expiry_date": str(res),
                            "input_date": str(date.today())
                        })
                    else:
                        st.error(res)

            st.divider()
            if st.button("一括登録を確定する", type="primary", use_container_width=True):
                if final_inputs:
                    new_df = pd.concat([df_records, pd.DataFrame(final_inputs)], ignore_index=True)
                    save_data(new_df, "expiry_records")
                    st.success("スプレッドシートへの保存が完了しました！")
                    st.balloons()
                else:
                    st.warning("有効な入力データがありません。")
        else:
            st.info("登録されているアイテムがありません。管理者に連絡してください。")
    
    else:
        st.error("ログインIDが正しくありません。管理者に登録を確認してください。")

