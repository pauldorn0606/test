import sqlite3
import calendar
from datetime import datetime, date, timedelta
import streamlit as st
import pandas as pd
import altair as alt

# -----------------------------------------------------------------------------
# 1. 資料庫初始化與操作函式
# -----------------------------------------------------------------------------
DB_FILE = "nutrition_logs.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # 飲食紀錄表
    c.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_date TEXT,
            item TEXT,
            calories REAL,
            protein REAL,
            carbs REAL,
            fat REAL
        )
    ''')
    # 運動紀錄表
    c.execute('''
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_date TEXT,
            item TEXT,
            calories_burned REAL,
            workout_type TEXT,
            distance REAL,
            duration_min REAL,
            avg_hr REAL,
            body_part TEXT,
            volume_kg REAL,
            workout_notes TEXT,
            rpe REAL,
            shoe TEXT
        )
    ''')
    # 體重與體脂紀錄表
    c.execute('''
        CREATE TABLE IF NOT EXISTS weight_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_date TEXT UNIQUE,
            weight REAL,
            body_fat REAL,
            note TEXT
        )
    ''')
    # 設定值儲存表
    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value REAL
        )
    ''')
    
    # 動態補齊 workouts 新欄位
    existing_workout_cols = [col[1] for col in c.execute("PRAGMA table_info(workouts)").fetchall()]
    new_workout_cols = {
        "workout_type": "TEXT",
        "distance": "REAL",
        "duration_min": "REAL",
        "avg_hr": "REAL",
        "body_part": "TEXT",
        "volume_kg": "REAL",
        "workout_notes": "TEXT",
        "rpe": "REAL",
        "shoe": "TEXT"
    }
    for col_name, col_type in new_workout_cols.items():
        if col_name not in existing_workout_cols:
            c.execute(f"ALTER TABLE workouts ADD COLUMN {col_name} {col_type}")
            
    # 動態補齊 weight_logs 體脂欄位 (body_fat)
    existing_weight_cols = [col[1] for col in c.execute("PRAGMA table_info(weight_logs)").fetchall()]
    if "body_fat" not in existing_weight_cols:
        c.execute("ALTER TABLE weight_logs ADD COLUMN body_fat REAL")
            
    conn.commit()
    conn.close()

# --- 設定值 DB 操作 ---
def get_target_settings():
    default_targets = {
        "target_cal": 2200.0,
        "target_p": 140.0,
        "target_carbs": 250.0,
        "target_fat": 60.0
    }
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT key, value FROM settings")
    rows = c.fetchall()
    conn.close()
    
    saved_settings = dict(rows)
    for k, v in default_targets.items():
        if k not in saved_settings:
            saved_settings[k] = v
    return saved_settings

def save_target_settings(cal, p, carbs, fat):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('target_cal', ?)", (cal,))
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('target_p', ?)", (p,))
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('target_carbs', ?)", (carbs,))
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('target_fat', ?)", (fat,))
    conn.commit()
    conn.close()

# --- 體重/體脂 DB 操作 ---
def add_or_update_weight(log_date, weight, body_fat=None, note=""):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO weight_logs (log_date, weight, body_fat, note)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(log_date) DO UPDATE SET weight=excluded.weight, body_fat=excluded.body_fat, note=excluded.note
    ''', (log_date, weight, body_fat, note))
    conn.commit()
    conn.close()

def get_weight_by_date(log_date):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM weight_logs WHERE log_date = ?", conn, params=(log_date,))
    conn.close()
    return df

def delete_weight_log(log_date):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM weight_logs WHERE log_date = ?", (log_date,))
    conn.commit()
    conn.close()

def get_recent_weights(days=30):
    conn = sqlite3.connect(DB_FILE)
    end_date = date.today()
    start_date = end_date - timedelta(days=days-1)
    df = pd.read_sql_query(
        "SELECT log_date, weight, body_fat FROM weight_logs WHERE log_date >= ? AND log_date <= ? ORDER BY log_date ASC",
        conn, params=(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
    )
    conn.close()
    return df

# --- 飲食 DB 操作 ---
def add_log(log_date, item, calories, protein, carbs, fat):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO logs (log_date, item, calories, protein, carbs, fat)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (log_date, item, calories, protein, carbs, fat))
    conn.commit()
    conn.close()

def update_log(log_id, item, calories, protein, carbs, fat):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        UPDATE logs
        SET item = ?, calories = ?, protein = ?, carbs = ?, fat = ?
        WHERE id = ?
    ''', (item, calories, protein, carbs, fat, log_id))
    conn.commit()
    conn.close()

