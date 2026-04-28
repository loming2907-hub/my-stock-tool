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
    df = yf.download(ticker, period="1y", interval="1d", auto_adjust=True)
    if not df.empty:
        # 用 Pandas 內建 rolling 算均線，不依賴 pandas-ta
        df['SMA20'] = df['Close'].rolling(window=20).mean()
        
        current_price = float(df['Close'].values[-1])
        # 處理 SMA 可能為空的情況
        last_sma = df['SMA20'].values[-1]
        last_sma = float(last_sma) if not pd.isna(last_sma) else current_price
        
        # 資金計算
        stop_loss = current_price * 0.95
        risk_money = capital * risk_pct
        shares = int(risk_money / (current_price - stop_loss)) if current_price > stop_loss else 0

        # 顯示
        c1, c2, c3 = st.columns(3)
        c1.metric("現價", f"{current_price:.2f}")
        c2.metric("趨勢", "多頭 🟢" if current_price > last_sma else "空頭 🔴")
        c3.metric("入貨量", f"{shares} 股")

        # 圖表
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA20'], name='20MA', line=dict(color='orange')))
        fig.update_layout(xaxis_rangeslider_visible=False, height=400, margin=dict(l=5,r=5,t=5,b=5))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("代號無效")
except Exception as e:
    st.error(f"錯誤: {e}")
