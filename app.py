import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from groq import Groq

# 1. 頁面設定
st.set_page_config(page_title="AI Stock Pro", layout="wide")
st.title("📈 專業投資配資分析")

# 2. 側邊欄設定
st.sidebar.header("⚙️ 系統設定")
groq_api_key = st.sidebar.text_input("輸入 Groq API Key", type="password")
ticker_input = st.sidebar.text_input("股票代號 (例: 0700.HK, AAPL)", "0700.HK").upper()
total_capital = st.sidebar.number_input("可用本金", min_value=0, value=100000, step=10000)
risk_percent = st.sidebar.slider("單筆最大風險 (%)", 0.5, 5.0, 2.0, 0.5) / 100

try:
    # 3. 抓取股票詳細資訊
    yt = yf.Ticker(ticker_input)
    stock_info = yt.info
    
    # 取得股票名稱
    stock_name = stock_info.get('longName', ticker_input)
    
    # 取得每手股數 (港股專用，美股預設為 1)
    lot_size = stock_info.get('lotSize', 1) 
    if lot_size is None: lot_size = 1
    
    # 4. 抓取歷史數據
    df = yt.history(period="1y", interval="1d")
    
    if not df.empty:
        df['SMA20'] = df['Close'].rolling(window=20).mean()
        
        # 提取最新數據
        current_price = float(df['Close'].values.flatten()[-1])
        sma_values = df['SMA20'].values.flatten()
        last_sma = float(sma_values[-1]) if not pd.isna(sma_values[-1]) else current_price
        
        # 5. 核心計算邏輯
        # 止蝕價：設為現價跌 5% (可根據需求調整)
        stop_loss_price = current_price * 0.95
        
        # 風險金額：本金 * 風險 %
        risk_money = total_capital * risk_percent
        
        # 建議股數 = 風險金額 / (買入價 - 止蝕價)
        price_diff = current_price - stop_loss_price
        raw_suggested_shares = risk_money / price_diff if price_diff > 0 else 0
        
        # 建議手數 = 總股數 / 每手股數 (無條件捨去取整數)
        suggested_lots = int(raw_suggested_shares // lot_size)
        final_shares = suggested_lots * lot_size
        
        # 預計投入成本 = 最終股數 * 現價
        total_cost = final_shares * current_price

        # 6. 頂部儀表板 (四個指標)
        st.subheader(f"🔍 {stock_name} ({ticker_input})")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("現價", f"{current_price:.2f}")
        c2.metric("趨勢", "多頭 🟢" if current_price > last_sma else "空頭 🔴")
        c3.metric("建議手數", f"{suggested_lots} 手", f"共 {final_shares} 股")
        c4.metric("止蝕價", f"{stop_loss_price:.2f}", f"跌幅 5%")
        
        # 顯示投入成本
        if total_cost > total_capital:
            st.warning(f"⚠️ 警告：預計成本 (${total_cost:,.0f}) 已超過可用本金！")
        else:
            st.success(f"💰 預計投入成本: **${total_cost:,.0f}** (佔本金 {total_cost/total_capital:.1%})")

        # 7. Groq AI 分析
        if st.button("🤖 啟動 Groq AI 深度分析"):
            if not groq_api_key:
                st.error("請在左側輸入 Groq API Key")
            else:
                with st.spinner("AI 分析中..."):
                    client = Groq(api_key=groq_api_key)
                    recent_summary = df[['Close', 'SMA20']].tail(10).to_string()
                    
                    prompt = f"""
                    分析股票: {stock_name} ({ticker_input})
                    現價: {current_price:.2f}, 20MA: {last_sma:.2f}, 止蝕價: {stop_loss_price:.2f}
                    最近10日數據: {recent_summary}
                    
                    請用繁體中文提供：
                    1. 走勢點評。
                    2. 操作建議 (針對建議購入 {suggested_lots} 手的觀點)。
                    3. 給 iPhone 用戶的一句話總結。
                    """
                    
                    completion = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    st.info("### 🤖 Groq AI 專家建議")
                    st.write(completion.choices[0].message.content)

        # 8. 圖表
        fig = go.Figure(data=[go.Candlestick(
            x=df.index,
            open=df['Open'].values.flatten(),
            high=df['High'].values.flatten(),
            low=df['Low'].values.flatten(),
            close=df['Close'].values.flatten(),
            name='K線'
        )])
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA20'].values.flatten(), name='20MA', line=dict(color='orange')))
        # 增加一條紅色的止蝕線
        fig.add_hline(y=stop_loss_price, line_dash="dash", line_color="red", annotation_text="止蝕參考")
        
        fig.update_layout(xaxis_rangeslider_visible=False, height=450, margin=dict(l=5, r=5, t=5, b=5))
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.error("代號無效")
except Exception as e:
    st.error(f"錯誤: {e}")
