from datetime import datetime, date
import streamlit as st

# 設定網頁標題與圖示
st.set_page_config(page_title="每日營養計算器", page_icon="🥗", layout="centered")

st.title("🥗 每日營養計算器")

# 初始化 Session State 結構
if "logs" not in st.session_state:
    # 結構: { "2026-08-24": [ {"item": "雞胸肉", "c": 165, "p": 31, "carbs": 0, "f": 3.6}, ... ] }
    st.session_state.logs = {}

# 側邊欄：設定每日目標
st.sidebar.header("🎯 每日營養目標")
target_cal = st.sidebar.number_input("目標熱量 (kcal)", value=2200, step=50)
target_p = st.sidebar.number_input("目標蛋白質 (g)", value=140, step=5)
target_carbs = st.sidebar.number_input("目標碳水化合物 (g)", value=250, step=5)
target_fat = st.sidebar.number_input("目標脂肪 (g)", value=60, step=5)

# 日期選擇器
st.divider()
selected_date = st.date_input("📅 選擇紀錄/查閱日期", value=date.today())
date_str = selected_date.strftime("%Y-%m-%d")

# 確保該日期的紀錄清單存在
if date_str not in st.session_state.logs:
    st.session_state.logs[date_str] = []

# --- 輸入區塊 ---
st.subheader(f"➕ 新增餐點紀錄 ({date_str})")
with st.form("meal_form", clear_on_submit=True):
    item_name = st.text_input("品項名稱 (例如: 雞胸肉、午餐小吃)", value="")
    
    col1, col2 = st.columns(2)
    with col1:
        c_in = st.number_input("熱量 (kcal)", min_value=0.0, step=10.0)
        p_in = st.number_input("蛋白質 (g)", min_value=0.0, step=1.0)
    with col2:
        carbs_in = st.number_input("碳水化合物 (g)", min_value=0.0, step=1.0)
        f_in = st.number_input("脂肪 (g)", min_value=0.0, step=1.0)
    
    submit = st.form_submit_button("加入紀錄", use_container_width=True)

if submit:
    display_name = item_name.strip() if item_name.strip() else "未命名餐點"
    st.session_state.logs[date_str].append({
        "item": display_name,
        "calories": c_in,
        "protein": p_in,
        "carbs": carbs_in,
        "fat": f_in
    })
    st.toast(f"已成功加入 {date_str} 的紀錄！")

# --- 計算當日總攝取量 ---
day_logs = st.session_state.logs[date_str]
consumed = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}

for record in day_logs:
    consumed["calories"] += record["calories"]
    consumed["protein"] += record["protein"]
    consumed["carbs"] += record["carbs"]
    consumed["fat"] += record["fat"]

# --- 顯示當日攝取進度 ---
st.divider()
st.subheader(f"📊 {date_str} 攝取進度與剩餘所需")

rem_cal = target_cal - consumed["calories"]
rem_p = target_p - consumed["protein"]
rem_carbs = target_carbs - consumed["carbs"]
rem_f = target_fat - consumed["fat"]

m1, m2, m3, m4 = st.columns(4)
m1.metric("熱量剩餘", f"{rem_cal:.0f} kcal", delta=f"已攝取 {consumed['calories']:.0f}")
m2.metric("蛋白質剩餘", f"{rem_p:.1f} g", delta=f"已攝取 {consumed['protein']:.1f}")
m3.metric("碳水剩餘", f"{rem_carbs:.1f} g", delta=f"已攝取 {consumed['carbs']:.1f}")
m4.metric("脂肪剩餘", f"{rem_f:.1f} g", delta=f"已攝取 {consumed['fat']:.1f}")

# --- 顯示與管理當日明細 ---
st.divider()
st.subheader(f"📝 {date_str} 食物明細清單")

if day_logs:
    for idx, record in enumerate(day_logs):
        col_info, col_del = st.columns([4, 1])
        with col_info:
            st.write(
                f"**{idx + 1}. {record['item']}** — "
                f"{record['calories']:.0f} kcal | "
                f"P: {record['protein']:.1f}g | "
                f"C: {record['carbs']:.1f}g | "
                f"F: {record['fat']:.1f}g"
            )
        with col_del:
            if st.button("刪除", key=f"del_{date_str}_{idx}"):
                st.session_state.logs[date_str].pop(idx)
                st.rerun()
else:
    st.info("當天尚無記錄任何餐點。")

# 清空當天紀錄按鈕
if day_logs and st.button("🗑️ 清空該日所有紀錄", type="secondary"):
    st.session_state.logs[date_str] = []
    st.rerun()