import streamlit as st

# 設定網頁標題與圖示
st.set_page_config(page_title="每日營養計算器", page_icon="🥗", layout="centered")

st.title("🥗 每日營養計算器")

# 初始化 session_state（讓資料在重新整理時不會消失）
if "consumed" not in st.session_state:
    st.session_state.consumed = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
if "history" not in st.session_state:
    st.session_state.history = []

# 側邊欄：設定每日目標
st.sidebar.header("🎯 每日營養目標")
target_cal = st.sidebar.number_input("目標熱量 (kcal)", value=2200, step=50)
target_p = st.sidebar.number_input("目標蛋白質 (g)", value=140, step=5)
target_carbs = st.sidebar.number_input("目標碳水化合物 (g)", value=250, step=5)
target_fat = st.sidebar.number_input("目標脂肪 (g)", value=60, step=5)

# 主畫面：輸入此餐數據
st.subheader("➕ 新增餐點紀錄")
with st.form("meal_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        c_in = st.number_input("熱量 (kcal)", min_value=0.0, step=10.0)
        p_in = st.number_input("蛋白質 (g)", min_value=0.0, step=1.0)
    with col2:
        carbs_in = st.number_input("碳水化合物 (g)", min_value=0.0, step=1.0)
        f_in = st.number_input("脂肪 (g)", min_value=0.0, step=1.0)
    
    submit = st.form_submit_button("加入紀錄", use_container_width=True)

if submit:
    st.session_state.consumed["calories"] += c_in
    st.session_state.consumed["protein"] += p_in
    st.session_state.consumed["carbs"] += carbs_in
    st.session_state.consumed["fat"] += f_in
    st.session_state.history.append((c_in, p_in, carbs_in, f_in))
    st.toast("已成功新增餐點！")

# 顯示剩餘目標
st.divider()
st.subheader("📊 今日攝取進度與剩餘所需")

rem_cal = target_cal - st.session_state.consumed["calories"]
rem_p = target_p - st.session_state.consumed["protein"]
rem_carbs = target_carbs - st.session_state.consumed["carbs"]
rem_f = target_fat - st.session_state.consumed["fat"]

m1, m2, m3, m4 = st.columns(4)
m1.metric("熱量剩餘", f"{rem_cal:.0f} kcal", delta=f"已攝取 {st.session_state.consumed['calories']:.0f}")
m2.metric("蛋白質剩餘", f"{rem_p:.1f} g", delta=f"已攝取 {st.session_state.consumed['protein']:.1f}")
m3.metric("碳水剩餘", f"{rem_carbs:.1f} g", delta=f"已攝取 {st.session_state.consumed['carbs']:.1f}")
m4.metric("脂肪剩餘", f"{rem_f:.1f} g", delta=f"已攝取 {st.session_state.consumed['fat']:.1f}")

# 重設按鈕
if st.button("🔄 清空今日紀錄", type="secondary"):
    st.session_state.consumed = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
    st.session_state.history = []
    st.rerun()