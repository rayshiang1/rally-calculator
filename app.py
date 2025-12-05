import streamlit as st
import time
import re
import pandas as pd
import requests
import os

# --- 設定區 ---
GAS_URL = "https://script.google.com/macros/s/AKfycbwYKFTNQTeoaATKxillgfdFgwJnTS4o7J0nkOG077GNcJFJGKw9xd151yFdvUdoB_r5QQ/exec"

st.set_page_config(page_title="War Sync Calc", page_icon="⚔️", layout="wide")

hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            div.block-container {padding-top: 2rem;}
            .stDataFrame {width: 100%;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- Google Sheet 串接函式 ---
def load_roster():
    try:
        if "你的_ID_亂碼" in GAS_URL:
            st.error("⚠️ 請先在程式碼中填入正確的 GAS_URL")
            return {}
        response = requests.get(GAS_URL)
        if response.status_code == 200:
            return response.json()
        return {}
    except Exception as e:
        st.error(f"連線失敗: {e}")
        return {}

def update_player_in_sheet(name, seconds):
    try:
        requests.post(GAS_URL, json={"action": "upsert", "name": name, "time": seconds})
    except Exception as e:
        st.error(f"儲存失敗: {e}")

def delete_player_from_sheet(name):
    try:
        requests.post(GAS_URL, json={"action": "delete", "name": name})
    except Exception as e:
        st.error(f"刪除失敗: {e}")

if 'roster' not in st.session_state:
    with st.spinner('Loading roster...'):
        st.session_state.roster = load_roster()

# --- 工具函式 ---
def parse_seconds(time_str: str) -> int:
    time_str = str(time_str).lower().strip()
    if time_str.isdigit(): return int(time_str)
    if ":" in time_str:
        parts = time_str.split(":")
        if len(parts) == 2:
            try: return int(parts[0]) * 60 + int(parts[1])
            except: pass
    seconds = 0
    match_m = re.search(r"(\d+)m", time_str)
    match_s = re.search(r"(\d+)s", time_str)
    if match_m: seconds += int(match_m.group(1)) * 60
    if match_s: seconds += int(match_s.group(1))
    return seconds if seconds > 0 else 0

# --- 側邊欄 ---
with st.sidebar:
    st.header("👥 Roster Manager")
    with st.expander("✏️ Add / Update Player", expanded=True):
        new_name = st.text_input("Name", placeholder="Player Name")
        new_time_str = st.text_input("March Time", placeholder="e.g. 45, 1:30")
        if st.button("Save / Update"):
            secs = parse_seconds(new_time_str)
            if new_name and secs > 0:
                with st.spinner('Saving...'):
                    update_player_in_sheet(new_name, secs)
                st.session_state.roster[new_name] = secs
                st.success(f"Saved {new_name}")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Invalid input.")

    if st.session_state.roster:
        st.write("---")
        if st.button("🔄 Sync with Sheet"):
             st.session_state.roster = load_roster()
             st.rerun()
        to_remove = st.selectbox("Select to delete", [""] + list(st.session_state.roster.keys()))
        if to_remove and st.button(f"Delete {to_remove}", type="secondary"):
            with st.spinner('Deleting...'):
                delete_player_from_sheet(to_remove)
            if to_remove in st.session_state.roster:
                del st.session_state.roster[to_remove]
            st.rerun()

# --- 主畫面 ---
st.title("⚔️ War Sync Calculator")

# 模式選擇
col_mode1, col_mode2 = st.columns([1, 1])
with col_mode1:
    mode = st.radio("", ["⚔️ Attack / Rally", "🛡️ Defense / Garrison"], horizontal=True)
    is_defense = "Defense" in mode
with col_mode2:
    is_multi = st.toggle("🔥 Multi-Rally Mode", value=False)

st.divider()

# --- 資料準備 ---
roster_data = [{"name": n, "time": t} for n, t in st.session_state.roster.items()]
roster_data.sort(key=lambda x: x['time'], reverse=True) # 預設按時間排序
all_player_names = [p['name'] for p in roster_data]

# --- 輸入處理 (單一 vs 多重) ---
targets_list = []

if is_multi:
    st.info("💡 在下方表格輸入多個敵軍集結。設定完成後，在下方分配人員。")
    
    # 初始化表格資料
    if 'multi_target_df' not in st.session_state:
        st.session_state.multi_target_df = pd.DataFrame(
            [{"Target Name": "Rally A", "March (s)": 30, "Rally (m:s)": "5:00"}]
        )

    edited_df = st.data_editor(
        st.session_state.multi_target_df, 
        num_rows="dynamic", 
        use_container_width=True,
        column_config={
            "Target Name": st.column_config.TextColumn("Target Name", help="敵軍名稱或目標", required=True),
            "March (s)": st.column_config.NumberColumn("March (s)", help="敵軍行軍時間", min_value=0, step=1, required=True),
            "Rally (m:s)": st.column_config.TextColumn("Rally (m:s)", help="集結倒數 (如 5:00)", required=True),
        }
    )
    
    # 解析表格資料
    for index, row in edited_df.iterrows():
        if row["Target Name"]:
            targets_list.append({
                "name": row["Target Name"],
                "enemy_march": int(row["March (s)"]),
                "enemy_rally": str(row["Rally (m:s)"])
            })

else:
    # 單一模式介面
    c1, c2 = st.columns([2, 1])
    with c1:
        st.markdown("### Participants")
        # 這裡的選擇稍後處理，先存設定
    with c2:
        st.markdown("### Target")
        if is_defense:
            e_march = st.number_input("Enemy March (s)", 0, step=1)
            e_rally = st.text_input("Countdown (m:s)", "0:00")
            t_name = "Defense"
        else:
            e_march = 0
            e_rally = "0:00"
            t_name = st.text_input("Target Name", "Target")
        
        targets_list.append({
            "name": t_name,
            "enemy_march": e_march,
            "enemy_rally": e_rally
        })

# --- 分配邏輯與計算 ---
master_results = []
remaining_players = all_player_names.copy()

# 如果是單一模式，顯示標準選擇器
if not is_multi:
    with c1:
        selected = st.multiselect("Select Players", remaining_players, default=remaining_players)
        # 單一模式的手動輸入
        manual_add = st.text_input("Manual Add (Optional)", placeholder="e.g. 45 1:30")
        
    # 加入手動玩家到暫存 pool
    current_pool = [p for p in roster_data if p['name'] in selected]
    if manual_add:
        for i, t_str in enumerate(manual_add.replace(",", " ").split()):
            s = parse_seconds(t_str)
            if s > 0: current_pool.append({"name": f"Manual-{i+1}", "time": s})
            
    # 將唯一的 target 賦予這個 pool
    targets_list[0]['assigned_pool'] = current_pool

else:
    # 多重模式：依序分配
    st.markdown("### 👮 Assign Players to Targets")
    cols = st.columns(len(targets_list)) if len(targets_list) > 0 else [st.container()]
    
    for i, target in enumerate(targets_list):
        with cols[i % len(cols)]: # 避免 columns 太多
            st.markdown(f"**Target: {target['name']}**")
            
            # 使用 remaining_players 確保不重複選
            selected_for_target = st.multiselect(
                f"Pick for {target['name']}", 
                remaining_players, 
                key=f"multi_select_{i}"
            )
            
            # 更新剩餘名單
            remaining_players = [p for p in remaining_players if p not in selected_for_target]
            
            # 建立這個 target 的 roster
            pool = [p for p in roster_data if p['name'] in selected_for_target]
            target['assigned_pool'] = pool


# --- 核心計算迴圈 ---
st.write("---")

display_sections = [] # 儲存要顯示的 UI 區塊

for target in targets_list:
    pool = target.get('assigned_pool', [])
    
    if not pool:
        continue

    # 計算目標時間
    starter = max(pool, key=lambda x: x['time']) # 預設最慢者為基準
    max_time = starter['time']
    
    if is_defense:
        e_sec = parse_seconds(target['enemy_rally'])
        # [規則] Defense 目標 = Rally + March + 1s 緩衝
        impact_time = e_sec + target['enemy_march'] + 1
        if impact_time == 1: impact_time = max_time # 防呆
        mode_title = f"🛡️ {target['name']} (Impact: {impact_time}s)"
    else:
        impact_time = max_time
        mode_title = f"⚔️ {target['name']} (Max: {max_time}s)"

    # 計算個別等待時間
    target_results = []
    copy_lines = [f"--- Plan: {target['name']} ---"]
    
    # 排序：行軍時間長的先計算 (Gap logic)
    pool.sort(key=lambda x: x['time'], reverse=True)
    
    for i, p in enumerate(pool):
        wait = impact_time - p['time']
        is_late = is_defense and wait < 0
        
        # [過濾] 遲到者移除
        if is_late: continue
        
        # 狀態文字
        if wait == 0: action = "SEND"
        else: action = f"Wait {wait}s"
        
        res_obj = {
            "target": target['name'],
            "name": p['name'],
            "travel": p['time'],
            "wait": wait,
            "action": action,
            "role": "Starter" if i==0 else "Follower"
        }
        target_results.append(res_obj)
        master_results.append(res_obj)
        copy_lines.append(f"[{p['name']}]: {action}")

    # 準備顯示資料 (個別 Target 的表格)
    if target_results:
        target_results.sort(key=lambda x: x['wait']) # 按等待時間排序顯示
        
        df_disp = pd.DataFrame([{
            "Role": r['role'], "Player": r['name'], 
            "Travel": f"{r['travel']}s", "Action": r['action']
        } for r in target_results])
        
        display_sections.append({
            "title": mode_title,
            "df": df_disp,
            "copy_text": "\n".join(copy_lines)
        })

# --- 顯示個別計畫表 ---
if display_sections:
    # 使用 Tabs 來節省空間，或者 Columns
    if is_multi:
        st.subheader("📋 Strategy Plans")
        my_tabs = st.tabs([d['title'] for d in display_sections])
        for i, tab in enumerate(my_tabs):
            with tab:
                c1, c2 = st.columns([2, 1])
                with c1: st.dataframe(display_sections[i]['df'], hide_index=True, use_container_width=True)
                with c2: st.text_area("Copy", display_sections[i]['copy_text'], height=200)
    else:
        # 單一模式維持原樣
        d = display_sections[0]
        st.subheader(d['title'])
        c1, c2 = st.columns([2, 1])
        with c1: st.dataframe(d['df'], hide_index=True, use_container_width=True)
        with c2: st.text_area("Copy", d['copy_text'], height=200)

else:
    st.warning("⚠️ No valid plans generated. Check players or times.")


# --- Live Dashboard (Unified) ---
st.divider()
st.write("### ⏱️ Master Live Sequence")

if st.button("🚀 Start Sequence (All Targets)", type="primary", use_container_width=True):
    start_ts = time.time()
    
    # 計算最大等待時間，決定何時結束迴圈
    if master_results:
        max_wait_total = max([r['wait'] for r in master_results])
        # 也要考慮 impact time
        max_impact = 0
        for t in targets_list:
             imp = parse_seconds(t['enemy_rally']) + t['enemy_march'] + 1
             if imp > max_impact: max_impact = imp
        max_wait_total = max(max_wait_total, max_impact)
    else:
        max_wait_total = 0

    l_col1, l_col2 = st.columns([1, 2])
    with l_col1:
        spotlight = st.empty()
        st.caption("Monitoring all targets...")
    with l_col2:
        table_ph = st.empty()

    while True:
        elapsed = time.time() - start_ts
        live_rows = []
        
        # 1. 顯示所有敵軍撞擊倒數
        if is_defense:
            for t in targets_list:
                imp = parse_seconds(t['enemy_rally']) + t['enemy_march'] + 1
                left = imp - elapsed
                status = "💥 IMPACT" if left <= 0 else f"⚔️ {left:.1f}s"
                live_rows.append({"Target": t['name'], "Player": "🔴 ENEMY", "Status": status, "SortKey": left})

        # 2. 顯示所有玩家狀態
        all_sent = True
        next_event_time = 9999
        next_event_text = "✅ All Clear"
        
        for res in master_results:
            time_left = res['wait'] - elapsed
            p_label = f"{res['name']} ({res['travel']}s)"
            
            if time_left <= 0:
                status = "✅ SENT"
                sort_key = -999 # 已發送沈底
            else:
                all_sent = False
                status = f"⏳ {time_left:.1f}s"
                sort_key = time_left
                
                # 找下一個最近的事件
                if time_left < next_event_time:
                    next_event_time = time_left
                    # 顯示 去哪裡 (To Target)
                    next_event_text = f"🚀 {res['name']} \n➜ {res['target']}\nin {time_left:.1f}s"

            live_rows.append({
                "Target": res['target'],
                "Player": p_label, 
                "Status": status, 
                "SortKey": sort_key
            })
        
        # 排序：即將發生的排前面，已發送的排後面
        live_rows.sort(key=lambda x: x['SortKey'])
        
        # 顯示 Spotlight
        if all_sent:
            spotlight.success("## ✅ Complete")
        elif next_event_time < 3: # 3秒內變紅色警告
            spotlight.error(f"## {next_event_text}")
        else:
            spotlight.info(f"## {next_event_text}")

        # 顯示表格 (移除 SortKey 欄位)
        df_live = pd.DataFrame(live_rows).drop(columns=["SortKey"])
        table_ph.dataframe(df_live, use_container_width=True, hide_index=True)
        
        # 結束條件
        if all_sent and elapsed > (max_wait_total + 3):
            break
            
        time.sleep(0.1)
    
    st.success("All sequences finished.")
