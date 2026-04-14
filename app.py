import streamlit as st
import pandas as pd
from opencc import OpenCC

# 初始化轉換器 (s2twp 是簡體轉台灣繁體，包含慣用語轉換)
cc = OpenCC('s2twp')

st.set_page_config(page_title="FF14 部隊工房材料計算器", layout="wide")

# 加入一點點 CSS 讓介面更精緻
st.markdown("""
    <style>
    .main { background-color: #f5f5f5; }
    .stCheckbox { font-size: 1.2rem; }
    </style>
    """, unsafe_allow_view_ba=True)

st.title("🛠️ FF14 部隊工房材料計算器")

with st.sidebar:
    st.header("1. 設定與輸入")
    item_name = st.text_input("製作項目名稱", value="蛟龍級潛水艇船體")
    multiplier = st.number_input("製作數量", min_value=1, value=1, step=1)
    
    # 簡繁轉換開關
    auto_convert = st.checkbox("自動將簡體轉換為繁體", value=True)
    
    st.subheader("貼上 Wiki 資料")
    st.caption("格式：名稱, 數量, 來源 (每行一筆)")
    raw_data = st.text_area(
        "材料清單 (可直接貼上簡中 Wiki 內容)", 
        height=300,
        placeholder="暗银锭, 30, 制作\n暗银矿, 120, 采集"
    )

def parse_data(data, convert_to_tw):
    lines = data.strip().split('\n')
    parsed_items = []
    for line in lines:
        if line.strip():
            # 如果開啟自動轉換，先處理字體
            processed_line = cc.convert(line) if convert_to_tw else line
            
            # 解析逗號或空格分隔的資料
            if ',' in processed_line:
                parts = [p.strip() for p in processed_line.split(',')]
            else:
                # 支援空格分隔
                parts = [p.strip() for p in processed_line.split()]
                
            if len(parts) >= 2:
                name = parts[0]
                try:
                    # 濾掉數字中的非數字字元 (例如 'x30' 轉成 '30')
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

if raw_data:
    # 如果標題也需要轉換
    display_name = cc.convert(item_name) if auto_convert else item_name
    items = parse_data(raw_data, auto_convert)
    
    if items:
        df = pd.DataFrame(items)
        st.header(f"📊 {display_name} - 材料清單 (預計製作: {multiplier} 件)")
        
        tab1, tab2 = st.tabs(["✅ 進度追蹤清單", "📋 原始數據預覽"])
        
        with tab1:
            # 建立表頭
            h1, h2, h3, h4 = st.columns([1, 4, 2, 2])
            h1.write("**完成**")
            h2.write("**材料名稱**")
            h3.write("**總共所需**")
            h4.write("**來源**")
            st.divider()
            
            completion_status = []
            for idx, row in df.iterrows():
                c1, c2, c3, c4 = st.columns([1, 4, 2, 2])
                # 使用 key 確保狀態會被儲存
                is_done = c1.checkbox("", key=f"check_{idx}")
                
                # 這裡可以針對特定關鍵字加粗或變色
                material_text = f"**{row['材料名稱']}**" if not is_done else f"~~{row['材料名稱']}~~"
                c2.markdown(material_text)
                c3.write(f"{row['總共所需']}")
                
                # 來源顏色標記
                src = row['來源']
                if "軍票" in src or "军票" in src:
                    c4.warning(f"🎫 {src}")
                elif "採集" in src or "采集" in src:
                    c4.success(f"⛏️ {src}")
                elif "航行" in src or "潜艇" in src:
                    c4.info(f"🚢 {src}")
                else:
                    c4.write(src)
                
                completion_status.append(is_done)
            
            # 進度條
            st.divider()
            progress = sum(completion_status) / len(completion_status)
            st.subheader(f"目前收集進度：{int(progress*100)}%")
            st.progress(progress)
            
        with tab2:
            st.table(df)
    else:
        st.error("解析失敗，請確認資料格式。")
else:
    st.info("💡 提示：你可以直接從灰機 Wiki 或其他簡中網站複製清單貼上，我會幫你轉成繁體。")
