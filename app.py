import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from groq import Groq
import time

# 1. 頁面設定
st.set_page_config(page_title="AI Stock Pro", layout="wide")
st.title("📈 專業投資配資分析")

# 2. 側邊欄設定
st.sidebar.header("⚙️ 系統設定")
groq_api_key = st.sidebar.text_input("輸入 Groq API Key", type="password")
ticker_input = st.sidebar.text_input("股票代號 (例: 0700.HK, AAPL)", "0700.HK").upper()
total_capital = st.sidebar.number_input("可用本金", min_value=0, value=100000, step=10000)
risk_percent = st.sidebar.slider("單筆最大風險 (%)", 0.5, 5.0, 2.0, 0.5) / 100

# --- 新增快取函數：防止頻繁請求被封鎖 ---
@st.cache_data(ttl=3600)  # 數據緩存 1 小時
def get_stock_data(ticker):
    yt = yf.Ticker(ticker)
    # 抓取 Info
    info = yt.info
    # 抓取歷史數據
    df = yt.history(period="1y", interval="1d")
    return info, df

try:
    # 3. 執行抓取
    with st.spinner('正在獲取市場數據...'):
        stock_info, df = get_stock_data(ticker_input)
    
    if not df.empty:
        # 取得股票名稱與每手股數
        stock_name = stock_info.get('longName', ticker_input)
        lot_size = stock_info.get('lotSize', 1) 
        if lot_size is None: lot_size = 1
        
        # 計算 20MA
        df['SMA20'] = df['Close'].rolling(window=20).mean()
        
        # 提取最新數據 (使用 flatten 確保安全)
        current_price = float(df['Close'].values.flatten()[-1])
        sma_values = df['SMA20'].values.flatten()
        last_sma = float(sma_values[-1]) if not pd.isna(sma_values[-1]) else current_price
        
        # 4. 核心計算邏輯
        stop_loss_price = current_price * 0.95 # 5% 止蝕
        risk_money = total_capital * risk_percent
        price_diff = current_price - stop_loss_price
        
        # 建議手數計算
        raw_suggested_shares = risk_money / price_diff if price_diff > 0 else 0
        suggested_lots = int(raw_suggested_shares // lot_size)
        final_shares = suggested_lots * lot_size
        total_cost = final_shares * current_price

        # 5. 介面顯示
        st.subheader(f"🔍 {stock_name}")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("現價", f"{current_price:.2f}")
        c2.metric("趨勢", "多頭 🟢" if current_price > last_sma else "空頭 🔴")
        c3.metric("建議手數", f"{suggested_lots} 手", f"共 {final_shares} 股")
        c4.metric("止蝕價", f"{stop_loss_price:.2f}")
        
        if total_cost > total_capital:
            st.warning(f"⚠️ 成本 (${total_cost:,.0f}) 超過本金！")
        else:
            st.success(f"💰 預計成本: **${total_cost:,.0f}** | 每手股數: {lot_size}")

        # 6. Groq AI 分析
        if st.button("🤖 啟動 Groq AI 分析"):
            if not groq_api_key:
                st.error("請輸入 Groq API Key")
            else:
                with st.spinner("AI 正在分析..."):
                    client = Groq(api_key=groq_api_key)
                    recent_summary = df[['Close', 'SMA20']].tail(10).to_string()
                    prompt = f"分析股票: {stock_name}\n數據: {recent_summary}\n建議入貨: {suggested_lots}手\n請給予繁體中文簡短分析。"
                    
                    completion = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    st.info("### 🤖 Groq AI 建議")
                    st.write(completion.choices[0].message.content)

        # 7. 圖表
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'].values.flatten(), high=df['High'].values.flatten(), low=df['Low'].values.flatten(), close=df['Close'].values.flatten(), name='K線')])
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA20'].values.flatten(), name='20MA', line=dict(color='orange')))
        fig.add_hline(y=stop_loss_price, line_dash="dash", line_color="red")
        fig.update_layout(xaxis_rangeslider_visible=False, height=450, margin=dict(l=5, r=5, t=5, b=5))
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.error("目前無法獲取數據。")
        st.info("原因：Yahoo Finance 暫時限制了您的連線。請等待 5-10 分鐘後重新整理，或檢查代號是否正確。")

except Exception as e:
    if "Too Many Requests" in str(e):
        st.error("❌ 請求過於頻繁 (Rate Limit)")
        st.info("Yahoo Finance 伺服器拒絕了本次連線。請等待幾分鐘再嘗試，或者點擊瀏覽器重新整理。")
    else:
        st.error(f"系統錯誤: {e}")
