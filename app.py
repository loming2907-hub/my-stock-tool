import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import google.generativeai as genai  # 新增 AI 套件

st.set_page_config(page_title="AI Stock Analyzer", layout="wide")
st.title("📈 AI 智能投資工具")

# --- 側邊欄設定 ---
st.sidebar.header("⚙️ 設定")
api_key = st.sidebar.text_input("輸入 Gemini API Key", type="password") # 建議把 Key 放這
ticker = st.sidebar.text_input("股票代號", "0700.HK").upper()
capital = st.sidebar.number_input("本金", value=100000)
risk_pct = st.sidebar.slider("風險 (%)", 0.5, 5.0, 2.0) / 100

if api_key:
    genai.configure(api_key=api_key)

try:
    df = yf.download(ticker, period="1y", interval="1d", auto_adjust=True)
    
    if not df.empty:
        df['SMA20'] = df['Close'].rolling(window=20).mean()
        current_price = float(df['Close'].values.flatten()[-1])
        last_sma = float(df['SMA20'].values.flatten()[-1]) if not pd.isna(df['SMA20'].values.flatten()[-1]) else current_price
        
        # 顯示基礎指標
        c1, c2, c3 = st.columns(3)
        c1.metric("現價", f"{current_price:.2f}")
        c2.metric("趨勢", "多頭 🟢" if current_price > last_sma else "空頭 🔴")
        
        # --- AI 分析按鈕 ---
        st.markdown("---")
        if st.button("🤖 啟動 Gemini AI 深度分析"):
            if not api_key:
                st.warning("請先在左側輸入 API Key")
            else:
                with st.spinner("Gemini 正在分析數據中..."):
                    # 準備數據給 AI
                    recent_data = df.tail(10)[['Close', 'SMA20']].to_string()
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    prompt = f"""
                    你是一位專業的股票分析師。請分析以下 {ticker} 的數據：
                    最近 10 日價格與 20MA 均線：
                    {recent_data}
                    
                    當前價格為 {current_price:.2f}，20MA 為 {last_sma:.2f}。
                    請用繁體中文提供：
                    1. 短期走勢評論
                    2. 給投資者的入貨或持倉建議
                    3. 潛在風險提示
                    """
                    
                    response = model.generate_content(prompt)
                    st.info("### 🤖 Gemini AI 分析結果")
                    st.write(response.text)

        # 畫圖
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'].values.flatten(), high=df['High'].values.flatten(), low=df['Low'].values.flatten(), close=df['Close'].values.flatten())])
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA20'].values.flatten(), name='20MA', line=dict(color='orange')))
        fig.update_layout(xaxis_rangeslider_visible=False, height=400)
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.error("代號無效")
except Exception as e:
    st.error(f"錯誤: {e}")
