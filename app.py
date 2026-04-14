import streamlit as st
import pandas as pd
from opencc import OpenCC

# 初始化轉換器 (s2twp 為簡體轉台灣繁體，包含慣用語轉換)
cc = OpenCC('s2twp')

# 設定頁面資訊
st.set_page_config(page_title="FF14 部隊工房材料計算器", layout="wide")

# 套用自定義 CSS (修復後的參數名稱)
st.markdown("""
    <style>
    .stCheckbox { font-size: 1.2rem; }
    .main { background-color: #f9f9f9; }
    .st-emotion-cache-1kyx001 {
        background-color: #ffffff;
        padding: 2rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🛠️ FF14 部隊工房材料計算器")
st.write("適合專案管理與進度追蹤的工匠工具。")

# 側邊欄設定
with st.sidebar:
    st.header("1. 設定與輸入")
    item_name = st.text_input("製作項目名稱", value="蛟龍級潛水艇船體")
    multiplier = st.number_input("預計製作數量", min_value=1, value=1, step=1)
    
    # 簡繁轉換開關
    auto_convert = st.checkbox("自動將簡中 Wiki 轉換為繁體", value=True)
    
    st.subheader("2. 貼上材料數據")
    st.caption("支援格式：名稱, 數量, 來源 (每行一筆)")
    raw_data = st.text_area(
        "材料清單", 
        height=350,
        placeholder="暗银锭, 30, 製作\n暗银矿, 120, 採集\n纯钛矿, 20, 航行取得"
    )
    
    st.info("💡 提示：你可以直接從灰機 Wiki 複製表格內容貼上，我會自動過濾多餘文字。")

# 核心解析邏輯
def parse_data(data, convert_to_tw):
    lines = data.strip().split('\n')
    parsed_items = []
    for line in lines:
        if line.strip():
            # 簡轉繁處理
            processed_line = cc.convert(line) if convert_to_tw else line
            
            # 解析邏輯：支援逗號、Tab 或 多格空格
            if ',' in processed_line:
                parts = [p.strip() for p in processed_line.split(',')]
            elif '\t' in processed_line:
                parts = [p.strip() for p in processed_line.split('\t')]
            else:
                parts = [p.strip() for p in processed_line.split()]
                
            if len(parts) >= 2:
                name = parts[0]
                try:
                    # 提取數字（處理如 'x30', '30個' 等狀況）
                    qty_str = "".join(filter(str.isdigit, parts[1]))
                    base_qty = int(qty_str) if qty_str else 0
                except:
                    base_qty = 0
                
                source = parts[2] if len(parts) > 2 else "基本材料"
                
                parsed_items.append({
                    "材料名稱": name,
                    "每件所需": base_qty,
                    "總共所需": base_qty * multiplier,
                    "來源": source
                })
    return parsed_items

# 主要呈現區
if raw_data:
    display_name = cc.convert(item_name) if auto_convert else item_name
    items = parse_data(raw_data, auto_convert)
    
    if items:
        df = pd.DataFrame(items)
        st.header(f"📊 {display_name} 製作清單")
        st.subheader(f"目標數量：{multiplier}")

        tab1, tab2 = st.tabs(["✅ 進度追蹤清單", "📋 完整數據表"])
        
        with tab1:
            # 表頭佈局
            h1, h2, h3, h4 = st.columns([1, 4, 2, 2])
            h1.write("**狀態**")
            h2.write("**材料名稱**")
            h3.write("**所需總量**")
            h4.write("**獲取來源**")
            st.divider()
            
            completion_status = []
            for idx, row in df.iterrows():
                c1, c2, c3, c4 = st.columns([1, 4, 2, 2])
                
                # Checkbox 狀態
                is_done = c1.checkbox("", key=f"mat_{idx}")
                
                # 名稱呈現 (完成後加刪除線)
                label = f"**{row['材料名稱']}**" if not is_done else f"~~{row['材料名稱']}~~"
                c2.markdown(label)
                
                # 數量呈現
                c3.write(f"`{row['總共所需']}`")
                
                # 來源標籤化
                src = row['來源']
                if any(k in src for k in ["軍票", "军票"]):
                    c4.warning(f"🎫 {src}")
                elif any(k in src for k in ["採集", "采集", "挖"]):
                    c4.success(f"⛏️ {src}")
                elif any(k in src for k in ["航行", "潛艇", "潜艇", "探索"]):
                    c4.info(f"🚢 {src}")
                else:
                    c4.write(src)
                
                completion_status.append(is_done)
            
            # 進度條計算
            st.divider()
            if completion_status:
                progress = sum(completion_status) / len(completion_status)
                st.write(f"### 目前收集進度：{int(progress*100)}%")
                st.progress(progress)
                if progress == 1.0:
                    st.balloons()
                    st.success("所有材料已湊齊！祝製作順利！")

        with tab2:
            st.write("可以將此表格複製到 Excel 或 Google 試算表備份。")
            st.dataframe(df, use_container_width=True)
    else:
        st.warning("無法解析資料。請確認輸入格式為「名稱 數量 來源」。")
else:
    st.info("👋 你好！請在左側貼入 Wiki 的材料資料。我會自動幫你處理簡轉繁，並計算總量。")
