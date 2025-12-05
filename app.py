import streamlit as st
import time
import re
import pandas as pd
import requests
import os

# --- 設定區 ---
# 請將此 URL 替換為您正確的 Google Apps Script 網址
GAS_URL = "https://script.google.com/macros/s/AKfycbwYKFTNQTeoaATKxillgfdFgwJnTS4o7J0nkOG077GNcJFJGKw9xd151yFdvUdoB_r5QQ/exec"

st.set_page_config(page_title="War Sync Calc", page_icon="⚔️", layout="wide")

# 隱藏 Streamlit 預設樣式
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            div.block-container {padding-top: 2rem;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- Google Sheet 串接函式 ---

def load_roster():
    """從 Google Sheet 讀取資料"""
    try:
        if "你的_ID_亂碼" in GAS_URL:
            st.error("⚠️ 請先在程式碼中填入正確的 GAS_URL")
            return {}
        response = requests.get(GAS_URL)
        if response.status_code == 200:
            return response.json() # 回傳格式: {"Name": time_int, ...}
        return {}
    except Exception as e:
        st.error(f"連線失敗: {e}")
        return {}

def update_player_in_sheet(name, seconds):
    """新增或更新玩家"""
    try:
        requests.post(GAS_URL, json={
            "action": "upsert",
            "name": name,
            "time": seconds
        })
    except Exception as e:
        st.error(f"儲存失敗: {e}")

def delete_player_from_sheet(name):
    """刪除玩家"""
    try:
        requests.post(GAS_URL, json={
            "action": "delete",
            "name": name
        })
    except Exception as e:
        st.error(f"刪除失敗: {e}")

# 初始化 Session State
if 'roster' not in st.session_state:
    with st.spinner('Loading roster from Google Sheet...'):
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

def format_timer(seconds: float) -> str:
    if seconds < 0: return "00:00"
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"

# --- 側邊欄 (Roster Manager) ---

with st.sidebar:
    st.header("👥 Roster Manager")
    
    with st.expander("✏️ Add / Update Player", expanded=True):
        new_name = st.text_input("Name", placeholder="Player Name")
        new_time_str = st.text_input("March Time", placeholder="e.g. 45, 1:30")
        
        if st.button("Save / Update"):
            secs = parse_seconds(new_time_str)
            if new_name and secs > 0:
                # 1. 更新 Google Sheet
                with st.spinner('Saving to Google Sheet...'):
                    update_player_in_sheet(new_name, secs)
                
                # 2. 更新本地 Session State
                st.session_state.roster[new_name] = secs
                
                action = "Updated" if new_name in st.session_state.roster else "Added"
                st.success(f"{action} {new_name} ({secs}s)")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Invalid input.")

    if st.session_state.roster:
        st.write("---")
        # 重新整理按鈕
        if st.button("🔄 Sync with Sheet"):
             st.session_state.roster = load_roster()
             st.rerun()

        to_remove = st.selectbox("Select to delete", [""] + list(st.session_state.roster.keys()))
        if to_remove and st.button(f"Delete {to_remove}", type="secondary"):
            # 1. 從 Google Sheet 刪除
            with st.spinner('Deleting...'):
                delete_player_from_sheet(to_remove)
            
            # 2. 從本地移除
            if to_remove in st.session_state.roster:
                del st.session_state.roster[to_remove]
            
            st.rerun()

# --- 主畫面 ---

st.title("⚔️ War Sync Calculator")

mode = st.radio("", ["⚔️ Attack / Rally", "🛡️ Defense / Garrison"], horizontal=True)
is_defense = "Defense" in mode

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### 1. Participants")
    roster_options = {f"{name} ({t}s)": {"name": name, "time": t} for name, t in st.session_state.roster.items()}
    sorted_options = sorted(roster_options.keys(), key=lambda k: roster_options[k]['time'], reverse=True)
    
    selected_labels = st.multiselect(
        "Select players (Default: All)", 
        options=sorted_options,
        default=sorted_options, 
        placeholder="Pick players..."
    )
    
    manual_input = st.text_input("Manual Add (Optional)", placeholder="e.g. 45 1:30")
    limit_count = st.number_input("Auto-Select Best Fit (Max)", min_value=1, value=15, step=1)

with col2:
    st.markdown("### 2. Target")
    if is_defense:
        c2a, c2b = st.columns(2)
        with c2a:
            enemy_march = st.number_input("Enemy March Walk Time (s)", min_value=0, value=0, step=1)
        with c2b:
            enemy_rally = st.text_input("Countdown to the Rally (m:s)", value="0:00")
        target_name = "Defense Target"
        st.caption("ℹ️ 自動加入 1 秒緩衝 (Target = Enemy + 1s)")
    else:
        target_name = st.text_input("Target Name", value="Target")

st.divider()

# --- 計算邏輯 ---

all_pool = []
for label in selected_labels:
    data = roster_options[label]
    all_pool.append({"name": data["name"], "time": data["time"]})

if manual_input:
    manual_times = manual_input.replace(",", " ").split()
    for i, t_str in enumerate(manual_times):
        s = parse_seconds(t_str)
        if s > 0: all_pool.append({"name": f"Manual-{i+1}", "time": s})

if not all_pool:
    st.info("👈 Waiting for players...")
else:
    all_pool.sort(key=lambda x: x['time'], reverse=True)
    starter = all_pool[0]
    
    for p in all_pool:
        p['gap'] = starter['time'] - p['time']
    
    all_pool.sort(key=lambda x: x['gap'])
    final_participants = all_pool[:limit_count]
    reserves = all_pool[limit_count:]

    max_time = starter['time']
    
    if is_defense:
        enemy_rally_sec = parse_seconds(enemy_rally)
        # [修改] 防守模式：目標時間 = 敵軍集結時間 + 敵軍行軍時間 + 1秒緩衝
        impact_time_rel = enemy_rally_sec + enemy_march + 1
        
        if impact_time_rel == 1: # 如果沒輸入任何時間，預設還是使用最慢者的時間
             impact_time_rel = max_time
             
        mode_title = f"🛡️ Timed Defense (Impact: {impact_time_rel}s)"
    else:
        impact_time_rel = max_time
        mode_title = f"⚔️ Rally Attack (Max: {max_time}s)"

    results = []
    for p in final_participants:
        t = p["time"]
        wait_seconds = impact_time_rel - t
        is_late = is_defense and wait_seconds < 0
        
        # [修改] 這裡過濾掉遲到 (Late) 的人，不顯示也不計算
        if is_late:
            continue
        
        results.append({"name": p["name"], "travel": t, "wait": wait_seconds, "is_late": is_late})
    
    results.sort(key=lambda x: x['wait'])

    st.subheader(f"{mode_title}")

    display_data = []
    copy_lines = [f"--- Plan: {target_name} ---"]
    
    for i, res in enumerate(results):
        if i == 0 and not res['is_late']:
            role_icon = "🟢 Starter"
        else:
            role_icon = f"{i+1}️⃣ Follower"

        # 這裡的 is_late 雖然上面已經過濾了，但保留邏輯結構無妨
        if res['is_late']:
            status = "💀 TOO LATE"
            action = "SKIP"
        elif res['wait'] == 0:
            status = "🚀 GO NOW"
            action = "SEND"
        else:
            status = f"Wait {res['wait']}s"
            action = f"Wait {res['wait']}s"
        
        display_data.append({
            "Role": role_icon,
            "Player": res['name'],
            "Travel": f"{res['travel']}s",
            "Action": status
        })
        copy_lines.append(f"[{res['name']}]: {action}")

    col_table, col_copy = st.columns([2, 1])
    with col_table:
        # 如果 results 是空的(全部遲到)，這裡顯示提示
        if not results:
             st.warning("⚠️ No valid participants. Everyone is too late!")
        else:
             st.dataframe(pd.DataFrame(display_data), use_container_width=True, hide_index=True)
    
    with col_copy:
        st.text_area("📋 Copy Text", "\n".join(copy_lines), height=200)
        if reserves:
            st.caption(f"⚠️ **Reserves:** {', '.join([r['name'] for r in reserves])}")

    st.divider()

    # --- Live Dashboard ---
    st.write("### ⏱️ Live Sequence")
    
    if st.button("🚀 Start Sequence (Lock Time)", type="primary", use_container_width=True):
        start_ts = time.time()
        
        if results:
            max_wait = max([r['wait'] for r in results if not r['is_late']])
            if is_defense: max_wait = max(max_wait, impact_time_rel)
        else:
            max_wait = 0
        
        live_col1, live_col2 = st.columns([1, 2])
        
        with live_col1:
            spotlight = st.empty()
            progress_bar = st.progress(0)
        
        with live_col2:
            table_ph = st.empty()
        
        while True:
            elapsed = time.time() - start_ts
            current_status = []
            
            if is_defense:
                enemy_left = impact_time_rel - elapsed
                e_state = "💥 IMPACT" if enemy_left <= 0 else f"⚔️ {int(enemy_left)}s"
                current_status.append({"Player": "🔴 ENEMY", "Status": e_state, "Wait": enemy_left})
                
                prog_val = 1.0 - (enemy_left / impact_time_rel) if impact_time_rel > 0 else 0
                progress_bar.progress(min(max(prog_val, 0.0), 1.0))

            all_done = True
            next_action_text = "✅ All Sent"
            next_action_time = 999999
            
            for res in results:
                name_disp = f"{res['name']} ({res['travel']}s)"
                
                # 再次過濾，雖然 results 裡已經沒有 late 了
                if res['is_late']:
                    continue
                
                time_left = res['wait'] - elapsed
                
                if time_left <= 0:
                    current_status.append({"Player": name_disp, "Status": "✅ SENT"})
                else:
                    all_done = False
                    current_status.append({"Player": name_disp, "Status": f"⏳ {time_left:.1f}s"})
                    
                    if time_left < next_action_time:
                        next_action_time = time_left
                        next_action_text = f"🚀 Next: {res['name']}\nin {time_left:.1f}s"

            if all_done:
                spotlight.success("## ✅ Complete")
            elif next_action_time < 2:
                spotlight.error(f"## {next_action_text}")
            else:
                spotlight.info(f"## {next_action_text}")

            df_live = pd.DataFrame(current_status)
            if "Wait" in df_live.columns: df_live = df_live.drop(columns=["Wait"])
            table_ph.dataframe(df_live, use_container_width=True, hide_index=True)
            
            defense_end = (not is_defense) or (is_defense and (impact_time_rel - elapsed <= 0))
            # 增加一些緩衝時間讓迴圈結束，避免馬上消失
            if all_done and defense_end and elapsed > (max_wait + 3):
                break
                
            time.sleep(0.1)
        
        if not is_defense: st.balloons()
        st.success("Sequence Finished")

