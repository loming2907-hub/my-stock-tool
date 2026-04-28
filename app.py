import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from twelvedata import TDClient
from groq import Groq

# 1. 頁面基本設定
st.set_page_config(page_title="AI Stock Pro", layout="wide")
st.title("📈 專業投資配資分析")

# 2. 側邊欄設定
st.sidebar.header("⚙️ 系統設定")
td_api_key = st.sidebar.text_input("Twelve Data API Key", type="password")
groq_api_key = st.sidebar.text_input("Groq API Key", type="password")

# 港股輸入處理
raw_ticker = st.sidebar.text_input("股票代號 (例: 700, AAPL)", "700").upper()
is_hk = raw_ticker.isdigit()

# 針對港股的特殊處理：補齊 5 位數 (如 700 -> 00700)
if is_hk:
    ticker = raw_ticker.zfill(5)
    exchange_name = "XHKG"
    default_lot = 100
else:
    ticker = raw_ticker
    exchange_name = None
    default_lot = 1

# 手動修正每手股數 (港股必備)
lot_size = st.sidebar.number_input("每手股數 (Lot Size)", min_value=1, value=default_lot)
total_capital = st.sidebar.number_input("可用本金", min_value=0, value=100000)
risk_percent = st.sidebar.slider("單筆最大風險 (%)", 0.5, 5.0, 2.0, 0.5) / 100

# 3. 數據抓取函數
@st.cache_data(ttl=3600)
def fetch_td_data(api_key, symbol, exchange):
    try:
        td = TDClient(apikey=api_key)
        # 抓取 K 線
        ts = td.time_series(symbol=symbol, exchange=exchange, interval="1day", outputsize=100, order="ASC").as_pandas()
        # 抓取報價 (這裡最容易報錯，所以加強處理)
        quote = td.quote(symbol=symbol, exchange=exchange).as_json()
        return ts, quote
    except Exception as e:
        return None, str(e)

# 4. 主程式
if not td_api_key:
    st.info("💡 請輸入 Twelve Data API Key 以開始。")
else:
    with st.spinner("正在獲取數據..."):
        df, quote_data = fetch_td_data(td_api_key, ticker, exchange_name)

    if df is not None and isinstance(quote_data, dict):
        # 提取資訊
        stock_name = quote_data.get('name', ticker)
        current_price = float(quote_data.get('close', 0))
        
        # 計算技術指標
        df['SMA20'] = df['close'].rolling(window=20).mean()
        last_sma = df['SMA20'].iloc[-1]
        
        # 資金控管
        stop_loss_price = current_price * 0.95
        risk_money = total_capital * risk_percent
        price_diff = current_price - stop_loss_price
        
        suggested_lots = int((risk_money / price_diff) // lot_size) if price_diff > 0 else 0
        final_shares = suggested_lots * lot_size
        invest_cost = final_shares * current_price

        # 介面顯示
        st.subheader(f"🔍 {stock_name} ({ticker})")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("現價", f"{current_price:.2f}")
        c2.metric("趨勢", "多頭 🟢" if current_price > last_sma else "空頭 🔴")
        c3.metric("建議手數", f"{suggested_lots} 手", f"共 {final_shares} 股")
        c4.metric("止蝕建議", f"{stop_loss_price:.2f}")

        if invest_cost > total_capital:
            st.warning(f"⚠️ 警告：成本 (${invest_cost:,.0f}) 已超過本金！")
        else:
            st.success(f"💰 預計成本: **${invest_cost:,.0f}** | 每手股數: {lot_size}")

        # 5. Groq AI 分析
        if st.button("🤖 啟動 Groq AI 深度分析"):
            if not groq_api_key:
                st.error("請輸入 Groq API Key")
            else:
                with st.spinner("AI 分析中..."):
                    client = Groq(api_key=groq_api_key)
                    recent_data = df[['close', 'SMA20']].tail(10).to_string()
                    prompt = f"股票:{stock_name}\n現價:{current_price}\n建議:{suggested_lots}手\n請用繁體中文簡短分析走勢。"
                    completion = client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model="llama-3.3-70b-versatile")
                    st.info("### 🤖 Groq AI 專家建議")
                    st.write(completion.choices[0].message.content)

        # 6.
