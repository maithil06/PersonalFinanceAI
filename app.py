import gradio as gr
import os
from datetime import datetime, timedelta
from agno.agent import Agent
from agno.team import Team
from agno.models.anthropic import Claude
from agno.db.sqlite import SqliteDb
from agno.tools.duckduckgo import DuckDuckGoTools
import sys

# Global variable to store agent team
agent_team = None

def test_dependencies():
    """Test if all dependencies are working"""
    results = []
    
    # Test yfinance-cache
    try:
        import yfc as yf
        results.append("✅ yfinance-cache imported successfully")
        try:
            stock = yf.Ticker("AAPL")
            hist = stock.history(period="5d")
            if len(hist) > 0:
                results.append(f"✅ yfinance-cache working - AAPL price: ${hist['Close'].iloc[-1]:.2f}")
            else:
                results.append("❌ yfinance-cache - no data returned")
        except Exception as e:
            results.append(f"❌ yfinance-cache fetch failed: {str(e)}")
    except ImportError:
        results.append("⚠️ yfinance-cache not installed, trying regular yfinance")
        try:
            import yfinance as yf
            results.append("✅ yfinance imported successfully")
            try:
                stock = yf.Ticker("AAPL")
                hist = stock.history(period="5d")
                if len(hist) > 0:
                    results.append(f"✅ yfinance working - AAPL price: ${hist['Close'].iloc[-1]:.2f}")
                else:
                    results.append("❌ yfinance - no data returned")
            except Exception as e:
                results.append(f"❌ yfinance fetch failed: {str(e)}")
        except ImportError as e:
            results.append(f"❌ No yfinance package installed: {str(e)}")
    
    # Test pandas
    try:
        import pandas as pd
        results.append(f"✅ pandas {pd.__version__}")
    except ImportError as e:
        results.append(f"❌ pandas not installed: {str(e)}")
    
    # Test anthropic
    try:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            results.append("✅ ANTHROPIC_API_KEY found")
        else:
            results.append("❌ ANTHROPIC_API_KEY not set")
    except Exception as e:
        results.append(f"❌ API key check failed: {str(e)}")
    
    # Test network
    try:
        import urllib.request
        urllib.request.urlopen('https://www.google.com', timeout=5)
        results.append("✅ Network connectivity OK")
    except Exception as e:
        results.append(f"❌ Network issue: {str(e)}")
    
    return "\n".join(results)

print("=" * 60)
print("DEPENDENCY CHECK")
print("=" * 60)
print(test_dependencies())
print("=" * 60)

