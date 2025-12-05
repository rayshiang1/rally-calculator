import streamlit as st
import time
import re
import pandas as pd

# --- 設定頁面 ---
st.set_page_config(page_title="War Sync Calc", page_icon="🛡️", layout="centered")

# --- CSS 優化 (隱藏預設選單，讓畫面更乾淨) ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- 核心邏輯 ---
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

# --- 標題區 ---
st.title("⚔️ War Sync Calculator")
mode = st.radio("", ["⚔️ Attack / Rally (集結進攻)", "🛡️ Defense / Garrison (壓秒駐防)"], horizontal=True)
is_defense = "Defense" in mode

# --- 輸入區 ---
col1, col2 = st.columns([2, 1])
with col1:
    raw_input = st.text_input("March Times (Space separated)", placeholder="e.g. 45 1:30 38s")
with col2:
    if is_defense:
        landing_time = st.number_input("Enemy Landing (sec)", min_value=0, value=60, step=1)
    else:
        target_name = st.text_input("Target Name", value="Target")

st.divider()

# --- 計算邏輯 ---
if raw_input:
    # 1. 資料解析
    times_str = raw_input.replace(",", " ").split()
    parsed_data = []
    for t in times_str:
        secs = parse_seconds(t)
        if secs > 0: parsed_data.append(secs)

    if len(parsed_data) < 1:
        st.error("⚠️ Please enter valid march times.")
    else:
        # 2. 計算結果
        max_time = max(parsed_data)
        results = []

        if is_defense:
            # --- 防守模式邏輯 ---
            # 基準點是敵軍抵達時間 (landing_time)
            # 如果 landing_time = 0，則視為單純同步 (max_time 為基準)
            impact_time = landing_time if landing_time > 0 else max_time
            
            for t in parsed_data:
                # 需等待時間 = 敵軍剩餘時間 - 我的行軍時間
                wait = impact_time - t
                
                if wait < 0:
                    status = "💀 TOO LATE"
                    action = "SKIP"
                    color = "🔴" # Red circle
                elif wait == 0:
                    status = "🚀 GO NOW"
                    action = "SEND"
                    color = "🟢" # Green circle
                else:
                    status = f"⏳ Wait {wait}s"
                    action = f"Wait {wait}s"
                    color = "🟡" # Yellow circle
                
                results.append({
                    "Color": color,
                    "March Time": f"{t}s",
                    "Status": status,
                    "Action": action,
                    "_wait_sort": wait
                })
            
            # 防守模式依「等待時間」排序，來不及的放最後或最前看需求，這裡把能走的放前面
            results.sort(key=lambda x: x['_wait_sort'], reverse=True)

        else:
            # --- 進攻模式邏輯 ---
            # 基準點是行軍最久的那個人 (max_time)
            for t in parsed_data:
                delay = max_time - t
                results.append({
                    "March Time": f"{t}s",
                    "Wait Time": f"{delay}s",
                    "Action": "GO NOW" if delay == 0 else f"Wait {delay}s",
                    "_delay_sort": delay
                })
            # 進攻模式依「延遲時間」排序，Starter (0s) 在最前
            results.sort(key=lambda x: x['_delay_sort'])

        # --- 3. 顯示結果 (UI 優化) ---
        
        # 製作 DataFrame 供顯示
        df_display = pd.DataFrame(results)
        
        # 移除排序用的隱藏欄位
        cols_to_drop = [c for c in df_display.columns if c.startswith('_')]
        df_display = df_display.drop(columns=cols_to_drop)

        # 顯示表格
        st.subheader("📋 Plan Details")
        
        if is_defense:
            # 防守模式：使用更醒目的 Metric 顯示
            # 為了手機好讀，我們直接用 markdown 列表
            for row in results:
                icon = row['Color']
                msg = f"**{row['Action']}** (March: {row['March Time']})"
                if "LATE" in row['Status']:
                    st.error(f"{icon} {msg} - Too slow to reinforce!")
                elif "GO" in row['Status']:
                    st.success(f"{icon} {msg} - Send Immediately!")
                else:
                    st.info(f"{icon} {msg} - Prepare to send")
        else:
            # 進攻模式：顯示表格
            st.table(df_display)
            
            # 複製文字區
            copy_lines = [f"--- Attack Plan ---"]
            for res in results:
                copy_lines.append(f"[{res['March Time']} Team]: {res['Action']}")
            
            with st.expander("📋 Copy for In-Game Chat"):
                st.code("\n".join(copy_lines), language="yaml")

        # --- 4. 倒數計時器 (只在進攻模式顯示) ---
        if not is_defense:
            st.divider()
            st.write("### ⏱️ Sync Countdown")
            
            if st.button("🔥 Start 5s Countdown", type="primary", use_container_width=True):
                placeholder = st.empty()
                
                # 倒數動畫
                for i in range(5, 0, -1):
                    placeholder.warning(f"# ⚠️ LAUNCH IN {i}...")
                    time.sleep(1)
                
                placeholder.success("# 🚀 STARTER GO NOW!")
                
                # 開始追蹤 (進攻模式特有)
                start_ts = time.time()
                max_wait = max([r['_delay_sort'] for r in results])
                
                status_ph = st.empty()
                
                while True:
                    elapsed = time.time() - start_ts
                    current_status = []
                    all_done = True
                    
                    for i, res in enumerate(results):
                        delay = res['_delay_sort']
                        time_left = delay - elapsed
                        
                        role_name = f"Team {i+1} ({res['March Time']})"
                        
                        if time_left <= 0:
                            current_status.append({"Role": role_name, "Status": "✅ GO!"})
                        else:
                            all_done = False
                            current_status.append({"Role": role_name, "Status": f"⏳ {time_left:.1f}s"})
                    
                    status_ph.table(pd.DataFrame(current_status))
                    
                    if all_done and elapsed > (max_wait + 2):
                        break
                    time.sleep(0.1)
                
                st.success("All teams launched!")
