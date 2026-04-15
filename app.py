import streamlit as st
import pandas as pd
from opencc import OpenCC
import re
import requests

# 初始化轉換器 (簡轉繁)
cc = OpenCC('s2twp')

st.set_page_config(page_title="FF14 部隊工房材料計算器 (深層解析版)", layout="wide")

# 自定義 CSS
st.markdown("""
    <style>
    .stCheckbox { font-size: 1.2rem; }
    .main { background-color: #f9f9f9; }
    .st-emotion-cache-1kyx001 { padding: 1.5rem; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛠️ FF14 部隊工房材料計算器")
st.write("自動簡轉繁、API 抓取、並支援半成品遞迴展開。")

# --- 核心邏輯：API 抓取 ---
def fetch_wiki_raw(item_name):
    """透過 MediaWiki API 抓取原始文字"""
    api_url = "https://ff14.huijiwiki.com/api.php"
    params = {
        "action": "parse",
        "page": f"物品:{item_name}",
        "format": "json",
        "prop": "wikitext",
        "redirects": 1
    }
    try:
        response = requests.get(api_url, params=params, timeout=10)
        data = response.json()
        if "parse" in data:
            return data["parse"]["wikitext"]["*"]
        return None
    except:
        return None

def parse_material_lines(text):
    """從 Wikitext 或貼上的文字中提取名稱與數量"""
    results = []
    lines = text.strip().split('\n')
    for line in lines:
        # 匹配：[名稱] × [數字]
        match = re.search(r'([^\s\d\x00-\x7f]+.*?)\s*[×x*]\s*(\d+)', line)
        if match:
            name = match.group(1).strip()
            qty = int(match.group(2))
            # 排除雜訊
            if any(x in name for x in ["所需等級", "物品等級", "製作條件"]):
                continue
            results.append({"name": name, "qty": qty})
    return results

# --- 核心邏輯：遞迴解析引擎 ---
def recursive_solve(item_name, target_qty, depth=0, max_depth=2):
    """遞迴展開材料，如果 depth > 0 代表它是二級材料"""
    # 這裡可以定義哪些後綴需要展開 (例如：錠、板、鉚釘)
    expand_keywords = ["锭", "板", "铆钉", "连接板", "钢", "金锭", "胶", "纸"]
    
    # 基礎清單
    raw_text = fetch_wiki_raw(item_name)
    if not raw_text:
        return [{"name": item_name, "total": target_qty, "source": "直接獲取"}]
    
    first_level = parse_material_lines(raw_text)
    if not first_level: # 如果該頁面沒材料，代表它是原始材料
        return [{"name": item_name, "total": target_qty, "source": "原始材料"}]
    
    final_list = []
    for item in first_level:
        name = item['name']
        needed_qty = item['qty'] * target_qty
        
        # 判斷是否需要再往下挖 (且不超過最大深度，避免無限循環)
        if any(k in name for k in expand_keywords) and depth < max_depth:
            sub_items = recursive_solve(name, needed_qty, depth + 1, max_depth)
            final_list.extend(sub_items)
        else:
            final_list.append({"name": name, "total": needed_qty, "source": "基礎材料"})
            
    return final_list

# --- 側邊欄 ---
with st.sidebar:
    st.header("1. 專案設定")
    multiplier = st.number_input("製作數量", min_value=1, value=1)
    auto_convert = st.checkbox("自動簡轉繁", value=True)
    
    st.divider()
    st.header("2. 自動抓取模式")
    target_item = st.text_input("輸入 Wiki 物品名稱", placeholder="例如：甲鱟級船首")
    fetch_btn = st.button("從 Wiki 抓取並展開")
    
    st.divider()
    st.header("3. 手動輸入模式")
    st.write("💡 備案：直接貼上 Wiki 文字內容")
    manual_input = st.text_area("在此貼上 Wiki 文字", height=200)

# --- 資料處理 ---
items_to_show = []

# 處理自動抓取
if fetch_btn and target_item:
    with st.spinner(f"正在分析 {target_item} 的材料樹..."):
        # 這裡啟動遞迴解析
        results = recursive_solve(target_item, multiplier)
        # 彙整相同名稱的材料
        summary = {}
        for r in results:
            name = cc.convert(r['name']) if auto_convert else r['name']
            summary[name] = summary.get(name, 0) + r['total']
        
        for name, total in summary.items():
            items_to_show.append({"材料名稱": name, "總共所需": total, "來源": "API 自動展開"})

# 處理手動輸入 (若沒有自動抓取的結果)
elif manual_input and not items_to_show:
    lines = manual_input.strip().split('\n')
    for line in lines:
        if auto_convert: line = cc.convert(line)
        match = re.search(r'([^\s\d\x00-\x7f]+.*?)\s*[×x*]\s*(\d+)', line)
        if match:
            items_to_show.append({
                "材料名稱": match.group(1).strip(),
                "總共所需": int(match.group(2)) * multiplier,
                "來源": "手動貼上"
            })

# --- 主要畫面渲染 ---
if items_to_show:
    df = pd.DataFrame(items_to_show)
    st.header(f"📊 材料清單 (包含半成品展開)")
    
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
            c4.write(row['來源'])
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
    st.info("請在左側輸入物品名稱並點擊『抓取』，或手動貼上資料。")
