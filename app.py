import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="Stock Analyzer", layout="wide")
st.title("📈 投資配資分析工具")

st.sidebar.header("📊 投資參數")
ticker = st.sidebar.text_input("股票代號", "0700.HK").upper()
capital = st.sidebar.number_input("本金", value=100000)
risk_pct = st.sidebar.slider("風險 (%)", 0.5, 5.0, 2.0) / 100

try:
    # 抓取數據
    df = yf.download(ticker, period="1y", interval="1d", auto_adjust=True)
    
    if not df.empty:
        # 用 Pandas 內建 rolling 算均線
        df['SMA20'] = df['Close'].rolling(window=20).mean()
        
        # ⚠️ 修正：用 flatten() 確保拿到純數字
        current_price = float(df['Close'].values.flatten()[-1])
        sma_values = df['SMA20'].values.flatten()
        last_sma = float(sma_values[-1]) if not pd.isna(sma_values[-1]) else current_price
        
        # 資金計算 (5% 停損)
        stop_loss = current_price * 0.95
        risk_money = capital * risk_pct
        price_diff = current_price - stop_loss
        shares = int(risk_money / price_diff) if price_diff > 0 else 0

        # 顯示頂部卡片
        c1, c2, c3 = st.columns(3)
        c1.metric("現價", f"{current_price:.2f}")
        c2.metric("趨勢", "多頭 🟢" if current_price > last_sma else "空頭 🔴")
        c3.metric("建議入貨", f"{shares} 股")

        # 圖表設定
        fig = go.Figure(data=[go.Candlestick(
            x=df.index,
            open=df['Open'].values.flatten(),
            high=df['High'].values.flatten(),
            low=df['Low'].values.flatten(),
            close=df['Close'].values.flatten(),
            name='K線'
        )])
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA20'].values.flatten(), name='20MA', line=dict(color='orange')))
        fig.update_layout(xaxis_rangeslider_visible=False, height=450, margin=dict(l=5,r=5,t=5,b=5))
        st.plotly_chart(fig, use_container_width=True)
        
        st.success(f"iPhone 用戶提示：已根據最新數據計算。建議停損價：{stop_loss:.2f}")
    else:
        st.error("代號無效或抓不到數據")
except Exception as e:
    st.error(f"發生錯誤: {e}")