def get_market_data(ticker, period="3mo"):
    """
    Get comprehensive technical and fundamental data using yfinance with caching
    
    Parameters:
    ticker (str): Stock ticker symbol
    period (str): Data period (1mo, 3mo, 6mo, 1y, etc.)
    """
    try:
        # Import check - try yfinance-cache first, fallback to regular yfinance
        try:
            import yfc as yf  # yfinance-cache
            print(f"Using yfinance-cache for {ticker}")
        except ImportError:
            try:
                import yfinance as yf
                print(f"Using regular yfinance for {ticker}")
            except ImportError as e:
                return f"❌ Import Error: {str(e)}\n\nPlease ensure 'yfinance-cache' is in your requirements.txt file.", None
        
        try:
            import pandas as pd
            from time import sleep
        except ImportError as e:
            return f"❌ Import Error: {str(e)}", None
        
        # Fetch data with yfinance-cache (automatically handles caching and retries)
        try:
            print(f"Fetching data for {ticker}...")
            stock = yf.Ticker(ticker)
            
            # Get historical data
            hist = stock.history(period=period)
            
            if hist is None or len(hist) == 0:
                return f"❌ No data available for {ticker}. Please verify the ticker symbol is correct.", None
            
            print(f"Successfully fetched {len(hist)} days of data for {ticker}")
            
        except Exception as e:
            return f"❌ Error fetching history for {ticker}: {str(e)}\n\nPlease try again or use a different ticker.", None
        
        # Get stock info with error handling
        info = {}
        try:
            info = stock.info
            print(f"Successfully fetched info for {ticker}")
        except Exception as e:
            print(f"Warning: Could not fetch detailed info for {ticker}: {str(e)}")
            # Continue with just historical data
            info = {}
        
        # Calculate technical indicators
        hist['SMA_10'] = hist['Close'].rolling(window=10).mean()
        hist['SMA_20'] = hist['Close'].rolling(window=20).mean()
        hist['SMA_50'] = hist['Close'].rolling(window=50).mean()
        hist['Daily_Return'] = hist['Close'].pct_change() * 100
        
        # Current metrics
        current_price = hist['Close'].iloc[-1]
        sma_10 = hist['SMA_10'].iloc[-1] if not pd.isna(hist['SMA_10'].iloc[-1]) else None
        sma_20 = hist['SMA_20'].iloc[-1] if not pd.isna(hist['SMA_20'].iloc[-1]) else None
        sma_50 = hist['SMA_50'].iloc[-1] if not pd.isna(hist['SMA_50'].iloc[-1]) else None
        
        # Volatility
        volatility = hist['Daily_Return'].std()
        avg_daily_return = hist['Daily_Return'].mean()
        
        # Price changes
        if len(hist) >= 7:
            change_7d = ((hist['Close'].iloc[-1] - hist['Close'].iloc[-7]) / hist['Close'].iloc[-7]) * 100
        else:
            change_7d = 0
        
        if len(hist) >= 30:
            change_30d = ((hist['Close'].iloc[-1] - hist['Close'].iloc[-30]) / hist['Close'].iloc[-30]) * 100
        else:
            change_30d = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
        
        # Volume analysis
        avg_volume = hist['Volume'].mean()
        recent_volume = hist['Volume'].iloc[-5:].mean()  # Last 5 days
        volume_trend = "Increasing" if recent_volume > avg_volume * 1.1 else "Decreasing" if recent_volume < avg_volume * 0.9 else "Stable"
        
        # Trend analysis
        if sma_10 and sma_20 and sma_50:
            if current_price > sma_10 > sma_20 > sma_50:
                trend = "Strong Uptrend"
            elif current_price < sma_10 < sma_20 < sma_50:
                trend = "Strong Downtrend"
            elif current_price > sma_20:
                trend = "Uptrend"
            elif current_price < sma_20:
                trend = "Downtrend"
            else:
                trend = "Sideways"
        else:
            trend = "Insufficient data"
        
        # Safely format market cap
        market_cap_str = "N/A"
        if info.get('marketCap'):
            try:
                market_cap_str = f"${info.get('marketCap'):,}"
            except:
                market_cap_str = str(info.get('marketCap'))
        
        # Safely format dividend yield
        div_yield_str = "N/A"
        if info.get('dividendYield'):
            try:
                div_yield_str = f"{info.get('dividendYield') * 100:.2f}%"
            except:
                div_yield_str = str(info.get('dividendYield'))
        
        # Build comprehensive summary with safe formatting
        market_summary = f"""
## 📈 TECHNICAL & FUNDAMENTAL DATA: {ticker}

### 🏢 COMPANY INFO
- **Name:** {info.get('longName', 'N/A')}
- **Sector:** {info.get('sector', 'N/A')}
- **Industry:** {info.get('industry', 'N/A')}

### 💰 CURRENT PRICE METRICS
- **Current Price:** ${current_price:.2f}
- **52-Week High:** ${info.get('fiftyTwoWeekHigh', 'N/A')}
- **52-Week Low:** ${info.get('fiftyTwoWeekLow', 'N/A')}
- **50-Day Average:** ${info.get('fiftyDayAverage', 'N/A')}
- **200-Day Average:** ${info.get('twoHundredDayAverage', 'N/A')}

### 📊 PRICE PERFORMANCE
- **7-Day Change:** {change_7d:+.2f}%
- **30-Day Change:** {change_30d:+.2f}%
- **Average Daily Return:** {avg_daily_return:+.2f}%
- **Daily Volatility:** {volatility:.2f}%

### 📉 TECHNICAL INDICATORS
- **10-Day SMA:** {"$" + f"{sma_10:.2f}" if sma_10 else "N/A"} {('✅ Above' if current_price > sma_10 else '⚠️ Below') if sma_10 else ""}
- **20-Day SMA:** {"$" + f"{sma_20:.2f}" if sma_20 else "N/A"} {('✅ Above' if current_price > sma_20 else '⚠️ Below') if sma_20 else ""}
- **50-Day SMA:** {"$" + f"{sma_50:.2f}" if sma_50 else "N/A"} {('✅ Above' if current_price > sma_50 else '⚠️ Below') if sma_50 else ""}
- **Trend:** {trend}

### 📦 VOLUME ANALYSIS
- **Average Volume:** {avg_volume:,.0f}
- **Recent Volume (5d avg):** {recent_volume:,.0f}
- **Volume Trend:** {volume_trend}
- **Beta:** {info.get('beta', 'N/A')}

### 💼 VALUATION RATIOS
- **Market Cap:** {market_cap_str}
- **P/E Ratio (Trailing):** {info.get('trailingPE', 'N/A')}
- **Forward P/E:** {info.get('forwardPE', 'N/A')}
- **PEG Ratio:** {info.get('pegRatio', 'N/A')}
- **Price to Book:** {info.get('priceToBook', 'N/A')}

### 💵 DIVIDEND INFORMATION
- **Dividend Yield:** {div_yield_str}
- **Dividend Rate:** ${info.get('dividendRate', 'N/A')}
- **Payout Ratio:** {info.get('payoutRatio', 'N/A')}

### 🎯 ANALYST CONSENSUS
- **Recommendation:** {info.get('recommendationKey', 'N/A').upper() if info.get('recommendationKey') else 'N/A'}
- **Target Price:** ${info.get('targetMeanPrice', 'N/A')}
- **Number of Analysts:** {info.get('numberOfAnalystOpinions', 'N/A')}

### 📊 TECHNICAL SUMMARY
**Price Position:** {'Bullish' if change_30d > 5 else 'Bearish' if change_30d < -5 else 'Neutral'} (30-day: {change_30d:+.2f}%)
**Momentum:** {'Strong' if abs(avg_daily_return) > 1 else 'Moderate' if abs(avg_daily_return) > 0.3 else 'Weak'}
**Volatility Level:** {'High' if volatility > 3 else 'Moderate' if volatility > 1.5 else 'Low'}
**Overall Technical Signal:** {trend}

---
"""
        
        # Store structured data
        data = {
            'ticker': ticker,
            'current_price': current_price,
            'change_7d': change_7d,
            'change_30d': change_30d,
            'trend': trend,
            'volatility': volatility,
            'volume_trend': volume_trend,
            'analyst_rating': info.get('recommendationKey', 'N/A'),
            'market_cap': info.get('marketCap', 'N/A'),
            'pe_ratio': info.get('trailingPE', 'N/A'),
        }
        
        return market_summary, data
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return f"❌ Unexpected error fetching data for {ticker}:\n\n{str(e)}\n\nDetails:\n{error_details}", None

