import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from opencc import OpenCC
import re

# 初始化轉換器
cc = OpenCC('s2twp')

st.set_page_config(page_title="FF14 部隊工房自動計算器", layout="wide")

st.markdown("""
    <style>
    .stCheckbox { font-size: 1.2rem; }
    .main { background-color: #f9f9f9; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛠️ FF14 部隊工房材料計算器 (自動抓取版)")

# --- 側邊欄設定 ---
with st.sidebar:
    st.header("1. 專案設定")
    multiplier = st.number_input("預計製作數量", min_value=1, value=1, step=1)
    auto_convert = st.checkbox("自動簡轉繁", value=True)
    
    st.divider()
    st.header("2. 數據來源")
    data_mode = st.radio("選擇輸入方式", ["自動抓取網址", "手動貼上數據"])

# --- 核心邏輯：爬蟲功能 ---
def scrape_huiji_wiki(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 移除干擾元素
        for tag in soup(['script', 'style', 'sup']):
            tag.decompose()

        materials = []
        
        # 策略一：針對灰機 Wiki 物品頁面最核心的材料區塊
        # 通常位於 class 包含 'xiv-item-sources' 或 'xiv-item-recipe' 的區塊
        source_sections = soup.find_all('div', class_=re.compile(r'xiv-item-sources|xiv-item-recipe'))
        
        if not source_sections:
            # 如果找不到特定區塊，就掃描整個內容區 (mw-content-text 是 Wiki 標準內容區)
            source_sections = [soup.find('div', class_='mw-parser-output')]

        for section in source_sections:
            if not section: continue
            
            # 尋找所有文字行，特別是包含「×」的
            lines = section.get_text(separator="\n").split('\n')
            for line in lines:
                line = line.strip()
                # 匹配：[物品名稱] × [數量] (例如：白钢锭 × 30)
                # 正則說明：([^\s\d]+.*?) 匹配非數字開頭的名稱，\s*[×x]\s* 匹配乘號，(\d+) 匹配數量
                match = re.search(r'([^\s\d\x00-\x7f]+.*?)\s*[×x]\s*(\d+)', line)
                if match:
                    name = match.group(1).strip()
                    qty = match.group(2).strip()
                    # 嘗試在同一行找來源資訊，通常在括號內 [ ]
                    source_match = re.search(r'\[(.*?)\]', line)
                    source = source_match.group(1) if source_match else "製作/兌換"
                    
                    materials.append(f"{name}, {qty}, {source}")

        # 策略二：去重並過濾
        unique_materials = []
        seen = set()
        for m in materials:
            if m not in seen:
                # 過濾掉一些明顯不是材料的抓取結果（例如等級限制）
                name_part = m.split(',')[0]
                if "级" not in name_part[-1:] and "★" not in name_part:
                    unique_materials.append(m)
                    seen.add(m)

        if unique_materials:
            return "\n".join(unique_materials)
        else:
            return "抓取成功但未解析到材料。建議將 Wiki 頁面的『材料』區域手動全選複製，直接貼到『手動貼上』區塊，App 一樣能識別。"
            
    except Exception as e:
        return f"連線錯誤: {str(e)}"
        
# --- 核心邏輯：解析與呈現 ---
def parse_data(data, convert_to_tw):
    lines = data.strip().split('\n')
    parsed_items = []
    for line in lines:
        if line.strip():
            processed_line = cc.convert(line) if convert_to_tw else line
            parts = [p.strip() for p in re.split(r'[,，\t\s]+', processed_line)]
            if len(parts) >= 2:
                name = parts[0]
                qty_str = "".join(filter(str.isdigit, parts[1]))
                base_qty = int(qty_str) if qty_str else 0
                source = parts[2] if len(parts) > 2 else "基本材料"
                parsed_items.append({"材料名稱": name, "總共所需": base_qty * multiplier, "來源": source})
    return parsed_items

# --- 主畫面 UI ---
final_raw_data = ""

if data_mode == "自動抓取網址":
    wiki_url = st.text_input("輸入灰機 Wiki 網址 (例如零件頁面)", placeholder="https://ff14.huijiwiki.com/wiki/Item:蛟龙级潜艇船体")
    if st.button("開始抓取"):
        with st.spinner('正在讀取 Wiki 數據...'):
            scraped_result = scrape_huiji_wiki(wiki_url)
            st.session_state['scraped_data'] = scraped_result
    
    if 'scraped_data' in st.session_state:
        final_raw_data = st.text_area("抓取結果 (可手動微調)", value=st.session_state['scraped_data'], height=200)

else:
    final_raw_data = st.text_area("手動貼上數據", height=300, placeholder="名稱, 數量, 來源")

# --- 渲染清單 ---
if final_raw_data:
    items = parse_data(final_raw_data, auto_convert)
    if items:
        df = pd.DataFrame(items)
        st.header("📊 材料進度追蹤")
        
        tab1, tab2 = st.tabs(["✅ 收集清單", "📋 數據預覽"])
        with tab1:
            completion_status = []
            for idx, row in df.iterrows():
                c1, c2, c3, c4 = st.columns([1, 4, 2, 2])
                is_done = c1.checkbox("", key=f"m_{idx}")
                label = f"**{row['材料名稱']}**" if not is_done else f"~~{row['材料名稱']}~~"
                c2.markdown(label)
                c3.write(f"`{row['總共所需']}`")
                
                src = row['來源']
                if any(k in src for k in ["軍票", "兌換"]): c4.warning(f"🎫 {src}")
                elif any(k in src for k in ["採集", "挖"]): c4.success(f"⛏️ {src}")
                else: c4.write(src)
                completion_status.append(is_done)
            
            if completion_status:
                progress = sum(completion_status) / len(completion_status)
                st.progress(progress)
                st.write(f"進度: {int(progress*100)}%")
    else:
        st.info("請輸入有效數據或嘗試抓取。")
