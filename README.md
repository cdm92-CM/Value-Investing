Value Investing & Retirement Sentinel
An end-to-end quantitative platform designed for long-term retirement portfolio management. This suite automates the entire value investing lifecycle: from harvesting market data and performing deep intrinsic valuations to daily intelligence monitoring and weekly rebalancing.

🚀 Core Functionality
1. Market Harvesting & Valuation
Multi-Index Scanning: Automatically retrieves and processes constituents from the S&P 500 and TSX 60.

Intrinsic Valuation Engine: Utilizes Free Cash Flow to Equity (FCFE) models coupled with advanced Cost of Equity calculations.

Risk Modeling: Employs Monte Carlo simulations and Fama-French factor analysis to stress-test valuations and growth assumptions across different economic tiers.

2. The Retirement Sentinel
Daily Intelligence: A scheduled "Sentinel" service that dispatches a 9:00 AM briefing to the user’s inbox, containing curated news headlines for the core portfolio anchors.

Weekly Market Sweeps: A Sunday morning audit of the broader market to identify new value opportunities where the margin of safety exceeds established thresholds.

Rebalance Automation: Compares current holdings against an optimized Efficient Frontier model to provide specific dollar-amount trade instructions.

📁 Repository Structure
master_pipeline.py: The central orchestrator for data harvesting and initial screening.

automated_valuation.py: High-volume valuation logic for multi-stock analysis.

fcfe_calc.py & cost_of_equity.py: Modular financial engines for fundamental analysis.

retirement_sentinel.py: The 24/7 automation hub for notifications and scheduling.

winning_tickets.py: Filtering logic to isolate high-conviction assets with a significant margin of safety.

deploy_portfolio.py: Optimization script for calculating target asset weights.

🛠️ Setup & Security
Installation
Clone the repository.

Create a virtual environment: python -m venv venv.

Install dependencies: pip install -r requirements.txt.

Environment Variables
This project utilizes a .env file for secure credential management. Never commit the .env file to version control.

Plaintext
EMAIL_ADDRESS=your.email@gmail.com
EMAIL_PASSWORD=your_app_password
📈 Methodology
The platform is built on the philosophy of "Margin of Safety." By automating the grunt work of data collection and discounted cash flow modeling, the user can focus on high-level strategic decisions. The system is designed to ignore short-term market noise, focusing instead on long-term retirement compounding.