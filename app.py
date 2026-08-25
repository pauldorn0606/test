import calendar
from datetime import date, timedelta
import sqlite3
import altair as alt
import pandas as pd
import streamlit as st

DB_NAME = "health_app.db"


# =============================================================================
# 1. 資料庫連線與初始化 (Database Helpers)
# =============================================================================
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化 SQLite 資料庫表格"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. 食物資料庫表格
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS foods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            calories REAL DEFAULT 0.0,
            protein REAL DEFAULT 0.0,
            carbs REAL DEFAULT 0.0,
            fat REAL DEFAULT 0.0,
            serving_unit TEXT DEFAULT '份'
        )
    """
    )

    # 2. 每日飲食紀錄表格
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_date TEXT NOT NULL,
            item TEXT NOT NULL,
            calories REAL DEFAULT 0.0,
            protein REAL DEFAULT 0.0,
            carbs REAL DEFAULT 0.0,
            fat REAL DEFAULT 0.0
        )
    """
    )

    # 3. 運動紀錄表格
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_date TEXT NOT NULL,
            item TEXT NOT NULL,
            calories_burned REAL DEFAULT 0.0,
            workout_type TEXT DEFAULT '其他',
            distance REAL,
            duration_min REAL,
            avg_hr INTEGER,
            shoe TEXT,
            body_part TEXT,
            workout_notes TEXT,
            rpe INTEGER
        )
    """
    )

    # 4. 體重體脂表格
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS weight_logs (
            log_date TEXT PRIMARY KEY,
            weight REAL NOT NULL,
            body_fat REAL,
            note TEXT
        )
    """
    )

    # 預設注入常用食物（若食物庫為空）
    cursor.execute("SELECT COUNT(*) FROM foods")
    if cursor.fetchone()[0] == 0:
        default_foods = [
            ("雞胸肉 (100g)", 110.0, 23.0, 0.0, 1.2, "100g"),
            ("水煮蛋 (顆)", 75.0, 6.3, 0.6, 5.3, "顆"),
            ("植物蛋白粉/樂維根 (份)", 140.0, 20.0, 4.0, 2.5, "份"),
            ("全脂鮮乳 (200ml)", 130.0, 6.2, 9.6, 7.6, "杯"),
            ("白飯 (碗)", 280.0, 5.0, 60.0, 0.8, "碗"),
            ("雞腿便當 (個)", 750.0, 35.0, 85.0, 28.0, "個"),
            ("地瓜 (中/150g)", 130.0, 2.0, 30.0, 0.3, "個"),
        ]
        cursor.executemany(
            """
            INSERT INTO foods (name, calories, protein, carbs, fat, serving_unit)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            default_foods,
        )

    conn.commit()
    conn.close()


# =============================================================================
# 2. 食物資料庫 & 紀錄操作 CRUD 函式
# =============================================================================
def get_all_foods():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM foods ORDER BY name ASC", conn)
    conn.close()
    return df


def add_food_item(name, calories, protein, carbs, fat, unit="份"):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO foods (name, calories, protein, carbs, fat, serving_unit)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (name, calories, protein, carbs, fat, unit),
        )
        conn.commit()
        return True, "成功新增食物至資料庫！"
    except sqlite3.IntegrityError:
        return False, "新增失敗：該食物名稱已存在。"
    finally:
        conn.close()


# 【新增】更新食物資料庫品項
def update_food_item(food_id, name, calories, protein, carbs, fat, unit="份"):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE foods 
            SET name=?, calories=?, protein=?, carbs=?, fat=?, serving_unit=? 
            WHERE id=?
        """,
            (name, calories, protein, carbs, fat, unit, food_id),
        )
        conn.commit()
        return True, "成功更新食物資料！"
    except sqlite3.IntegrityError:
        return False, "更新失敗：該食物名稱與其他既有品項重複。"
    finally:
        conn.close()


# 【新增】刪除食物資料庫品項
def delete_food_item(food_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM foods WHERE id = ?", (food_id,))
    conn.commit()
    conn.close()


def add_log(date_str, item, cal, p, c, f):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO daily_logs (log_date, item, calories, protein, carbs, fat)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (date_str, item, cal, p, c, f),
    )
    conn.commit()
    conn.close()


def update_log(log_id, item, cal, p, c, f):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE daily_logs SET item=?, calories=?, protein=?, carbs=?, fat=? WHERE id=?
    """,
        (item, cal, p, c, f, log_id),
    )
    conn.commit()
    conn.close()


def delete_log(log_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM daily_logs WHERE id=?", (log_id,))
    conn.commit()
    conn.close()


def add_workout(
    date_str,
    item,
    cal_burned,
    w_type="其他",
    distance=None,
    duration_min=None,
    avg_hr=None,
    shoe=None,
    body_part=None,
    workout_notes=None,
    rpe=None,
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO workouts (log_date, item, calories_burned, workout_type, distance, duration_min, avg_hr, shoe, body_part, workout_notes, rpe)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            date_str,
            item,
            cal_burned,
            w_type,
            distance,
            duration_min,
            avg_hr,
            shoe,
            body_part,
            workout_notes,
            rpe,
        ),
    )
    conn.commit()
    conn.close()


def update_workout(
    w_id,
    item,
    cal_burned,
    w_type,
    distance=None,
    duration_min=None,
    avg_hr=None,
    shoe=None,
    body_part=None,
    workout_notes=None,
    rpe=None,
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE workouts SET item=?, calories_burned=?, workout_type=?, distance=?, duration_min=?, avg_hr=?, shoe=?, body_part=?, workout_notes=?, rpe=?
        WHERE id=?
    """,
        (
            item,
            cal_burned,
            w_type,
            distance,
            duration_min,
            avg_hr,
            shoe,
            body_part,
            workout_notes,
            rpe,
            w_id,
        ),
    )
    conn.commit()
    conn.close()


