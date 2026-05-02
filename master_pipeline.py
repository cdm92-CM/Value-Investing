import time
from generate_report import generate_weekly_data
from deploy_portfolio import get_clean_winners, optimize_deployment

def run_investing_system():
    print("="*60)
    print("STARTING FULL VALUE INVESTING PIPELINE")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    # STEP 1: THE DATA ENGINE
    # This runs the ~17 minute sweep of the S&P 500 and TSX 60
    print("\n[STEP 1/2] Launching Quantitative Bulk Processor...")
    generate_weekly_data()

    # STEP 2: THE STRATEGY ENGINE
    # This runs the Forensic Scrubber and Efficient Frontier Optimizer
    print("\n[STEP 2/2] Launching Portfolio Optimizer...")
    
    # 1. Scrub the data
    winning_df = get_clean_winners("weekly_factor_data.csv")
    
    if not winning_df.empty:
        # --- UPDATE YOUR SETTINGS HERE ---
        my_holdings = {
            "NVDA": 2000.00,
        }
        new_cash = 20000.00 
        # ---------------------------------
        
        # 2. Run optimization and generate PDF/CSV
        optimize_deployment(winning_df, my_holdings, new_cash)
    else:
        print("Error: No stocks passed the forensic scrubber. Check weekly_factor_data.csv.")

    print("\n" + "="*60)
    print("PIPELINE EXECUTION COMPLETE")
    print(f"Check your folder for the new PDF Action Plan.")
    print("="*60)

if __name__ == "__main__":
    run_investing_system()