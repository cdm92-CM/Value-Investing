import yfinance as yf
import random
import statistics

def run_3_stage_monte_carlo(ticker_symbol, current_fcfe, cost_of_equity, iterations=10000):
    print(f"Running 3-Stage Monte Carlo ({iterations:,} iterations) for {ticker_symbol}...")
    
    try:
        stock = yf.Ticker(ticker_symbol)
        shares_outstanding = stock.info.get('sharesOutstanding')
        
        if not shares_outstanding:
            return "Error: Could not pull shares outstanding."

        # --- THE 3-TIERED ASSUMPTIONS ---
        
        # TIER 1: Near-Term (The Wall Street Catalyst)
        # e.g., The next 3 years of hyper-growth driven by current market trends
        tier_1_years = 3
        tier_1_mean_growth = 0.35      # 35% growth (from Wall Street Consensus)
        tier_1_volatility = 0.12       # 12% volatility (slightly higher uncertainty)
        
        # TIER 2: Medium-Term (The Mean Reversion)
        # e.g., Years 4 through 7 where growth cools back to historical averages
        tier_2_years = 4 
        tier_2_mean_growth = 0.15      # 15% growth (from Historical CAGR)
        tier_2_volatility = 0.08       # 8% volatility (from Historical Std Dev)
        
        # TIER 3: Long-Term (Terminal State)
        # Year 8 to infinity
        perpetual_growth_rate = 0.025  # 2.5% Macroeconomic ceiling
        
        total_explicit_years = tier_1_years + tier_2_years
        simulated_intrinsic_values = []

        # --- THE MONTE CARLO ENGINE ---
        for _ in range(iterations):
            projected_cash_flows = []
            simulated_fcfe = current_fcfe
            
            # Simulate Tier 1 & Tier 2 Explicit Years
            for year in range(1, total_explicit_years + 1):
                
                # Apply the correct parameters based on which Tier we are in
                if year <= tier_1_years:
                    randomized_growth = random.gauss(tier_1_mean_growth, tier_1_volatility)
                else:
                    randomized_growth = random.gauss(tier_2_mean_growth, tier_2_volatility)
                    
                simulated_fcfe = simulated_fcfe * (1 + randomized_growth)
                
                # Discount back to present value
                discounted_cf = simulated_fcfe / ((1 + cost_of_equity) ** year)
                projected_cash_flows.append(discounted_cf)
            
            # Simulate Tier 3: Terminal Value
            terminal_value = (simulated_fcfe * (1 + perpetual_growth_rate)) / (cost_of_equity - perpetual_growth_rate)
            discounted_terminal_value = terminal_value / ((1 + cost_of_equity) ** total_explicit_years)
            
            # Tally up the Total Enterprise Value for this universe
            total_enterprise_value = sum(projected_cash_flows) + discounted_terminal_value
            value_per_share = total_enterprise_value / shares_outstanding
            simulated_intrinsic_values.append(value_per_share)

        # --- ANALYZE THE DISTRIBUTION ---
        simulated_intrinsic_values.sort()
        percentile_10 = simulated_intrinsic_values[int(iterations * 0.10)]
        median_value = statistics.median(simulated_intrinsic_values)
        percentile_90 = simulated_intrinsic_values[int(iterations * 0.90)]
        
        current_price = stock.fast_info['last_price']
        
        return {
            "Ticker": ticker_symbol,
            "Current Market Price": round(current_price, 2),
            "Pessimistic Case (10th Percentile)": round(percentile_10, 2),
            "Base Case (Median Intrinsic Value)": round(median_value, 2),
            "Optimistic Case (90th Percentile)": round(percentile_90, 2)
        }

    except Exception as e:
        return f"Simulation failed: {e}"

# Run the test
if __name__ == "__main__":
    target = "AMD"
    fcfe_baseline = 8226000000  # $8.226 Billion
    ke_baseline = 0.1436        # 14.36% Discount Rate
    
    result = run_3_stage_monte_carlo(target, fcfe_baseline, ke_baseline)
    
    print("\n--- 3-Stage Intrinsic Value Simulation ---")
    for key, value in result.items():
        if isinstance(value, float):
            print(f"{key}: ${value:,.2f}")
        else:
            print(f"{key}: {value}")