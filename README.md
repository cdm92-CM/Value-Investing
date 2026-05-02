# Value Investing & Retirement Sentinel

An end-to-end quantitative platform designed for long-term retirement portfolio management. This suite automates the entire value investing lifecycle: from harvesting market data and performing deep intrinsic valuations to daily intelligence monitoring and weekly rebalancing.

## 🚀 Core Functionality

### 1. Market Harvesting & Valuation
* **Multi-Index Scanning:** Automatically retrieves and processes constituents from the **S&P 500** and **TSX 60**.
* **Intrinsic Valuation Engine:** Utilizes Free Cash Flow to Equity (FCFE) models coupled with advanced Cost of Equity calculations.
* **Risk Modeling:** Employs **Monte Carlo simulations** and **Fama-French factor analysis** to stress-test valuations and growth assumptions.

### 2. The Retirement Sentinel
* **Daily Intelligence:** A scheduled service that dispatches a 9:00 AM briefing to the user’s inbox, containing curated news headlines for core portfolio anchors.
* **Weekly Market Sweeps:** A Sunday morning audit of the broader market to identify new value opportunities.
* **Rebalance Automation:** Compares current holdings against an optimized model to provide specific trade instructions.

## 📁 Repository Structure
* `master_pipeline.py`: Central orchestrator for data harvesting.
* `retirement_sentinel.py`: The 24/7 automation hub.
* `fcfe_calc.py` & `cost_of_equity.py`: Core financial engines.

## 🛠️ Setup & Security
This project utilizes a `.env` file for secure credential management. **The `.env` file is ignored by Git to protect private data.**