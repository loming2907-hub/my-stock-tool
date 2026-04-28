import streamlit as st
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
import pandas as pd

# 1. 頁面基本設定
st.set_page_config(page_title="Stock Analyzer", layout="wide")

# 2. 標題與簡介
st.title("📈 個人投資配資工具")
st.markdown("---")

# 3. 側邊欄：輸入參數
st.sidebar.header("📊 投資參數")
ticker_input = st.sidebar.text_input("股票代號 (例: 0700.HK, NVDA)", "0700.HK").upper()
total_capital = st.sidebar.number_input("可用本金 (HKD/USD)", min_value=0, value=100000, step=10000)
risk_percent = st.sidebar.slider("願意承擔的單筆風險 (%)", 0.5, 5.0, 2.0, 0.5) / 100

# 4. 抓取數據 (加入快取機制減少報錯)
@st.cache_data(ttl=3600)
def get_data(symbol):
    try:
        # 抓取一年歷史數據
        df = yf.download(symbol, period="1y", interval="1d", auto_adjust=True)
        return df
    except:
        return pd.DataFrame()

df = get_data(ticker_input)

# 5. 數據分析與介面顯示
if not df.empty and len(df) > 20:
    # 計算技術指標
    df['SMA20'] = ta.sma(df['Close'], length=20)
    
    # --- 關鍵修正：使用 values[-1] 提取純數字，避免 TypeError ---
    try:
        # 取得最新股價
        current_price = float(df['Close'].values[-1])
        # 取得前一天均線
        last_sma20 = df['SMA20'].values[-1]
        last_sma20 = float(last_sma20) if pd.notnull(last_sma20) else current_price
        
        # --- 資金控管邏輯 ---
        # 策略：設 5% 為停損位
        stop_loss_level = 0.05
        stop_loss_price = current_price * (1 - stop_loss_level)
        
        # 根據「風險百分比」算出這筆買賣輸得起的金額
        risk_amount = total_capital * risk_percent
        
        # 計算建議股數 = 風險金額 / (買入價 - 停損價)
        price_diff = current_price - stop_loss_price
        suggested_shares = int(risk_amount / price_diff) if price_diff > 0 else 0
        
        # 6. 介面顯示：上方數據卡
        st.subheader("💡 分析摘要")
        m1, m2, m3 = st.columns(3)
        m1.metric("當前股價", f"{current_price:.2f}")
        
        trend = "多頭 🟢" if current_price > last_sma20 else "空頭 🔴"
        m2.metric("20日走勢", trend)
        
        m3.metric("建議入貨", f"{suggested_shares} 股")

        # 7. 計算細節 (iPhone 使用 expander 節省空間)
        with st.expander("📊 查看詳細計算細節"):
            st.write(f"當前本金: **${total_capital:,.0f}**")
            st.write(f"單筆最大容許虧損: **${risk_amount:,.0f}**")
            st.write(f"預設停損價: **${stop_loss_price:.2f}** (跌幅 5%)")
            st.write(f"建議投入金額: **${(suggested_shares * current_price):,.0f}**")

        # 8. 視覺化圖表
        st.subheader("🔍 歷史趨勢圖")
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['Open'], high=df['High'],
            low=df['Low'], close=df['Close'],
            name='K線'
        ))
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA20'], name='20MA', line=dict(color='orange', width=1.5)))
        
        fig.update_layout(
            xaxis_rangeslider_visible=False,
            height=450,
            margin=dict(l=5, r=5, t=10, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"數據解析出錯，請嘗試刷新 App。錯誤訊息: {e}")

else:
    st.warning("⚠️ 無法獲取數據，請檢查股票代號 (如: 0700.HK 或 AAPL) 或稍後再試。")
