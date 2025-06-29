import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st

st.set_page_config(page_title="TGA流动性仪表盘", layout="wide")
st.title("📊 TGA账户与股市流动性分析仪表盘")

# 文件上传
tga_file = st.file_uploader("📤 上传TGA账户数据 (CSV)", type=["csv"])
signal_file = st.file_uploader("📤 上传策略信号数据 (CSV)", type=["csv"], key="backtest")

if tga_file:
    tga = pd.read_csv(tga_file, parse_dates=['date'])
    tga.set_index('date', inplace=True)
    tga = tga.sort_index()
    tga['ΔTGA'] = tga['tga_balance'].diff()

    spx = yf.download('^GSPC', start=tga.index.min(), end=tga.index.max() + pd.Timedelta(days=2))
    spx_weekly = spx['Adj Close'].resample('W-THU').last()
    spx_ret = spx_weekly.pct_change()

    df = pd.concat([tga['ΔTGA'], spx_ret.rename('spx_ret')], axis=1).dropna()

    st.subheader("📈 TGA余额与S&P500走势")
    fig1, ax1 = plt.subplots(figsize=(12, 5))
    ax1.plot(tga.index, tga['tga_balance'], color='blue', label='TGA余额')
    ax2 = ax1.twinx()
    ax2.plot(spx_weekly.index, spx_weekly, color='red', label='S&P 500')
    ax1.set_ylabel("TGA余额")
    ax2.set_ylabel("S&P 500")
    st.pyplot(fig1)

    st.subheader("📉 ΔTGA 与 股市收益率")
    fig2, ax2 = plt.subplots()
    sns.regplot(x=df['ΔTGA'], y=df['spx_ret'] * 100, ax=ax2)
    ax2.set_xlabel("ΔTGA（十亿美元）")
    ax2.set_ylabel("S&P500 周收益率 (%)")
    st.pyplot(fig2)

if signal_file:
    signal_df = pd.read_csv(signal_file, parse_dates=['date'])
    score_thresh = st.slider("🎯 情绪评分下限", 0, 100, 60)
    use_resonance = st.checkbox("仅选择共振 = 是", value=True)

    cond = signal_df['情绪评分'] >= score_thresh
    if use_resonance:
        cond &= signal_df['枢轴点共振'] == '是'

    signal_df['策略信号'] = cond.astype(int)
    signal_df['策略收益'] = signal_df['策略信号'] * signal_df['S&P500收益率(%)']
    signal_df['策略累计收益'] = (1 + signal_df['策略收益'] / 100).cumprod()
    signal_df['市场累计收益'] = (1 + signal_df['S&P500收益率(%)'] / 100).cumprod()

    st.subheader("📊 策略累计收益 vs 市场")
    fig_bt, ax_bt = plt.subplots()
    ax_bt.plot(signal_df['date'], signal_df['策略累计收益'], label='策略收益')
    ax_bt.plot(signal_df['date'], signal_df['市场累计收益'], label='市场收益', linestyle='--')
    ax_bt.legend()
    st.pyplot(fig_bt)
