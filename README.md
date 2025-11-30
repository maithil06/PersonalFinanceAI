# 📈 Personal Finance AI: Sentiment & Market Analyzer

A multi-agent AI system that performs **portfolio-level sentiment analysis** on stock tickers. It combines recent market data from Yahoo Finance with curated, high-reliability financial news to generate an explainable **Portfolio Sentiment Analysis** in Markdown.


<img width="1920" height="1038" alt="Screenshot (543)" src="https://github.com/user-attachments/assets/3bc557d2-9312-4890-80d5-c523d6f9254a" />


> ⚠️ This tool is for research and educational purposes only. It is **not** financial advice.

---

## 🚀 What This App Actually Does

Given one or more stock tickers (e.g. `AAPL, MSFT, NVDA`), the app:

1. **Fetches recent market data** for each ticker using `yfinance-cache` (with a safe fallback to `yfinance` if needed).
2. Computes **technical indicators & performance metrics** (SMA10/20/50, 7-day & ~30-day returns, volatility, volume trends, etc.) and formats them into a structured Markdown block for each ticker.
3. Feeds this structured market data into a **multi-agent team** built with the **Agno** framework:
   - A **News Reliability Analyst** agent that uses DuckDuckGo tools to find **only credible financial news**.
   - A **Portfolio Sentiment Synthesizer** agent that merges news + market data into a full portfolio report.
4. Returns a **single coherent Markdown report** in the Gradio interface, including:
   - Per-stock analysis,
   - A portfolio-level sentiment index,
   - A table of individual stock scores.

---

## 🔍 Data & Features (From the Code)

### 1. Market Data & Technicals

`get_market_data(ticker, period="3mo")`:

- Uses **`yfc` (yfinance-cache)** if installed, otherwise gracefully falls back to **`yfinance`**.
- Fetches historical OHLCV data over the last 3 months.
- Computes:

  - **Simple Moving Averages:**
    - SMA-10, SMA-20, SMA-50 on closing prices
  - **Returns & Volatility:**
    - Daily returns (%)
    - Standard deviation of daily returns as **volatility**
    - **7-day change** and **~30-day change** in price
  - **Volume Analysis:**
    - Average volume (full period)
    - Recent volume (last 5 days)
    - Volume trend classified as **Increasing / Decreasing / Stable**
  - **Trend Classification:**
    - `Strong Uptrend`, `Strong Downtrend`, `Uptrend`, `Downtrend`, or `Sideways` based on the relationship between price and SMAs.

- Pulls **fundamentals & metadata** from `stock.info` (where available), including:
  - Company name, sector, industry
  - 52-week high/low
  - 50- and 200-day averages
  - Market cap, trailing/forward P/E, PEG, price-to-book
  - Dividend yield/rate & payout ratio
  - Beta
  - Analyst recommendation (e.g. `buy`, `hold`, `sell`)
  - Mean target price and number of analyst opinions

- Formats all of this into a **Markdown block** for each ticker:

  ```markdown
  ## 📈 TECHNICAL & FUNDAMENTAL DATA: TICKER

  ### 🏢 COMPANY INFO
  - Name, Sector, Industry

  ### 💰 CURRENT PRICE METRICS
  ...

  ### 📊 PRICE PERFORMANCE
  - 7-Day Change
  - 30-Day Change
  - Average Daily Return
  - Daily Volatility

  ### 📉 TECHNICAL INDICATORS
  - SMA10, SMA20, SMA50 + whether current price is above/below each
  - Trend classification

  ### 📦 VOLUME ANALYSIS
  - Average volume, recent volume, volume trend, beta

  ### 💼 VALUATION RATIOS
  ### 💵 DIVIDEND INFORMATION
  ### 🎯 ANALYST CONSENSUS
  ### 📊 TECHNICAL SUMMARY
