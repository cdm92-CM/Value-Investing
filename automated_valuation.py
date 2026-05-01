import yfinance as yf
import random
import statistics

def fetch_raw_assumptions(stock_obj):
    """Scrapes yfinance but DOES NOT apply any caps yet."""
    info = stock_obj.info
    
    # 1. Forward Estimates
    raw_fwd_growth = info.get('earningsGrowth') or info.get('revenueGrowth')
    
    # 2. Historical Data
    try:
        income_stmt = stock_obj.financials
        if 'Total Revenue' in income_stmt.index:
            rev_data = income_stmt.loc['Total Revenue'].dropna()[::-1]
            years = len(rev_data) - 1
            if years > 0:
                beg_rev = rev_data.iloc[0]
                end_rev = rev_data.iloc[-1]
                hist_cagr = (end_rev / beg_rev) ** (1 / years) - 1
                yoy_growth = rev_data.pct_change().dropna()
                hist_vol = yoy_growth.std()
            else:
                hist_cagr, hist_vol = None, None
        else:
            hist_cagr, hist_vol = None, None
    except Exception:
        hist_cagr, hist_vol = None, None

    return raw_fwd_growth, hist_cagr, hist_vol

def run_monte_carlo_engine(current_fcfe, cost_of_equity, shares, t1_growth, t1_vol, t2_growth, t2_vol, iterations=10000):
    """The core mathematical engine. Now returns the full distribution percentiles."""
    tier_1_years = 3
    tier_2_years = 4 
    perpetual_growth_rate = 0.025
    total_explicit_years = tier_1_years + tier_2_years
    simulated_intrinsic_values = []

    for _ in range(iterations):
        projected_cash_flows = []
        simulated_fcfe = current_fcfe
        
        for year in range(1, total_explicit_years + 1):
            if year <= tier_1_years:
                randomized_growth = random.gauss(t1_growth, t1_vol)
            else:
                randomized_growth = random.gauss(t2_growth, t2_vol)
                
            simulated_fcfe = simulated_fcfe * (1 + randomized_growth)
            discounted_cf = simulated_fcfe / ((1 + cost_of_equity) ** year)
            projected_cash_flows.append(discounted_cf)
        
        # Terminal Value
        terminal_value = (simulated_fcfe * (1 + perpetual_growth_rate)) / (cost_of_equity - perpetual_growth_rate)
        discounted_terminal_value = terminal_value / ((1 + cost_of_equity) ** total_explicit_years)
        
        total_enterprise_value = sum(projected_cash_flows) + discounted_terminal_value
        value_per_share = total_enterprise_value / shares
        simulated_intrinsic_values.append(value_per_share)

    # --- Extract Percentiles ---
    simulated_intrinsic_values.sort()
    percentile_10 = simulated_intrinsic_values[int(iterations * 0.10)]
    median_value = statistics.median(simulated_intrinsic_values)
    percentile_90 = simulated_intrinsic_values[int(iterations * 0.90)]
    
    return percentile_10, median_value, percentile_90

def evaluate_stock_scenarios(ticker_symbol, current_fcfe, cost_of_equity, iterations=10000):
    print(f"Fetching data and evaluating scenarios for {ticker_symbol}...")
    
    try:
        stock = yf.Ticker(ticker_symbol)
        shares_outstanding = stock.info.get('sharesOutstanding')
        current_price = stock.fast_info['last_price']
        
        if not shares_outstanding:
            return f"Error: Could not pull shares outstanding for {ticker_symbol}."

        # 1. Get raw data
        raw_fwd_growth, hist_cagr, hist_vol = fetch_raw_assumptions(stock)
        
        # Determine Base Volatility and T2 Growth
        base_vol = hist_vol if hist_vol is not None else 0.10
        t1_vol = base_vol * 1.2
        t2_vol = base_vol
        
        # Fallback for T1 if missing
        t1_raw = raw_fwd_growth if raw_fwd_growth is not None else (hist_cagr if hist_cagr is not None else 0.10)
        
        # T2 Growth cools down
        t2_growth = hist_cagr if hist_cagr is not None else (t1_raw * 0.5)

        print(f"Current Market Price: ${current_price:,.2f}")
        print(f"Raw Extracted T1 Growth: {t1_raw*100:.1f}%\n")
        
        # 2. SCENARIO BRANCHING
        results = {}
        
        if t1_raw > 0.50:
            print("Hyper-growth detected! Running Scenario Analysis...")
            # We run 3 different realities
            scenarios = {
                "Conservative (50% Cap)": 0.50,
                "Aggressive (100% Cap)": 1.00,
                f"Uncapped (Raw {t1_raw*100:.1f}%)": t1_raw
            }
        else:
            # Normal growth, just run one standard scenario
            scenarios = {
                f"Base Case ({t1_raw*100:.1f}% Growth)": t1_raw
            }
            
        # 3. RUN THE SCENARIOS
        for scenario_name, t1_assumption in scenarios.items():
            pessimistic, base, optimistic = run_monte_carlo_engine(
                current_fcfe, cost_of_equity, shares_outstanding, 
                t1_assumption, t1_vol, t2_growth, t2_vol, iterations
            )
            
            margin = ((base - current_price) / current_price) * 100
            
            results[scenario_name] = {
                "Pessimistic": pessimistic,
                "Base": base,
                "Optimistic": optimistic,
                "Margin": margin
            }
            
        return results

    except Exception as e:
        return f"Simulation failed: {e}"

# Run the test
if __name__ == "__main__":
    target = "AMD"
    fcfe_baseline = 8226000000  
    ke_baseline = 0.1436        
    
    scenarios_output = evaluate_stock_scenarios(target, fcfe_baseline, ke_baseline)
    
    print("--- Valuation Scenarios ---")
    if isinstance(scenarios_output, dict):
        for scenario, metrics in scenarios_output.items():
            print(f"{scenario}:")
            print(f"  -> Pessimistic Case (10th):  ${metrics['Pessimistic']:,.2f}")
            print(f"  -> Base Case (Median):       ${metrics['Base']:,.2f}")
            print(f"  -> Optimistic Case (90th):   ${metrics['Optimistic']:,.2f}")
            print(f"  -> Margin of Safety (Base):  {metrics['Margin']:,.1f}%\n")
    else:
        print(scenarios_output)