import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from twelvedata import TDClient
from groq import Groq

# 1. 頁面基本設定
st.set_page_config(page_title="AI Stock Pro (Twelve Data)", layout="wide")
st.title("📈 專業投資配資分析 (Twelve Data 版)")

# 2. 側邊欄設定
st.sidebar.header("⚙️ 系統設定")
td_api_key = st.sidebar.text_input("輸入 Twelve Data API Key", type="password")
groq_api_key = st.sidebar.text_input("輸入 Groq API Key", type="password")

# 處理代號：Twelve Data 港股通常使用 "0700:XHKG" 或 "0700" 配合 exchange 參數
raw_ticker = st.sidebar.text_input("股票代號 (例: 0700, AAPL)", "0700").upper()
total_capital = st.sidebar.number_input("可用本金", min_value=0, value=100000, step=10000)
risk_percent = st.sidebar.slider("單筆最大風險 (%)", 0.5, 5.0, 2.0, 0.5) / 100

# 港股格式轉換邏輯
if raw_ticker.isdigit():
    # 港股需要補齊 4 位數並指定交易所
    ticker = raw_ticker.zfill(4)
    exchange_param = "XHKG"
else:
    ticker = raw_ticker
    exchange_param = None

# 3. 數據抓取函數
@st.cache_data(ttl=3600)
def fetch_td_data(api_key, symbol, exchange):
    try:
        td = TDClient(apikey=api_key)
        # 抓取 K 線數據
        ts = td.time_series(
            symbol=symbol,
            exchange=exchange,
            interval="1day",
            outputsize=100,
            order="ASC"
        ).as_pandas()
        
        # 抓取即時報價與詳細資訊
        quote = td.quote(symbol=symbol, exchange=exchange).as_json()
        return ts, quote
    except Exception as e:
        return None, str(e)

# 4. 主程式邏輯
if not td_api_key:
    st.info("💡 請在左側輸入你的 Twelve Data API Key。")
else:
    with st.spinner("正在從 Twelve Data 獲取數據..."):
        df, quote_data = fetch_td_data(td_api_key, ticker, exchange_param)

    if df is not None and not isinstance(quote_data, str):
        # A. 提取資訊
        stock_name = quote_data.get('name', ticker)
        current_price = float(quote_data.get('close', 0))
        
        # B. 每手股數設定 (Twelve Data 免費版可能無法直接提供港股 lotSize)
        # 港股預設 100 股一手 (常見)，美股 1 股
        lot_size = 100 if exchange_param == "XHKG" else 1
        
        # C. 計算技術指標
        df['SMA20'] = df['close'].rolling(window=20).mean()
        last_sma = float(df['SMA20'].iloc[-1]) if not pd.isna(df['SMA20'].iloc[-1]) else current_price
        
        # D. 資金控管與止蝕
        stop_loss_price = current_price * 0.95
        risk_money = total_capital * risk_percent
        price_diff = current_price - stop_loss_price
        
        # 換算手數
        raw_shares = risk_money / price_diff if price_diff > 0 else 0
        suggested_lots = int(raw_shares // lot_size)
        final_shares = suggested_lots * lot_size
        invest_cost = final_shares * current_price

        # E. 數據顯示儀表板
        st.subheader(f"🔍 {stock_name} ({ticker})")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("現價", f"{current_price:.2f}")
        c2.metric("趨勢 (20MA)", "多頭 🟢" if current_price > last_sma else "空頭 🔴")
        c3.metric("建議入貨", f"{suggested_lots} 手", f"共 {final_shares} 股")
        c4.metric("止蝕位", f"{stop_loss_price:.2f}")

        if invest_cost > total_capital:
            st.warning(f"⚠️ 預計成本 (${invest_cost:,.0f}) 已超過本金！")
        else:
            st.success(f"💰 預計成本: **${invest_cost:,.0f}** | 每手股數: {lot_size}")

        # 5. Groq AI 分析
        st.markdown("---")
        if st.button("🤖 啟動 Groq AI 深度分析"):
            if not groq_api_key:
                st.error("請輸入 Groq API Key")
            else:
                with st.spinner("AI 正在極速分析中..."):
                    try:
                        client = Groq(api_key=groq_api_key)
                        recent_summary = df[['close', 'SMA20']].tail(10).to_string()
                        
                        prompt = f"""分析股票: {stock_name} ({ticker})
現價: {current_price:.2f}, 20MA: {last_sma:.2f}
建議購入: {suggested_lots} 手 (每手{lot_size}股), 止蝕位 {stop_loss_price:.2f}

最近10日數據:
{recent_summary}

請用繁體中文簡短提供：
1. 走勢點評。
2. 操作與風險建議。
3. 給 iPhone 用戶的一句話總結。"""

                        chat_completion = client.chat.completions.create(
                            messages=[{"role": "user", "content": prompt}],
                            model="llama-3.3-70b-versatile",
                        )
                        st.info("### 🤖 Groq AI 專家建議")
                        st.write(chat_completion.choices[0].message.content)
                    except Exception as ai_e:
                        st.error(f"AI 分析失敗: {ai_e}")

        # 6. K 線圖表
        fig = go.Figure(data=[go.Candlestick(
            x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='K線'
        )])
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA20'], name='20MA', line=dict(color='orange')))
        fig.add_hline(y=stop_loss_price, line_dash="dash", line_color="red", annotation_text="止蝕參考")
        
        fig.update_layout(xaxis_rangeslider_visible=False, height=450, margin=dict(l=5, r=5, t=5, b=5))
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.error(f"獲取數據失敗：{quote_data}")
        st.info("提示：免費版 Twelve Data 每分鐘限制 8 次請求。如果是港股，請輸入純數字（如 0700）。")
