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
            rpe REAL,
            shoe TEXT
        )
    ''')
    # 體重紀錄表
    c.execute('''
        CREATE TABLE IF NOT EXISTS weight_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_date TEXT UNIQUE,
            weight REAL,
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
    
    # 動態補齊 workout 新欄位
    existing_cols = [col[1] for col in c.execute("PRAGMA table_info(workouts)").fetchall()]
    new_cols = {
        "workout_type": "TEXT",
        "distance": "REAL",
        "duration_min": "REAL",
        "avg_hr": "REAL",
        "body_part": "TEXT",
        "volume_kg": "REAL",
        "rpe": "REAL",
        "shoe": "TEXT"
    }
    for col_name, col_type in new_cols.items():
        if col_name not in existing_cols:
            c.execute(f"ALTER TABLE workouts ADD COLUMN {col_name} {col_type}")
            
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

# --- 體重 DB 操作 ---
def add_or_update_weight(log_date, weight, note=""):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO weight_logs (log_date, weight, note)
        VALUES (?, ?, ?)
        ON CONFLICT(log_date) DO UPDATE SET weight=excluded.weight, note=excluded.note
    ''', (log_date, weight, note))
    conn.commit()
    conn.close()

def get_weight_by_date(log_date):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM weight_logs WHERE log_date = ?", conn, params=(log_date,))
    conn.close()
    return df

def get_recent_weights(days=30):
    conn = sqlite3.connect(DB_FILE)
    end_date = date.today()
    start_date = end_date - timedelta(days=days-1)
    df = pd.read_sql_query(
        "SELECT log_date, weight FROM weight_logs WHERE log_date >= ? AND log_date <= ? ORDER BY log_date ASC",
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
def add_workout(log_date, item, calories_burned, workout_type, distance=None, duration_min=None, avg_hr=None, body_part=None, volume_kg=None, rpe=None, shoe=None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO workouts (log_date, item, calories_burned, workout_type, distance, duration_min, avg_hr, body_part, volume_kg, rpe, shoe)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (log_date, item, calories_burned, workout_type, distance, duration_min, avg_hr, body_part, volume_kg, rpe, shoe))
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

# --- 當月跑量統計 ---
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
    logs_df = pd.read_sql_query("SELECT '飲食' as 類別, log_date, item, calories, protein, carbs, fat, NULL as calories_burned, NULL as workout_type, NULL as distance, NULL as duration_min, NULL as avg_hr, NULL as body_part, NULL as volume_kg, NULL as rpe, NULL as shoe FROM logs", conn)
    workouts_df = pd.read_sql_query("SELECT '運動' as 類別, log_date, item, NULL as calories, NULL as protein, NULL as carbs, NULL as fat, calories_burned, workout_type, distance, duration_min, avg_hr, body_part, volume_kg, rpe, shoe FROM workouts", conn)
    weight_df = pd.read_sql_query("SELECT '體重' as 類別, log_date, note as item, NULL as calories, NULL as protein, NULL as carbs, NULL as fat, NULL as calories_burned, NULL as workout_type, NULL as distance, NULL as duration_min, NULL as avg_hr, NULL as body_part, NULL as volume_kg, NULL as rpe, NULL as shoe FROM weight_logs", conn)
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
# 2. Streamlit 介面配置與灰藍色樣式注入 (CSS)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="每日營養與運動紀錄器", page_icon="🥗", layout="centered")

# 注入灰藍色調自訂 CSS 樣式
st.markdown("""
    <style>
    /* 灰藍色風格客製化 */
    :root {
        --slate-blue: #5A738E;
        --slate-blue-dark: #4A607A;
        --slate-blue-light: #EBF0F5;
        --slate-blue-bg: #F4F7FA;
    }
    
    /* Multiselect 選項標籤改為灰藍色 */
    span[data-baseweb="tag"] {
        background-color: var(--slate-blue) !important;
        color: #ffffff !important;
        border-radius: 6px !important;
        padding: 4px 8px !important;
    }
    
    /* 區塊容器樣式 */
    div[data-testid="stForm"] {
        border-radius: 10px;
    }
    
    /* 自訂主區塊外框灰藍主題 */
    .slate-box {
        background-color: var(--slate-blue-bg);
        border: 1.5px solid #CBD5E1;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 15px;
    }
    
    /* 進度條顏色覆蓋為灰藍色 */
    .stProgress > div > div > div > div {
        background-color: var(--slate-blue) !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🥗 每日營養與運動紀錄器")

saved_targets = get_target_settings()

# 側邊欄：目標設定
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

# 側邊欄：跑鞋履歷統計
st.sidebar.divider()
st.sidebar.header("👟 跑鞋退役里程追蹤")
shoe_df = get_shoe_mileage()
if not shoe_df.empty:
    for _, row in shoe_df.iterrows():
        s_name = row['shoe']
        s_dist = row['total_dist']
        st.sidebar.write(f"**{s_name}**: {s_dist:.1f} km / 600 km")
        st.sidebar.progress(min(s_dist / 600.0, 1.0))
else:
    st.sidebar.caption("尚無跑鞋紀錄")

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

# -----------------------------------------------------------------------------
# 主畫面頂部：日期選擇與放大的灰藍色顯示/順序設定區塊
# -----------------------------------------------------------------------------
st.divider()
selected_date = st.date_input("📅 選擇紀錄/查閱日期", value=date.today())
date_str = selected_date.strftime("%Y-%m-%d")

# 加大版的區塊順序與顯示控制卡片
ALL_SECTIONS = [
    "新增紀錄區塊",
    "當日攝取進度與目標",
    "當月跑量統計區塊",
    "當日明細清單",
    "近30天體重趨勢圖",
    "熱量與營養趨勢圖",
    "慢跑心率 vs. 配速散佈圖",
    "慢跑近7天里程圖",
    "重訓總量趨勢圖",
    "重訓部位分布圖"
]

with st.container(border=True):
    st.markdown("<h4 style='color: #4A607A; margin-bottom: 0px;'>🔀 畫面區塊顯示與顯示順序設定</h4>", unsafe_allow_html=True)
    st.caption("提示：點擊標籤旁的 'x' 可隱藏區塊，也可直接拖拉標籤重新排列版面顯示順序。")
    
    selected_sections = st.multiselect(
        "版面區塊與顯示順序：",
        options=ALL_SECTIONS,
        default=[
            "新增紀錄區塊",
            "當日攝取進度與目標",
            "當月跑量統計區塊",
            "當日明細清單",
            "近30天體重趨勢圖",
            "熱量與營養趨勢圖",
            "慢跑心率 vs. 配速散佈圖",
            "慢跑近7天里程圖"
        ],
        label_visibility="collapsed"
    )

# -----------------------------------------------------------------------------
# 3. 區塊渲染邏輯（動態依據 selected_sections 順序繪製）
# -----------------------------------------------------------------------------

def render_add_records():
    st.subheader(f"➕ 新增紀錄 ({date_str})")
    tab_food, tab_exercise, tab_weight = st.tabs(["🍱 新增飲食", "🏃 新增運動", "⚖️ 體重紀錄"])

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
                col_a, col_b = st.columns(2)
                with col_a:
                    body_part_in = st.selectbox("主要訓練部位", ["胸部", "背部", "腿部", "肩部", "手臂", "核心", "全身/其他"])
                    vol_in = st.number_input("總訓練量 Volume (kg)", min_value=0.0, value=None, placeholder="重量x組數x次數", step=50.0)
                with col_b:
                    rpe_in = st.slider("自覺強度 (RPE 1-10)", min_value=1, max_value=10, value=7)
                    cal_burned_in = st.number_input("估計消耗熱量 (kcal)", min_value=0.0, value=None, placeholder="0", step=10.0)
                
                submit_workout = st.form_submit_button("加入重訓紀錄", use_container_width=True)
                if submit_workout:
                    b_val = cal_burned_in if cal_burned_in is not None else 0.0
                    add_workout(date_str, workout_name, b_val, "重訓", body_part=body_part_in, volume_kg=vol_in, rpe=rpe_in)
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
        curr_w = curr_w_df["weight"].iloc[0] if not curr_w_df.empty else None
        curr_note = curr_w_df["note"].iloc[0] if not curr_w_df.empty else ""

        with st.form("weight_form"):
            w_input = st.number_input("今日體重 (kg)", min_value=30.0, max_value=200.0, value=float(curr_w) if curr_w else None, placeholder="輸入體重，如 62.5", step=0.1)
            w_note = st.text_input("備註 (如: 早晨空腹/運動後)", value=curr_note)
            submit_weight = st.form_submit_button("💾 儲存體重紀錄", use_container_width=True)
            
            if submit_weight and w_input:
                add_or_update_weight(date_str, w_input, w_note)
                st.toast(f"已更新 {date_str} 體重：{w_input} kg")
                st.rerun()

def render_daily_progress():
    logs_df = get_logs_by_date(date_str)
    consumed_cal = logs_df["calories"].sum() if not logs_df.empty else 0.0
    consumed_p = logs_df["protein"].sum() if not logs_df.empty else 0.0
    consumed_carbs = logs_df["carbs"].sum() if not logs_df.empty else 0.0
    consumed_f = logs_df["fat"].sum() if not logs_df.empty else 0.0

    st.subheader(f"📊 {date_str} 攝取進度與目標")

    # 顯示當日體重
    weight_df = get_weight_by_date(date_str)
    if not weight_df.empty:
        w_val = weight_df["weight"].iloc[0]
        st.info(f"⚖️ **{date_str} 紀錄體重**：**{w_val:.1f} kg**")

    rem_cal = target_cal - consumed_cal
    rem_p = target_p - consumed_p
    rem_carbs = target_carbs - consumed_carbs
    rem_f = target_fat - consumed_f

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("熱量剩餘", f"{rem_cal:.0f} kcal", delta=f"已攝取 {consumed_cal:.0f}")
    m2.metric("蛋白質剩餘", f"{rem_p:.1f} g", delta=f"已攝取 {consumed_p:.1f}")
    m3.metric("碳水剩餘", f"{rem_carbs:.1f} g", delta=f"已攝取 {consumed_carbs:.1f}")
    m4.metric("脂肪剩餘", f"{rem_f:.1f} g", delta=f"已攝取 {consumed_f:.1f}")

def render_monthly_run_stat():
    monthly_dist, run_count = get_monthly_running_distance(selected_date)
    last_day_of_month = calendar.monthrange(selected_date.year, selected_date.month)[1]
    
    st.subheader(f"🏃 {selected_date.year} 年 {selected_date.month} 月跑量統計")
    col_run1, col_run2 = st.columns(2)
    col_run1.metric("當月累積跑量", f"{monthly_dist:.2f} km")
    col_run2.metric("當月跑步次數", f"{run_count} 次")
    st.caption(f"📅 統計區間：{selected_date.year}-{selected_date.month:02d}-01 至 {selected_date.year}-{selected_date.month:02d}-{last_day_of_month:02d}")

def render_daily_logs():
    logs_df = get_logs_by_date(date_str)
    workouts_df = get_workouts_by_date(date_str)
    
    st.subheader(f"📝 {date_str} 明細清單")
    list_tab1, list_tab2 = st.tabs([f"🍱 飲食明細 ({len(logs_df)})", f"🏃 運動明細 ({len(workouts_df)})"])

    with list_tab1:
        if not logs_df.empty:
            for _, row in logs_df.iterrows():
                col_info, col_del = st.columns([4, 1])
                with col_info:
                    st.write(
                        f"**• {row['item']}** — "
                        f"{row['calories']:.0f} kcal | "
                        f"P: {row['protein']:.1f}g | "
                        f"C: {row['carbs']:.1f}g | "
                        f"F: {row['fat']:.1f}g"
                    )
                with col_del:
                    if st.button("刪除", key=f"del_food_{row['id']}"):
                        delete_log(row['id'])
                        st.rerun()
        else:
            st.info("當天尚無飲食紀錄。")

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
                        st.write(
                            f"**🏋️ {row['item']} ({row['body_part'] or '未設定'})** — "
                            f"總訓練量: **{row['volume_kg'] or 0:.0f} kg** | "
                            f"RPE: **{row['rpe'] or '-'}** | "
                            f"消耗: {row['calories_burned']:.0f} kcal"
                        )
                    else:
                        st.write(
                            f"**• {row['item']}** — 消耗 **{row['calories_burned']:.0f}** kcal"
                        )
                with col_del:
                    if st.button("刪除", key=f"del_workout_{row['id']}"):
                        delete_workout(row['id'])
                        st.rerun()
        else:
            st.info("當天尚無運動紀錄。")

def render_weight_chart():
    st.markdown("#### ⚖️ 近 30 天體重趨勢圖")
    w_df = get_recent_weights(30)
    if not w_df.empty:
        st.line_chart(w_df, x="log_date", y="weight", color="#5A738E")
    else:
        st.info("尚無體重紀錄，可在上方「新增紀錄 -> ⚖️ 體重紀錄」輸入數據。")

def render_cal_chart():
    st.markdown("#### 🔥 熱量與三大營養素趨勢")
    recent_logs_df, recent_workouts_df = get_recent_logs(days=7)
    today_dt = date.today()
    date_range = [(today_dt - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]

    food_summary = recent_logs_df.groupby("log_date").sum().reindex(date_range).fillna(0) if not recent_logs_df.empty else pd.DataFrame(0, index=date_range, columns=["calories", "protein", "carbs", "fat"])

    if not recent_workouts_df.empty:
        workout_summary = recent_workouts_df.groupby("log_date").agg({
            "calories_burned": "sum", "distance": "sum", "volume_kg": "sum"
        }).reindex(date_range).fillna(0)
    else:
        workout_summary = pd.DataFrame(0, index=date_range, columns=["calories_burned", "distance", "volume_kg"])

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
            color=alt.Color('shoe:N', title='跑鞋', scale=alt.Scale(scheme='tableau10')),
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
    st.bar_chart(workout_summary, x="日期", y="慢跑里程(km)", color="#4A607A")

def render_gym_chart():
    st.markdown("#### 🏋️ 近 7 天重訓總量")
    recent_logs_df, recent_workouts_df = get_recent_logs(days=7)
    today_dt = date.today()
    date_range = [(today_dt - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]

    if not recent_workouts_df.empty:
        workout_summary = recent_workouts_df.groupby("log_date").agg({"volume_kg": "sum"}).reindex(date_range).fillna(0).reset_index()
    else:
        workout_summary = pd.DataFrame({"log_date": date_range, "volume_kg": [0.0]*7})
    workout_summary.rename(columns={"log_date": "日期", "volume_kg": "重訓總量(kg)"}, inplace=True)
    st.bar_chart(workout_summary, x="日期", y="重訓總量(kg)", color="#78909C")

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
    "當月跑量統計區塊": render_monthly_run_stat,
    "當日明細清單": render_daily_logs,
    "近30天體重趨勢圖": render_weight_chart,
    "熱量與營養趨勢圖": render_cal_chart,
    "慢跑心率 vs. 配速散佈圖": render_pace_hr_chart,
    "慢跑近7天里程圖": render_run_chart,
    "重訓總量趨勢圖": render_gym_chart,
    "重訓部位分布圖": render_part_chart,
}

# 依據使用者自訂的順序繪製介面
for section_name in selected_sections:
    st.divider()
    if section_name in SECTION_MAP:
        SECTION_MAP[section_name]()
