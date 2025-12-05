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

# [New] Initialize Assignment Memory
if 'saved_assignments' not in st.session_state:
    st.session_state.saved_assignments = {}

# --- Utility Functions ---
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
        st.info(f"💡 **Dynamic Mode:** Adding rows won't reset existing assignments. Waterfall fills new targets.")
    with c_reset:
        if st.button("🔄 Reset All Allocations"):
            st.session_state.saved_assignments = {}
            st.rerun()

    # Initialize Table
    if 'multi_target_df' not in st.session_state:
        st.session_state.multi_target_df = pd.DataFrame(
            [{"Target Name": "Rally A", "March (s)": 30, "Rally (m:s)": "5:00"}]
        )

    edited_df = st.data_editor(
        st.session_state.multi_target_df, 
        num_rows="dynamic", 
        use_container_width=True,
        column_config={
            "Target Name": st.column_config.TextColumn("Target Name", help="Unique Name Required", required=True),
            "March (s)": st.column_config.NumberColumn("March (s)", min_value=0, step=1, required=True),
            "Rally (m:s)": st.column_config.TextColumn("Rally (m:s)", required=True),
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
    # Single Mode UI
    c1, c2 = st.columns([2, 1])
    with c1:
        st.markdown("### Participants")
    with c2
