import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import google.generativeai as genai

# 1. 頁面基本設定
st.set_page_config(page_title="AI Stock Pro", layout="wide")
st.title("📈 AI 智能投資配資工具")

# 2. 側邊欄：參數設定與 API Key
st.sidebar.header("⚙️ 系統設定")
api_key = st.sidebar.text_input("輸入 Gemini API Key", type="password", help="請到 Google AI Studio 申請免費 Key")
ticker_input = st.sidebar.text_input("股票代號 (例: 0700.HK, NVDA)", "0700.HK").upper()
total_capital = st.sidebar.number_input("可用本金", min_value=0, value=100000)
risk_percent = st.sidebar.slider("單筆最大風險 (%)", 0.5, 5.0, 2.0, 0.5) / 100

# 設定 Gemini
if api_key:
    genai.configure(api_key=api_key)

try:
    # 3. 抓取數據
    df = yf.download(ticker_input, period="1y", interval="1d", auto_adjust=True)
    
    if not df.empty:
        # 計算 20MA
        df['SMA20'] = df['Close'].rolling(window=20).mean()
        
        # 提取最新數據 (使用數據壓平技術確保 scalar 轉換成功)
        current_price = float(df['Close'].values.flatten()[-1])
        sma_values = df['SMA20'].values.flatten()
        last_sma = float(sma_values[-1]) if not pd.isna(sma_values[-1]) else current_price
        
        # 4. 資金控管邏輯
        stop_loss_price = current_price * 0.95  # 預設 5% 停損
        risk_money = total_capital * risk_percent
        price_diff = current_price - stop_loss_price
        suggested_shares = int(risk_money / price_diff) if price_diff > 0 else 0

        # 5. 頂部儀表板
        c1, c2, c3 = st.columns(3)
        c1.metric("當前股價", f"{current_price:.2f}")
        
        trend_label = "多頭 🟢" if current_price > last_sma else "空頭 🔴"
        c2.metric("20MA 趨勢", trend_label)
        
        c3.metric("建議入貨量", f"{suggested_shares} 股")

        # 6. AI 深度分析模組
        st.markdown("---")
        if st.button("🤖 啟動 Gemini AI 專家分析"):
            if not api_key:
                st.error("請在左側選單輸入 API Key 才能啟動 AI 分析。")
            else:
                with st.spinner("AI 正在閱讀 K 線與均線數據..."):
                    try:
                        # 準備傳送給 AI 的簡化數據
                        recent_summary = df[['Close', 'SMA20']].tail(15).to_string()
                        
                        # 嘗試最通用的模型名稱
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        
                        prompt = f"""
                        你是一位資深股票分析專家。請分析股票 {ticker_input}：
                        
                        [最新數據]
                        - 現價: {current_price:.2f}
                        - 20日均線 (20MA): {last_sma:.2f}
                        - 趨勢狀態: {trend_label}
                        
                        [最近15日歷史數據]
                        {recent_summary}
                        
                        請根據以上數據提供：
                        1. 走勢點評 (判斷支撐位或壓力位)。
                        2. 具體操作建議 (現在適合入貨、加倉還是觀望？)。
                        3. 給投資者的風險提示。
                        請用繁體中文回答，語氣要專業且精簡。
                        """
                        
                        response = model.generate_content(prompt)
                        st.info("### 🤖 Gemini 投資建議")
                        st.write(response.text)
                    except Exception as ai_err:
                        st.error(f"AI 分析失敗: {ai_err}")

        # 7. 動態 K 線圖
        st.subheader("🔍 市場走勢圖")
        fig = go.Figure(data=[go.Candlestick(
            x=df.index,
            open=df['Open'].values.flatten(),
            high=df['High'].values.flatten(),
            low=df['Low'].values.flatten(),
            close=df['Close'].values.flatten(),
            name='K線'
        )])
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA20'].values.flatten(), name='20MA', line=dict(color='orange', width=2)))
        
        fig.update_layout(
            xaxis_rangeslider_visible=False,
            height=500,
            margin=dict(l=5, r=5, t=10, b=10),
            template="plotly_white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.caption(f"數據更新時間: {df.index[-1].strftime('%Y-%m-%d')}")

    else:
        st.warning("無法獲取數據，請檢查股票代號是否正確。")

except Exception as e:
    st.error(f"系統運行出錯: {e}")
