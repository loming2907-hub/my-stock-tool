import streamlit as st
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go

# 1. 介面設定
st.set_page_config(page_title="投資分析工具", layout="wide")
st.title("📈 股票走勢與資金配置工具")

# 2. 側邊欄：輸入參數
st.sidebar.header("投資設定")
ticker = st.sidebar.text_input("輸入股票代號 (例如: 0700.HK 或 NVDA)", "0700.HK")
capital = st.sidebar.number_input("總本金 (HKD/USD)", min_value=0, value=100000)
risk_ratio = st.sidebar.slider("每筆交易願意承受的風險 (%)", 1, 10, 2) / 100

# 3. 抓取數據
data = yf.download(ticker, period="1y", interval="1d")

if not data.empty:
    # 4. 技術指標計算 (簡單均線走勢)
    data['SMA20'] = ta.sma(data['Close'], length=20)
    data['SMA50'] = ta.sma(data['Close'], length=50)
    
    # 5. 走勢判斷邏輯
    current_price = data['Close'].iloc[-1]
    sma20 = data['SMA20'].iloc[-1]
    
    st.subheader(f"{ticker} 當前分析")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("當前股價", f"{current_price:.2f}")
    with col2:
        trend = "多頭 (Bullish)" if current_price > sma20 else "空頭 (Bearish)"
        st.metric("短期走勢", trend)
    with col3:
        # 簡單計算：若以近期低點作為停損點
        stop_loss = current_price * 0.95 # 假設設 5% 停損
        # 計算可買入股數 (本金 * 風險) / (進場價 - 停損價)
        risk_amount = capital * risk_ratio
        suggested_shares = int(risk_amount / (current_price - stop_loss))
        st.metric("建議入貨股數", f"{suggested_shares} 股")

    # 6. 畫出圖表
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name='K線'))
    fig.add_trace(go.Scatter(x=data.index, y=data['SMA20'], name='20MA', line=dict(color='orange')))
    fig.update_layout(title=f"{ticker} 歷史走勢", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
    
    st.info(f"💡 根據你的設定：每筆交易風險金額為 {risk_amount:.0f}。若在 {stop_loss:.2f} 停損，建議入貨量為 {suggested_shares} 股。")
else:
    st.error("找不到股票數據，請檢查代號是否正確。")
