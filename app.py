import streamlit as st
import time
import re
import pandas as pd
import requests
import os

# --- Configuration ---
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

# --- Google Sheet Connection ---
def load_roster():
    try:
        if "YOUR_ID_HERE" in GAS_URL:
            st.error("⚠️ Please fill in the correct GAS_URL in the code.")
            return {}
        response = requests.get(GAS_URL)
        if response.status_code == 200:
            return response.json()
        return {}
    except Exception as e:
        st.error(f"Connection failed: {e}")
        return {}

def update_player_in_sheet(name, seconds):
    try:
        requests.post(GAS_URL, json={"action": "upsert", "name": name, "time": seconds})
    except Exception as e:
        st.error(f"Save failed: {e}")

def delete_player_from_sheet(name):
    try:
        requests.post(GAS_URL, json={"action": "delete", "name": name})
    except Exception as e:
        st.error(f"Delete failed: {e}")

if 'roster' not in st.session_state:
    with st.spinner('Loading roster...'):
        st.session_state.roster = load_roster()

# Initialize Assignment Memory
if 'saved_assignments' not in st.session_state:
    st.session_state.saved_assignments = {}

# --- Utility Functions ---
def parse_seconds(time_str: str) -> int:
    time_str = str(time_str).lower().strip()
    if time_str.isdigit(): 
        return int(time_str)
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

# --- Sidebar ---
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

# --- Main Interface ---
st.title("⚔️ War Sync Calculator")

# Mode Selection
col_mode1, col_mode2, col_mode3 = st.columns([1, 1, 1])
with col_mode1:
    mode = st.radio("", ["⚔️ Attack / Rally", "🛡️ Defense / Garrison"], horizontal=True)
    is_defense = "Defense" in mode
with col_mode2:
    is_multi = st.toggle("🔥 Multi-Rally Mode", value=False)
with col_mode3:
    limit_per_target = st.number_input("Max Players per Target", min_value=1, value=6, step=1)

st.divider()

# --- Data Prep ---
roster_data = [{"name": n, "time": t} for n, t in st.session_state.roster.items()]
# Sort by Time Descending (Slowest first)
roster_data.sort(key=lambda x: x['time'], reverse=True) 
all_player_names = [p['name'] for p in roster_data]

# --- Input Handling ---
targets_list = []

if is_multi:
    c_info, c_reset = st.columns([4, 1])
    with c_info:
        st.info(f"💡 **Dynamic Mode:** Adding rows won't reset existing assignments. Time format: '1:30' or '90'.")
    with c_reset:
        if st.button("🔄 Reset All"):
            st.session_state.saved_assignments = {}
            st.rerun()

    if 'multi_target_df' not in st.session_state:
        st.session_state.multi_target_df = pd.DataFrame(
            [{"Target Name": "Rally A", "March (s)": 30, "Rally (m:s)": "300"}] 
        )

    edited_df = st.data_editor(
        st.session_state.multi_target_df, 
        num_rows="dynamic", 
        use_container_width=True,
        column_config={
            "Target Name": st.column_config.TextColumn("Target Name", help="Unique Name Required", required=True),
            "March (s)": st.column_config.NumberColumn("March (s)", min_value=0, step=1, required=True),
            "Rally (m:s)": st.column_config.TextColumn("Rally (m:s)", help="e.g. '5:00' or '300'", required=True),
        }
    )
    
    for index, row in edited_df.iterrows():
        if row["Target Name"]:
            targets_list.append({
                "name": row["Target Name"],
                "enemy_march": int(row["March (s)"]),
                "enemy_rally": str(row["Rally (m:s)"])
            })

else:
    c1, c2 = st.columns([2, 1])
    with c1:
        st.markdown("### Participants")
    with c2:
        st.markdown("### Target")
        if is_defense:
            e_march = st.number_input("Enemy March (s)", 0, step=1)
            e_rally = st.text_input("Countdown (m:s or s)", "0:00")
            t_name = "Defense"
            st.caption("ℹ️ Auto +1s Buffer (Target = Enemy + 1s)")
        else:
            e_march = 0
            e_rally = "0:00"
            t_name = st.text_input("Target Name", "Target")
        
        targets_list.append({
            "name": t_name,
            "enemy_march": e_march,
            "enemy_rally": e_rally
        })

