import yfinance as yf
import pandas as pd

def calculate_recent_fcfe(ticker_symbol):
    """
    Pulls cash flow data from Yahoo Finance and calculates FCFE.
    Formula: FCFE = Operating Cash Flow - CapEx + Net Borrowing
    """
    print(f"Fetching data for {ticker_symbol}...")
    stock = yf.Ticker(ticker_symbol)
    
    # Pull the annual cash flow statement
    cf = stock.cash_flow
    
    if cf.empty:
        return {"Error": f"No cash flow data available for {ticker_symbol}."}

    try:
        # yfinance returns dates as columns; .iloc[:, 0] grabs the most recent reporting year
        recent_cf = cf.iloc[:, 0] 
        
        # 1. Operating Cash Flow
        ocf = recent_cf.get('Operating Cash Flow', 0)
        
        # 2. Capital Expenditures (yfinance often reports this as a negative outflow)
        capex_raw = recent_cf.get('Capital Expenditure', 0)
        capex = abs(capex_raw) if pd.notna(capex_raw) else 0
        
        # 3. Net Borrowing (Issuance of Debt - Repayment of Debt)
        # We use .get() so the script doesn't crash if a company has zero debt activity
        debt_issued = recent_cf.get('Issuance Of Debt', 0)
        if pd.isna(debt_issued): debt_issued = 0
            
        debt_repaid_raw = recent_cf.get('Repayment Of Debt', 0)
        # Repayment is usually reported as negative
        debt_repaid = debt_repaid_raw if pd.notna(debt_repaid_raw) else 0 
        
        net_borrowing = debt_issued + debt_repaid
        
        # Calculate final FCFE
        fcfe = ocf - capex + net_borrowing
        
        return {
            "Ticker": ticker_symbol,
            "Operating Cash Flow": ocf,
            "Capital Expenditures": capex,
            "Net Borrowing": net_borrowing,
            "FCFE": fcfe
        }

    except Exception as e:
        return {"Error": f"Calculation failed for {ticker_symbol}: {e}"}

# Run the test
if __name__ == "__main__":
    target_ticker = "AMD"
    result = calculate_recent_fcfe(target_ticker)
    
    print("\n--- FCFE Results (in actual dollars) ---")
    for key, value in result.items():
        # Formatting the output for readability
        if isinstance(value, (int, float)):
            print(f"{key}: ${value:,.2f}")
        else:
            print(f"{key}: {value}")