import streamlit as st
import pandas as pd
import requests
import re
from opencc import OpenCC

# 初始化轉換器 (簡轉繁)
cc = OpenCC('s2twp')

st.set_page_config(page_title="FF14 部隊工房專業計算器", layout="wide")

# 自定義 CSS 優化介面
st.markdown("""
    <style>
    .stCheckbox { font-size: 1.1rem; }
    .main { background-color: #f8f9fa; }
    .st-emotion-cache-1kyx001 { padding: 1.5rem; border-radius: 12px; border: 1px solid #e0e0e0; }
    h1 { color: #2c3e50; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛠️ FF14 部隊工房材料計算器 (XIVAPI 聯動版)")
st.write("結合 Wiki 數據與遊戲原始配方庫，一鍵拆解部隊零件至原始材料。")

# --- 核心邏輯：XIVAPI 查詢 ---
def get_recipe_from_xivapi(item_name_cn):
    """透過 XIVAPI 查詢半成品的製作配方"""
    try:
        # 1. 搜尋物品
        search_url = "https://xivapi.com/search"
        params = {"string": item_name_cn, "indexes": "Item", "language": "cn"}
        res = requests.get(search_url, params=params, timeout=5).json()
        
        if not res.get("Results"):
            return None
        item_id = search_res_results = res["Results"][0]["ID"]
        
        # 2. 獲取物品詳情與配方
        item_url = f"https://xivapi.com/Item/{item_id}"
        detail = requests.get(item_url, timeout=5).json()
        
        # 檢查是否有配方
        recipe = detail.get("Recipe")
        if not recipe:
            return None
        
        ingredients = []
        # XIVAPI 的配方結構：ItemIngredient0...9
        for i in range(10):
            ing_item = recipe.get(f"ItemIngredient{i}")
            amount = recipe.get(f"AmountIngredient{i}")
            if ing_item and amount and amount > 0:
                ingredients.append({
                    "name": ing_item.get("Name_cn") or ing_item.get("Name"),
                    "qty": int(amount)
                })
        return ingredients
    except Exception as e:
        return None

# --- 核心邏輯：Wiki API 抓取第一層 ---
def fetch_wiki_first_layer(item_name):
    """透過 MediaWiki API 抓取部隊零件的第一層需求"""
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
        res_data = response.json()
        # 修正原先 SyntaxError 的位置
        if "parse" in res_data:
            wikitext = res_data["parse"]["wikitext"]["*"]
            return wikitext
        return None
    except Exception as e:
        st.error(f"Wiki API 連線失敗: {e}")
        return None

# --- 遞迴計算引擎 ---
def recursive_calculator(item_name, target_qty, expand_depth=0):
    """
    遞迴展開邏輯：
    - 深度 0: 從 Wiki 抓取部隊工房零件階段
    - 深度 > 0: 從 XIVAPI 抓取一般物品配方
    """
    # 定義需要被展開的後綴關鍵字
    expand_keywords = ["锭", "板", "铆钉", "连接板", "钢", "金锭", "胶", "纸", "布"]
    
    first_level = []
    
    if expand_depth == 0:
        # 第一層處理：部隊零件專用（Wiki 抓取）
        raw_text = fetch_wiki_first_layer(item_name)
        if not raw_text:
            return []
        
        lines = raw_text.split('\n')
        for line in lines:
            # 匹配「名稱 × 數量」格式
            match = re.search(r'([^\s\d\x00-\x7f]+.*?)\s*[×x*]\s*(\d+)', line)
            if match:
                first_level.append({
                    "name": match.group(1).strip(), 
                    "qty": int(match.group(2))
                })
    else:
        # 深層處理：一般製作半成品（XIVAPI 抓取）
        ingredients = get_recipe_from_xivapi(item_name)
        if ingredients:
            first_level = ingredients
        else:
            # 查無配方，視為採集或原始材料
            return [{"name": item_name, "total": target_qty, "type": "原始材料"}]

    final_results = []
    for item in first_level:
        name = item['name']
        total_needed = item['qty'] * target_qty
        
        # 判斷是否需要繼續展開 (深度限制設為 2，避免無限循環)
        if any(k in name for k in expand_keywords) and expand_depth < 2:
            sub_results = recursive_calculator(name, total_needed, expand_depth + 1)
            final_results.extend(sub_results)
        else:
            final_results.append({
                "name": name, 
                "total": total_needed, 
                "type": "基礎/採集"
            })
            
    return final_results

# --- UI 側邊欄 ---
with st.sidebar:
    st.header("⚙️ 核心設定")
    multiplier = st.number_input("預計製作數量", min_value=1, value=1)
    auto_convert = st.checkbox("自動繁體化", value=True)
    st.divider()
    target_item = st.text_input("部隊零件名稱 (需簡中)", value="甲鱟級船首")
    st.caption("例如：甲鱟级船首、蛟龙级船体")
    run_btn = st.button("🚀 開始遞迴計算")
    st.divider()
    st.info("💡 說明：本工具會先從灰機 Wiki 獲取零件階段，再透過 XIVAPI 拆解半成品配方。")

# --- 主畫面渲染 ---
if run_btn and target_item:
    with st.spinner(f"正在分析「{target_item}」的深層材料樹..."):
        # 執行遞迴計算
        raw_results = recursive_calculator(target_item, multiplier)
        
        if raw_results:
            # 加總相同名稱的材料
            summary = {}
            for r in raw_results:
                name = cc.convert(r['name']) if auto_convert else r['name']
                summary[name] = summary.get(name, 0) + r['total']
            
            # 轉換為 DataFrame 進行顯示
            df_summary = pd.DataFrame([
                {"材料名稱": k, "總共所需": v} for k, v in summary.items()
            ])
            
            display_title = cc.convert(target_item) if auto_convert else target_item
            st.header(f"📊 {display_title} 材料總計")
            st.success(f"已完成半成品拆解，製作 {multiplier} 件所需的原始清單如下：")
            
            # 進度清單介面
            col1, col2, col3 = st.columns([1, 4, 2])
            col1.write("**完成**")
            col2.write("**材料名稱**")
            col3.write("**總量**")
            st.divider()
            
            check_list = []
            for idx, row in df_summary.iterrows():
                c1, c2, c3 = st.columns([1, 4, 2])
                done = c1.checkbox("", key=f"chk_{idx}")
                
                # 完成後顯示刪除線
                label = f"**{row['材料名稱']}**" if not done else f"~~{row['材料名稱']}~~"
                c2.markdown(label)
                c3.write(f"`{row['總共所需']}`")
                check_list.append(done)
            
            # 進度條計算
            if check_list:
                st.divider()
                prog = sum(check_list) / len(check_list)
                st.subheader(f"目前收集進度：{int(prog*100)}%")
                st.progress(prog)
                if prog == 1.0:
                    st.balloons()
                    st.success("恭喜！所有材料已備齊。")
        else:
            st.error("無法解析該物品。請確認名稱是否與 Wiki 標題一致，且為部隊工房可製作零件。")
