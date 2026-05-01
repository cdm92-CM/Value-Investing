import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

def run_portfolio_stress_test():
    # Your 16 optimized tickers
    tickers = ["PGR", "GOOGL", "APH", "CASY", "L.TO", "LLY", "MCK", "TRGP", 
               "WN.TO", "NVDA", "COR", "CF", "CME", "VLO", "SU.TO", "CNQ.TO"]
    
    # Weights from your optimizer (rounded for the test)
    weights = [0.0329, 0.0235, 0.0162, 0.10, 0.10, 0.10, 0.10, 0.10, 
               0.10, 0.0962, 0.0914, 0.0081, 0.0071, 0.0064, 0.0635, 0.0546]

    print("Fetching historical crash data...")
    # Download data from 2020 to capture both COVID and the 2022 Tech Crash
    data = yf.download(tickers, start="2020-01-01")['Adj Close'].ffill()
    spy = yf.download("SPY", start="2020-01-01")['Adj Close']

    # Calculate Portfolio Returns
    daily_returns = data.pct_change()
    port_returns = (daily_returns * weights).sum(axis=1)
    cum_port_returns = (1 + port_returns).cumprod()

    # Calculate S&P 500 Benchmark Returns
    cum_spy_returns = (1 + spy.pct_change()).cumprod()

    # Plotting the Stress Test
    plt.figure(figsize=(12,6))
    plt.plot(cum_port_returns, label="Your 16-Stock Retirement Mix", color='blue', linewidth=2)
    plt.plot(cum_spy_returns, label="S&P 500 (Benchmark)", color='red', linestyle='--', alpha=0.7)
    plt.title("Portfolio Stress Test: 2020 - Present")
    plt.ylabel("Growth of $1")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.show()

    # Calculate Max Drawdown
    roll_max = cum_port_returns.cummax()
    drawdown = cum_port_returns / roll_max - 1.0
    max_drawdown = drawdown.min()
    
    print(f"\n--- STRESS TEST RESULTS ---")
    print(f"Max Portfolio Drawdown: {max_drawdown*100:.2f}%")
    print(f"Final Value of $1 invested in 2020: ${cum_port_returns.iloc[-1]:.2f}")

if __name__ == "__main__":
    run_portfolio_stress_test()