def get_logs_by_date(log_date):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM logs WHERE log_date = ?", conn, params=(log_date,))
    conn.close()
    return df

def delete_log(log_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM logs WHERE id = ?", (log_id,))
    conn.commit()
    conn.close()

# --- 運動 DB 操作 ---
def add_workout(log_date, item, calories_burned, workout_type, distance=None, duration_min=None, avg_hr=None, body_part=None, volume_kg=None, workout_notes=None, rpe=None, shoe=None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO workouts (log_date, item, calories_burned, workout_type, distance, duration_min, avg_hr, body_part, volume_kg, workout_notes, rpe, shoe)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (log_date, item, calories_burned, workout_type, distance, duration_min, avg_hr, body_part, volume_kg, workout_notes, rpe, shoe))
    conn.commit()
    conn.close()

def get_workouts_by_date(log_date):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM workouts WHERE log_date = ?", conn, params=(log_date,))
    conn.close()
    return df

def delete_workout(workout_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM workouts WHERE id = ?", (workout_id,))
    conn.commit()
    conn.close()

# --- 當月跑量與跑鞋統計 ---
def get_monthly_running_distance(target_date):
    conn = sqlite3.connect(DB_FILE)
    first_day = date(target_date.year, target_date.month, 1)
    last_day_num = calendar.monthrange(target_date.year, target_date.month)[1]
    last_day = date(target_date.year, target_date.month, last_day_num)
    
    df = pd.read_sql_query(
        "SELECT SUM(distance) as total, COUNT(id) as run_count FROM workouts WHERE workout_type = '慢跑' AND log_date >= ? AND log_date <= ?",
        conn, params=(first_day.strftime("%Y-%m-%d"), last_day.strftime("%Y-%m-%d"))
    )
    conn.close()
    total_dist = df["total"].iloc[0] if df["total"].iloc[0] is not None else 0.0
    run_count = df["run_count"].iloc[0] if df["run_count"].iloc[0] is not None else 0
    return total_dist, run_count

def get_shoe_mileage():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(
        "SELECT shoe, SUM(distance) as total_dist FROM workouts WHERE workout_type = '慢跑' AND shoe IS NOT NULL AND shoe != '' GROUP BY shoe",
        conn
    )
    conn.close()
    return df

def get_running_history():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(
        "SELECT log_date, item, distance, duration_min, avg_hr, shoe FROM workouts WHERE workout_type = '慢跑' AND distance > 0 AND duration_min > 0 ORDER BY log_date DESC",
        conn
    )
    conn.close()
    if not df.empty:
        df["pace_decimal"] = df["duration_min"] / df["distance"]
        df["配速"] = df.apply(lambda r: calculate_pace(r["distance"], r["duration_min"]), axis=1)
        df["shoe"] = df["shoe"].fillna("未指定")
    return df

# --- 歷史與匯出 ---
def get_recent_logs(days=7):
    conn = sqlite3.connect(DB_FILE)
    end_date = date.today()
    start_date = end_date - timedelta(days=days-1)
    
    logs_df = pd.read_sql_query(
        "SELECT log_date, calories, protein, carbs, fat FROM logs WHERE log_date >= ? AND log_date <= ?",
        conn, params=(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
    )
    workouts_df = pd.read_sql_query(
        "SELECT * FROM workouts WHERE log_date >= ? AND log_date <= ?",
        conn, params=(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
    )
    conn.close()
    return logs_df, workouts_df

def get_all_logs():
    conn = sqlite3.connect(DB_FILE)
    logs_df = pd.read_sql_query("SELECT '飲食' as 類別, log_date, item, calories, protein, carbs, fat, NULL as calories_burned, NULL as workout_type, NULL as distance, NULL as duration_min, NULL as avg_hr, NULL as body_part, NULL as workout_notes, NULL as rpe, NULL as shoe, NULL as body_fat FROM logs", conn)
    workouts_df = pd.read_sql_query("SELECT '運動' as 類別, log_date, item, NULL as calories, NULL as protein, NULL as carbs, NULL as fat, calories_burned, workout_type, distance, duration_min, avg_hr, body_part, workout_notes, rpe, shoe, NULL as body_fat FROM workouts", conn)
    weight_df = pd.read_sql_query("SELECT '體重/體脂' as 類別, log_date, note as item, NULL as calories, NULL as protein, NULL as carbs, NULL as fat, NULL as calories_burned, NULL as workout_type, NULL as distance, NULL as duration_min, NULL as avg_hr, NULL as body_part, NULL as workout_notes, NULL as rpe, NULL as shoe, body_fat FROM weight_logs", conn)
    conn.close()
    combined = pd.concat([logs_df, workouts_df, weight_df]).sort_values(by=["log_date"], ascending=False)
    return combined

def calculate_pace(distance, duration_min):
    if distance and duration_min and distance > 0 and duration_min > 0:
        pace_dec = duration_min / distance
        pace_min = int(pace_dec)
        pace_sec = int(round((pace_dec - pace_min) * 60))
        if pace_sec == 60:
            pace_min += 1
            pace_sec = 0
        return f"{pace_min:02d}'{pace_sec:02d}\""
    return "-"

# 初始化資料庫
init_db()

# -----------------------------------------------------------------------------
# 2. Streamlit 介面配置與灰藍色 CSS 主題覆蓋
# -----------------------------------------------------------------------------
st.set_page_config(page_title="每日營養與運動紀錄器", page_icon="🥗", layout="centered")

# 全域灰藍色主題 CSS 覆蓋
st.markdown("""
    <style>
    div[data-testid="stSidebar"] {
        background-color: #F8FAFC !important;
    }
    .stButton > button[kind="primary"] {
        background-color: #5A738E !important;
        border-color: #5A738E !important;
    }
    .stProgress > div > div > div > div {
        background-color: #5A738E !important;
    }
    .order-box {
        background-color: #EFF4F8;
        padding: 8px 12px;
        border-radius: 6px;
        border-left: 4px solid #5A738E;
        margin-bottom: 8px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🥗 每日營養與運動紀錄器")

saved_targets = get_target_settings()

# --- 側邊欄配置 ---
st.sidebar.header("🎯 每日營養目標設定")
with st.sidebar.form("target_settings_form"):
    target_cal = st.number_input("目標熱量 (kcal)", value=int(saved_targets["target_cal"]), step=50)
    target_p = st.number_input("目標蛋白質 (g)", value=int(saved_targets["target_p"]), step=5)
    target_carbs = st.number_input("目標碳水化合物 (g)", value=int(saved_targets["target_carbs"]), step=5)
    target_fat = st.number_input("目標脂肪 (g)", value=int(saved_targets["target_fat"]), step=5)
    
    submit_targets = st.form_submit_button("💾 儲存目標設定", use_container_width=True)
    if submit_targets:
        save_target_settings(target_cal, target_p, target_carbs, target_fat)
        st.sidebar.success("目標設定已成功更新！")
        st.rerun()

# 側邊欄：數字設定顯示順序
st.sidebar.divider()
st.sidebar.header("🔢 區塊順序與顯示設定")
st.sidebar.caption("💡 數字越小越靠前顯示（例如：1 為最上方）。取消勾選可隱藏該區塊。")

DEFAULT_SECTIONS = [
    ("新增紀錄區塊", 1, True),
    ("當日攝取進度與目標", 2, True),
    ("月跑量與跑鞋追蹤", 3, True),
    ("當日明細清單", 4, True),
    ("近30天體重與體脂趨勢圖", 5, True),
    ("熱量與營養趨勢圖", 6, True),
    ("慢跑心率 vs. 配速散佈圖", 7, True),
    ("慢跑近7天里程圖", 8, True),
    ("重訓部位分布圖", 9, False)
]

section_configs = []

with st.sidebar.expander("⚙️ 調整區塊順序與開關", expanded=True):
    for sec_name, default_order, default_show in DEFAULT_SECTIONS:
        col_chk, col_num = st.columns([2.5, 1.5])
        with col_chk:
            show_sec = st.checkbox(sec_name, value=default_show, key=f"show_{sec_name}")
        with col_num:
            order_val = st.number_input(
                "順序",
                min_value=1,
                max_value=20,
                value=default_order,
                key=f"order_{sec_name}",
                label_visibility="collapsed"
            )
        if show_sec:
            section_configs.append((sec_name, order_val))

# 依數字排序區塊
section_configs.sort(key=lambda x: x[1])
ordered_sections = [sec[0] for sec in section_configs]

# 側邊欄：資料備份
st.sidebar.divider()
st.sidebar.header("💾 資料備份")
all_df = get_all_logs()
if not all_df.empty:
    csv_data = all_df.to_csv(index=False).encode('utf-8-sig')
    st.sidebar.download_button(
        label="📥 下載完整歷史紀錄 (CSV)",
        data=csv_data,
        file_name=f"nutrition_workout_logs_{date.today().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

# --- 主畫面日期選擇器 ---
st.divider()
selected_date = st.date_input("📅 選擇紀錄/查閱日期", value=date.today())
date_str = selected_date.strftime("%Y-%m-%d")

# -----------------------------------------------------------------------------
# 3. 區塊渲染邏輯
# -----------------------------------------------------------------------------

def render_add_records():
    st.subheader(f"➕ 新增紀錄 ({date_str})")
    tab_food, tab_exercise, tab_weight = st.tabs(["🍱 新增飲食", "🏃 新增運動", "⚖️ 體重與體脂"])

    with tab_food:
        with st.form("meal_form", clear_on_submit=True):
            item_name = st.text_input("品項名稱 (例如: 雞胸肉、蛋白飲)", value="")
            col1, col2 = st.columns(2)
            with col1:
                c_in = st.number_input("熱量 (kcal)", min_value=0.0, value=None, placeholder="0", step=10.0)
                p_in = st.number_input("蛋白質 (g)", min_value=0.0, value=None, placeholder="0", step=1.0)
            with col2:
                carbs_in = st.number_input("碳水化合物 (g)", min_value=0.0, value=None, placeholder="0", step=1.0)
                f_in = st.number_input("脂肪 (g)", min_value=0.0, value=None, placeholder="0", step=1.0)
            
            submit_food = st.form_submit_button("加入飲食紀錄", use_container_width=True)

        if submit_food:
            c_val = c_in if c_in is not None else 0.0
            p_val = p_in if p_in is not None else 0.0
            carbs_val = carbs_in if carbs_in is not None else 0.0
            f_val = f_in if f_in is not None else 0.0
            display_name = item_name.strip() if item_name.strip() else "未命名餐點"
            
            add_log(date_str, display_name, c_val, p_val, carbs_val, f_val)
            st.toast(f"已加入飲食：{display_name}")
            st.rerun()

    with tab_exercise:
        workout_category = st.radio("選擇運動類別", ["🏃 慢跑/有氧", "🏋️ 重訓/健身", "🚴 一般/其他"], horizontal=True)

        with st.form("workout_form", clear_on_submit=True):
            if workout_category == "🏃 慢跑/有氧":
                workout_name = st.text_input("運動名稱", value="慢跑")
                col_a, col_b = st.columns(2)
                with col_a:
                    dist_in = st.number_input("跑步距離 (km)", min_value=0.0, value=None, placeholder="0.0", step=0.1)
                    duration_in = st.number_input("時間 (分鐘)", min_value=0.0, value=None, placeholder="0", step=1.0)
                    shoe_in = st.selectbox("使用跑鞋", ["Adidas Boston 13", "Adidas Adizero", "Ricoh / 其他", "不指定"])
                with col_b:
                    hr_in = st.number_input("平均心率 (bpm)", min_value=0, value=None, placeholder="0", step=1)
                    cal_burned_in = st.number_input("消耗熱量 (kcal)", min_value=0.0, value=None, placeholder="0", step=10.0)
                
                submit_workout = st.form_submit_button("加入慢跑紀錄", use_container_width=True)
                if submit_workout:
                    b_val = cal_burned_in if cal_burned_in is not None else 0.0
                    add_workout(date_str, workout_name, b_val, "慢跑", distance=dist_in, duration_min=duration_in, avg_hr=hr_in, shoe=shoe_in)
                    st.toast(f"已加入慢跑紀錄：{dist_in or 0} km ({shoe_in})")
                    st.rerun()

            elif workout_category == "🏋️ 重訓/健身":
                workout_name = st.text_input("運動名稱", value="重量訓練")
                body_part_in = st.selectbox("主要訓練部位", ["胸部", "背部", "腿部", "肩部", "手臂", "核心", "全身/其他"])
                notes_in = st.text_area("動作與組數紀錄 (文字紀錄)", placeholder="例如：\n臥推 60kg x 8r x 4s\n上斜啞鈴臥推 20kg x 10r x 3s", height=100)
                
                col_a, col_b = st.columns(2)
                with col_a:
                    rpe_in = st.slider("自覺強度 (RPE 1-10)", min_value=1, max_value=10, value=7)
                with col_b:
                    cal_burned_in = st.number_input("估計消耗熱量 (kcal)", min_value=0.0, value=None, placeholder="0", step=10.0)
                
                submit_workout = st.form_submit_button("加入重訓紀錄", use_container_width=True)
                if submit_workout:
                    b_val = cal_burned_in if cal_burned_in is not None else 0.0
                    add_workout(date_str, workout_name, b_val, "重訓", body_part=body_part_in, workout_notes=notes_in, rpe=rpe_in)
                    st.toast(f"已加入重訓紀錄：{body_part_in}")
                    st.rerun()

            else:
                workout_name = st.text_input("運動名稱", value="")
                cal_burned_in = st.number_input("消耗熱量 (kcal)", min_value=0.0, value=None, placeholder="0", step=10.0)
                submit_workout = st.form_submit_button("加入運動紀錄", use_container_width=True)
                if submit_workout:
                    b_val = cal_burned_in if cal_burned_in is not None else 0.0
                    display_w = workout_name.strip() if workout_name.strip() else "一般運動"
                    add_workout(date_str, display_w, b_val, "其他")
                    st.toast(f"已加入運動紀錄：{display_w}")
                    st.rerun()

    with tab_weight:
        curr_w_df = get_weight_by_date(date_str)
        curr_w = curr_w_df["weight"].iloc[0] if not curr_w_df.empty and pd.notna(curr_w_df["weight"].iloc[0]) else None
        curr_fat = curr_w_df["body_fat"].iloc[0] if not curr_w_df.empty and "body_fat" in curr_w_df.columns and pd.notna(curr_w_df["body_fat"].iloc[0]) else None
        curr_note = curr_w_df["note"].iloc[0] if not curr_w_df.empty and pd.notna(curr_w_df["note"].iloc[0]) else ""

        with st.form("weight_form"):
            col_w1, col_w2 = st.columns(2)
            with col_w1:
                w_input = st.number_input("今日體重 (kg)", min_value=30.0, max_value=200.0, value=float(curr_w) if curr_w else None, placeholder="如 62.5", step=0.1)
            with col_w2:
                fat_input = st.number_input("體脂率 (%)", min_value=3.0, max_value=60.0, value=float(curr_fat) if curr_fat else None, placeholder="如 15.2", step=0.1)
            
            w_note = st.text_input("備註 (如: 早晨空腹/運動後)", value=curr_note)
            submit_weight = st.form_submit_button("💾 儲存體重與體脂紀錄", use_container_width=True)
            
            if submit_weight and w_input:
                add_or_update_weight(date_str, w_input, fat_input, w_note)
                st.toast(f"已更新 {date_str} 體重：{w_input} kg" + (f", 體脂：{fat_input}%" if fat_input else ""))
                st.rerun()

def render_daily_progress():
    logs_df = get_logs_by_date(date_str)
    consumed_cal = logs_df["calories"].sum() if not logs_df.empty else 0.0
    consumed_p = logs_df["protein"].sum() if not logs_df.empty else 0.0
    consumed_carbs = logs_df["carbs"].sum() if not logs_df.empty else 0.0
    consumed_f = logs_df["fat"].sum() if not logs_df.empty else 0.0

    st.subheader(f"📊 {date_str} 攝取進度與目標")

    weight_df = get_weight_by_date(date_str)
    if not weight_df.empty:
        w_val = weight_df["weight"].iloc[0]
        fat_val = weight_df["body_fat"].iloc[0] if "body_fat" in weight_df.columns and pd.notna(weight_df["body_fat"].iloc[0]) else None
        fat_str = f" | 體脂率：**{fat_val:.1f}%**" if fat_val else ""
        st.info(f"⚖️ **{date_str} 紀錄數據**：體重 **{w_val:.1f} kg**{fat_str}")

    rem_cal = target_cal - consumed_cal
    rem_p = target_p - consumed_p
    rem_carbs = target_carbs - consumed_carbs
    rem_f = target_fat - consumed_f

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("熱量剩餘", f"{rem_cal:.0f} kcal", delta=f"已攝取 {consumed_cal:.0f}")
    m2.metric("蛋白質剩餘", f"{rem_p:.1f} g", delta=f"已攝取 {consumed_p:.1f}")
    m3.metric("碳水剩餘", f"{rem_carbs:.1f} g", delta=f"已攝取 {consumed_carbs:.1f}")
    m4.metric("脂肪剩餘", f"{rem_f:.1f} g", delta=f"已攝取 {consumed_f:.1f}")

def render_monthly_run_and_shoes():
    monthly_dist, run_count = get_monthly_running_distance(selected_date)
    last_day_of_month = calendar.monthrange(selected_date.year, selected_date.month)[1]
    
    st.subheader(f"🏃 月跑量統計與跑鞋履歷")
    
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        st.markdown(f"#### 📅 {selected_date.year} 年 {selected_date.month} 月跑量")
        m_c1, m_c2 = st.columns(2)
        m_c1.metric("當月累積跑量", f"{monthly_dist:.2f} km")
        m_c2.metric("當月跑步次數", f"{run_count} 次")
        st.caption(f"統計區間：{selected_date.year}-{selected_date.month:02d}-01 至 {selected_date.year}-{selected_date.month:02d}-{last_day_of_month:02d}")

    with col_right:
        st.markdown("#### 👟 跑鞋退役里程追蹤 (全歷史)")
        shoe_df = get_shoe_mileage()
        if not shoe_df.empty:
            for _, row in shoe_df.iterrows():
                s_name = row['shoe']
                s_dist = row['total_dist']
                st.write(f"**{s_name}**: {s_dist:.1f} km / 600 km")
                st.progress(min(s_dist / 600.0, 1.0))
        else:
            st.info("尚無跑鞋里程紀錄。")

def render_daily_logs():
    logs_df = get_logs_by_date(date_str)
    workouts_df = get_workouts_by_date(date_str)
    weight_df = get_weight_by_date(date_str)
    
    st.subheader(f"📝 {date_str} 明細清單")
    list_tab1, list_tab2, list_tab3 = st.tabs([
        f"🍱 飲食明細 ({len(logs_df)})", 
        f"🏃 運動明細 ({len(workouts_df)})", 
        f"⚖️ 體重/體脂 ({len(weight_df)})"
    ])

    # --- 1. 飲食明細 (支援編輯與刪除) ---
    with list_tab1:
        if not logs_df.empty:
            for _, row in logs_df.iterrows():
                log_id = row['id']
                col_info, col_edit, col_del = st.columns([3.5, 0.8, 0.8])
                with col_info:
                    st.write(
                        f"**• {row['item']}** — "
                        f"{row['calories']:.0f} kcal | "
                        f"P: {row['protein']:.1f}g | "
                        f"C: {row['carbs']:.1f}g | "
                        f"F: {row['fat']:.1f}g"
                    )
                with col_edit:
                    if st.button("✏️ 編輯", key=f"btn_edit_food_{log_id}"):
                        st.session_state[f"editing_food_{log_id}"] = not st.session_state.get(f"editing_food_{log_id}", False)
                with col_del:
                    if st.button("🗑️ 刪除", key=f"del_food_{log_id}"):
                        delete_log(log_id)
                        st.toast(f"已刪除飲食：{row['item']}")
                        st.rerun()

                # 展開內嵌編輯表單
                if st.session_state.get(f"editing_food_{log_id}", False):
                    with st.form(key=f"form_edit_food_{log_id}"):
                        st.caption(f"🛠️ 編輯飲食紀錄 (ID: {log_id})")
                        e_item = st.text_input("品項名稱", value=row['item'])
                        col_e1, col_e2 = st.columns(2)
                        with col_e1:
                            e_cal = st.number_input("熱量 (kcal)", value=float(row['calories']), step=5.0)
                            e_p = st.number_input("蛋白質 (g)", value=float(row['protein']), step=1.0)
                        with col_e2:
                            e_carbs = st.number_input("碳水 (g)", value=float(row['carbs']), step=1.0)
                            e_fat = st.number_input("脂肪 (g)", value=float(row['fat']), step=1.0)
                        
                        btn_save_food = st.form_submit_button("💾 儲存變更")
                        if btn_save_food:
                            update_log(log_id, e_item.strip(), e_cal, e_p, e_carbs, e_fat)
                            st.session_state[f"editing_food_{log_id}"] = False
                            st.toast("飲食紀錄已更新！")
                            st.rerun()
                    st.divider()
        else:
            st.info("當天尚無飲食紀錄。")

    # --- 2. 運動明細 (支援刪除) ---
    with list_tab2:
        if not workouts_df.empty:
            for _, row in workouts_df.iterrows():
                col_info, col_del = st.columns([4, 1])
                with col_info:
                    w_type = row.get("workout_type", "其他")
                    if w_type == "慢跑":
                        pace = calculate_pace(row["distance"], row["duration_min"])
                        shoe_str = f" | 👟 {row['shoe']}" if row.get('shoe') else ""
                        st.write(
                            f"**🏃 {row['item']}** — "
                            f"**{row['distance'] or 0:.2f} km** | "
                            f"配速: **{pace}** | "
                            f"時間: {row['duration_min'] or 0:.0f}分 | "
                            f"心率: {row['avg_hr'] or '-'} bpm"
                            f"{shoe_str}"
                        )
                    elif w_type == "重訓":
                        notes_str = f"\n> {row['workout_notes'].replace(chr(10), ' / ')}" if row.get('workout_notes') else ""
                        st.write(
                            f"**🏋️ {row['item']} ({row['body_part'] or '未設定'})** — "
                            f"RPE: **{row['rpe'] or '-'}** | "
                            f"消耗: {row['calories_burned']:.0f} kcal"
                            f"{notes_str}"
                        )
                    else:
                        st.write(
                            f"**• {row['item']}** — 消耗 **{row['calories_burned']:.0f}** kcal"
                        )
                with col_del:
                    if st.button("🗑️ 刪除", key=f"del_workout_{row['id']}"):
                        delete_workout(row['id'])
                        st.toast("已刪除運動紀錄")
                        st.rerun()
        else:
            st.info("當天尚無運動紀錄。")

    # --- 3. 體重/體脂明細 (支援編輯與刪除) ---
    with list_tab3:
        if not weight_df.empty:
            w_row = weight_df.iloc[0]
            col_info, col_edit, col_del = st.columns([3.5, 0.8, 0.8])
            with col_info:
                fat_disp = f" | 體脂: {w_row['body_fat']:.1f}%" if "body_fat" in w_row and pd.notna(w_row['body_fat']) else ""
                note_disp = f" ({w_row['note']})" if w_row.get('note') else ""
                st.write(f"**⚖️ 體重: {w_row['weight']:.1f} kg**{fat_disp}{note_disp}")
            with col_edit:
                if st.button("✏️ 編輯", key=f"btn_edit_weight_{date_str}"):
                    st.session_state[f"editing_weight_{date_str}"] = not st.session_state.get(f"editing_weight_{date_str}", False)
            with col_del:
                if st.button("🗑️ 刪除", key=f"del_weight_{date_str}"):
                    delete_weight_log(date_str)
                    st.toast(f"已刪除 {date_str} 的體重紀錄")
                    st.rerun()

            if st.session_state.get(f"editing_weight_{date_str}", False):
                with st.form(key=f"form_edit_weight_{date_str}"):
                    st.caption("🛠️ 編輯體重與體脂紀錄")
                    col_ew1, col_ew2 = st.columns(2)
                    with col_ew1:
                        ew_val = st.number_input("體重 (kg)", value=float(w_row['weight']), step=0.1)
                    with col_ew2:
                        efat_val = st.number_input("體脂率 (%)", value=float(w_row['body_fat']) if ("body_fat" in w_row and pd.notna(w_row['body_fat'])) else None, step=0.1)
                    ew_note = st.text_input("備註", value=w_row['note'] if pd.notna(w_row['note']) else "")
                    
                    btn_save_weight = st.form_submit_button("💾 儲存變更")
                    if btn_save_weight and ew_val:
                        add_or_update_weight(date_str, ew_val, efat_val, ew_note)
                        st.session_state[f"editing_weight_{date_str}"] = False
                        st.toast("體重紀錄已更新！")
                        st.rerun()
        else:
            st.info("當天尚無體重/體脂紀錄。")

def render_weight_chart():
    st.markdown("#### ⚖️ 近 30 天體重與體脂趨勢圖")
    w_df = get_recent_weights(30)
    if not w_df.empty:
        chart_tab1, chart_tab2 = st.tabs(["📉 體重趨勢 (kg)", "% 體脂率趨勢 (%)"])
        with chart_tab1:
            st.line_chart(w_df, x="log_date", y="weight", color="#5A738E")
        with chart_tab2:
            fat_df = w_df.dropna(subset=["body_fat"])
            if not fat_df.empty:
                st.line_chart(fat_df, x="log_date", y="body_fat", color="#D97706")
            else:
                st.info("近 30 天尚無體脂率紀錄數據。")
    else:
        st.info("尚無體重紀錄，可在上方「新增紀錄 -> ⚖️ 體重與體脂」輸入數據。")

def render_cal_chart():
    st.markdown("#### 🔥 熱量與三大營養素趨勢")
    recent_logs_df, recent_workouts_df = get_recent_logs(days=7)
    today_dt = date.today()
    date_range = [(today_dt - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]

    food_summary = recent_logs_df.groupby("log_date").sum().reindex(date_range).fillna(0) if not recent_logs_df.empty else pd.DataFrame(0, index=date_range, columns=["calories", "protein", "carbs", "fat"])

    if not recent_workouts_df.empty:
        workout_summary = recent_workouts_df.groupby("log_date").agg({
            "calories_burned": "sum", "distance": "sum"
        }).reindex(date_range).fillna(0)
    else:
        workout_summary = pd.DataFrame(0, index=date_range, columns=["calories_burned", "distance"])

    daily_summary = food_summary.join(workout_summary).reset_index()
    daily_summary.rename(columns={
        "index": "日期", "log_date": "日期", 
        "calories": "攝取熱量(kcal)", "calories_burned": "運動消耗(kcal)", 
        "protein": "蛋白質(g)", "carbs": "碳水(g)", "fat": "脂肪(g)"
    }, inplace=True)

    st.line_chart(daily_summary, x="日期", y="攝取熱量(kcal)", color="#5A738E")
    st.line_chart(daily_summary, x="日期", y=["蛋白質(g)", "碳水(g)", "脂肪(g)"])

def render_pace_hr_chart():
    st.markdown("#### 🏃 慢跑心率 vs. 配速散佈圖 (心肺效率)")
    run_hist_df = get_running_history()
    if not run_hist_df.empty and run_hist_df["avg_hr"].notna().any():
        st.caption("💡 右下方代表相同心率下配速更快。滑鼠移至點點上可查閱詳細日期與紀錄。")
        scatter_chart = alt.Chart(run_hist_df).mark_circle(size=90).encode(
            x=alt.X('avg_hr:Q', title='平均心率 (bpm)', scale=alt.Scale(zero=False)),
            y=alt.Y('pace_decimal:Q', title='配速 (分鐘/km)', scale=alt.Scale(zero=False, reverse=True)),
            color=alt.Color('shoe:N', title='跑鞋'),
            tooltip=[
                alt.Tooltip('log_date:N', title='日期'),
                alt.Tooltip('item:N', title='項目'),
                alt.Tooltip('distance:Q', title='距離 (km)', format='.2f'),
                alt.Tooltip('配速:N', title='配速'),
                alt.Tooltip('avg_hr:Q', title='平均心率 (bpm)'),
                alt.Tooltip('shoe:N', title='跑鞋')
            ]
        ).interactive()
        st.altair_chart(scatter_chart, use_container_width=True)
    else:
        st.info("尚無包含平均心率的慢跑紀錄，填寫心率後即可自動生成散佈圖。")

def render_run_chart():
    st.markdown("#### 🏃 近 7 天慢跑里程")
    recent_logs_df, recent_workouts_df = get_recent_logs(days=7)
    today_dt = date.today()
    date_range = [(today_dt - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]

    if not recent_workouts_df.empty:
        workout_summary = recent_workouts_df.groupby("log_date").agg({"distance": "sum"}).reindex(date_range).fillna(0).reset_index()
    else:
        workout_summary = pd.DataFrame({"log_date": date_range, "distance": [0.0]*7})
    workout_summary.rename(columns={"log_date": "日期", "distance": "慢跑里程(km)"}, inplace=True)
    st.bar_chart(workout_summary, x="日期", y="慢跑里程(km)", color="#5A738E")

def render_part_chart():
    st.markdown("#### 📊 近 7 天重訓部位分布")
    _, recent_workouts_df = get_recent_logs(days=7)
    if not recent_workouts_df.empty and "body_part" in recent_workouts_df.columns:
        part_df = recent_workouts_df[recent_workouts_df["workout_type"] == "重訓"]
        if not part_df.empty:
            part_counts = part_df["body_part"].value_counts()
            st.bar_chart(part_counts, color="#5A738E")
        else:
            st.info("近 7 天尚無重訓資料。")
    else:
        st.info("近 7 天尚無重訓資料。")

# 區塊渲染對應表
SECTION_MAP = {
    "新增紀錄區塊": render_add_records,
    "當日攝取進度與目標": render_daily_progress,
    "月跑量與跑鞋追蹤": render_monthly_run_and_shoes,
    "當日明細清單": render_daily_logs,
    "近30天體重與體脂趨勢圖": render_weight_chart,
    "熱量與營養趨勢圖": render_cal_chart,
    "慢跑心率 vs. 配速散佈圖": render_pace_hr_chart,
    "慢跑近7天里程圖": render_run_chart,
    "重訓部位分布圖": render_part_chart,
}

# 依據使用者設定的數字順序繪製介面
for section_name in ordered_sections:
    st.divider()
    if section_name in SECTION_MAP:
        SECTION_MAP[section_name]()
