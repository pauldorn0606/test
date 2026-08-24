import sqlite3
from datetime import datetime, date, timedelta
import streamlit as st
import pandas as pd

# -----------------------------------------------------------------------------
# 1. 資料庫初始化與操作函式 (SQLite 持久化 - 飲食與運動獨立)
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
            calories_burned REAL
        )
    ''')
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
def add_workout(log_date, item, calories_burned):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO workouts (log_date, item, calories_burned)
        VALUES (?, ?, ?)
    ''', (log_date, item, calories_burned))
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
        "SELECT log_date, calories_burned FROM workouts WHERE log_date >= ? AND log_date <= ?",
        conn, params=(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
    )
    conn.close()
    return logs_df, workouts_df

def get_all_logs():
    conn = sqlite3.connect(DB_FILE)
    logs_df = pd.read_sql_query("SELECT '飲食' as 類別, log_date, item, calories, protein, carbs, fat, NULL as calories_burned FROM logs", conn)
    workouts_df = pd.read_sql_query("SELECT '運動' as 類別, log_date, item, NULL as calories, NULL as protein, NULL as carbs, NULL as fat, calories_burned FROM workouts", conn)
    conn.close()
    combined = pd.concat([logs_df, workouts_df]).sort_values(by=["log_date"], ascending=False)
    return combined

# 初始化資料庫
init_db()

# -----------------------------------------------------------------------------
# 2. Streamlit 介面配置
# -----------------------------------------------------------------------------
st.set_page_config(page_title="每日營養與運動計算器", page_icon="🥗", layout="centered")

st.title("🥗 每日營養與運動計算器")

# 側邊欄：目標設定與資料備份
st.sidebar.header("🎯 每日營養目標")
target_cal = st.sidebar.number_input("目標熱量 (kcal)", value=2200, step=50)
target_p = st.sidebar.number_input("目標蛋白質 (g)", value=140, step=5)
target_carbs = st.sidebar.number_input("目標碳水化合物 (g)", value=250, step=5)
target_fat = st.sidebar.number_input("目標脂肪 (g)", value=60, step=5)

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

# 日期選擇器
st.divider()
selected_date = st.date_input("📅 選擇紀錄/查閱日期", value=date.today())
date_str = selected_date.strftime("%Y-%m-%d")

# -----------------------------------------------------------------------------
# 3. 輸入區塊（飲食 & 運動 分頁）
# -----------------------------------------------------------------------------
st.subheader(f"➕ 新增紀錄 ({date_str})")
tab_food, tab_exercise = st.tabs(["🍱 新增飲食", "🏃 新增運動"])

with tab_food:
    with st.form("meal_form", clear_on_submit=True):
        item_name = st.text_input("品項名稱 (例如: 雞胸肉、午餐小吃)", value="")
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
    with st.form("workout_form", clear_on_submit=True):
        workout_name = st.text_input("運動名稱 (例如: 慢跑、路跑、重量訓練)", value="")
        cal_burned_in = st.number_input("消耗熱量 (kcal)", min_value=0.0, value=None, placeholder="0", step=10.0)
        
        submit_workout = st.form_submit_button("加入運動紀錄", use_container_width=True)

    if submit_workout:
        burned_val = cal_burned_in if cal_burned_in is not None else 0.0
        display_workout = workout_name.strip() if workout_name.strip() else "未命名運動"
        
        add_workout(date_str, display_workout, burned_val)
        st.toast(f"已加入運動紀錄：{display_workout}")
        st.rerun()

# -----------------------------------------------------------------------------
# 4. 當日進度與數據計算 (單純顯示飲食剩餘與運動消耗)
# -----------------------------------------------------------------------------
logs_df = get_logs_by_date(date_str)
workouts_df = get_workouts_by_date(date_str)

consumed_cal = logs_df["calories"].sum() if not logs_df.empty else 0.0
consumed_p = logs_df["protein"].sum() if not logs_df.empty else 0.0
consumed_carbs = logs_df["carbs"].sum() if not logs_df.empty else 0.0
consumed_f = logs_df["fat"].sum() if not logs_df.empty else 0.0

burned_cal = workouts_df["calories_burned"].sum() if not workouts_df.empty else 0.0

st.divider()
st.subheader(f"📊 {date_str} 攝取進度與剩餘所需")

# 單純的飲食熱量剩餘：目標 - 已攝取
rem_cal = target_cal - consumed_cal
rem_p = target_p - consumed_p
rem_carbs = target_carbs - consumed_carbs
rem_f = target_fat - consumed_f

m1, m2, m3, m4 = st.columns(4)
m1.metric("熱量剩餘", f"{rem_cal:.0f} kcal", delta=f"已攝取 {consumed_cal:.0f}")
m2.metric("蛋白質剩餘", f"{rem_p:.1f} g", delta=f"已攝取 {consumed_p:.1f}")
m3.metric("碳水剩餘", f"{rem_carbs:.1f} g", delta=f"已攝取 {consumed_carbs:.1f}")
m4.metric("脂肪剩餘", f"{rem_f:.1f} g", delta=f"已攝取 {consumed_f:.1f}")

# 運動累計提示欄（不參與扣抵計算）
if burned_cal > 0:
    st.info(f"🏃 今日運動累計消耗：**{burned_cal:.0f}** kcal（獨立紀錄，不影響上述熱量剩餘計算）")

# -----------------------------------------------------------------------------
# 5. 當日細項清單與刪除管理 (飲食 & 運動)
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
# 6. 近 7 天歷史趨勢圖表
# -----------------------------------------------------------------------------
st.divider()
st.subheader("📈 近 7 天營養與運動趨勢")

recent_logs_df, recent_workouts_df = get_recent_logs(days=7)

today_dt = date.today()
date_range = [(today_dt - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]

food_summary = recent_logs_df.groupby("log_date").sum().reindex(date_range).fillna(0) if not recent_logs_df.empty else pd.DataFrame(0, index=date_range, columns=["calories", "protein", "carbs", "fat"])
workout_summary = recent_workouts_df.groupby("log_date").sum().reindex(date_range).fillna(0) if not recent_workouts_df.empty else pd.DataFrame(0, index=date_range, columns=["calories_burned"])

daily_summary = food_summary.join(workout_summary).reset_index()
daily_summary.rename(columns={"index": "日期", "log_date": "日期", "calories": "攝取熱量(kcal)", "calories_burned": "運動消耗(kcal)", "protein": "蛋白質(g)", "carbs": "碳水(g)", "fat": "脂肪(g)"}, inplace=True)

chart_tab1, chart_tab2, chart_tab3 = st.tabs(["🔥 攝取熱量趨勢", "🏃 運動消耗趨勢", "🥩 三大營養素趨勢"])

with chart_tab1:
    st.line_chart(daily_summary, x="日期", y="攝取熱量(kcal)", color="#FF4B4B")
    st.caption(f"目標參考線：每日飲食熱量 {target_cal} kcal")

with chart_tab2:
    st.bar_chart(daily_summary, x="日期", y="運動消耗(kcal)", color="#29B6F6")
    st.caption("近 7 天每日運動消耗卡路里長條圖")

with chart_tab3:
    st.line_chart(daily_summary, x="日期", y=["蛋白質(g)", "碳水(g)", "脂肪(g)"])
    st.caption(f"目標參考：蛋白質 {target_p}g | 碳水 {target_carbs}g | 脂肪 {target_fat}g")