import schedule
import time
from datetime import datetime
import pandas as pd
import os
from master_pipeline import get_major_indices_tickers, run_screener
from winning_tickets import generate_winning_tickets

def run_weekly_sweep():
    """Weekly scanning function for value opportunities in S&P 500 and TSX 60."""
    print(f"\n--- STARTING WEEKLY AUTOMATED SWEEP: {datetime.now().strftime('%Y-%m-%d')} ---")
    
    # 1. Run full screen across major indices
    tickers = get_major_indices_tickers()
    if not tickers:
        print("Failed to retrieve universe. Exiting.")
        return
        
    # 2. Run your valuation pipeline to get new valuation metrics
    results = run_screener(tickers)
    
    if results:
        # 3. Process new "Winning Tickets" with our safety filters
        winning_list = generate_winning_tickets()
        print(f"Weekly Sweep Complete. Updated {len(winning_list)} assets in winning_tickets.csv")
    else:
        print("No successful runs generated this week.")
        
    print("=" * 60)

# --- AUTOMATION SCHEDULE ---
# Run every Sunday at 8:00 AM so it is ready for your portfolio check
schedule.every().sunday.at("08:00").do(run_weekly_sweep)

if __name__ == "__main__":
    print("Weekly Sweeper Automation is now active.")
    print("Monitoring S&P 500 and TSX 60 for new entries.")
    
    # To run a test of the sweep immediately at startup, uncomment the line below:
    # run_weekly_sweep()
    
    while True:
        schedule.run_pending()
        time.sleep(60)