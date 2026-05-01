import yfinance as yf
import pandas as pd
import numpy as np
from scipy.optimize import minimize
import os

# --- RETIREMENT ACCOUNT PARAMETERS ---
EXISTING_NVDA_VAL = 2000.00
NEW_CASH_TO_INVEST = 20000.00
TOTAL_PORTFOLIO_VAL = EXISTING_NVDA_VAL + NEW_CASH_TO_INVEST
MAX_POSITION_SIZE = 0.10  # 10% Cap (Stricter cap because we have more stocks)

def load_all_winning_tickers(filepath="winning_tickets.csv"):
    """Loads EVERY ticker that passed the sanity filters."""
    print("--- Stage 1: Loading Full Universe of Winners ---")
    if not os.path.exists(filepath):
        print(f"Error: {filepath} not found. Run master_pipeline.py and winning_tickets.py first.")
        return []
    
    df = pd.read_csv(filepath)
    tickers = df['Ticker'].tolist()
    
    if "NVDA" not in tickers:
        tickers.append("NVDA")
    
    print(f"Targeting ALL {len(tickers)} assets for retirement allocation.\n")
    return tickers

def fetch_data_robustly(tickers):
    """Downloads data and handles MultiIndex/KeyError issues."""
    print(f"Downloading historical data for {len(tickers)} stocks...")
    raw_data = yf.download(tickers, period="5y", interval="1d", auto_adjust=True)
    
    if isinstance(raw_data.columns, pd.MultiIndex):
        data = raw_data['Close']
    else:
        data = raw_data[['Close']]
        
    # Drop stocks that are missing too much data (e.g., recent IPOs or ticker changes)
    # This prevents math errors in the covariance matrix
    data = data.dropna(axis=1, thresh=len(data) * 0.8)
    data = data.ffill().dropna() 
    return data

def optimize_full_universe(data):
    """Runs a large-scale optimization across all surviving winners."""
    print("Running Mean-Variance Optimization...")
    returns = data.pct_change().dropna()
    mean_returns = returns.mean() * 252
    cov_matrix = returns.cov() * 252
    rf_rate = 0.043 

    num_assets = len(data.columns)
    
    def neg_sharpe(weights):
        p_ret = np.sum(mean_returns * weights)
        p_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        return -(p_ret - rf_rate) / (p_vol + 1e-9)

    constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
    # Bounds: 0% minimum, 10% maximum per stock
    bounds = tuple((0.0, MAX_POSITION_SIZE) for _ in range(num_assets))
    init_guess = num_assets * [1. / num_assets]

    opt_result = minimize(neg_sharpe, init_guess, method='SLSQP', bounds=bounds, constraints=constraints)
    
    weights = opt_result.x if opt_result.success else init_guess
    return dict(zip(data.columns, weights))

def generate_full_deployment_plan(weights_dict):
    print("\n" + "="*60)
    print("      FULL UNIVERSE RETIREMENT DEPLOYMENT PLAN     ")
    print("="*60)
    
    results = []
    for ticker, weight in weights_dict.items():
        target_dollars = TOTAL_PORTFOLIO_VAL * weight
        current_dollars = EXISTING_NVDA_VAL if ticker == "NVDA" else 0.0
        action_needed = target_dollars - current_dollars
        
        # Only list it if the optimizer gave it more than 0.1% weight
        if weight > 0.001:
            results.append({
                "Ticker": ticker,
                "Mix %": f"{weight*100:.2f}%",
                "Target Value": f"${target_dollars:,.2f}",
                "ACTION": f"BUY ${action_needed:,.2f}" if action_needed > 1 else f"HOLD/SELL ${abs(action_needed):,.2f}"
            })

    df_plan = pd.DataFrame(results).sort_values(by="Target Value", ascending=False)
    print(df_plan.to_string(index=False))
    
    print("\n" + "="*60)
    print(f"Total Unique Assets to Buy: {len(df_plan)}")
    print(f"Average Position Size:     ${TOTAL_PORTFOLIO_VAL / len(df_plan):,.2f}")
    print("="*60)

if __name__ == "__main__":
    # 1. Load the entire list of 70+ winners
    all_tickers = load_all_winning_tickers("winning_tickets.csv")
    
    # 2. Get Data
    price_history = fetch_data_robustly(all_tickers)
    
    # 3. Optimize and Print
    final_weights = optimize_full_universe(price_history)
    generate_full_deployment_plan(final_weights)