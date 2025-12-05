import streamlit as st
import time
import re
import pandas as pd

# --- 設定網頁標題與圖示 ---
st.set_page_config(page_title="Rally Sync Calculator", page_icon="⚔️")

# --- 核心邏輯 (從 Bot 移植) ---
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

# --- 網頁介面 ---
st.title("⚔️ Rally Sync Calculator")
st.markdown("輸入所有隊伍的行軍時間，計算壓秒出發時機。")

# 1. 輸入區
col1, col2 = st.columns([3, 1])
with col1:
    raw_input = st.text_input("March Times (space separated)", placeholder="e.g. 45 1:30 38s")
with col2:
    target_name = st.text_input("Target Name", value="Target")

# 2. 解析資料
if raw_input:
    times_str = raw_input.replace(",", " ").split()
    parsed_data = []
    for t in times_str:
        secs = parse_seconds(t)
        if secs > 0: parsed_data.append(secs)

    if len(parsed_data) < 2:
        st.error("⚠️ At least 2 valid times are required.")
    else:
        # 計算邏輯
        max_time = max(parsed_data)
        results = []
        for t in parsed_data:
            delay = max_time - t
            results.append({"travel": t, "delay": delay})
        
        # 排序
        results.sort(key=lambda x: x['delay'])

        # --- 顯示預覽表格 ---
        st.divider()
        st.subheader(f"🎯 Plan: {target_name} (Max: {max_time}s)")

        # 準備顯示資料
        display_data = []
        copy_text_lines = [f"--- Sync Plan: {target_name} ---"]
        
        for i, res in enumerate(results):
            role = "🟢 Starter" if i == 0 else f"{i+1}️⃣ Follower"
            action = "GO NOW" if res['delay'] == 0 else f"Wait {res['delay']}s"
            
            display_data.append({
                "Role": role,
                "Travel Time": f"{res['travel']}s",
                "Delay (Wait)": f"{res['delay']}s",
                "Status": "Ready"
            })
            copy_text_lines.append(f"[{res['travel']}s Team]: {action}")

        # 顯示靜態表格
        st.table(pd.DataFrame(display_data))

        # 複製文字區
        with st.expander("📋 Copy for In-Game Chat"):
            st.code("\n".join(copy_text_lines), language="yaml")

        st.divider()
        
        # --- 實戰倒數區 ---
        st.write("### 🚀 Live Sequence")
        
        # 建立一個空的容器來放動態內容
        status_container = st.empty()
        
        if st.button("🔥 Start 5s Countdown"):
            # 1. 倒數 5 秒動畫
            for i in range(5, 0, -1):
                status_container.warning(f"## ⚠️ LAUNCH IN {i} SECONDS...")
                time.sleep(1)
            
            # 2. 正式開始 (校準時間)
            start_time = time.time()
            status_container.success("## 🚀 STARTER LAUNCH NOW!")
            
            # 3. 動態追蹤
            # 我們持續更新畫面，直到所有隊伍都出發
            max_delay = max(r['delay'] for r in results)
            
            # 建立動態顯示的 placeholder
            placeholders = []
            for i in range(len(results)):
                placeholders.append(st.empty())

            while True:
                current_elapsed = time.time() - start_time
                all_launched = True
                
                for i, res in enumerate(results):
                    delay = res['delay']
                    time_left = delay - current_elapsed
                    
                    # 顯示邏輯
                    if time_left <= 0:
                        # 時間到
                        msg = f"### ✅ Team {i+1} ({res['travel']}s): **GO NOW!**"
                        if i == 0: msg = f"### 🚀 Starter ({res['travel']}s): **LAUNCHED**"
                        placeholders[i].success(msg)
                    else:
                        # 還沒到
                        all_launched = False
                        placeholders[i].warning(f"⏳ Team {i+1} ({res['travel']}s): Wait **{time_left:.1f}s**")

                if all_launched:
                    break
                
                time.sleep(0.1) # 0.1秒刷新一次
            
            st.balloons() # 結束撒花
            st.success("All teams launched!")