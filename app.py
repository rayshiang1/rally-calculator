import streamlit as st
import time
import re
import pandas as pd

st.set_page_config(page_title="War Sync Calc", page_icon="⚔️", layout="centered")

hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

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

mode = st.radio("", ["⚔️ Attack / Rally", "🛡️ Defense / Garrison"], horizontal=True)
is_defense = "Defense" in mode

col1, col2 = st.columns([2, 1])
with col1:
    raw_input = st.text_input("March Times", placeholder="e.g. 45 1:30 38s")
with col2:
    if is_defense:
        landing_time = st.number_input("Enemy Landing (s)", min_value=0, value=0, step=1)
    else:
        target_name = st.text_input("Target Name", value="Target")

st.divider()

if raw_input:
    times_str = raw_input.replace(",", " ").split()
    parsed_data = []
    for t in times_str:
        secs = parse_seconds(t)
        if secs > 0: parsed_data.append(secs)

    if len(parsed_data) < 1:
        st.error("Invalid times.")
    else:
        max_time = max(parsed_data)
        
        if is_defense and landing_time > 0:
            impact_time_rel = landing_time
        else:
            impact_time_rel = max_time

        results = []
        for t in parsed_data:
            if is_defense and landing_time > 0:
                wait_seconds = impact_time_rel - t
            else:
                wait_seconds = max_time - t

            results.append({
                "travel": t,
                "wait": wait_seconds,
                "is_late": wait_seconds < 0
            })
        
        results.sort(key=lambda x: x['wait'])

        st.subheader("📋 Plan Details")
        
        display_data = []
        copy_lines = [f"--- Plan ---"]
        
        for i, res in enumerate(results):
            if i == 0 and not res['is_late']:
                role = "🟢 Starter"
            else:
                role = f"{i+1}️⃣ {get_ordinal(i+1)} Team"
            
            if res['is_late']:
                status = "💀 TOO LATE"
            elif res['wait'] == 0:
                status = "🚀 GO NOW"
            else:
                status = f"Wait {res['wait']}s"
            
            display_data.append({
                "Role": role,
                "Travel": f"{res['travel']}s",
                "Action": status
            })
            copy_lines.append(f"[{res['travel']}s]: {status}")

        st.table(pd.DataFrame(display_data))

        with st.expander("📋 Copy Text"):
            st.code("\n".join(copy_lines), language="yaml")

        st.divider()

        st.write("### ⏱️ Live Sequence")
        
        if st.button("🚀 Start Sequence", type="primary", use_container_width=True):
            start_ts = time.time()
            
            if results:
                max_wait = max([r['wait'] for r in results if not r['is_late']])
            else:
                max_wait = 0
            
            status_ph = st.empty()
            
            while True:
                elapsed = time.time() - start_ts
                current_status = []
                all_done = True
                
                for i, res in enumerate(results):
                    if res['is_late']:
                        current_status.append({"Role": f"Team {i+1} ({res['travel']}s)", "Status": "💀 LATE"})
                        continue
                        
                    time_left = res['wait'] - elapsed
                    
                    if time_left <= 0:
                        current_status.append({"Role": f"Team {i+1} ({res['travel']}s)", "Status": "✅ GO NOW!"})
                    else:
                        all_done = False
                        current_status.append({"Role": f"Team {i+1} ({res['travel']}s)", "Status": f"⏳ {time_left:.1f}s"})
                
                status_ph.table(pd.DataFrame(current_status))
                
                if all_done and elapsed > (max_wait + 3):
                    break
                    
                time.sleep(0.1)
            
            st.balloons()
            st.success("Sequence Complete!")
