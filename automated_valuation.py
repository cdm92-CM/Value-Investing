import yfinance as yf
import random
import statistics

# THE UPGRADE: Added 'target_lookback' parameter (defaulting to 5 years)
def fetch_raw_assumptions(stock_obj, target_lookback=5):
    """Scrapes yfinance and calculates historical metrics over a defined horizon."""
    info = stock_obj.info
    
    raw_fwd_growth = info.get('earningsGrowth') or info.get('revenueGrowth')
    
    try:
        income_stmt = stock_obj.financials
        if 'Total Revenue' in income_stmt.index:
            # Grab all available data and reverse it to chronological order
            all_rev_data = income_stmt.loc['Total Revenue'].dropna()[::-1]
            
            # THE HORIZON ENFORCER: 
            # To calculate 5 years of growth, we need 6 data points. 
            # .tail() ensures we only grab the exact timeframe you requested.
            points_needed = target_lookback + 1
            rev_data = all_rev_data.tail(points_needed)
            
            years = len(rev_data) - 1
            
            if years > 0:
                beg_rev = rev_data.iloc[0]
                end_rev = rev_data.iloc[-1]
                
                # The Failsafe for negative revenue (e.g., POW.TO)
                if beg_rev <= 0 or end_rev <= 0:
                    hist_cagr = None
                else:
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

def run_monte_carlo_engine(current_fcfe, cost_of_equity, shares, t1_growth, t1_vol, t2_growth, t2_vol, risk_free_rate, iterations=10000):
    tier_1_years = 3
    tier_2_years = 4 
    
    # PHASE 2 UPGRADE: Dynamic Macro-Tied Terminal Growth
    # The firm grows at the risk-free rate, but strictly capped at 3% (Long-Term GDP limit)
    # and floored at 0% to prevent negative perpetual growth in weird rate environments.
    perpetual_growth_rate = max(0.00, min(risk_free_rate, 0.03))
    
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

    simulated_intrinsic_values.sort()
    percentile_10 = simulated_intrinsic_values[int(iterations * 0.10)]
    median_value = statistics.median(simulated_intrinsic_values)
    percentile_90 = simulated_intrinsic_values[int(iterations * 0.90)]
    
    return percentile_10, median_value, percentile_90

# UPGRADE: Now accepts risk_free_rate
def evaluate_stock_scenarios(ticker_symbol, current_fcfe, cost_of_equity, risk_free_rate, iterations=10000):
    # (Silencing the terminal printout here so it doesn't spam during the bulk sweep)
    try:
        stock = yf.Ticker(ticker_symbol)
        shares_outstanding = stock.info.get('sharesOutstanding')
        current_price = stock.fast_info['last_price']
        
        if not shares_outstanding:
            return f"Error: Could not pull shares outstanding for {ticker_symbol}."

        raw_fwd_growth, hist_cagr, hist_vol = fetch_raw_assumptions(stock)
        
        base_vol = hist_vol if hist_vol is not None else 0.10
        t1_vol = base_vol * 1.2
        t2_vol = base_vol
        
        t1_raw = raw_fwd_growth if raw_fwd_growth is not None else (hist_cagr if hist_cagr is not None else 0.10)
        t2_growth = hist_cagr if hist_cagr is not None else (t1_raw * 0.5)

        results = {}
        
        if t1_raw > 0.50:
            scenarios = {
                "Conservative (50% Cap)": 0.50,
                "Aggressive (100% Cap)": 1.00,
                f"Uncapped (Raw {t1_raw*100:.1f}%)": t1_raw
            }
        else:
            scenarios = {
                f"Base Case ({t1_raw*100:.1f}% Growth)": t1_raw
            }
            
        for scenario_name, t1_assumption in scenarios.items():
            # Passing the new risk_free_rate parameter into the Monte Carlo engine
            pessimistic, base, optimistic = run_monte_carlo_engine(
                current_fcfe, cost_of_equity, shares_outstanding, 
                t1_assumption, t1_vol, t2_growth, t2_vol, risk_free_rate, iterations
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
# =====================================================================
# NEW COMMERCIAL API ADDITION: Wraps everything into a clean dictionary
# =====================================================================
def run_full_analysis(ticker):
    from fcfe_calc import calculate_recent_fcfe
    from cost_of_equity import calculate_fama_french_ke
    from value_shields import calculate_shields # <-- IMPORTS YOUR NEW MODULE
    import yfinance as yf
    
    try:
        fcfe_data = calculate_recent_fcfe(ticker)
        if "Error" in fcfe_data: 
            return {"Ticker": ticker, "Status": fcfe_data["Error"]}
        
        current_fcfe = fcfe_data["FCFE"]
        if current_fcfe <= 0: 
            return {"Ticker": ticker, "Status": "Failed - Negative FCFE"}

        ke_data = calculate_fama_french_ke(ticker)
        if "Error" in ke_data: 
            return {"Ticker": ticker, "Status": ke_data["Error"]}
            
        cost_of_equity = ke_data["Cost of Equity (Ke) (%)"] / 100
        risk_free_rate = ke_data["10-Yr Risk Free Rate (%)"] / 100
        
        scenarios = evaluate_stock_scenarios(ticker, current_fcfe, cost_of_equity, risk_free_rate)
        if isinstance(scenarios, str) and "Error" in scenarios:
            return {"Ticker": ticker, "Status": scenarios}
            
        target_scenario = "Aggressive (100% Cap)" if "Aggressive (100% Cap)" in scenarios else list(scenarios.keys())[0]
        base_metrics = scenarios[target_scenario]
        
        # --- CALCULATE THE SHIELDS ---
        forensics = calculate_shields(ticker)
        
        stock = yf.Ticker(ticker)
        try:
            current_price = stock.fast_info['last_price']
        except:
            current_price = stock.history(period="1d")['Close'].iloc[-1]
        
        return {
            "Ticker": ticker,
            "Current_Price": round(current_price, 2),
            "Intrinsic_Value_Worst": round(base_metrics["Pessimistic"], 2),
            "Intrinsic_Value_Base": round(base_metrics["Base"], 2),
            "Intrinsic_Value_Best": round(base_metrics["Optimistic"], 2),
            "Margin_of_Safety_Pct": round(base_metrics["Margin"], 2),
            "Market_Beta": ke_data.get("Market Beta", 0),
            "Value_Factor_HML": ke_data.get("Value Beta (HML)", 0),
            "Cost_of_Equity_Pct": round(cost_of_equity * 100, 2),
            "Altman_Z_Score": forensics["Altman_Z"],     # <-- ADDED
            "Piotroski_F_Score": forensics["Piotroski_F"], # <-- ADDED
            "Used_Scenario": target_scenario,
            "Status": "Success"
        }
    except Exception as e:
        return {"Ticker": ticker, "Status": f"Failed: {str(e)}"}
        
# Run the test
if __name__ == "__main__":
    test_result = run_full_analysis("AMD")
    print(test_result)