def initialize_agents():
    """Initialize the sentiment analysis agent team"""
    global agent_team
    
    if agent_team is not None:
        return agent_team
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found. Please set it in Hugging Face Spaces secrets.")
    
    db = SqliteDb(db_file="sentiment_agents.db")
    
    # Agent 1: News Collector
    news_collector = Agent(
        name="News Reliability Analyst",
        role="Collect and verify news from reliable financial sources only",
        model=Claude(id="claude-sonnet-4-20250514", api_key=api_key),
        tools=[DuckDuckGoTools()],
        instructions=[
            "You are a news reliability specialist. Your PRIMARY task is to collect and present news ONLY from highly credible sources.",
            "",
            "**STRICT SOURCE REQUIREMENTS - ONLY USE:**",
            "- Bloomberg, Reuters, Financial Times, Wall Street Journal, CNBC, MarketWatch",
            "- Official company press releases and SEC filings (sec.gov, investor relations pages)",
            "- Major business publications: Forbes, Fortune, Business Insider (verified articles)",
            "- Established financial analysis: Morningstar, S&P Global, Moody's",
            "",
            "**IMMEDIATELY REJECT:**",
            "- Social media (Twitter/X, Reddit, StockTwits, Facebook)",
            "- Anonymous blogs, personal websites, or unverified sources",
            "- Promotional content, advertorials, or sponsored posts",
            "",
            "**Your Process:**",
            "1. For EACH stock, search for recent news (last 30 days)",
            "2. Verify EVERY source against the approved list above",
            "3. Present findings in a clear, structured format",
            "",
            "**REQUIRED OUTPUT FORMAT FOR EACH STOCK:**",
            "",
            "## 📰 NEWS ANALYSIS: [TICKER]",
            "",
            "**Reliable Sources Found:** [Number]",
            "",
            "### Recent News Items:",
            "",
            "**1. [Headline]**",
            "- **Source:** [Publication Name]",
            "- **Date:** [YYYY-MM-DD]",
            "- **Summary:** [2-3 sentences explaining the news]",
            "- **Sentiment:** [Positive/Negative/Neutral - with brief explanation]",
            "",
            "**2. [Headline]**",
            "- **Source:** [Publication Name]",
            "- **Date:** [YYYY-MM-DD]",
            "- **Summary:** [2-3 sentences]",
            "- **Sentiment:** [Positive/Negative/Neutral - with explanation]",
            "",
            "[Continue for all relevant news items, minimum 3-5 per stock]",
            "",
            "### Key Sentiment Drivers:",
            "- **Positive Factors:** [List key positive developments from verified sources]",
            "- **Negative Factors:** [List key negative developments from verified sources]",
            "- **Neutral/Mixed:** [Any ambiguous or balanced news]",
            "",
            "**News Sentiment Preliminary Score:** [Estimate -50 to +50 based on news alone]",
            "",
            "---",
            "",
            "**CRITICAL:** If you cannot find at least 3 reliable news sources for a stock, explicitly state:",
            "'⚠️ Insufficient reliable news coverage found for [TICKER]. Only [X] credible sources located.'",
            "",
            "**Remember:** Every news item MUST include source name, date, summary, and sentiment assessment.",
        ],
        db=db,
        add_history_to_context=True,
        markdown=True,
    )
    
    # Agent 2: Sentiment Scorer
    sentiment_scorer = Agent(
        name="Portfolio Sentiment Synthesizer",
        role="Synthesize news and market data into comprehensive portfolio sentiment index",
        model=Claude(id="claude-sonnet-4-20250514", api_key=api_key),
        tools=[],
        instructions=[
            "You are the lead sentiment analyst. You will receive:",
            "1. Detailed news analysis from the News Reliability Analyst (with specific news items)",
            "2. Market data with price action, volume, fundamentals, and analyst ratings",
            "",
            "Your job is to synthesize BOTH into a comprehensive report.",
            "",
            "**Output Structure:**",
            "",
            "# 📊 PORTFOLIO SENTIMENT ANALYSIS",
            "",
            "## 📰 NEWS SUMMARY",
            "[Present the news analysis from the News Reliability Analyst - include headlines, sources, dates]",
            "",
            "## 📈 MARKET DATA SUMMARY",
            "[Present key market metrics for each stock]",
            "",
            "## 🔍 DETAILED ANALYSIS BY STOCK",
            "",
            "### [TICKER 1]",
            "",
            "**Recent News Highlights:**",
            "- [Key news point 1 with source]",
            "- [Key news point 2 with source]",
            "- [Key news point 3 with source]",
            "",
            "**Market Performance:**",
            "- Price trend: [analysis]",
            "- Volume: [analysis]",
            "- Analyst sentiment: [ratings]",
            "",
            "**Positive Factors:**",
            "1. [Factor from news or data]",
            "2. [Factor from news or data]",
            "",
            "**Negative Factors:**",
            "1. [Factor from news or data]",
            "2. [Factor from news or data]",
            "",
            "**Individual Sentiment Score: [X/100]**",
            "**Rationale:** [Explain the score based on news + data]",
            "",
            "[Repeat for each stock]",
            "",
            "---",
            "",
            "## 💡 REASONING",
            "",
            "**Methodology:**",
            "- News weight: 50% (recent news 60%, older 40%)",
            "- Market data weight: 50%",
            "- [Explain any adjustments made]",
            "",
            "**Key Findings:**",
            "- [Most important discovery 1]",
            "- [Most important discovery 2]",
            "- [Most important discovery 3]",
            "",
            "**Data Quality Assessment:**",
            "- News coverage: [High/Medium/Low for each stock]",
            "- Market data: [Complete/Partial/Limited]",
            "",
            "**Limitations:**",
            "- [Any stocks with insufficient data]",
            "- [Any caveats about the analysis]",
            "",
            "---",
            "",
            "## 🎯 FINAL SENTIMENT INDEX",
            "",
            "### Portfolio Overall Sentiment: **[Score from -100 to +100]**",
            "",
            "**Confidence Level:** [High/Medium/Low]",
            "",
            "**Outlook Summary:**",
            "[2-3 sentences on overall portfolio sentiment based on all analyzed factors]",
            "",
            "### Individual Stock Scores:",
            "",
            "| Ticker | Score | Key Driver | Confidence |",
            "|--------|-------|------------|------------|",
            "| [TICKER] | [X/100] | [Main factor] | [H/M/L] |",
            "",
            "---",
            "",
            "⚠️ **Disclaimer:** This analysis is based on available data and should not be considered investment advice.",
        ],
        db=db,
        add_history_to_context=True,
        markdown=True,
    )
    
    # Team Lead
    agent_team = Team(
        name="Portfolio Sentiment Analysis Team",
        model=Claude(id="claude-sonnet-4-20250514", api_key=api_key),
        members=[news_collector, sentiment_scorer],
        instructions=[
            "You coordinate portfolio sentiment analysis.",
            "",
            "**Workflow:**",
            "1. Receive portfolio stocks and market data from user",
            "2. News Reliability Analyst: gather verified news for each stock",
            "3. Portfolio Sentiment Synthesizer: combine news + market data for final assessment",
            "4. Present comprehensive analysis",
            "",
            "**Quality Control:**",
            "- Verify all news sources are reliable",
            "- Use the provided market data from yfinance",
            "- Reject social media and unverified sources",
            "- Flag stocks with insufficient data",
        ],
        markdown=True,
    )
    
    return agent_team

