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
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 移除不需要的干擾元素（如腳註、腳本）
        for tag in soup(['script', 'style', 'sup']):
            tag.decompose()

        materials = []
        
        # 策略 A：尋找所有包含「×」或「x」數字的文字行
        # 這是最暴力但也最有效的方式，能抓到隱藏在各種標籤裡的材料
        # 我們掃描所有的表格行 (tr) 和 清單項目 (li)
        potential_elements = soup.find_all(['tr', 'li', 'p'])
        
        for el in potential_elements:
            text = el.get_text(separator=" ", strip=True)
            # 正則表達式強化：匹配「名稱 × 數量」或「名稱 x 數量」
            # 支援「白钢锭 × 30」或「白钢锭×30」
            match = re.search(r'([^\s\d\x00-\x7f]+.*?)\s*[×x*]\s*(\d+)', text)
            
            if match:
                name = match.group(1).strip()
                qty = match.group(2).strip()
                
                # 過濾掉一些可能的雜訊（例如等級要求）
                if len(name) > 1 and not name.isdigit():
                    materials.append(f"{name}, {qty}, Wiki自動抓取")
        
        # 策略 B：去重（因為有些材料可能出現在不同的標籤層級中）
        seen = set()
        unique_materials = []
        for m in materials:
            if m not in seen:
                unique_materials.append(m)
                seen.add(m)
        
        if unique_materials:
            return "\n".join(unique_materials)
        else:
            return "抓取成功但未發現材料數據。請確認該頁面是否包含『名稱 × 數量』格式的文字。"
            
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
