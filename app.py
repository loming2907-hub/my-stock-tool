import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from groq import Groq

# 1. 頁面基本設定
st.set_page_config(page_title="AI Stock Terminal", layout="wide")
st.title("📈 AI 智能投資終端")

# 2. 側邊欄：參數設定
st.sidebar.header("⚙️ 系統設定")
groq_api_key = st.sidebar.text_input("輸入 Groq API Key", type="password")
ticker_input = st.sidebar.text_input("股票代號 (例: 0700.HK, AAPL)", "0700.HK").upper()
total_capital = st.sidebar.number_input("可用本金 (HKD/USD)", min_value=0, value=100000, step=10000)
risk_percent = st.sidebar.slider("單筆最大風險 (%)", 0.5, 5.0, 2.0, 0.5) / 100

# 3. 數據抓取函數 (加入偽裝 Headers)
@st.cache_data(ttl=600) # 快取 10 分鐘，兼顧即時性與防封鎖
def get_data_with_mask(ticker):
    try:
        # 建立 yfinance 物件
        yt = yf.Ticker(ticker)
        
        # 偽裝成 iPhone 的 Safari 瀏覽器
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1'
        }
        
        # 抓取歷史數據
        df = yt.history(period="1y", interval="1d", context=headers)
        # 抓取基本資訊
        info = yt.info
        
        return df, info
    except Exception as e:
        return pd.DataFrame(), str(e)

# 4. 執行抓取與分析
if ticker_input:
    df, info = get_data_with_mask(ticker_input)
    
    if not df.empty and len(df) > 20:
        # 提取基本資訊
        stock_name = info.get('longName', ticker_input)
        lot_size = info.get('lotSize', 1) or 1
        
        # 技術指標計算
        df['SMA20'] = df['Close'].rolling(window=20).mean()
        
        # 確保數據壓平為純數字
        current_price = float(df['Close'].values.flatten()[-1])
        sma_values = df['SMA20'].values.flatten()
        last_sma = float(sma_values[-1]) if not pd.isna(sma_values[-1]) else current_price
        
        # 5. 資金控管邏輯 (Risk Management)
        stop_loss_price = current_price * 0.95  # 5% 止蝕
        risk_money = total_capital * risk_percent
        price_diff = current_price - stop_loss_price
        
        # 計算建議手數
        raw_shares = risk_money / price_diff if price_diff > 0 else 0
        suggested_lots = int(raw_shares // lot_size)
        final_shares = suggested_lots * lot_size
        invest_cost = final_shares * current_price

        # 6. 介面顯示
        st.subheader(f"🔍 {stock_name} ({ticker_input})")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("現價", f"{current_price:.2f}")
        c2.metric("趨勢", "多頭 🟢" if current_price > last_sma else "空頭 🔴")
        c3.metric("建議手數", f"{suggested_lots} 手", f"每手 {lot_size} 股")
        c4.metric("止蝕建議", f"{stop_loss_price:.2f}")

        # 顯示成本與警告
        if invest_cost > total_capital:
            st.warning(f"⚠️ 預計成本 (${invest_cost:,.0f}) 已超過可用本金！")
        else:
            st.success(f"💰 預計投入成本: **${invest_cost:,.0f}** | 總入貨量: {final_shares} 股")

        # 7. Groq AI 分析模組
        st.markdown("---")
        if st.button("🤖 啟動 Groq AI 深度分析"):
            if not groq_api_key:
                st.error("請在左側輸入 Groq API Key")
            else:
                with st.spinner("Llama-3 正在分析走勢..."):
                    try:
                        client = Groq(api_key=groq_api_key)
                        recent_summary = df[['Close', 'SMA20']].tail(10).to_string()
                        
                        prompt = f"""
                        你是資深投資顧問。請分析 {stock_name} ({ticker_input})：
                        - 現價: {current_price:.2f}
                        - 20MA: {last_sma:.2f}
                        - 建議操作: 買入 {suggested_lots} 手，止蝕價設在 {stop_loss_price:.2f}
                        
                        最近10日數據:
                        {recent_summary}
                        
                        請用繁體中文簡短回答：
                        1. 當