def analyze_portfolio(portfolio_text):
    """Analyze portfolio sentiment"""
    try:
        # Initialize agents if needed
        team = initialize_agents()
        
        # Parse tickers
        if not portfolio_text or not portfolio_text.strip():
            return "❌ Please enter at least one stock ticker."
        
        tickers = [t.strip().upper() for t in portfolio_text.replace('\n', ',').split(',') if t.strip()]
        
        if not tickers:
            return "❌ Please enter valid stock tickers."
        
        # Fetch market data for all stocks
        market_data_summary = "# Market Data from YFinance\n\n"
        all_data = {}
        errors = []
        
        for ticker in tickers:
            data_text, data_dict = get_market_data(ticker)
            if data_dict is None:
                errors.append(f"- {ticker}: Failed to fetch data")
            market_data_summary += data_text + "\n---\n\n"
            all_data[ticker] = data_dict
        
        # If all tickers failed, return error
        if len(errors) == len(tickers):
            return f"❌ **All tickers failed to fetch data:**\n\n" + "\n".join(errors) + "\n\n**Please check:**\n- Ticker symbols are correct\n- yfinance is installed\n- Network connection is working"
        
        # Add warning for partial failures
        warning = ""
        if errors:
            warning = f"\n\n⚠️ **Warning:** Some tickers failed:\n" + "\n".join(errors) + "\n\n"
        
        # Run analysis with market data included
        query = f"""Analyze sentiment for portfolio: {', '.join(tickers)}

{market_data_summary}

Follow the complete sentiment analysis framework. Use the market data above along with news from reliable sources to provide comprehensive sentiment analysis."""
        
        response = team.run(query)
        result = response.content if hasattr(response, 'content') else str(response)
        
        # Add header
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        output = f"# 📊 Portfolio Sentiment Analysis\n\n"
        output += f"**Stocks:** {', '.join(tickers)}\n\n"
        output += f"**Timestamp:** {timestamp}\n\n"
        output += warning
        output += "---\n\n"
        output += result
        
        return output
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return f"❌ **Error:** {str(e)}\n\n**Details:**\n```\n{error_details}\n```\n\nPlease check your API key and stock tickers, then try again."

