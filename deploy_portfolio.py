import pandas as pd
import yfinance as yf
import numpy as np
from scipy.optimize import minimize
import os

# --- STAGE 1: THE SCRUBBER ---
def get_clean_winners(input_file="valuation_results.csv", top_n=25):
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found. Run master_pipeline.py first.")
        return []

    df = pd.read_csv(input_file)
    clean_df = df[
        (df['Margin of Safety (%)'] <= 150.0) & 
        (df['Margin of Safety (%)'] >= 10.0) &  
        (df['Cost of Equity (%)'] >= 6.0)       
    ]
    clean_df = clean_df.sort_values(by='Margin of Safety (%)', ascending=False)
    return clean_df.head(top_n)['Ticker'].tolist()

# --- STAGE 2: THE OPTIMIZER & DIVIDEND TRACKER ---
def optimize_deployment(tickers, current_holdings, new_capital):
    if "NVDA" not in tickers:
        tickers.append("NVDA")
        
    print(f"--- Stage 2: Optimizing {len(tickers)} Assets ---")
    
    # Download data with auto_adjust
    raw_data = yf.download(tickers, period="5y", interval="1d", auto_adjust=True)
    
    # Handle the price data correctly
    if isinstance(raw_data.columns, pd.MultiIndex):
        data = raw_data['Close']
    else:
        data = raw_data[['Close']]

    # IMPROVED DATA CLEANING: Only drop columns that are almost entirely empty
    # Then fill small gaps with the previous day's price
    data = data.dropna(thresh=len(data) * 0.5, axis=1) # Must have at least 50% of history
    data = data.ffill().dropna() # Fill small gaps, then drop remaining leading NaNs
    
    num_assets = len(data.columns)
    if num_assets == 0:
        print("Error: No stocks survived the data cleaning process. Check ticker validity.")
        return

    # Calculate returns and risk
    returns = data.pct_change().dropna()
    mean_returns = returns.mean() * 252
    cov_matrix = returns.cov() * 252
    rf_rate = 0.043 
    
    def negative_sharpe(weights):
        p_ret = np.sum(mean_returns * weights)
        p_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        # Annualized Sharpe Ratio calculation:
        # $$Sharpe = \frac{R_p - R_f}{\sigma_p}$$
        return -(p_ret - rf_rate) / (p_vol + 1e-9)

    constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
    bounds = tuple((0.0, 0.15) for _ in range(num_assets)) 
    init_guess = num_assets * [1. / num_assets,]
    
    opt_result = minimize(negative_sharpe, init_guess, method='SLSQP', bounds=bounds, constraints=constraints)
    weights = opt_result.x if opt_result.success else init_guess
    
    # FETCH DIVIDEND DATA
    print("Calculating expected dividend yield...")
    div_yields = {}
    for t in data.columns:
        try:
            info = yf.Ticker(t).info
            div_yields[t] = info.get('dividendYield', 0) or 0
        except:
            div_yields[t] = 0

    # FINAL REPORTING
    total_val = sum(current_holdings.values()) + new_capital
    print("\n===========================================")
    print("       25-STOCK DEPLOYMENT ACTION PLAN      ")
    print("===========================================\n")
    
    orders = []
    total_annual_div = 0
    
    for ticker, weight in zip(data.columns, weights):
        target_dollars = total_val * weight
        current_dollars = current_holdings.get(ticker, 0.0)
        diff = target_dollars - current_dollars
        
        annual_div = target_dollars * div_yields.get(ticker, 0)
        total_annual_div += annual_div
        
        if weight > 0.005:
            orders.append({
                "Ticker": ticker,
                "Weight": f"{weight*100:.1f}%",
                "Target Value": f"${target_dollars:,.2f}",
                "Div Yield": f"{div_yields.get(ticker, 0)*100:.2f}%",
                "ACTION": f"BUY ${diff:,.2f}" if diff > 1.0 else f"HOLD/SELL ${abs(diff):,.2f}"
            })
            
    order_df = pd.DataFrame(orders).sort_values(by="Weight", ascending=False)
    print(order_df.to_string(index=False))
    
    print("\n--- PORTFOLIO HEALTH SUMMARY ---")
    print(f"Total Target Value:       ${total_val:,.2f}")
    print(f"Est. Annual Dividends:    ${total_annual_div:,.2f}")
    print(f"Est. Monthly Passive:     ${total_annual_div/12:,.2f}")
    print(f"Avg Portfolio Yield:      {(total_annual_div/total_val)*100:.2f}%")
    print("===========================================\n")

if __name__ == "__main__":
    top_25_list = get_clean_winners("valuation_results.csv", top_n=25)
    if top_25_list:
        my_holdings = {"NVDA": 2000.00}
        new_cash = 20000.00
        optimize_deployment(top_25_list, my_holdings, new_cash)