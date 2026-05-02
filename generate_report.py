import multiprocessing
import pandas as pd
import time
from automated_valuation import run_full_analysis

def get_product_universe():
    """Dynamically scrapes the current constituents of the S&P 500 and TSX 60."""
    print("Fetching live index constituents for the S&P 500 and TSX 60...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        sp500_tables = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies', storage_options=headers)
        sp500_tickers = []
        for table in sp500_tables:
            for col in ['Symbol', 'Ticker symbol', 'Ticker']:
                if col in table.columns:
                    sp500_tickers = table[col].tolist()
                    break
            if sp500_tickers: break
        
        sp500_tickers = [str(t).replace('.', '-') for t in sp500_tickers]
        
        tsx_tables = pd.read_html('https://en.wikipedia.org/wiki/S%26P/TSX_60', storage_options=headers)
        tsx_tickers = []
        for table in tsx_tables:
            for col in ['Symbol', 'Ticker', 'Ticker symbol']:
                if col in table.columns:
                    tsx_tickers = table[col].tolist()
                    break
            if tsx_tickers: break
            
        tsx_tickers = [f"{str(t).replace('.', '-')}.TO" for t in tsx_tickers]
        
        combined_universe = sp500_tickers + tsx_tickers
        print(f"Successfully loaded {len(combined_universe)} tickers for bulk analysis.\n")
        return combined_universe
        
    except Exception as e:
        print(f"Error fetching ticker lists: {e}")
        return []

def generate_weekly_data():
    print("="*50)
    print("INITIALIZING QUANTITATIVE BULK PROCESSOR (RATE-LIMITED)")
    print("="*50)
    start_time = time.time()

    target_tickers = get_product_universe()
    
    if not target_tickers:
        print("Aborting: Could not load target universe.")
        return

    # THE FIX: Stricter Throttling
    # We drop the cores to 2 or 3 to be gentler on the API
    safe_cores = min(3, multiprocessing.cpu_count()) 
    batch_size = safe_cores * 4 # Process in smaller waves of 8 to 12
    
    print(f"Booting rate-limited multicore processing ({safe_cores} threads)...")
    print("Processing in batches to avoid Yahoo Finance IP bans. Please wait...\n")

    results = []
    
    for i in range(0, len(target_tickers), batch_size):
        batch = target_tickers[i:i+batch_size]
        
        with multiprocessing.Pool(processes=safe_cores) as pool:
            batch_results = pool.map(run_full_analysis, batch)
            results.extend(batch_results)
            
        progress = min(i + batch_size, len(target_tickers))
        print(f"\n--- Processed {progress} / {len(target_tickers)} assets. Initiating 10-second API cooldown... ---")
        
        # The Politeness Delay: Increased to 10 seconds
        time.sleep(10) 
            
    print("\nProcessing complete. Assembling data matrix...")
    
    try:
        df = pd.DataFrame(results)
        
        successful_data = df[df["Status"] == "Success"].drop(columns=["Status"])
        failed_data = df[df["Status"] != "Success"]
        
        if not successful_data.empty:
            successful_data = successful_data.sort_values(by="Margin_of_Safety_Pct", ascending=False)
        
        output_filename = "weekly_factor_data.csv"
        successful_data.to_csv(output_filename, index=False)
        
        end_time = time.time()
        
        print("\n" + "="*50)
        print("REPORT GENERATION SUCCESSFUL")
        print("="*50)
        print(f"File Saved:    {output_filename}")
        print(f"Assets Scored: {len(successful_data)}")
        if not failed_data.empty:
            print(f"Failed Scans:  {len(failed_data)} (Usually due to legitimately missing Yahoo data)")
        print(f"Compute Time:  {round((end_time - start_time) / 60, 2)} minutes")
        print("="*50)

    except Exception as e:
        print(f"Critical System Failure: {e}")

if __name__ == "__main__":
    generate_weekly_data()