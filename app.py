import streamlit as st
import time
import re
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="War Sync Calculator", page_icon="⚔️", layout="centered")

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

def get_ordinal(n):
    if 11 <= (n % 100) <= 13: suffix = 'th'
    else: suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"

st.title("⚔️ War Sync Calculator")

mode = st.radio("Select Mode / 選擇模式", ["⚔️ Rally Attack (集結進攻)", "🛡️ Rally Defense (壓秒駐防)"], horizontal=True)
is_defense = "Defense" in mode

col1, col2 = st.columns([2, 1])
with col1:
    raw_input = st.text_input("March Times (行軍時間)", placeholder="e.g. 45 1:30 38s")
with col2:
    target_name = st.text_input("Target Name", value="Target")

landing_time = 0
if is_defense:
    landing_time = st.number_input("Enemy Landing In (seconds) / 敵軍抵達倒數", min_value=0, value=0, step=1, help="0 means simple sync (just gather together).")

st.divider()

if raw_input:
    times_str = raw_input.replace(",", " ").split()
    parsed_data = []
    for t in times_str:
        secs = parse_seconds(t)
        if secs > 0: parsed_data.append(secs)

    if len(parsed_data) < 1:
        st.error("⚠️ Please enter valid times.")
    else:
        max_time = max(parsed_data)
        current_now = time.time()
        
        if is_defense and landing_time > 0:
            impact_time_rel = landing_time
            mode_title = f"🛡️ Timed Defense (Impact in {landing_time}s)"
        else:
            impact_time_rel = max_time
            mode_title = "⚔️ Sync Attack / Defense"

        results = []
        for t in parsed_data:
            launch_at_rel = impact_time_rel - t
            wait_seconds = launch_at_rel
            
            if is_defense and landing_time > 0:
                wait_seconds = launch_at_rel
            else:
                wait_seconds = max_time - t

            results.append({
                "travel": t,
                "wait": wait_seconds,
                "is_late": wait_seconds < 0
            })
        
        results.sort(key=lambda x: x['wait'])

        st.subheader(f"{mode_title}")
        
        display_data = []
        copy_lines = [f"--- Plan: {target_name} ---"]
        
        for i, res in enumerate(results):
            role = "🟢 Starter" if i == 0 and not res['is_late'] else f"{i+1}️⃣ Team"
            
            if res['is_late']:
                action = "TOO LATE (SKIP)"
                status = "💀 Skip"
            elif res['wait'] == 0:
                action = "GO NOW"
                status = "🚀 Start"
            else:
                action = f"Wait {res['wait']}s"
                status = f"Wait {res['wait']}s"
            
            display_data.append({
                "Role": role,
                "Travel": f"{res['travel']}s",
                "Action": status
            })
            copy_lines.append(f"[{res['travel']}s Team]: {action}")

        st.table(pd.DataFrame(display_data))

        with st.expander("📋 Copy for In-Game Chat"):
            st.code("\n".join(copy_lines), language="yaml")

        st.divider()

        st.write("### ⏱️ Live Countdown Timer")
        
        if st.button("🔥 Start 5s Countdown", type="primary"):
            placeholder = st.empty()
            
            for i in range(5, 0, -1):
                placeholder.warning(f"# ⚠️ LAUNCH IN {i}...")
                time.sleep(1)
            
            placeholder.success("# 🚀 SEQUENCE START!")
            time.sleep(1)
            
            start_ts = time.time()
            
            max_wait = max([r['wait'] for r in results if not r['is_late']]) if results else 0
            
            table_placeholder = st.empty()
            
            while True:
                elapsed = time.time() - start_ts
                current_status = []
                all_done = True
                
                for i, res in enumerate(results):
                    if res['is_late']:
                        current_status.append({"Role": f"Team {i+1}", "Status": "💀 LATE"})
                        continue
                        
                    time_left = res['wait'] - elapsed
                    
                    if time_left <= 0:
                        current_status.append({"Role": f"Team {i+1}", "Status": "✅ GO NOW!"})
                    else:
                        all_done = False
                        current_status.append({"Role": f"Team {i+1}", "Status": f"⏳ Wait {time_left:.1f}s"})
                
                table_placeholder.table(pd.DataFrame(current_status))
                
                if all_done and elapsed > (max_wait + 2):
                    break
                    
                time.sleep(0.1)
            
            st.balloons()
            st.success("Sequence Complete!")
