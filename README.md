# 📈 Personal Finance AI: Sentiment & Market Analyzer

A multi-agent AI system that performs comprehensive sentiment analysis on stock portfolios. By combining real-time market data from Yahoo Finance with verified news from credible sources, this tool provides a sophisticated "Sentiment Index" for investment research.

## 🚀 Project Overview

This application leverages the **Agno** framework to orchestrate a team of AI agents powered by **Anthropic's Claude**. Unlike simple news aggregators, it filters for high-reliability sources (Bloomberg, WSJ, Reuters) and synthesizes that qualitative data with quantitative market metrics (technicals, fundamentals) to generate a balanced investment outlook.

## ⚙️ How It Works (Project Flow)

The system follows a multi-step pipeline to ensure high-quality analysis:

1.  **User Input:** The user enters stock tickers (e.g., AAPL, MSFT) into the Gradio web interface.
2.  **Market Data Retrieval:** The system fetches real-time prices, volume, technical indicators (SMA, volatility), and fundamental data (P/E, Market Cap) using `yfinance`.
3.  **Agent Orchestration:** A team of two specialized AI agents is initialized:
    * **🕵️ News Reliability Analyst:** Searches the web using DuckDuckGo but applies strict filters to only accept news from verified financial publications (rejecting social media/blogs).
    * **🧠 Portfolio Sentiment Synthesizer:** Takes the structured news data and the quantitative market data to produce a final report.
4.  **Synthesis & Scoring:** The agents calculate a "Sentiment Score" (-100 to +100) and generate a detailed report explaining the drivers behind the score.
5.  **Output:** The analysis is rendered in Markdown within the Gradio UI.

## 🛠️ Tech Stack

* **Language:** Python 3.10+
* **UI Framework:** [Gradio](https://gradio.app/) (Web Interface)
* **AI Framework:** [Agno](https://github.com/agno-agi/agno) (Agent Orchestration & Teams)
* **LLM Provider:** Anthropic (Claude 3.5 Sonnet / Sonnet 4)
* **Market Data:** `yfinance-cache` (Yahoo Finance API wrapper with caching)
* **Search Tool:** DuckDuckGo Search (`ddgs`)
* **Database:** SQLite (for agent memory and history)

## 📦 Installation & Setup

### Prerequisites

* Python 3.10 or higher
* An Anthropic API Key

### 1. Clone the Repository

```bash
git clone [https://github.com/yourusername/personalfinanceai.git](https://github.com/yourusername/personalfinanceai.git)
cd personalfinanceai
