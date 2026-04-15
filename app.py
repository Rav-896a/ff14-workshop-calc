import streamlit as st
import pandas as pd
import requests
import re
from opencc import OpenCC

# 初始化轉換器
cc = OpenCC('s2twp')

st.set_page_config(page_title="FF14 部隊工房專業計算器", layout="wide")

st.markdown("""
    <style>
    .stCheckbox { font-size: 1.1rem; }
    .main { background-color: #f8f9fa; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛠️ FF14 部隊工房材料計算器 (XIVAPI 聯動版)")
st.write("輸入零件名稱，系統會自動透過 Wiki 抓取第一層清單，並利用 XIVAPI 拆解半成品。")

# --- 核心邏輯：XIVAPI 查詢 ---
def get_recipe_from_xivapi(item_name_cn):
    """透過 XIVAPI 查詢半成品的製作配方"""
    try:
        # 1. 搜尋物品
        search_url = "https://xivapi.com/search"
        params = {"string": item_name_cn, "indexes": "Item", "language": "cn"}
        res = requests.get(search_url, params=params, timeout=5).json()
        
        if not res.get("Results"): return None
        item_id = res["Results"][0]["ID"]
        
        # 2. 獲取物品詳情與配方
        item_url = f"https://xivapi.com/Item/{item_id}"
        detail = requests.get(item_url, timeout=5).json()
        
        # 檢查是否有配方
        recipe = detail.get("Recipe")
        if not recipe: return None
        
        ingredients = []
        # XIVAPI 的配方結構中，材料通常在 ItemIngredient0...7
        for i in range(10):
            ing_item = recipe.get(f"ItemIngredient{i}")
            amount = recipe.get(f"AmountIngredient{i}")
            if ing_item and amount > 0:
                ingredients.append({
                    "name": ing_item.get("Name_cn") or ing_item.get("Name"),
                    "qty": int(amount)
                })
        return ingredients
    except:
        return None

# --- 核心邏輯：Wiki API 抓取第一層 ---
def fetch_wiki_first_layer(item_name):
    api_url = "https://ff14.huijiwiki.com/api.php"
    params = {"action": "parse", "page": f"物品:{item_name}", "format": "json", "prop": "wikitext", "redirects": 1}
    try:
        res = requests.get(api_url, params=params, timeout=10).json()
        if "parse" in data := res:
            wikitext = data["parse"]["wikitext"]["*"]
            return wikitext
        return None
    except:
        return None

# --- 遞迴計算引擎 ---
def recursive_calculator(item_name, target_qty, expand_depth=0):
    # 定義需要被展開的後綴 (半成品關鍵字)
    expand_keywords = ["锭", "板", "铆钉", "连接板", "钢", "金锭", "胶", "纸"]
    
    # 如果是第一層 (大件零件)，去 Wiki 抓
    if expand_depth == 0:
        raw_text = fetch_wiki_first_layer(item_name)
        if not raw_text: return []
        
        # 解析 Wiki 中的 材料 x 數量
        first_level = []
        lines = raw_text.split('\n')
        for line in lines:
            match = re.search(r'([^\s\d\x00-\x7f]+.*?)\s*[×x*]\s*(\d+)', line)
            if match:
                first_level.append({"name": match.group(1).strip(), "qty": int(match.group(2))})
    else:
        # 如果是深層展開，去 XIVAPI 抓配方
        ingredients = get_recipe_from_xivapi(item_name)
        if ingredients:
            first_level = ingredients
        else:
            # 沒配方了，代表是原始材料
            return [{"name": item_name, "total": target_qty, "type": "原始材料"}]

    final_results = []
    for item in first_level:
        name = item['name']
        total_needed = item['qty'] * target_qty
        
        # 判斷是否繼續展開 (限制深度避免死循環)
        if any(k in name for k in expand_keywords) and expand_depth < 2:
            sub_results = recursive_calculator(name, total_needed, expand_depth + 1)
            final_results.extend(sub_results)
        else:
            final_results.append({"name": name, "total": total_needed, "type": "基礎/採集"})
            
    return final_results

# --- UI 介面 ---
with st.sidebar:
    st.header("⚙️ 核心設定")
    multiplier = st.number_input("製作數量", min_value=1, value=1)
    auto_convert = st.checkbox("自動繁體化", value=True)
    st.divider()
    target_item = st.text_input("輸入部隊零件名稱", value="甲鱟級船首")
    run_btn = st.button("🚀 開始計算 (Wiki + API)")

if run_btn and target_item:
    with st.spinner(f"正在分析 {target_item} 的深層材料結構..."):
        raw_results = recursive_calculator(target_item, multiplier)
        
        if raw_results:
            # 加總相同材料
            summary = {}
            for r in raw_results:
                name = cc.convert(r['name']) if auto_convert else r['name']
                summary[name] = summary.get(name, 0) + r['total']
            
            # 轉為 DataFrame
            df = pd.DataFrame([{"材料名稱": k, "總共所需": v} for k, v in summary.items()])
            
            st.header(f"📊 {cc.convert(target_item)} 材料總計")
            st.success(f"已自動展開半成品，以下為製作 {multiplier} 件所需的原始材料清單。")
            
            # 進度清單
            col1, col2, col3 = st.columns([1, 4, 2])
            col1.write("**完成**")
            col2.write("**材料名稱**")
            col3.write("**所需數量**")
            st.divider()
            
            check_list = []
            for idx, row in df.iterrows():
                c1, c2, c3 = st.columns([1, 4, 2])
                done = c1.checkbox("", key=f"chk_{idx}")
                label = f"**{row['材料名稱']}**" if not done else f"~~{row['材料名稱']}~~"
                c2.markdown(label)
                c3.write(f"`{row['總共所需']}`")
                check_list.append(done)
            
            if check_list:
                prog = sum(check_list) / len(check_list)
                st.progress(prog)
                st.write(f"收集進度：{int(prog*100)}%")
                if prog == 1.0: st.balloons()
        else:
            st.error("找不到該物品的資料，請確認名稱是否正確（需使用 Wiki 上的名稱）。")
