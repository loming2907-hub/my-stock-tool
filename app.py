import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from twelvedata import TDClient
from groq import Groq

# 1. 頁面設定
st.set_page_config(page_title="Twelve Data Stock Pro", layout="wide")
st.title("📈 Twelve Data 智能投資分析")

# 2. 側邊欄：API Keys 與 參數
st.sidebar.header("⚙️ 系統設定")
td_api_key = st.sidebar.text_input("Twelve Data API Key", type="password")
groq_api_key = st.sidebar.text_input("Groq API Key", type="password")

# 提示：港股代號需轉換為 Twelve Data 格式 (例: 0700 -> 0700:XHKG)
raw_ticker = st.sidebar.text_input("股票代號 (例: 0700, AAPL)", "0700").upper()
total_capital = st.sidebar.number_input("可用本金", value=100000)
risk_percent = st.sidebar.slider("單筆最大風險 (%)", 0.5, 5.0, 2.0) / 100

# 自動處理代號格式
if raw_ticker.isdigit():
    ticker = f"{raw_ticker}:XHKG"  # 港股格式
else:
    ticker = raw_ticker           # 美股格式

# 3. 抓取數據函數 (加入快取)
@st.cache_data(ttl=3600)
def fetch_td_data(api_key, symbol):
    td = TDClient(apikey=api_key)
    # 獲取歷史數據
    ts = td.time_series(symbol=symbol, interval="1day", outputsize=250).as_pandas()
    # 獲取股票報價與基礎資訊
    quote = td.quote(symbol=symbol).as_json()
    return ts, quote

if not td_api_key:
    st.warning("請先在左側輸入 Twelve Data API Key。")
else:
    try:
        df, quote = fetch_td_data(td_api_key, ticker)
        
        if df is not None and not df.empty:
            # Twelve Data 返回的數據通常按時間倒序，需反轉
            df = df.sort_index()
            
            # 計算 20MA
            df['SMA20'] = df['close'].rolling(window=20).mean()
            
            # 提取數據
            current_price = float(quote['close'])
            stock_name = quote['name']
            # Twelve Data 免費版可能拿不到港股 lotSize，預設設為 100 (或手動輸入)
            lot_size = 100 if ":XHKG" in ticker else 1 
            
            # 4. 核心計算
            stop_loss_price = current_price * 0.95
            risk_money = total_capital * risk_percent
            price_diff = current_price - stop_loss_price
            
            suggested_lots = int((risk_money / price_diff) // lot_size) if price_diff > 0 else 0
            final_shares = suggested_lots * lot_size
            total_cost = final_shares * current_price

            # 5. 顯示數據卡
            st.subheader(f"🔍 {stock_name} ({ticker})")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("現價", f"{current_price:.2f}")
            
            last_sma = df['SMA20'].iloc[-1]
            c2.metric("趨勢", "多頭 🟢" if current_price > last_sma else "空頭 🔴")
            c3.metric("建議手數", f"{suggested_lots} 手", f"共 {final_shares} 股")
            c4.metric("止蝕價", f"{stop_loss_price:.2f}")

            if total_cost > total_capital:
                st.warning(f"⚠️ 成本 (${total_cost:,.0f}) 已超過本金！")
            else:
                st.success(f"💰 預計投入成本: **${total_cost:,.0f}**")

            # 6. Groq AI 分析
            if st.button("🤖 啟動 Groq AI 分析"):
                if not groq_api_key:
                    st.error("請輸入 Groq API Key")
                else:
                    with st.spinner("AI 正在分析..."):
                        client = Groq(api_key=groq_api_key)
                        recent_summary = df[['close', 'SMA20']].tail(10).to_string()
                        prompt = f"股票:{stock_name}\n現價:{current_price}\n10日數據:{recent_summary}\n請提供繁體中文投資建議。"
                        
                        completion = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[{"role": "user", "content": prompt}]
                        )
                        st.info("### 🤖 Groq AI 建議")
                        st.write(completion.choices[0].message.content)

            # 7. 圖表
            fig = go.Figure(data=[go.Candlestick(
                x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='K線'
            )])
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA20'], name='20MA', line=dict(color='orange')))
            fig.add_hline(y=stop_loss_price, line_dash="dash", line_color="red")
            fig.update_layout(xaxis_rangeslider_visible=False, height=450, margin=dict(l=5, r=5, t=5, b=5))
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"獲取數據失敗: {e}")
        st.info("提示：Twelve Data 免費版每分鐘有限制，請勿頻繁刷新。如果是港股，請確保代號輸入正確。")
