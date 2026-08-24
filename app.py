import sqlite3
import calendar
from datetime import datetime, date, timedelta
import streamlit as st
import pandas as pd
import plotly.express as px

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
    # 設定值儲存表
    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value REAL
        )
    ''')
    
    # 動態補齊新欄位
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
        "target_fat": 60.0,
        "monthly_run_target": 120.0  # 客製化每月跑量目標 (預設 120 km)
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

def save_target_settings(cal, p, carbs, fat, monthly_run_target):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('target_cal', ?)", (cal,))
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('target_p', ?)", (p,))
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('target_carbs', ?)", (carbs,))
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('target_fat', ?)", (fat,))
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('monthly_run_target', ?)", (monthly_run_target,))
    conn.commit()
    conn.close()

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

# --- 當月跑量統計 (依據當月第一天到最後一天) ---
def get_monthly_running_distance(target_date):
    conn = sqlite3.connect(DB_FILE)
    
    # 計算當月第一天與最後一天
    first_day = date(target_date.year, target_date.month, 1)
    last_day_num = calendar.monthrange(target_date.year, target_date.month)[1]
    last_day = date(target_date.year, target_date.month, last_day_num)
    
    df = pd.read_sql_query(
        "SELECT SUM(distance) as total FROM workouts WHERE workout_type = '慢跑' AND log_date >= ? AND log_date <= ?",
        conn, params=(first_day.strftime("%Y-%m-%d"), last_day.strftime("%Y-%m-%d"))
    )
    conn.close()
    return df["total"].iloc[0] if df["total"].iloc[0] is not None else 0.0

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
        df["pace_decimal"] = df["duration_min"] / df["distance"]  # 分鐘/公里 (數值型態)
        df["配速"] = df.apply(lambda r: calculate_pace(r["distance"], r["duration_min"]), axis=1)
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
    conn.close()
    combined = pd.concat([logs_df, workouts_df]).sort_values(by=["log_date"], ascending=False)
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
# 2. Streamlit 介面配置與側邊欄
# -----------------------------------------------------------------------------
st.set_page_config(page_title="每日營養與運動紀錄器", page_icon="🥗", layout="centered")

st.title("🥗 每日營養與運動紀錄器")

saved_targets = get_target_settings()

# 側邊欄：目標設定 (支援客製化每月跑量)
st.sidebar.header("🎯 每日與每月目標設定")
with st.sidebar.form("target_settings_form"):
    target_cal = st.number_input("目標熱量 (kcal)", value=int(saved_targets["target_cal"]), step=50)
    target_p = st.number_input("目標蛋白質 (g)", value=int(saved_targets["target_p"]), step=5)
    target_carbs = st.number_input("目標碳水化合物 (g)", value=int(saved_targets["target_carbs"]), step=5)
    target_fat = st.number_input("目標脂肪 (g)", value=int(saved_targets["target_fat"]), step=5)
    monthly_run_target = st.number_input("每月目標跑量 (km)", value=float(saved_targets.get("monthly_run_target", 120.0)), step=10.0)
    
    submit_targets = st.form_submit_button("💾 儲存目標設定", use_container_width=True)
    if submit_targets:
        save_target_settings(target_cal, target_p, target_carbs, target_fat, monthly_run_target)
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

# 側邊欄：圖表顯示開關設定
st.sidebar.divider()
st.sidebar.header("⚙️ 介面與圖表顯示設定")
show_cal_chart = st.sidebar.checkbox("顯示 熱量與營養趨勢圖", value=True)
show_pace_hr_chart = st.sidebar.checkbox("顯示 慢跑心率 vs. 配速散佈圖", value=True)
show_run_chart = st.sidebar.checkbox("顯示 慢跑近7天里程圖", value=True)
show_gym_chart = st.sidebar.checkbox("顯示 重訓總量趨勢圖", value=False)
show_part_chart = st.sidebar.checkbox("顯示 重訓部位分布圖", value=False)

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

# 主畫面日期選擇器 (日曆視圖)
st.divider()
selected_date = st.date_input("📅 選擇紀錄/查閱日期", value=date.today())
date_str = selected_date.strftime("%Y-%m-%d")

# -----------------------------------------------------------------------------
# 3. 輸入區塊（飲食 & 運動）
# -----------------------------------------------------------------------------
st.subheader(f"➕ 新增紀錄 ({date_str})")
tab_food, tab_exercise = st.tabs(["🍱 新增飲食", "🏃 新增運動"])

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

# -----------------------------------------------------------------------------
# 4. 當日進度與「當月」跑量目標條（精準 01號 到 當月最後一天）
# -----------------------------------------------------------------------------
logs_df = get_logs_by_date(date_str)
workouts_df = get_workouts_by_date(date_str)

consumed_cal = logs_df["calories"].sum() if not logs_df.empty else 0.0
consumed_p = logs_df["protein"].sum() if not logs_df.empty else 0.0
consumed_carbs = logs_df["carbs"].sum() if not logs_df.empty else 0.0
consumed_f = logs_df["fat"].sum() if not logs_df.empty else 0.0

st.divider()
st.subheader(f"📊 {date_str} 攝取進度與目標")

rem_cal = target_cal - consumed_cal
rem_p = target_p - consumed_p
rem_carbs = target_carbs - consumed_carbs
rem_f = target_fat - consumed_f

m1, m2, m3, m4 = st.columns(4)
m1.metric("熱量剩餘", f"{rem_cal:.0f} kcal", delta=f"已攝取 {consumed_cal:.0f}")
m2.metric("蛋白質剩餘", f"{rem_p:.1f} g", delta=f"已攝取 {consumed_p:.1f}")
m3.metric("碳水剩餘", f"{rem_carbs:.1f} g", delta=f"已攝取 {consumed_carbs:.1f}")
m4.metric("脂肪剩餘", f"{rem_f:.1f} g", delta=f"已攝取 {consumed_f:.1f}")

# 當月跑量目標進度條 (精準從 1號 到當月最後一天)
monthly_dist = get_monthly_running_distance(selected_date)
run_pct = min(monthly_dist / monthly_run_target, 1.0) if monthly_run_target > 0 else 0.0
rem_run = max(monthly_run_target - monthly_dist, 0.0)

last_day_of_month = calendar.monthrange(selected_date.year, selected_date.month)[1]
st.markdown(f"🏃 **{selected_date.year} 年 {selected_date.month} 月累積跑量 (1日~{last_day_of_month}日)：{monthly_dist:.2f} / {monthly_run_target:.1f} km** (還差 {rem_run:.2f} km)")
st.progress(run_pct)

# -----------------------------------------------------------------------------
# 5. 當日細項清單與刪除管理
# -----------------------------------------------------------------------------
st.divider()
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

# -----------------------------------------------------------------------------
# 6. 趨勢與進階分析圖表 (互動式散佈圖 Hover 含日期)
# -----------------------------------------------------------------------------
st.divider()
st.subheader("📈 歷史數據與慢跑進階分析")

recent_logs_df, recent_workouts_df = get_recent_logs(days=7)
today_dt = date.today()
date_range = [(today_dt - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]

food_summary = recent_logs_df.groupby("log_date").sum().reindex(date_range).fillna(0) if not recent_logs_df.empty else pd.DataFrame(0, index=date_range, columns=["calories", "protein", "carbs", "fat"])

if not recent_workouts_df.empty:
    workout_summary = recent_workouts_df.groupby("log_date").agg({
        "calories_burned": "sum",
        "distance": "sum",
        "volume_kg": "sum"
    }).reindex(date_range).fillna(0)
else:
    workout_summary = pd.DataFrame(0, index=date_range, columns=["calories_burned", "distance", "volume_kg"])

daily_summary = food_summary.join(workout_summary).reset_index()
daily_summary.rename(columns={
    "index": "日期", "log_date": "日期", 
    "calories": "攝取熱量(kcal)", "calories_burned": "運動消耗(kcal)", 
    "protein": "蛋白質(g)", "carbs": "碳水(g)", "fat": "脂肪(g)",
    "distance": "慢跑里程(km)", "volume_kg": "重訓總量(kg)"
}, inplace=True)

# 熱量圖表
if show_cal_chart:
    st.markdown("#### 🔥 熱量與三大營養素趨勢")
    st.line_chart(daily_summary, x="日期", y="攝取熱量(kcal)", color="#FF4B4B")
    st.line_chart(daily_summary, x="日期", y=["蛋白質(g)", "碳水(g)", "脂肪(g)"])

# 慢跑配速 vs. 心率散佈圖 (Plotly 點點 Hover 顯示日期、移除下方表格)
if show_pace_hr_chart:
    st.markdown("#### 🏃 慢跑心率 vs. 配速散佈圖 (心肺效率)")
    run_hist_df = get_running_history()
    if not run_hist_df.empty and run_hist_df["avg_hr"].notna().any():
        st.caption("💡 點擊或懸停在數據點上可查看**日期**與詳細數據。右下方代表相同心率下配速更快。")
        
        # 使用 Plotly 繪製具備完整 Hover 資訊的散佈圖
        fig = px.scatter(
            run_hist_df,
            x="avg_hr",
            y="pace_decimal",
            color="shoe" if "shoe" in run_hist_df.columns else None,
            hover_data={
                "log_date": True,     # 顯示日期
                "配速": True,          # 顯示格式化配速 (例如 05'30")
                "avg_hr": True,        # 平均心率
                "distance": ":.2f",    # 距離
                "item": True,          # 項目名稱
                "pace_decimal": False  # 隱藏浮點數配速
            },
            labels={
                "avg_hr": "平均心率 (bpm)",
                "pace_decimal": "配速 (分鐘/公里)",
                "shoe": "跑鞋",
                "log_date": "日期",
                "distance": "距離 (km)",
                "item": "項目"
            }
        )
        fig.update_traces(marker=dict(size=10, opacity=0.8))
        fig.update_layout(margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("尚無包含平均心率的慢跑紀錄，填寫心率後即可自動生成散佈圖。")

# 近 7 天慢跑里程
if show_run_chart:
    st.markdown("#### 🏃 近 7 天慢跑里程")
    st.bar_chart(daily_summary, x="日期", y="慢跑里程(km)", color="#00C853")

# 重訓總量
if show_gym_chart:
    st.markdown("#### 🏋️ 近 7 天重訓總量")
    st.bar_chart(daily_summary, x="日期", y="重訓總量(kg)", color="#29B6F6")

# 重訓部位分布
if show_part_chart:
    st.markdown("#### 📊 近 7 天重訓部位分布")
    if not recent_workouts_df.empty and "body_part" in recent_workouts_df.columns:
        part_df = recent_workouts_df[recent_workouts_df["workout_type"] == "重訓"]
        if not part_df.empty:
            part_counts = part_df["body_part"].value_counts()
            st.bar_chart(part_counts)
        else:
            st.info("近 7 天尚無重訓資料。")
    else:
        st.info("近 7 天尚無重訓資料。")
