import streamlit as st
import time
import re
import pandas as pd

st.set_page_config(page_title="War Sync Calc", page_icon="⚔️", layout="centered")

# --- Hide Streamlit Branding ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- Logic Functions ---
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
    """Format seconds into MM:SS"""
    if seconds < 0: return "00:00"
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"

def get_ordinal(n):
    if 11 <= (n % 100) <= 13: suffix = 'th'
    else: suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"

# --- UI Start ---
st.title("⚔️ War Sync Calculator")

mode = st.radio("", ["⚔️ Attack / Rally", "🛡️ Defense / Garrison"], horizontal=True)
is_defense = "Defense" in mode

col1, col2 = st.columns([1.5, 1])

with col1:
    raw_input = st.text_input("Your Team March Times", placeholder="e.g. 45 1:30 38s")

with col2:
    if is_defense:
        st.markdown("**Enemy Info**")
        c2a, c2b = st.columns(2)
        with c2a:
            enemy_march = st.number_input("March (s)", min_value=0, value=0, step=1, help="Enemy travel time to target")
        with c2b:
            enemy_rally = st.text_input("Rally Time", value="0:00", help="Time remaining on Enemy Rally")
        target_name = "My Structure"
    else:
        target_name = st.text_input("Target Name", value="Target")

st.divider()

if raw_input:
    # 1. Parse User Times
    times_str = raw_input.replace(",", " ").split()
    parsed_data = []
    for t in times_str:
        secs = parse_seconds(t)
        if secs > 0: parsed_data.append(secs)

    if len(parsed_data) < 1:
        st.error("⚠️ Please enter valid march times.")
    else:
        # 2. Calculate Calculations
        max_time = max(parsed_data)
        
        # Determine Impact Time (Relative to T=0 start)
        if is_defense:
            # Defense: Impact = Enemy Rally Count + Enemy March Time
            enemy_rally_sec = parse_seconds(enemy_rally)
            impact_time_rel = enemy_rally_sec + enemy_march
            
            # If user put 0 for both, default to simple sync (max_time)
            if impact_time_rel == 0:
                impact_time_rel = max_time
                
        else:
            # Attack: Impact = Slowest marcher
            impact_time_rel = max_time

        results = []
        for t in parsed_data:
            # Calculation:
            # Wait = Total Impact Time - My Travel Time
            wait_seconds = impact_time_rel - t

            results.append({
                "travel": t,
                "wait": wait_seconds,
                "is_late": wait_seconds < 0
            })
        
        # Sort by wait time (Action order)
        results.sort(key=lambda x: x['wait'])

        # 3. Static Plan Table
        st.subheader("📋 Plan Details")
        if is_defense:
            st.caption(f"Enemy arrives in: **{format_timer(impact_time_rel)}** ({int(impact_time_rel)}s)")
        
        display_data = []
        copy_lines = [f"--- Plan ---"]
        
        for i, res in enumerate(results):
            # Determine Role Name
            if i == 0 and not res['is_late']:
                role = "🟢 Starter"
            else:
                role = f"{i+1}️⃣ {get_ordinal(i+1)} Team"
            
            # Determine Status
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

        # 4. Live Sequence
        st.write("### ⏱️ Live Sequence")
        
        if st.button("🚀 Start Sequence", type="primary", use_container_width=True):
            start_ts = time.time()
            
            # Determine loop duration (until last person goes + buffer)
            if results:
                max_wait = max([r['wait'] for r in results if not r['is_late']])
                # If defending, also keep showing until enemy hits
                if is_defense:
                    max_wait = max(max_wait, impact_time_rel)
            else:
                max_wait = 0
            
            status_ph = st.empty()
            
            while True:
                elapsed = time.time() - start_ts
                current_status = []
                
                # --- [A] Add Attacker Row (Defense Only) ---
                if is_defense:
                    enemy_time_left = impact_time_rel - elapsed
                    if enemy_time_left <= 0:
                        enemy_state = "💥 IMPACT!"
                    else:
                        enemy_state = f"⚔️ {format_timer(enemy_time_left)}"
                    
                    current_status.append({
                        "Role": "🔴 Attacker (Enemy)", 
                        "Status": enemy_state
                    })

                # --- [B] Add Defender/Attacker Team Rows ---
                all_teams_launched = True
                
                for i, res in enumerate(results):
                    # Skip logic for late teams
                    if res['is_late']:
                        current_status.append({"Role": f"Team {i+1} ({res['travel']}s)", "Status": "💀 LATE"})
                        continue
                        
                    time_left = res['wait'] - elapsed
                    
                    if time_left <= 0:
                        current_status.append({"Role": f"Team {i+1} ({res['travel']}s)", "Status": "✅ GO NOW!"})
                    else:
                        all_teams_launched = False
                        # Show seconds for precision
                        current_status.append({"Role": f"Team {i+1} ({res['travel']}s)", "Status": f"⏳ {time_left:.1f}s"})
                
                # Render Table
                status_ph.table(pd.DataFrame(current_status))
                
                # Exit Condition: All teams launched AND (if defense) enemy has arrived
                defense_finished = (not is_defense) or (is_defense and (impact_time_rel - elapsed <= 0))
                
                if all_teams_launched and defense_finished and elapsed > (max_wait + 2):
                    break
                    
                time.sleep(0.1)
            
            if not is_defense:
                st.balloons()
            st.success("Sequence Complete!")
