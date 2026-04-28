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

# 處理代號：Twelve Data 港股通常使用 "0700:HK" 格式
raw_ticker = st.sidebar.text_input("股票代號 (例: 0700, AAPL)", "0700").upper()
total_capital = st.sidebar.number_input("可用本金", min_value=0, value=100000, step=10000)
risk_percent = st.sidebar.slider("單筆最大風險 (%)", 0.5, 5.0, 2.0, 0.5) / 100

# 港股代號自動轉換邏輯
if raw_ticker.isdigit():
    ticker = f"{raw_ticker}:HK"
else:
    ticker = raw_ticker

# 3. 數據抓取函數 (加入快取防止重複消耗 API 額度)
@st.cache_data(ttl=3600)
def fetch_stock_data(api_key, symbol):
    try:
        td = TDClient(apikey=api_key)
        # 抓取歷史 K 線 (250 天足以計算 20MA)
        ts = td.time_series(symbol=symbol, interval="1day", outputsize=250, order="ASC").as_pandas()
        # 抓取即時報價與詳細資訊 (包含名稱)
        quote = td.quote(symbol=symbol).as_json()
        return ts, quote
    except Exception as e:
        return None, str(e)

# 4. 主程式邏輯
if not td_api_key:
    st.info("💡 請在左側輸入你的 Twelve Data API Key 以開始。")
else:
    with st.spinner("正在從 Twelve Data 獲取數據..."):
        df, quote_data = fetch_stock_data(td_api_key, ticker)

    if df is not None and not isinstance(quote_data, str):
        # A. 提取基本資訊
        stock_name = quote_data.get('name', ticker)
        current_price = float(quote_data.get('close', 0))
        
        # B. 每手股數設定 (Twelve Data 免費版港股 lotSize 不一定有值，我們預設常見的)
        # 若為美股則為 1，港股預設 100 (或依需求修改)
        is_hk = ":HK" in ticker
        lot_size = 100 if is_hk else 1
        
        # C. 計算技術指標
        df['SMA20'] = df['close'].rolling(window=20).mean()
        last_sma = float(df['SMA20'].iloc[-1]) if not pd.isna(df['SMA20'].iloc[-1]) else current_price
        
        # D. 資金控管與止蝕計算
        stop_loss_price = current_price * 0.95  # 預設 5% 止蝕
        risk_money = total_capital * risk_percent
        price_diff = current_price - stop_loss_price
        
        # 計算建議手數 (無條件捨去)
        raw_suggested_shares = risk_money / price_diff if price_diff > 0 else 0
        suggested_lots = int(raw_suggested_shares // lot_size)
        final_shares = suggested_lots * lot_size
        total_cost = final_shares * current_price

        # E. 頂部儀表板
        st.subheader(f"🔍 {stock_name} ({ticker})")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("現價", f"{current_price:.2f}")
        c2.metric("趨勢", "多頭 🟢" if current_price > last_sma else "空頭 🔴")
        c3.metric("建議入貨", f"{suggested_lots} 手", f"共 {final_shares} 股")
        c4.metric("止蝕建議", f"{stop_loss_price:.2f}")

        if total_cost > total_capital:
            st.warning(f"⚠️ 預計成本 (${total_cost:,.0f}) 已超過可用本金！")
        else:
            st.success(f"💰 預計投入成本: **${total_cost:,.0f}** (每手 {lot_size} 股)")

        # 5. Groq AI 分析
        st.markdown("---")
        if st.button("🤖 啟動 Groq Llama-3 深度分析"):
            if not groq_api_key:
                st.error("請在左側輸入 Groq API Key")
            else:
                with st.spinner("Groq 正在極速分析中..."):
                    try:
                        client = Groq(api_key=groq_api_key)
                        recent_summary = df[['close', 'SMA20']].tail(10).to_string()
                        
                        prompt = f"""分析股票: {stock_name} ({ticker})
現價: {current_price:.2f}, 20MA: {last_sma:.2f}
建議策略: 購入 {suggested_lots} 手 (每手{lot_size}股), 止蝕位 {stop_loss_price:.2f}

最近10日數據:
{recent_summary}

請用繁體中文提供：
1. 走勢技術面點評。
2. 針對該配資建議的風險提示。
3. 給 iPhone 用戶的一句話總結。"""

                        chat_completion = client.chat.completions.create(
                            messages=[{"role": "user", "content": prompt}],
                            model="llama-3.3-70b-versatile",
                        )
                        st.info("### 🤖 Groq AI 專家分析")
                        st.write(chat_completion.choices[0].message.content)
                    except Exception as ai_e:
                        st.error(f"AI 分析出錯: {ai_e}")

        # 6. K 線圖表
        fig = go.Figure(data=[go.Candlestick(
            x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='K線'
        )])
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA20'], name='20MA', line=dict(color='orange')))
        fig.add_hline(y=stop_loss_price, line_dash="dash", line_color="red", annotation_text="止蝕位")
        
        fig.update_layout(xaxis_rangeslider_visible=False, height=450, margin=dict(l=5, r=5, t=5, b=5))
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.error(f"數據抓取失敗：{quote_data}")
        st.info("請檢查：1. API Key 是否正確 2. 代號是否有效 3. 是否超過免費版每分鐘 8 次的限制。")
