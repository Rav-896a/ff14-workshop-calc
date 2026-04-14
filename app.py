import streamlit as st
import pandas as pd
from opencc import OpenCC
import re

# 初始化轉換器
cc = OpenCC('s2twp')

st.set_page_config(page_title="FF14 部隊工房材料計算器", layout="wide")

# 自定義 CSS
st.markdown("""
    <style>
    .stCheckbox { font-size: 1.2rem; }
    .main { background-color: #f9f9f9; }
    .st-emotion-cache-1kyx001 { padding: 1.5rem; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛠️ FF14 部隊工房材料計算器")
st.write("自動簡轉繁，並從雜亂的 Wiki 文字中提取材料。")

# 側邊欄
with st.sidebar:
    st.header("1. 專案設定")
    multiplier = st.number_input("製作數量", min_value=1, value=1)
    auto_convert = st.checkbox("自動簡轉繁", value=True)
    
    st.divider()
    st.header("2. 資料輸入")
    st.write("💡 **最強撇步**：直接去 Wiki 頁面全選(Ctrl+A)並複製，直接貼在下方框框即可！")
    raw_input = st.text_area("在此貼上 Wiki 文字內容", height=400)

# 強化的解析邏輯
def smart_parse(data, multiplier, convert):
    lines = data.strip().split('\n')
    parsed_items = []
    seen_names = set() # 避免重複抓取

    for line in lines:
        if convert:
            line = cc.convert(line)
        
        # 核心正則：匹配 [名稱] [分隔符 ×/x/*] [數字]
        # 範例：白钢锭 × 30, 钴铁铆钉 x 30
        match = re.search(r'([^\s\d\x00-\x7f]+.*?)\s*[×x*]\s*(\d+)', line)
        
        if match:
            name = match.group(1).strip()
            # 排除掉一些常見的雜訊標籤
            if any(x in name for x in ["所需等級", "物品等級", "製作條件"]):
                continue
            
            try:
                qty = int(match.group(2))
            except:
                qty = 0
                
            if name not in seen_names and qty > 0:
                # 試著從原始行抓取來源 (例如 [ ] 內的文字)
                source_match = re.search(r'\[(.*?)\]', line)
                source = source_match.group(1) if source_match else "基礎材料/製作"
                
                parsed_items.append({
                    "材料名稱": name,
                    "每件所需": qty,
                    "總共所需": qty * multiplier,
                    "來源": source
                })
                seen_names.add(name)
                
    return parsed_items

# 主畫面渲染
if raw_input:
    items = smart_parse(raw_input, multiplier, auto_convert)
    
    if items:
        df = pd.DataFrame(items)
        st.header(f"📊 材料清單 (預計製作 {multiplier} 份)")
        
        # 建立 Tab
        tab1, tab2 = st.tabs(["✅ 進度追蹤", "📋 原始數據"])
        
        with tab1:
            h1, h2, h3, h4 = st.columns([1, 4, 2, 2])
            h1.write("**完成**")
            h2.write("**材料名稱**")
            h3.write("**總共所需**")
            h4.write("**來源提示**")
            st.divider()
            
            status = []
            for idx, row in df.iterrows():
                c1, c2, c3, c4 = st.columns([1, 4, 2, 2])
                is_done = c1.checkbox("", key=f"mat_{idx}")
                
                name_display = f"**{row['材料名稱']}**" if not is_done else f"~~{row['材料名稱']}~~"
                c2.markdown(name_display)
                c3.write(f"`{row['總共所需']}`")
                
                # 來源顏色標籤
                src = row['來源']
                if "兌換" in src or "軍票" in src:
                    c4.warning(f"🎫 {src}")
                elif "採集" in src or "挖" in src:
                    c4.success(f"⛏️ {src}")
                else:
                    c4.write(src)
                status.append(is_done)
            
            if status:
                progress = sum(status) / len(status)
                st.divider()
                st.subheader(f"整體收集進度: {int(progress*100)}%")
                st.progress(progress)
                if progress == 1.0:
                    st.balloons()
        
        with tab2:
            st.dataframe(df)
    else:
        st.error("無法從貼上的文字中識別材料。請確認文字中包含『名稱 × 數量』。")
else:
    st.info("請在左側貼上 Wiki 資料以開始。您可以直接全選 Wiki 網頁並複製貼上。")