# --- Assignment Logic (Strict Exclusion) ---
master_results = []

if not is_multi:
    with c1:
        default_sel = all_player_names[:limit_per_target]
        selected = st.multiselect("Select Players", all_player_names, default=default_sel)
        manual_add = st.text_input("Manual Add (Optional)", placeholder="e.g. 45 1:30")
        
    current_pool = [p for p in roster_data if p['name'] in selected]
    if manual_add:
        for i, t_str in enumerate(manual_add.replace(",", " ").split()):
            s = parse_seconds(t_str)
            if s > 0: current_pool.append({"name": f"Manual-{i+1}", "time": s})
    targets_list[0]['assigned_pool'] = current_pool

else:
    st.markdown(f"### 👮 Assign Players (Max {limit_per_target} per Target)")
    cols = st.columns(len(targets_list)) if len(targets_list) > 0 else [st.container()]
    
    # [Fix] Clean up saved_assignments for deleted targets
    current_target_names = [t['name'] for t in targets_list]
    keys_to_remove = [k for k in st.session_state.saved_assignments if k not in current_target_names]
    for k in keys_to_remove:
        del st.session_state.saved_assignments[k]

    # Iterate targets
    for i, target in enumerate(targets_list):
        t_name = target['name']
        with cols[i % len(cols)]: 
            st.markdown(f"**Target: {t_name}**")
            
            # --- Step 1: Identify who is busy in OTHER targets ---
            busy_players = set()
            for other_name, assigned_list in st.session_state.saved_assignments.items():
                if other_name != t_name: # Don't count self
                    busy_players.update(assigned_list)
            
            # --- Step 2: Determine Available Options for THIS target ---
            # Available = All players NOT busy elsewhere
            available_options = [p for p in all_player_names if p not in busy_players]
            
            # --- Step 3: Determine Default Selection ---
            if t_name in st.session_state.saved_assignments:
                # If memory exists, use memory (filtered by availability logic just in case)
                saved_list = st.session_state.saved_assignments[t_name]
                # Ensure saved players are still valid (not busy elsewhere due to conflict)
                # Note: We prioritize the current target's memory, but user can change it
                default_picks = [p for p in saved_list if p in all_player_names]
            else:
                # If new, Waterfall from available
                default_picks = available_options[:limit_per_target]

            # --- Step 4: Render ---
            # options MUST include default_picks to avoid Streamlit error
            # Ideally, default_picks are a subset of available_options. 
            # If a player is in default_picks but also in busy_players (conflict), 
            # we should technically remove them or flag them. Here we prioritize availability.
            
            final_options = available_options
            
            # Sanity check: Ensure defaults are in options
            # If a player was saved here, but is now selected in another box (rare race condition),
            # they might not be in available_options. We let the UI handle valid flow.
            safe_defaults = [p for p in default_picks if p in final_options]

            selected_for_target = st.multiselect(
                f"Pick for {t_name}", 
                options=final_options, # <--- Only show available players!
                default=safe_defaults, 
                key=f"multi_select_{i}_{t_name}"
            )
            
            # Save to state
            st.session_state.saved_assignments[t_name] = selected_for_target
            
            pool = [p for p in roster_data if p['name'] in selected_for_target]
            target['assigned_pool'] = pool


# --- Calculation Loop ---
st.write("---")

display_sections = [] 