def delete_workout(w_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM workouts WHERE id=?", (w_id,))
    conn.commit()
    conn.close()


def add_or_update_weight(date_str, weight, body_fat, note):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO weight_logs (log_date, weight, body_fat, note)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(log_date) DO UPDATE SET weight=excluded.weight, body_fat=excluded.body_fat, note=excluded.note
    """,
        (date_str, weight, body_fat, note),
    )
    conn.commit()
    conn.close()


def delete_weight_log(date_str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM weight_logs WHERE log_date=?", (date_str,))
    conn.commit()
    conn.close()


def get_logs_by_date(date_str):
    conn = get_db_connection()
    df = pd.read_sql_query(
        "SELECT * FROM daily_logs WHERE log_date = ?",
        conn,
        params=(date_str,),
    )
    conn.close()
    return df


def get_workouts_by_date(date_str):
    conn = get_db_connection()
    df = pd.read_sql_query(
        "SELECT * FROM workouts WHERE log_date = ?", conn, params=(date_str,)
    )
    conn.close()
    return df


def get_weight_by_date(date_str):
    conn = get_db_connection()
    df = pd.read_sql_query(
        "SELECT * FROM weight_logs WHERE log_date = ?",
        conn,
        params=(date_str,),
    )
    conn.close()
    return df


def get_recent_weights(days=30):
    conn = get_db_connection()
    df = pd.read_sql_query(
        "SELECT * FROM weight_logs ORDER BY log_date DESC LIMIT ?",
        conn,
        params=(days,),
    )
    conn.close()
    return df.sort_values("log_date") if not df.empty else df


def get_recent_logs(days=7):
    conn = get_db_connection()
    cutoff = (date.today() - timedelta(days=days)).strftime("%Y-%m-%d")
    logs_df = pd.read_sql_query(
        "SELECT * FROM daily_logs WHERE log_date >= ?",
        conn,
        params=(cutoff,),
    )
    workouts_df = pd.read_sql_query(
        "SELECT * FROM workouts WHERE log_date >= ?", conn, params=(cutoff,)
    )
    conn.close()
    return logs_df, workouts_df


def get_running_history():
    conn = get_db_connection()
    df = pd.read_sql_query(
        "SELECT * FROM workouts WHERE workout_type = '慢跑' AND distance > 0 AND duration_min > 0 ORDER BY log_date ASC",
        conn,
    )
    conn.close()
    if not df.empty:
        df["pace_decimal"] = df["duration_min"] / df["distance"]
        df["配速"] = df["pace_decimal"].apply(
            lambda p: f"{int(p)}'{int((p % 1) * 60):02d}\""
        )
    return df


def get_monthly_running_distance(target_date):
    year, month = target_date.year, target_date.month
    start_str = f"{year}-{month:02d}-01"
    end_day = calendar.monthrange(year, month)[1]
    end_str = f"{year}-{month:02d}-{end_day:02d}"

    conn = get_db_connection()
    df = pd.read_sql_query(
        "SELECT distance FROM workouts WHERE workout_type = '慢跑' AND log_date >= ? AND log_date <= ?",
        conn,
        params=(start_str, end_str),
    )
    conn.close()
    total_dist = df["distance"].sum() if not df.empty else 0.0
    run_count = len(df) if not df.empty else 0
    return total_dist, run_count


def get_shoe_mileage():
    conn = get_db_connection()
    df = pd.read_sql_query(
        "SELECT shoe, SUM(distance) as total_dist FROM workouts WHERE workout_type = '慢跑' AND shoe IS NOT NULL AND shoe != '' GROUP BY shoe",
        conn,
    )
    conn.close()
    return df


def get_weekly_workout_summary(target_date):
    start_of_week = target_date - timedelta(days=target_date.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    conn = get_db_connection()
    df = pd.read_sql_query(
        "SELECT log_date, item, body_part, workout_notes, rpe FROM workouts WHERE workout_type = '重訓' AND log_date >= ? AND log_date <= ? ORDER BY log_date ASC",
        conn,
        params=(
            start_of_week.strftime("%Y-%m-%d"),
            end_of_week.strftime("%Y-%m-%d"),
        ),
    )
    conn.close()
    if not df.empty:
        df.rename(
            columns={
                "log_date": "日期",
                "item": "項目",
                "body_part": "部位",
                "workout_notes": "動作與組數筆記",
                "rpe": "RPE",
            },
            inplace=True,
        )
    return df, start_of_week, end_of_week


def calculate_pace(dist, dur):
    if not dist or not dur or dist <= 0:
        return "-"
    pace_dec = dur / dist
    m = int(pace_dec)
    s = int((pace_dec % 1) * 60)
    return f"{m}'{s:02d}\""


# =============================================================================
# 3. UI 模組渲染函式 (Render Modules)
# =============================================================================


def render_add_records(date_str):
    st.subheader(f"➕ 新增紀錄 ({date_str})")
    food_tab, workout_tab, weight_tab, food_db_tab = st.tabs(
        ["🍱 新增飲食", "🏃 新增運動", "⚖️ 體重與體脂", "📚 食物庫管理"]
    )

    # --- 1. 新增飲食 (結合食物庫帶入) ---
    with food_tab:
        f_sub1, f_sub2 = st.tabs(["🔍 從食物庫選取", "✏️ 手動輸入熱量"])

        with f_sub1:
            food_df = get_all_foods()
            if not food_df.empty:
                selected_f_name = st.selectbox(
                    "選擇食物庫品項",
                    options=food_df["name"].tolist(),
                    key="sel_f_db",
                )
                f_info = food_df[food_df["name"] == selected_f_name].iloc[0]

                c_serv, c_info = st.columns(2)
                with c_serv:
                    servings = st.number_input(
                        f"份數 / 數量 ({f_info['serving_unit']})",
                        min_value=0.1,
                        value=1.0,
                        step=0.5,
                    )
                with c_info:
                    calc_cal = f_info["calories"] * servings
                    calc_p = f_info["protein"] * servings
                    calc_c = f_info["carbs"] * servings
                    calc_f = f_info["fat"] * servings
                    st.caption(
                        f"🔥 熱量: **{calc_cal:.0f}** kcal | P: **{calc_p:.1f}**g | C: **{calc_c:.1f}**g | F: **{calc_f:.1f}**g"
                    )

                if st.button("📥 快速加入飲食紀錄", use_container_width=True):
                    item_desc = f"{selected_f_name} x{servings}"
                    add_log(
                        date_str,
                        item_desc,
                        calc_cal,
                        calc_p,
                        calc_c,
                        calc_f,
                    )
                    st.toast(f"已加入：{item_desc}")
                    st.rerun()
            else:
                st.info("目前食物資料庫為空，可切換至「📚 食物庫管理」建立！")

        with f_sub2:
            with st.form("manual_food_form", clear_on_submit=True):
                food_item = st.text_input("食物名稱", placeholder="例如: 雞腿便當")
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    f_cal = st.number_input("熱量 (kcal)", min_value=0.0, value=None, placeholder="0",step=10.0)
                    f_p = st.number_input("蛋白質 (g)", min_value=0.0, value=None, placeholder="0",step=1.0)
                with col_f2:
                    f_fat = st.number_input("脂肪 (g)", min_value=0.0, value=None, placeholder="0",step=1.0)
                    f_carbs = st.number_input(
                        "碳水化合物 (g)", min_value=0.0, value=None, placeholder="0",step=1.0
                    )
                submit_food = st.form_submit_button(
                    "加入飲食紀錄", use_container_width=True
                )
                if submit_food and food_item.strip():
                    add_log(
                        date_str,
                        food_item.strip(),
                        f_cal,
                        f_p,
                        f_carbs,
                        f_fat,
                    )
                    st.toast(f"已加入飲食：{food_item}")
                    st.rerun()

    # --- 2. 新增運動 ---
    with workout_tab:
        w_type_sel = st.radio(
            "運動類型", ["慢跑", "重訓/健身", "其他運動"], horizontal=True
        )

        with st.form("add_workout_form", clear_on_submit=True):
            if w_type_sel == "慢跑":
                workout_name = st.text_input("慢跑名稱", value="路跑 / 慢跑")
                col_r1, col_r2 = st.columns(2)
                with col_r1:
                    run_dist = st.number_input(
                        "跑步距離 (km)",
                        min_value=0.0,
                        value=None,
                        placeholder="0",
                        step=0.5,
                    )
                    run_dur = st.number_input(
                        "跑步時間 (分鐘)", min_value=0.0, value=None, placeholder="0", step=1.0
                    )
                    shoe_opts = [
                        "Adidas Boston 13",
                        "Adidas Adizero",
                        "其他跑鞋",
                        "不指定",
                    ]
                    run_shoe = st.selectbox("搭配跑鞋", shoe_opts)
                with col_r2:
                    run_hr = st.number_input(
                        "平均心率 (bpm)", min_value=0, value=None, placeholder="0", max_value=220, step=1
                    )
                    cal_burned_in = st.number_input(
                        "消耗熱量 (kcal)", min_value=0.0, value=None, placeholder="0", step=10.0
                    )

                submit_run = st.form_submit_button(
                    "加入慢跑紀錄", use_container_width=True
                )
                if submit_run and run_dist > 0:
                    add_workout(
                        date_str,
                        workout_name,
                        cal_burned_in or 0.0,
                        "慢跑",
                        distance=run_dist,
                        duration_min=run_dur,
                        avg_hr=run_hr if run_hr > 0 else None,
                        shoe=run_shoe,
                    )
                    st.toast(f"已加入慢跑：{run_dist} km")
                    st.rerun()

            elif w_type_sel == "重訓/健身":
                workout_name = st.text_input("訓練名稱", value="力量訓練")
                body_opts = [
                    "胸部",
                    "背部",
                    "腿部",
                    "肩部",
                    "手臂",
                    "核心",
                    "全身/其他",
                ]
                body_part_in = st.selectbox("主要訓練部位", body_opts)
                notes_in = st.text_area(
                    "動作與組數筆記 (例: 深蹲 80kg x 8r x 4s)", height=80
                )

                col_w1, col_w2 = st.columns(2)
                with col_w1:
                    rpe_in = st.slider(
                        "自覺強度 (RPE 1-10)", min_value=1, max_value=10, value=7
                    )
                with col_w2:
                    cal_burned_in = st.number_input(
                        "估計消耗熱量 (kcal)", min_value=0.0, value=None, placeholder="0", step=10.0
                    )

                submit_workout = st.form_submit_button(
                    "加入重訓紀錄", use_container_width=True
                )
                if submit_workout:
                    b_val = cal_burned_in if cal_burned_in else 0.0
                    add_workout(
                        date_str,
                        workout_name,
                        b_val,
                        "重訓",
                        body_part=body_part_in,
                        workout_notes=notes_in,
                        rpe=rpe_in,
                    )
                    st.toast(f"已加入重訓紀錄：{body_part_in}")
                    st.rerun()

            else:
                workout_name = st.text_input("運動名稱", value="")
                cal_burned_in = st.number_input(
                    "消耗熱量 (kcal)", min_value=0.0, value=None, placeholder="0", step=10.0
                )
                submit_workout = st.form_submit_button(
                    "加入運動紀錄", use_container_width=True
                )
                if submit_workout:
                    b_val = cal_burned_in if cal_burned_in else 0.0
                    display_w = (
                        workout_name.strip()
                        if workout_name.strip()
                        else "一般運動"
                    )
                    add_workout(date_str, display_w, b_val, "其他")
                    st.toast(f"已加入運動紀錄：{display_w}")
                    st.rerun()

    # --- 3. 體重與體脂 ---
    with weight_tab:
        curr_w_df = get_weight_by_date(date_str)
        curr_w = (
            curr_w_df["weight"].iloc[0]
            if not curr_w_df.empty and pd.notna(curr_w_df["weight"].iloc[0])
            else None
        )
        curr_fat = (
            curr_w_df["body_fat"].iloc[0]
            if not curr_w_df.empty
            and "body_fat" in curr_w_df.columns
            and pd.notna(curr_w_df["body_fat"].iloc[0])
            else None
        )
        curr_note = (
            curr_w_df["note"].iloc[0]
            if not curr_w_df.empty and pd.notna(curr_w_df["note"].iloc[0])
            else ""
        )

        with st.form("weight_form"):
            col_w1, col_w2 = st.columns(2)
            with col_w1:
                w_input = st.number_input(
                    "今日體重 (kg)",
                    min_value=0.0,
                    value=None,
                    max_value=200.0,
                    placeholder="0",
                    step=0.1,
                )
            with col_w2:
                fat_input = st.number_input(
                    "體脂率 (%)",
                    min_value=0.0,
                    value=None,
                    max_value=100.0,
                    placeholder="0",
                    step=0.1,
                )

            w_note = st.text_input(
                "備註 (如: 早晨空腹/運動後)", value=curr_note
            )
            submit_weight = st.form_submit_button(
                "💾 儲存體重與體脂紀錄", use_container_width=True
            )

            if submit_weight and w_input:
                add_or_update_weight(date_str, w_input, fat_input, w_note)
                st.toast(
                    f"已更新 {date_str} 體重：{w_input} kg"
                    + (f", 體脂：{fat_input}%" if fat_input else "")
                )
                st.rerun()

    # --- 4. 管理與編輯食物資料庫 ---
    with food_db_tab:
        sub_tab1, sub_tab2 = st.tabs(["📋 食物清單與編輯", "➕ 新增食物品項"])

        # 子分頁 1：編輯 / 刪除既有食物
        with sub_tab1:
            st.markdown("#### 📖 現有食物庫資料")
            all_foods = get_all_foods()

            if not all_foods.empty:
                for _, f_row in all_foods.iterrows():
                    f_id = f_row["id"]
                    col_info, col_edit, col_del = st.columns([3.5, 0.8, 0.8])

                    with col_info:
                        st.write(
                            f"**{f_row['name']}** ({f_row['serving_unit']}) — "
                            f"{f_row['calories']:.0f} kcal | "
                            f"P: {f_row['protein']:.1f}g | "
                            f"C: {f_row['carbs']:.1f}g | "
                            f"F: {f_row['fat']:.1f}g"
                        )
                    with col_edit:
                        if st.button("✏️ 編輯", key=f"btn_edit_db_food_{f_id}"):
                            st.session_state[f"editing_db_food_{f_id}"] = (
                                not st.session_state.get(
                                    f"editing_db_food_{f_id}", False
                                )
                            )
                    with col_del:
                        if st.button("🗑️ 刪除", key=f"btn_del_db_food_{f_id}"):
                            delete_food_item(f_id)
                            st.toast(f"已從資料庫刪除：{f_row['name']}")
                            st.rerun()

                    # 展開編輯表單
                    if st.session_state.get(f"editing_db_food_{f_id}", False):
                        with st.form(key=f"form_edit_db_food_{f_id}"):
                            st.caption(f"🛠️ 編輯食物資料 (ID: {f_id})")
                            e_name = st.text_input("食物名稱", value=f_row["name"])
                            e_unit = st.text_input(
                                "單位描述", value=f_row["serving_unit"]
                            )

                            col_e1, col_e2 = st.columns(2)
                            with col_e1:
                                e_cal = st.number_input(
                                    "熱量 (kcal)",
                                    value=float(f_row["calories"]),
                                    step=5.0,
                                )
                                e_p = st.number_input(
                                    "蛋白質 (g)",
                                    value=float(f_row["protein"]),
                                    step=0.5,
                                )
                            with col_e2:
                                e_c = st.number_input(
                                    "碳水 (g)",
                                    value=float(f_row["carbs"]),
                                    step=0.5,
                                )
                                e_f = st.number_input(
                                    "脂肪 (g)",
                                    value=float(f_row["fat"]),
                                    step=0.5,
                                )

                            if st.form_submit_button("💾 儲存修改"):
                                ok, msg = update_food_item(
                                    f_id,
                                    e_name.strip(),
                                    e_cal,
                                    e_p,
                                    e_c,
                                    e_f,
                                    e_unit.strip(),
                                )
                                if ok:
                                    st.session_state[
                                        f"editing_db_food_{f_id}"
                                    ] = False
                                    st.toast(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                        st.divider()
            else:
                st.info("資料庫中目前沒有食物，請點選「新增食物品項」分頁進行新增。")

        # 子分頁 2：新增食物
        with sub_tab2:
            st.markdown("#### ➕ 新增食物至資料庫")
            with st.form("db_food_form", clear_on_submit=True):
                f_name = st.text_input("食物名稱 (例如: 醬燒雞腿飯)")
                f_unit = st.text_input(
                    "單位描述 (例如: 100g、一份、碗)", value="份"
                )
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    f_cal = st.number_input(
                        "每單位熱量 (kcal)", min_value=0.0, step=5.0
                    )
                    f_p = st.number_input("蛋白質 (g)", min_value=0.0, step=0.5)
                with col_d2:
                    f_c = st.number_input("碳水 (g)", min_value=0.0, step=0.5)
                    f_f = st.number_input("脂肪 (g)", min_value=0.0, step=0.5)

                if st.form_submit_button("💾 儲存至食物資料庫"):
                    if f_name.strip():
                        ok, msg = add_food_item(
                            f_name.strip(), f_cal, f_p, f_c, f_f, f_unit.strip()
                        )
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)


def render_daily_progress(
    date_str, target_cal, target_p, target_carbs, target_fat
):
    st.subheader(f"📊 每日進度與營養目標 ({date_str})")
    logs_df = get_logs_by_date(date_str)
    workouts_df = get_workouts_by_date(date_str)
    weight_df = get_weight_by_date(date_str)
    if not weight_df.empty:
        w_val = weight_df["weight"].iloc[0]
        fat_val = weight_df["body_fat"].iloc[0] if "body_fat" in weight_df.columns and pd.notna(weight_df["body_fat"].iloc[0]) else None
        fat_str = f" | 體脂率：**{fat_val:.1f}%**" if fat_val else ""
        st.info(f"⚖️ **{date_str} 紀錄數據**：體重 **{w_val:.1f} kg**{fat_str}")

    tot_cal = logs_df["calories"].sum() if not logs_df.empty else 0.0
    tot_p = logs_df["protein"].sum() if not logs_df.empty else 0.0
    tot_c = logs_df["carbs"].sum() if not logs_df.empty else 0.0
    tot_f = logs_df["fat"].sum() if not logs_df.empty else 0.0

    burned_cal = (
        workouts_df["calories_burned"].sum() if not workouts_df.empty else 0.0
    )
    net_cal = tot_cal - burned_cal

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric(
        "攝取熱量",
        f"{tot_cal:.0f} kcal",
        delta=f"{tot_cal - target_cal:.0f} kcal",
    )
    c2.metric("運動消耗", f"{burned_cal:.0f} kcal")
    c3.metric(
        "蛋白質",
        f"{tot_p:.1f} g",
        delta=f"{tot_p - target_p:.1f} g",
    )
    c4.metric(
        "碳水化合物",
        f"{tot_c:.1f} g",
        delta=f"{tot_c - target_carbs:.1f} g",
    )
    c5.metric(
        "脂肪",
        f"{tot_f:.1f} g",
        delta=f"{tot_f - target_fat:.1f} g",
    )

    p_cal_ratio = (tot_p * 4 / tot_cal * 100) if tot_cal > 0 else 0
    c_cal_ratio = (tot_c * 4 / tot_cal * 100) if tot_cal > 0 else 0
    f_cal_ratio = (tot_f * 9 / tot_cal * 100) if tot_cal > 0 else 0

    st.caption(
        f"💡 今日淨熱量: **{net_cal:.0f}** kcal | 三大營養素熱量佔比 — 蛋白質: **{p_cal_ratio:.1f}%** | 碳水: **{c_cal_ratio:.1f}%** | 脂肪: **{f_cal_ratio:.1f}%**"
    )


def render_weekly_workout_summary(selected_date):

    st.subheader("🏋️ 本週重訓彙總")

    summary_df, start_w, end_w = get_weekly_workout_summary(selected_date)

    st.caption(

        f"📅 統計區間：{start_w.strftime('%Y-%m-%d')} ~ {end_w.strftime('%Y-%m-%d')}"

    )



    if not summary_df.empty:

        st.dataframe(summary_df, use_container_width=True, hide_index=True)

    else:

        st.info("本週尚無重訓紀錄。")


def render_monthly_run_and_shoes(selected_date):
    st.subheader(f"🏃 {selected_date.year} 年 {selected_date.month} 月慢跑與跑鞋紀錄")
    col1, col2 = st.columns([1, 1])

    with col1:
        total_dist, run_cnt = get_monthly_running_distance(selected_date)
        st.metric("本月總跑量", f"{total_dist:.2f} km", f"共慢跑 {run_cnt} 次")

    with col2:
        st.markdown("**👟 跑鞋累積里程**")
        shoe_df = get_shoe_mileage()
        if not shoe_df.empty:
            shoe_df.columns = ["跑鞋名稱", "累積里程 (km)"]
            st.dataframe(shoe_df, use_container_width=True, hide_index=True)
        else:
            st.info("尚無跑鞋里程紀錄。")


def render_daily_logs(date_str):
    st.subheader(f"📋 當日明細紀錄 ({date_str})")
    logs_df = get_logs_by_date(date_str)
    workouts_df = get_workouts_by_date(date_str)
    weight_df = get_weight_by_date(date_str)

    list_tab1, list_tab2, list_tab3 = st.tabs(
        [f"🍱 飲食明細({len(logs_df)})", 
         f"🏃 運動明細({len(workouts_df)})", 
         f"⚖️ 體重/體脂紀錄({len(weight_df)})"]
    )

    # 1. 飲食明細
    with list_tab1:
        if not logs_df.empty:
            for _, row in logs_df.iterrows():
                log_id = row["id"]
                col_info, col_edit, col_del = st.columns([3.5, 0.8, 0.8])
                with col_info:
                    st.write(
                        f"**{row['item']}** — {row['calories']:.0f} kcal | P: {row['protein']:.1f}g | C: {row['carbs']:.1f}g | F: {row['fat']:.1f}g"
                    )
                with col_edit:
                    if st.button("✏️ 編輯", key=f"btn_edit_food_{log_id}"):
                        st.session_state[f"editing_food_{log_id}"] = (
                            not st.session_state.get(
                                f"editing_food_{log_id}", False
                            )
                        )
                with col_del:
                    if st.button("🗑️ 刪除", key=f"del_food_{log_id}"):
                        delete_log(log_id)
                        st.toast(f"已刪除：{row['item']}")
                        st.rerun()

                if st.session_state.get(f"editing_food_{log_id}", False):
                    with st.form(key=f"form_edit_food_{log_id}"):
                        st.caption(f"🛠️ 編輯飲食項目 ID: {log_id}")
                        e_item = st.text_input("食物名稱", value=row["item"])
                        col_e1, col_e2 = st.columns(2)
                        with col_e1:
                            e_cal = st.number_input(
                                "熱量 (kcal)",
                                value=float(row["calories"]),
                                step=10.0,
                            )
                            e_p = st.number_input(
                                "蛋白質 (g)",
                                value=float(row["protein"]),
                                step=1.0,
                            )
                        with col_e2:
                            e_c = st.number_input(
                                "碳水 (g)",
                                value=float(row["carbs"]),
                                step=1.0,
                            )
                            e_f = st.number_input(
                                "脂肪 (g)",
                                value=float(row["fat"]),
                                step=1.0,
                            )

                        if st.form_submit_button("💾 儲存變更"):
                            update_log(
                                log_id, e_item.strip(), e_cal, e_p, e_c, e_f
                            )
                            st.session_state[f"editing_food_{log_id}"] = False
                            st.toast("飲食紀錄已更新！")
                            st.rerun()
                    st.divider()
        else:
            st.info("當天尚無飲食紀錄。")

    # 2. 運動明細
    with list_tab2:
        if not workouts_df.empty:
            for _, row in workouts_df.iterrows():
                w_id = row["id"]
                w_type = row["workout_type"]
                col_info, col_edit, col_del = st.columns([3.5, 0.8, 0.8])

                with col_info:
                    if w_type == "慢跑":
                        pace_str = calculate_pace(
                            row["distance"], row["duration_min"]
                        )
                        hr_str = (
                            f" | 心率: {int(row['avg_hr'])} bpm"
                            if pd.notna(row["avg_hr"]) and row["avg_hr"] > 0
                            else ""
                        )
                        shoe_str = (
                            f" | 跑鞋: {row['shoe']}"
                            if pd.notna(row["shoe"])
                            else ""
                        )
                        st.write(
                            f"**🏃 {row['item']}** — {row['distance']:.2f} km | 配速: {pace_str} | 時間: {row['duration_min']:.0f} 分鐘{hr_str}{shoe_str} (🔥 {row['calories_burned']:.0f} kcal)"
                        )
                    elif w_type == "重訓":
                        body_str = (
                            f"[{row['body_part']}] "
                            if pd.notna(row["body_part"])
                            else ""
                        )
                        rpe_str = (
                            f" | RPE: {int(row['rpe'])}"
                            if pd.notna(row["rpe"])
                            else ""
                        )
                        notes_str = (
                            f"\n> 筆記: {row['workout_notes']}"
                            if pd.notna(row["workout_notes"])
                            and row["workout_notes"]
                            else ""
                        )
                        st.write(
                            f"**🏋️ {body_str}{row['item']}**{rpe_str} (🔥 {row['calories_burned']:.0f} kcal){notes_str}"
                        )
                    else:
                        st.write(
                            f"**🚴 {row['item']}** (🔥 {row['calories_burned']:.0f} kcal)"
                        )

                with col_edit:
                    if st.button("✏️ 編輯", key=f"btn_edit_workout_{w_id}"):
                        st.session_state[f"editing_workout_{w_id}"] = (
                            not st.session_state.get(
                                f"editing_workout_{w_id}", False
                            )
                        )
                with col_del:
                    if st.button("🗑️ 刪除", key=f"del_workout_{w_id}"):
                        delete_workout(w_id)
                        st.toast(f"已刪除：{row['item']}")
                        st.rerun()

                if st.session_state.get(f"editing_workout_{w_id}", False):
                    with st.form(key=f"form_edit_workout_{w_id}"):
                        st.caption(f"🛠️ 編輯運動紀錄 ID: {w_id}")
                        e_item = st.text_input("運動名稱", value=row["item"])

                        if w_type == "慢跑":
                            col_e1, col_e2 = st.columns(2)
                            with col_e1:
                                e_dist = st.number_input(
                                    "距離 (km)",
                                    value=float(row["distance"])
                                    if pd.notna(row["distance"])
                                    else 0.0,
                                    step=0.1,
                                )
                                e_dur = st.number_input(
                                    "時間 (分鐘)",
                                    value=float(row["duration_min"])
                                    if pd.notna(row["duration_min"])
                                    else 0.0,
                                    step=1.0,
                                )
                                shoe_opts = [
                                    "Adidas Boston 13",
                                    "Adidas Adizero",
                                    "其他跑鞋",
                                    "不指定",
                                ]
                                curr_shoe_idx = (
                                    shoe_opts.index(row["shoe"])
                                    if row["shoe"] in shoe_opts
                                    else 3
                                )
                                e_shoe = st.selectbox(
                                    "使用跑鞋",
                                    shoe_opts,
                                    index=curr_shoe_idx,
                                )
                            with col_e2:
                                e_hr = st.number_input(
                                    "平均心率 (bpm)",
                                    value=int(row["avg_hr"])
                                    if pd.notna(row["avg_hr"])
                                    else 0,
                                    step=1,
                                )
                                e_cal = st.number_input(
                                    "消耗熱量 (kcal)",
                                    value=float(row["calories_burned"])
                                    if pd.notna(row["calories_burned"])
                                    else 0.0,
                                    step=10.0,
                                )

                            if st.form_submit_button("💾 儲存變更"):
                                update_workout(
                                    w_id,
                                    e_item.strip(),
                                    e_cal,
                                    "慢跑",
                                    distance=e_dist,
                                    duration_min=e_dur,
                                    avg_hr=e_hr,
                                    shoe=e_shoe,
                                )
                                st.session_state[f"editing_workout_{w_id}"] = (
                                    False
                                )
                                st.toast("慢跑紀錄已更新！")
                                st.rerun()

                        elif w_type == "重訓":
                            body_opts = [
                                "胸部",
                                "背部",
                                "腿部",
                                "肩部",
                                "手臂",
                                "核心",
                                "全身/其他",
                            ]
                            curr_body_idx = (
                                body_opts.index(row["body_part"])
                                if row["body_part"] in body_opts
                                else 6
                            )
                            e_body = st.selectbox(
                                "主要訓練部位",
                                body_opts,
                                index=curr_body_idx,
                            )
                            e_notes = st.text_area(
                                "動作與組數紀錄",
                                value=row["workout_notes"]
                                if pd.notna(row["workout_notes"])
                                else "",
                                height=100,
                            )

                            col_e1, col_e2 = st.columns(2)
                            with col_e1:
                                e_rpe = st.slider(
                                    "自覺強度 (RPE 1-10)",
                                    min_value=1,
                                    max_value=10,
                                    value=int(row["rpe"])
                                    if pd.notna(row["rpe"])
                                    else 7,
                                )
                            with col_e2:
                                e_cal = st.number_input(
                                    "消耗熱量 (kcal)",
                                    value=float(row["calories_burned"])
                                    if pd.notna(row["calories_burned"])
                                    else 0.0,
                                    step=10.0,
                                )

                            if st.form_submit_button("💾 儲存變更"):
                                update_workout(
                                    w_id,
                                    e_item.strip(),
                                    e_cal,
                                    "重訓",
                                    body_part=e_body,
                                    workout_notes=e_notes,
                                    rpe=e_rpe,
                                )
                                st.session_state[f"editing_workout_{w_id}"] = (
                                    False
                                )
                                st.toast("重訓紀錄已更新！")
                                st.rerun()

                        else:
                            e_cal = st.number_input(
                                "消耗熱量 (kcal)",
                                value=float(row["calories_burned"])
                                if pd.notna(row["calories_burned"])
                                else 0.0,
                                step=10.0,
                            )
                            if st.form_submit_button("💾 儲存變更"):
                                update_workout(
                                    w_id, e_item.strip(), e_cal, "其他"
                                )
                                st.session_state[f"editing_workout_{w_id}"] = (
                                    False
                                )
                                st.toast("運動紀錄已更新！")
                                st.rerun()
                    st.divider()
        else:
            st.info("當天尚無運動紀錄。")

    # 3. 體重明細
    with list_tab3:
        if not weight_df.empty:
            w_row = weight_df.iloc[0]
            col_info, col_edit, col_del = st.columns([3.5, 0.8, 0.8])
            with col_info:
                fat_disp = (
                    f" | 體脂: {w_row['body_fat']:.1f}%"
                    if "body_fat" in w_row and pd.notna(w_row["body_fat"])
                    else ""
                )
                note_disp = (
                    f" ({w_row['note']})" if w_row.get("note") else ""
                )
                st.write(
                    f"**⚖️ 體重: {w_row['weight']:.1f} kg**{fat_disp}{note_disp}"
                )
            with col_edit:
                if st.button("✏️ 編輯", key=f"btn_edit_weight_{date_str}"):
                    st.session_state[f"editing_weight_{date_str}"] = (
                        not st.session_state.get(
                            f"editing_weight_{date_str}", False
                        )
                    )
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
                        ew_val = st.number_input(
                            "體重 (kg)",
                            value=float(w_row["weight"]),
                            step=0.1,
                        )
                    with col_ew2:
                        efat_val = st.number_input(
                            "體脂率 (%)",
                            value=float(w_row["body_fat"])
                            if (
                                "body_fat" in w_row
                                and pd.notna(w_row["body_fat"])
                            )
                            else None,
                            step=0.1,
                        )
                    ew_note = st.text_input(
                        "備註",
                        value=w_row["note"]
                        if pd.notna(w_row["note"])
                        else "",
                    )

                    if st.form_submit_button("💾 儲存變更") and ew_val:
                        add_or_update_weight(
                            date_str, ew_val, efat_val, ew_note
                        )
                        st.session_state[f"editing_weight_{date_str}"] = False
                        st.toast("體重紀錄已更新！")
                        st.rerun()
        else:
            st.info("當天尚無體重/體脂紀錄。")


def render_weight_chart():
    st.markdown("#### ⚖️ 近 30 天體重與體脂趨勢圖")
    w_df = get_recent_weights(30)
    if not w_df.empty:
        chart_tab1, chart_tab2 = st.tabs(
            ["📉 體重趨勢 (kg)", "📉 體脂率趨勢 (%)"]
        )
        with chart_tab1:
            st.line_chart(w_df, x="log_date", y="weight", color="#5A738E")
        with chart_tab2:
            fat_df = w_df.dropna(subset=["body_fat"])
            if not fat_df.empty:
                st.line_chart(
                    fat_df, x="log_date", y="body_fat", color="#D97706"
                )
            else:
                st.info("近 30 天尚無體脂率紀錄數據。")
    else:
        st.info(
            "尚無體重紀錄，可在上方「新增紀錄 -> ⚖️ 體重與體脂」輸入數據。"
        )


def render_cal_chart():
    st.markdown("#### 🔥 熱量與三大營養素趨勢")
    recent_logs_df, recent_workouts_df = get_recent_logs(days=7)
    today_dt = date.today()
    date_range = [
        (today_dt - timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(6, -1, -1)
    ]

    food_summary = (
        recent_logs_df.groupby("log_date").sum().reindex(date_range).fillna(0)
        if not recent_logs_df.empty
        else pd.DataFrame(
            0,
            index=date_range,
            columns=["calories", "protein", "carbs", "fat"],
        )
    )

    if not recent_workouts_df.empty:
        workout_summary = (
            recent_workouts_df.groupby("log_date")
            .agg({"calories_burned": "sum", "distance": "sum"})
            .reindex(date_range)
            .fillna(0)
        )
    else:
        workout_summary = pd.DataFrame(
            0, index=date_range, columns=["calories_burned", "distance"]
        )

    daily_summary = food_summary.join(workout_summary).reset_index()
    daily_summary.rename(
        columns={
            "index": "日期",
            "log_date": "日期",
            "calories": "攝取熱量(kcal)",
            "calories_burned": "運動消耗(kcal)",
            "protein": "蛋白質(g)",
            "carbs": "碳水(g)",
            "fat": "脂肪(g)",
        },
        inplace=True,
    )

    st.line_chart(daily_summary, x="日期", y="攝取熱量(kcal)", color="#5A738E")
    st.line_chart(
        daily_summary, x="日期", y=["蛋白質(g)", "碳水(g)", "脂肪(g)"]
    )

# =============================================================================
# 4. 主程式流程與動態分流渲染 (Main Program)
# =============================================================================
def main():
    st.set_page_config(
        page_title="個人健康與健身數據看板", page_icon="🏋️", layout="wide"
    )
    init_db()

    # --- 側邊欄設定 (自動預設當天日期) ---
    st.sidebar.title("⚙️ 系統設定")

    selected_date = st.sidebar.date_input("📅 選擇紀錄日期", value=date.today())
    date_str = selected_date.strftime("%Y-%m-%d")

    st.sidebar.divider()
    st.sidebar.subheader("🎯 每日營養目標")
    target_cal = st.sidebar.number_input(
        "目標熱量 (kcal)", value=2200, step=50
    )
    target_p = st.sidebar.number_input(
        "蛋白質目標 (g)", value=120.0, step=5.0
    )
    target_carbs = st.sidebar.number_input(
        "碳水目標 (g)", value=300.0, step=5.0
    )
    target_fat = st.sidebar.number_input("脂肪目標 (g)", value=65.0, step=5.0)

    # 頂部抬頭
    st.title("🏋️ 個人健康 & 運動數據看板")

    # 區塊與對應渲染函式的映射字典
    section_mapping = {
        "新增紀錄區塊": lambda: render_add_records(date_str),
        "當日攝取進度與目標": lambda: render_daily_progress(
            date_str, target_cal, target_p, target_carbs, target_fat
        ),
        "週重訓彙總表格": lambda: render_weekly_workout_summary(
            selected_date
        ),
        "月跑量與跑鞋追蹤": lambda: render_monthly_run_and_shoes(
            selected_date
        ),
        "當日明細清單": lambda: render_daily_logs(date_str),
        "近30天體重與體脂趨勢圖": render_weight_chart,
        "熱量與營養趨勢圖": render_cal_chart,
    }

    # 預設排版順序
    ordered_sections = [
        "新增紀錄區塊",
        "當日攝取進度與目標",
        "當日明細清單",
        "熱量與營養趨勢圖",
        "近30天體重與體脂趨勢圖",
        "月跑量與跑鞋追蹤",
        "週重訓彙總表格",
    ]

    # 依序渲染各個模組
    for sec_name in ordered_sections:
        if sec_name in section_mapping:
            section_mapping[sec_name]()
            st.divider()


if __name__ == "__main__":
    main()
