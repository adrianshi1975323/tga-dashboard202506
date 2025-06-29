# TGA流动性分析仪表盘（含中文标签与视觉优化）

import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
import base64
import os

plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.unicode_minus'] = False

st.set_page_config(page_title="TGA流动性仪表盘", layout="wide")
st.title("📊 TGA账户与股市流动性分析仪表盘")

# 示例数据下载按钮
def file_download_link(filename, link_text):
    with open(filename, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="{os.path.basename(filename)}">{link_text}</a>'
        return href

st.markdown("### 🧪 示例数据下载")
st.markdown(file_download_link("sample_tga.csv", "📥 下载 TGA账户示例数据 sample_tga.csv"), unsafe_allow_html=True)
st.markdown(file_download_link("sample_backtest_signals_clean.csv", "📥 下载 策略信号示例数据 sample_backtest_signals_clean.csv"), unsafe_allow_html=True)

# 文件上传
tga_file = st.file_uploader("📤 上传TGA账户数据 (CSV，含 'date' 和 'tga_balance')", type=["csv"])
signal_file = st.file_uploader("📤 上传策略信号数据 (CSV，含 'date', '情绪评分', '枢轴点共振', 'S&P500收益率(%)')", type=["csv"], key="backtest")

if tga_file:
    tga = pd.read_csv(tga_file, parse_dates=['date'])
    tga.set_index('date', inplace=True)
    tga = tga.sort_index()
    tga['ΔTGA'] = tga['tga_balance'].diff()

    spx = yf.download('^GSPC', start=tga.index.min(), end=tga.index.max() + pd.Timedelta(days=2), group_by='column')

    # 兼容不同列结构：尝试获取价格序列
    if 'Adj Close' in spx.columns:
        price_series = spx['Adj Close']
    elif ('^GSPC', 'Adj Close') in spx.columns:
        price_series = spx[('^GSPC', 'Adj Close')]
    else:
        st.error("❌ 获取 S&P500 数据失败：未找到 'Adj Close' 列")
        st.stop()

    spx_weekly = price_series.resample('W-THU').last()
    spx_ret = spx_weekly.pct_change()

    df = pd.concat([tga['ΔTGA'], spx_ret.rename('spx_ret')], axis=1).dropna()

    st.subheader("📈 TGA账户余额 与 标普500 指数走势")
    fig1, ax1 = plt.subplots(figsize=(12, 5))
    ax1.plot(tga.index, tga['tga_balance'], color='dodgerblue', label='TGA账户余额')
    ax2 = ax1.twinx()
    ax2.plot(spx_weekly.index, spx_weekly, color='crimson', label='S&P 500 指数')
    ax1.set_ylabel("TGA余额（十亿美元）", fontsize=12)
    ax2.set_ylabel("S&P500", fontsize=12)
    ax1.set_title("TGA账户与股市指数走势对比", fontsize=14)
    ax1.legend(loc='upper left')
    ax2.legend(loc='upper right')
    st.pyplot(fig1)

    st.subheader("📉 TGA变动量 与 股市收益率 散点图")
    fig2, ax2 = plt.subplots()
    sns.set_style("whitegrid")
    sns.regplot(x=df['ΔTGA'], y=df['spx_ret'] * 100, ax=ax2, scatter_kws={'color': 'teal'}, line_kws={'color': 'darkred'})
    ax2.set_xlabel("ΔTGA（周变动，十亿美元）")
    ax2.set_ylabel("标普500周收益率（%）")
    ax2.set_title("TGA资金流入/流出 vs 股市反应", fontsize=13)
    st.pyplot(fig2)

if signal_file:
    signal_df = pd.read_csv(signal_file, parse_dates=['date'])
    score_thresh = st.slider("🎯 策略筛选：情绪评分不低于", 0, 100, 60)
    use_resonance = st.checkbox("✅ 仅选择 '枢轴点共振 = 是'", value=True)

    cond = signal_df['情绪评分'] >= score_thresh
    if use_resonance:
        cond &= signal_df['枢轴点共振'] == '是'

    signal_df['策略信号'] = cond.astype(int)
    signal_df['策略收益'] = signal_df['策略信号'] * signal_df['S&P500收益率(%)']
    signal_df['策略累计收益'] = (1 + signal_df['策略收益'] / 100).cumprod()
    signal_df['市场累计收益'] = (1 + signal_df['S&P500收益率(%)'] / 100).cumprod()

    st.subheader("📊 策略收益 vs 市场收益 累积图")
    fig_bt, ax_bt = plt.subplots()
    ax_bt.plot(signal_df['date'], signal_df['策略累计收益'], label='📈 策略表现', color='forestgreen', linewidth=2)
    ax_bt.plot(signal_df['date'], signal_df['市场累计收益'], label='📉 市场基准', linestyle='--', color='gray')
    ax_bt.set_ylabel("收益倍数")
    ax_bt.set_title("策略累计收益 vs 标普500", fontsize=13)
    ax_bt.legend()
    st.pyplot(fig_bt)

    # 简要统计
    st.markdown("### 📌 策略简要表现指标")
    total_return = signal_df['策略累计收益'].iloc[-1] - 1
    market_return = signal_df['市场累计收益'].iloc[-1] - 1
    win_rate = (signal_df['策略收益'] > 0).mean()
    st.success(f"📈 策略总收益：{total_return:.2%} | 📉 市场总收益：{market_return:.2%} | 🎯 策略胜率：{win_rate:.1%}")
