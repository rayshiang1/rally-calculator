import streamlit as st
import time
import re
import pandas as pd
import json
import os

st.set_page_config(page_title="War Sync Calc", page_icon="⚔️", layout="wide")

hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

ROSTER_FILE = "roster.json"

def load_roster():
    if os.path.exists(ROSTER_FILE):
        try:
            with open(ROSTER_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return {}
    return {}

def save_roster(data):
    with open(ROSTER_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

if 'roster' not in st.session_state:
    st.session_state.roster = load_roster()

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

with st.sidebar:
    st.header("👥 Player Roster")
    
    with st.expander("➕ Add New Player", expanded=True):
        new_name = st.text_input("Name", placeholder="Player Name")
        new_time_str = st.text_input("March Time", placeholder="e.g. 45, 1:30")
        
        if st.button("Save Player"):
            secs = parse_seconds(new_time_str)
            if new_name and secs > 0:
                st.session_state.roster[new_name] = secs
                save_roster(st.session_state.roster)
                st.success(f"Added {new_name} ({secs}s)")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Invalid name or time.")

    if st.session_state.roster:
        st.write("---")
        st.write("❌ **Remove Player**")
        to_remove = st.selectbox("Select to delete", [""] + list(st.session_state.roster.keys()))
        if to_remove and st.button(f"Delete {to_remove}"):
            del st.session_state.roster[to_remove]
            save_roster(st.session_state.roster)
            st.rerun()

st.title("⚔️ War Sync Calculator")

mode = st.radio("", ["⚔️ Attack / Rally", "🛡️ Defense / Garrison"], horizontal=True)
is_defense = "Defense" in mode

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### 1. Select Participants")
    roster_options = {f"{name} ({t}s)": {"name": name, "time": t} for name, t in st.session_state.roster.items()}
    
    sorted_options = sorted(roster_options.keys(), key=lambda k: roster_options[k]['time'], reverse=True)
    
    # ★ 修改處：加入 default=sorted_options 全選所有名單
    selected_labels = st.multiselect(
        "Who is available? (Uncheck offline players)", 
        options=sorted_options,
        default=sorted_options, 
        placeholder="Select online players..."
    )
    
    manual_input = st.text_input("Manual Input (Optional)", placeholder="e.g. 45 1:30")

    limit_count = st.number_input("Max Participants (Auto-select best fit)", min_value=1, value=15, step=1)

with col2:
    st.markdown("### 2. Target Info")
    if is_defense:
        c2a, c2b = st.columns(2)
        with c2a:
            enemy_march = st.number_input("Enemy March (s)", min_value=0, value=0, step=1)
        with c2b:
            enemy_rally = st.text_input("Enemy Rally", value="0:00")
        target_name = "Defense Target"
    else:
        target_name = st.text_input("Target Name", value="Target")

st.divider()

all_pool = []

for label in selected_labels:
    data = roster_options[label]
    all_pool.append({"name": data["name"], "time": data["time"]})

if manual_input:
    manual_times = manual_input.replace(",", " ").split()
    for i, t_str in enumerate(manual_times):
        s = parse_seconds(t_str)
        if s > 0:
            all_pool.append({"name": f"Manual-{i+1}", "time": s})

if not all_pool:
    st.info("👈 Please check players in the list.")
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
        impact_time_rel = enemy_rally_sec + enemy_march
        if impact_time_rel == 0: impact_time_rel = max_time
        mode_title = f"🛡️ Timed Defense (Impact: {impact_time_rel}s)"
    else:
        impact_time_rel = max_time
        mode_title = f"⚔️ Rally Attack (Max: {max_time}s)"

    results = []
    for p in final_participants:
        t = p["time"]
        wait_seconds = impact_time_rel - t

        is_late = False
        if is_defense and wait_seconds < 0:
            is_late = True

        results.append({
            "name": p["name"],
            "travel": t,
            "wait": wait_seconds,
            "is_late": is_late
        })
    
    results.sort(key=lambda x: x['wait'])

    st.subheader(f"{mode_title} - Top {len(final_participants)} Picked")
    
    if reserves:
        st.caption(f"⚠️ **Reserves (Excluded):** {', '.join([r['name'] for r in reserves])}")

    display_data = []
    copy_lines = [f"--- Plan: {target_name} ---"]
    
    for i, res in enumerate(results):
        if i == 0 and not res['is_late']:
            role_icon = "🟢 Starter"
        else:
            role_icon = f"{i+1}️⃣ Follower"

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

    st.table(pd.DataFrame(display_data))

    with st.expander("📋 Copy for Chat"):
        st.code("\n".join(copy_lines), language="yaml")

    st.divider()

    st.write("### ⏱️ Live Dashboard")
    
    if st.button("🚀 Start Sequence (Lock Time)", type="primary", use_container_width=True):
        start_ts = time.time()
        
        if results:
            max_wait = max([r['wait'] for r in results if not r['is_late']])
            if is_defense: max_wait = max(max_wait, impact_time_rel)
        else:
            max_wait = 0
        
        status_ph = st.empty()
        
        while True:
            elapsed = time.time() - start_ts
            current_status = []
            
            if is_defense:
                enemy_left = impact_time_rel - elapsed
                e_state = "💥 IMPACT" if enemy_left <= 0 else f"⚔️ {int(enemy_left)}s"
                current_status.append({"Player": "🔴 ENEMY", "Status": e_state, "Action": "INCOMING"})

            all_done = True
            for res in results:
                name_disp = f"{res['name']} ({res['travel']}s)"
                
                if res['is_late']:
                    current_status.append({"Player": name_disp, "Status": "💀 LATE", "Action": "SKIP"})
                    continue
                
                time_left = res['wait'] - elapsed
                
                if time_left <= 0:
                    current_status.append({"Player": name_disp, "Status": "✅ GO NOW!", "Action": "SENT"})
                else:
                    all_done = False
                    current_status.append({"Player": name_disp, "Status": f"⏳ {time_left:.1f}s", "Action": "WAIT"})
            
            status_ph.table(pd.DataFrame(current_status))
            
            defense_end = (not is_defense) or (is_defense and (impact_time_rel - elapsed <= 0))
            if all_done and defense_end and elapsed > (max_wait + 3):
                break
                
            time.sleep(0.1)
        
        if not is_defense: st.balloons()
        st.success("Sequence Finished")
