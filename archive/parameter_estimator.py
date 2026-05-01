import yfinance as yf
import pandas as pd
import numpy as np

def get_monte_carlo_parameters(ticker_symbol):
    print(f"Scraping historical data and Wall Street consensus for {ticker_symbol}...\n")
    stock = yf.Ticker(ticker_symbol)
    
    # --- 1. HISTORICAL DATA (The "Past") ---
    # We use Total Revenue because it is less prone to wild accounting swings than Net Income
    try:
        income_stmt = stock.financials
        
        if 'Total Revenue' in income_stmt.index:
            # yfinance returns newest data first; we slice it [::-1] to reverse it to oldest -> newest
            rev_data = income_stmt.loc['Total Revenue'].dropna()[::-1] 
            
            years = len(rev_data) - 1
            if years > 0:
                # Calculate Compound Annual Growth Rate (CAGR)
                beginning_rev = rev_data.iloc[0]
                ending_rev = rev_data.iloc[-1]
                cagr = (ending_rev / beginning_rev) ** (1 / years) - 1
                
                # Calculate Year-over-Year (YoY) Growth Rates to find Volatility
                yoy_growth = rev_data.pct_change().dropna()
                volatility = yoy_growth.std()
            else:
                cagr, volatility = None, None
        else:
            cagr, volatility = None, None
            
    except Exception as e:
        print(f"Error pulling historical data: {e}")
        cagr, volatility = None, None
        
    # --- 2. FORWARD-LOOKING DATA (Wall Street Consensus) ---
    info = stock.info
    
    # Extracting consensus estimates provided by Yahoo Finance's data providers
    fwd_rev_growth = info.get('revenueGrowth')
    fwd_earn_growth = info.get('earningsGrowth')
    
    # Calculate implied 1-year forward EPS growth (Forward EPS / Trailing EPS)
    trailing_eps = info.get('trailingEps')
    forward_eps = info.get('forwardEps')
    
    if trailing_eps and forward_eps and trailing_eps > 0:
        implied_eps_growth = (forward_eps - trailing_eps) / trailing_eps
    else:
        implied_eps_growth = None

    # --- 3. OUTPUT & FORMATTING ---
    print(f"--- {ticker_symbol} Monte Carlo Parameters ---")
    
    print("\n[ PAST: Historical Performance ]")
    if cagr is not None:
        print(f"Historical Revenue CAGR ({years} Years): {cagr*100:.2f}%")
        print(f"Historical Growth Volatility (Std Dev):  {volatility*100:.2f}%")
    else:
        print("Historical data unavailable.")
        
    print("\n[ FUTURE: Wall Street Consensus ]")
    if fwd_rev_growth: print(f"Next Year Revenue Growth Est:        {fwd_rev_growth*100:.2f}%")
    if fwd_earn_growth: print(f"Next Year Earnings Growth Est:       {fwd_earn_growth*100:.2f}%")
    if implied_eps_growth: print(f"Implied 1-Yr Forward EPS Growth:     {implied_eps_growth*100:.2f}%")

if __name__ == "__main__":
    get_monte_carlo_parameters("AMD")