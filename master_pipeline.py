import pandas as pd
from tqdm import tqdm
import time
import sys
import os

# Import the core engines we built in the previous steps
# (Make sure these file names match your VS Code folder exactly!)
from fcfe_calc import calculate_recent_fcfe
from cost_of_equity import calculate_fama_french_ke
from automated_valuation import evaluate_stock_scenarios

def get_major_indices_tickers():
    """Dynamically scrapes ALL constituents of the S&P 500 and TSX 60."""
    print("Scraping FULL S&P 500 and TSX 60 constituents from Wikipedia...")
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    sp500_tickers = []
    tsx60_tickers = []
    
    try:
        # 1. S&P 500 (US) - Grabbing ALL ~503 tickers
        us_tables = pd.read_html(
            'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies', 
            storage_options=headers
        )
        for table in us_tables:
            for col in ['Symbol', 'Ticker symbol', 'Ticker']:
                if col in table.columns:
                    sp500_tickers = table[col].tolist()
                    break
            if sp500_tickers: 
                break
                
        # Notice we removed the [:100] limit here!
        sp500_tickers = [str(t).replace('.', '-') for t in sp500_tickers] 
        
        # 2. S&P/TSX 60 (Canada) - Grabbing ALL 60 tickers
        ca_tables = pd.read_html(
            'https://en.wikipedia.org/wiki/S%26P/TSX_60', 
            storage_options=headers
        )
        for table in ca_tables:
            for col in ['Symbol', 'Ticker', 'Ticker symbol']:
                if col in table.columns:
                    tsx60_tickers = table[col].tolist()
                    break
            if tsx60_tickers:
                break
                
        # Notice we removed the [:50] limit here!
        tsx60_tickers = [f"{str(t).replace('.', '-')}.TO" for t in tsx60_tickers]
        
        combined_tickers = sp500_tickers + tsx60_tickers
        print(f"Successfully loaded {len(combined_tickers)} target companies for a full market sweep.\n")
        return combined_tickers
        
    except Exception as e:
        print(f"Error fetching tickers: {e}")
        return []

def run_screener(tickers, output_file="valuation_results.csv"):
    results_list = []
    
    print("Starting Valuation Engine. Grab a coffee, this full sweep will take roughly 45-60 minutes...\n")
    # tqdm creates the dynamic progress bar in the terminal
    for ticker in tqdm(tickers, desc="Evaluating Universe", unit="stock"):
        try:
            # 1. Fetch FCFE
            fcfe_data = calculate_recent_fcfe(ticker)
            if "Error" in fcfe_data:
                continue
            current_fcfe = fcfe_data["FCFE"]

            # Skip companies with negative FCFE
            if current_fcfe <= 0:
                continue

            # 2. Fetch Cost of Equity
            ke_data = calculate_fama_french_ke(ticker)
            if "Error" in ke_data:
                continue
            cost_of_equity = ke_data["Cost of Equity (Ke) (%)"] / 100 
            
            # 3. Run the Scenarios
            scenarios = evaluate_stock_scenarios(ticker, current_fcfe, cost_of_equity)
            
            if isinstance(scenarios, str) and "Error" in scenarios:
                continue
            
            # 4. Extract the primary scenario
            target_scenario = "Aggressive (100% Cap)" if "Aggressive (100% Cap)" in scenarios else list(scenarios.keys())[0]
            base_metrics = scenarios[target_scenario]
            
            results_list.append({
                "Ticker": ticker,
                "Used Scenario": target_scenario,
                "FCFE ($B)": round(current_fcfe / 1e9, 2),
                "Cost of Equity (%)": round(cost_of_equity * 100, 2),
                "Intrinsic Value": round(base_metrics["Base"], 2),
                "Margin of Safety (%)": round(base_metrics["Margin"], 2)
            })
            
            # INCREASED SAFETY PAUSE: 0.5 seconds to prevent Yahoo Finance from blocking you
            time.sleep(0.5)

        except Exception:
            pass

    # --- POST-PROCESSING & FILTERING ---
    if results_list:
        df = pd.DataFrame(results_list)
        df = df.sort_values(by="Margin of Safety (%)", ascending=False)
        df.to_csv(output_file, index=False)
        
        print(f"\n\nFull Market Screener complete! Successfully valued {len(df)} companies.")
        print(f"Full data saved to: {output_file}")
        
        # THE FILTER: We only care about companies trading at a discount
        buy_zone = df[df["Margin of Safety (%)"] >= 15.0]
        
        print(f"\n=== QUANTITATIVE BUY ZONE (Margin > 15%) ===")
        if not buy_zone.empty:
            # We now print the top 15 so you have more options to pick from
            print(buy_zone[['Ticker', 'Used Scenario', 'Intrinsic Value', 'Margin of Safety (%)']].head(15).to_string(index=False))
            print("============================================\n")
            
            return buy_zone["Ticker"].tolist()
        else:
            print("No stocks met the 15% Margin of Safety criteria today.")
            return []
    else:
        print("No successful valuations to save.")
        return []

if __name__ == "__main__":
    target_universe = get_major_indices_tickers()
    
    if target_universe:
        surviving_tickers = run_screener(target_universe)
        
        if surviving_tickers:
            print(f"Next Step: Feed the top candidates into your portfolio optimizer.")
    else:
        print("\nScript stopped: Could not load the target universe.")