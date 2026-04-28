import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from groq import Groq  # 引入 Groq

# 1. 頁面基本設定
st.set_page_config(page_title="Groq Stock AI", layout="wide")
st.title("📈 Groq 智能投資工具")

# 2. 側邊欄：設定
st.sidebar.header("⚙️ 系統設定")
# 請到 https://console.groq.com/keys 申請免費 API Key
groq_api_key = st.sidebar.text_input("輸入 Groq API Key", type="password")
ticker_input = st.sidebar.text_input("股票代號 (例: 0700.HK, TSLA)", "0700.HK").upper()
total_capital = st.sidebar.number_input("可用本金", min_value=0, value=100000)
risk_percent = st.sidebar.slider("單筆最大風險 (%)", 0.5, 5.0, 2.0, 0.5) / 100

try:
    # 3. 抓取數據
    df = yf.download(ticker_input, period="1y", interval="1d", auto_adjust=True)
    
    if not df.empty:
        # 計算 20MA
        df['SMA20'] = df['Close'].rolling(window=20).mean()
        
        # 提取最新數據 (使用 flatten 確保安全)
        current_price = float(df['Close'].values.flatten()[-1])
        sma_values = df['SMA20'].values.flatten()
        last_sma = float(sma_values[-1]) if not pd.isna(sma_values[-1]) else current_price
        
        # 4. 資金控管邏輯
        stop_loss_price = current_price * 0.95  # 5% 停損
        risk_money = total_capital * risk_percent
        price_diff = current_price - stop_loss_price
        suggested_shares = int(risk_money / price_diff) if price_diff > 0 else 0

        # 5. 頂部儀表板
        c1, c2, c3 = st.columns(3)
        c1.metric("現價", f"{current_price:.2f}")
        trend_label = "多頭 🟢" if current_price > last_sma else "空頭 🔴"
        c2.metric("趨勢", trend_label)
        c3.metric("建議股數", f"{suggested_shares}")

        # 6. Groq AI 分析模組
        st.markdown("---")
        if st.button("🤖 啟動 Groq Llama-3 AI 分析"):
            if not groq_api_key:
                st.error("請在左側輸入 Groq API Key。")
            else:
                with st.spinner("Groq 正在極速分析中..."):
                    try:
                        # 初始化 Groq 客戶端
                        client = Groq(api_key=groq_api_key)
                        
                        # 準備數據摘要 (最近10天)
                        recent_summary = df[['Close', 'SMA20']].tail(10).to_string()
                        
                        # 調用 Llama 3.3 模型 (目前 Groq 上最強且穩定的免費模型)
                        completion = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[
                                {
                                    "role": "system",
                                    "content": "你是一位精通港股與美股的技術分析專家，擅長使用均線理論提供簡潔的操作建議。"
                                },
                                {
                                    "role": "user",
                                    "content": f"""
                                    分析股票: {ticker_input}
                                    現價: {current_price:.2f}
                                    20MA: {last_sma:.2f}
                                    趨勢: {trend_label}
                                    
                                    最近10日數據:
                                    {recent_summary}
                                    
                                    請以繁體中文提供：
                                    1. 走勢點評。
                                    2. 具體的操作建議（入貨/觀望/止蝕）。
                                    3. 給 iPhone 用戶的一句話總結。
                                    回答要極簡，不要廢話。
                                    """
                                }
                            ],
                            temperature=0.5,
                            max_tokens=500
                        )
                        
                        st.info("### 🤖 Groq AI 專家建議")
                        st.write(completion.choices[0].message.content)
                    except Exception as ai_err:
                        st.error(f"AI 分析失敗: {ai_err}")

        # 7. 圖表
        fig = go.Figure(data=[go.Candlestick(
            x=df.index,
            open=df['Open'].values.flatten(),
            high=df['High'].values.flatten(),
            low=df['Low'].values.flatten(),
            close=df['Close'].values.flatten(),
            name='K線'
        )])
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA20'].values.flatten(), name='20MA', line=dict(color='orange')))
        fig.update_layout(xaxis_rangeslider_visible=False, height=450, margin=dict(l=5, r=5, t=5, b=5))
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("找不到數據，請檢查代號。")
except Exception as e:
    st.error(f"錯誤: {e}")