for target in targets_list:
    pool = target.get('assigned_pool', [])
    if not pool: continue

    starter = max(pool, key=lambda x: x['time']) 
    max_time = starter['time']
    
    if is_defense:
        e_sec = parse_seconds(target['enemy_rally'])
        impact_time = e_sec + target['enemy_march'] + 1
        if impact_time == 1: impact_time = max_time 
        mode_title = f"🛡️ {target['name']} (Impact: {impact_time}s)"
    else:
        impact_time = max_time
        mode_title = f"⚔️ {target['name']} (Max: {max_time}s)"

    target_results = []
    copy_lines = [f"--- Plan: {target['name']} ---"]
    
    pool.sort(key=lambda x: x['time'], reverse=True)
    
    for i, p in enumerate(pool):
        wait = impact_time - p['time']
        is_late = is_defense and wait < 0
        if is_late: continue
        
        if wait == 0: 
            action = "SEND"
            send_str = "T + 0s (NOW)"
        else: 
            action = f"Wait {wait}s"
            send_str = f"T + {wait}s"
        
        res_obj = {
            "target": target['name'],
            "name": p['name'],
            "travel": p['time'],
            "wait": wait,
            "send_str": send_str,
            "action": action,
            "role": "Starter" if i==0 else "Follower",
            "impact_time": impact_time,
            "enemy_rally_sec": parse_seconds(target['enemy_rally']),
            "enemy_march": target['enemy_march']
        }
        target_results.append(res_obj)
        master_results.extend(target_results) 
        copy_lines.append(f"[{p['name']}]: {action}")

    if target_results:
        target_results.sort(key=lambda x: x['wait'])
        df_disp = pd.DataFrame([{
            "Role": r['role'], 
            "Player": r['name'], 
            "Travel": f"{r['travel']}s", 
            "🚀 Send @": r['send_str'],
            "Action": r['action']
        } for r in target_results])
        
        display_sections.append({
            "title": mode_title,
            "df": df_disp,
            "copy_text": "\n".join(copy_lines)
        })

if display_sections:
    st.subheader("📋 Strategy Plans")
    for section in display_sections:
        with st.container(border=True):
            st.markdown(f"#### {section['title']}")
            c_table, c_copy = st.columns([3, 1])
            with c_table:
                st.dataframe(section['df'], hide_index=True, use_container_width=True)
            with c_copy:
                st.text_area(f"Copy", section['copy_text'], height=150, key=f"copy_{section['title']}")
else:
    st.warning("⚠️ No valid plans generated. Check players or times.")


# --- Live Dashboard (Independent Blocks) ---
st.divider()
st.write("### ⏱️ Master Live Sequence")

if st.button("🚀 Start Sequence (All Targets)", type="primary", use_container_width=True):
    start_ts = time.time()
    
    max_wait_total = 0
    if master_results:
        max_wait_total = max([r['wait'] for r in master_results])
    
    spotlight_ph = st.empty()
    target_placeholders = {}
    
    st.caption("Monitoring active targets...")
    
    unique_target_names = list(set([r['target'] for r in master_results]))
    
    for t_name in unique_target_names:
        with st.container(border=True):
            st.markdown(f"#### 📡 Live: {t_name}")
            target_placeholders[t_name] = st.empty()

    while True:
        elapsed = time.time() - start_ts
        
        next_event_time_global = 9999
        next_event_text_global = "✅ All Clear"
        all_sent_global = True
        
        for t_name in unique_target_names:
            t_results = [r for r in master_results if r['target'] == t_name]
            live_rows = []
            
            if is_defense and t_results:
                imp = t_results[0]['impact_time']
                left = imp - elapsed
                status = "💥 IMPACT" if left <= 0 else f"⚔️ {left:.1f}s"
                live_rows.append({"Player": "🔴 ENEMY", "Status": status, "SortKey": left})

            for res in t_results:
                time_left = res['wait'] - elapsed
                p_label = f"{res['name']} ({res['travel']}s)"
                
                if time_left <= 0:
                    status = "✅ SENT"
                    sort_key = -999 
                else:
                    all_sent_global = False
                    status = f"⏳ {time_left:.1f}s"
                    sort_key = time_left
                    
                    if time_left < next_event_time_global:
                        next_event_time_global = time_left
                        next_event_text_global = f"🚀 {res['name']} \n➜ {res['target']}\nin {time_left:.1f}s"

                live_rows.append({
                    "Player": p_label, 
                    "Status": status, 
                    "SortKey": sort_key
                })
            
            live_rows.sort(key=lambda x: x['SortKey'])
            df_live = pd.DataFrame(live_rows).drop(columns=["SortKey"])
            target_placeholders[t_name].dataframe(df_live, use_container_width=True, hide_index=True)

        if all_sent_global:
            spotlight_ph.success("## ✅ All Targets Complete")
        elif next_event_time_global < 3:
            spotlight_ph.error(f"## {next_event_text_global}")
        else:
            spotlight_ph.info(f"## {next_event_text_global}")

        if all_sent_global and elapsed > (max_wait_total + 5):
            break
            
        time.sleep(0.1)
    
    st.success("All sequences finished.")