# Create Gradio interface
with gr.Blocks() as demo:
    gr.HTML("""
    <style>
    .gradio-container {
        font-family: 'Inter', sans-serif !important;
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
    }
    h1 {
        text-align: center;
        color: #00ff88 !important;
        font-weight: 300;
        letter-spacing: 0.5rem;
        text-transform: uppercase;
        margin-bottom: 0.5rem;
    }
    .subtitle {
        text-align: center;
        color: #888;
        letter-spacing: 0.2rem;
        font-size: 0.9rem;
        margin-bottom: 2rem;
    }
    </style>
    """)
    
    gr.HTML("<h1>SENTIMENT</h1>")
    gr.HTML("<p class='subtitle'>AI-Powered Portfolio Sentiment Analysis</p>")
    
    with gr.Row():
        with gr.Column(scale=3):
            portfolio_input = gr.Textbox(
                label="📈 Portfolio Input",
                placeholder="Enter stock tickers (comma-separated or one per line)\n\nExample: AAPL, MSFT, TSLA",
                lines=5,
                max_lines=10
            )
        
        with gr.Column(scale=1):
            gr.Markdown("### Quick Examples")
            tech_btn = gr.Button("Tech Portfolio", size="sm")
            finance_btn = gr.Button("Finance Stocks", size="sm")
            ev_btn = gr.Button("EV Leaders", size="sm")
            ecom_btn = gr.Button("E-Commerce", size="sm")
    
    analyze_btn = gr.Button("🔍 ANALYZE SENTIMENT", variant="primary", size="lg")
    
    output = gr.Markdown(
        label="Analysis Results",
        value="Enter stock tickers above and click 'ANALYZE SENTIMENT' to begin.\n\n**Features:**\n- Real-time market data from Yahoo Finance\n- News from verified sources only (Bloomberg, Reuters, WSJ, etc.)\n- Multi-agent AI analysis with Claude Sonnet 4"
    )
    
    # Button actions
    tech_btn.click(lambda: "AAPL, MSFT, GOOGL, NVDA", outputs=portfolio_input)
    finance_btn.click(lambda: "JPM, BAC, GS, WFC", outputs=portfolio_input)
    ev_btn.click(lambda: "TSLA, RIVN, LCID", outputs=portfolio_input)
    ecom_btn.click(lambda: "AMZN, SHOP, MELI", outputs=portfolio_input)
    
    # Analysis action
    analyze_btn.click(
        fn=analyze_portfolio,
        inputs=portfolio_input,
        outputs=output
    )
    
    # Info section
    with gr.Accordion("ℹ️ About This Tool", open=False):
        gr.Markdown("""
        ## Multi-Agent Sentiment Analysis System
        
        **Two Specialized Agents:**
        1. 🔍 **News Reliability Analyst** - Collects news from verified sources only
        2. 🎯 **Sentiment Synthesizer** - Combines news + market data into final assessment
        
        **Data Sources:**
        - ✅ **Market Data:** Direct from Yahoo Finance API (real-time)
        - ✅ **News:** Bloomberg, Reuters, WSJ, Financial Times, SEC filings
        - ❌ **Excluded:** Social media, unverified blogs, promotional content
        
        **What You Get:**
        - Real-time price data, volume, fundamentals
        - Analyst ratings and price targets
        - Recent news from credible sources only
        - Sentiment score: -100 (bearish) to +100 (bullish)
        
        ⚠️ **Disclaimer:** This is analysis, not investment advice. Consult licensed financial advisors before making investment decisions.
        """)
    
    with gr.Accordion("🔧 Troubleshooting", open=False):
        gr.Markdown("""
        ## Common Issues
        
        **"No data available" error:**
        - Check that ticker symbols are correct (e.g., AAPL not Apple)
        - Verify yfinance is installed: add to requirements.txt
        - Check network connectivity
                
        **Slow response:**
        - Multi-agent analysis takes 30-60 seconds
        - News gathering requires web searches
        - Be patient for comprehensive results
        
        **Need help?**
        - Test with a single ticker first (e.g., AAPL)
        """)

# Launch the app
if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0", 
        server_port=7860,
        ssr_mode=False  # Disable experimental SSR mode
    )
