import streamlit as st
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
import pandas as pd

# 1. 頁面基本設定 (適合手機瀏覽)
st.set_page_config(page_title="HK/US Stock Analyzer", layout="wide")

st.title("📈 投資配資分析工具")
st.caption("專為 iPhone 14 優化之流動分析介面")

# 2. 側邊欄：投資參數設定
st.sidebar.header("📊 投資設定")
ticker = st.sidebar.text_input("股票代號 (例: 0700.HK, NVDA)", "0700.HK").upper()
total_capital = st.sidebar.number_input("總本金 (港幣/美金)", min_value=0, value=100000, step=5000)
risk_percent = st.sidebar.slider("願意承擔的總風險 (%)", 0.5, 5.0, 2.0, 0.5) / 100

# 3. 抓取數據
try:
    # 增加 auto_adjust 以解決股價權益調整問題
    df = yf.download(ticker, period="1y", interval="1d", auto_adjust=True)

    if not df.empty:
        # 4. 技術指標計算 (計算 20 日及 50 日均線)
        df['SMA20'] = ta.sma(df['Close'], length=20)
        df['SMA50'] = ta.sma(df['Close'], length=50)

        # ⚠️ 修復：確保取出的值是純數字 (float)，解決 TypeError
        current_price = float(df['Close'].iloc[-1])
        last_sma20 = float(df['SMA20'].iloc[-1])
        
        # 5. 資金控管邏輯 (固定風險模型)
        # 假設以當前價格的 5% 跌幅作為停損點
        stop_loss_price = current_price * 0.95 
        risk_amount_dollars = total_capital * risk_percent
        
        # 計算建議股數：風險金額 / (進場價 - 停損價)
        price_diff = current_price - stop_loss_price
        if price_diff > 0:
            suggested_shares = int(risk_amount_dollars / price_diff)
        else:
            suggested_shares = 0

        # 6. 介面顯示：上方數據卡片
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("當前股價", f"{current_price:.2f}")
        with col2:
            trend = "多頭 🟢" if current_price > last_sma20 else "空頭 🔴"
            st.metric("20MA 走勢", trend)
        with col3:
            st.metric("建議入貨", f"{suggested_shares} 股")

        # 7. 投資細節說明
        with st.expander("🔍 查看詳細配資建議"):
            st.write(f"**股票代號:** {ticker}")
            st.write(f"**最大可承受虧損:** ${risk_amount_dollars:,.0f}")
            st.write(f"**預設停損價 (5%):** ${stop_loss_price:.2f}")
            st.write(f"**預計投入資金:** ${ (suggested_shares * current_price):,.0f}")

        # 8. 畫出 K 線圖
        fig = go.Figure()
        # K線圖
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['Open'], high=df['High'],
            low=df['Low'], close=df['Close'],
            name='K線'
        ))
        # 均線
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA20'], name='20MA', line=dict(color='orange', width=1.5)))
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA50'], name='50MA', line=dict(color='blue', width=1.5)))
        
        fig.update_layout(
            height=450,
            margin=dict(l=10, r=10, t=30, b=10),
            xaxis_rangeslider_visible=False,
            template="plotly_white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.error("❌ 找不到數據。如果是港股請加 .HK (例: 0005.HK)")

except Exception as e:
    st.error(f"發生錯誤: {e}")
    st.info("提示：請確保 Python 版本為 3.11 或 3.12，並檢查 requirements.txt 是否包含 pandas-ta")
