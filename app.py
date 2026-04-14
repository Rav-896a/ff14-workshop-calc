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
    
    st
