import yfinance as yf
import pandas as pd

def calculate_shields(ticker_symbol):
    """Calculates the Altman Z-Score and Piotroski F-Score to prevent value traps."""
    # We assign default "Safe" scores in case Yahoo Finance is missing data 
    # (common for banks/financials which don't report standard 'Current Assets')
    z_score = 3.0 
    f_score = 6   
    
    try:
        stock = yf.Ticker(ticker_symbol)
        bs = stock.balance_sheet
        ist = stock.financials
        cf = stock.cash_flow

        if bs.empty or ist.empty or cf.empty:
            return {"Altman_Z": z_score, "Piotroski_F": f_score}

        cols = bs.columns
        if len(cols) < 2:
            return {"Altman_Z": z_score, "Piotroski_F": f_score}

        yr0 = cols[0] # Current Year
        yr1 = cols[1] # Previous Year

        def get_val(df, row_name, col_name, default=0.0):
            try:
                if row_name in df.index:
                    val = df.loc[row_name, col_name]
                    return float(val) if pd.notna(val) else default
                return default
            except:
                return default

        # ---------------------------------------------------------
        # 1. ALTMAN Z-SCORE (Bankruptcy Risk)
        # ---------------------------------------------------------
        total_assets = get_val(bs, 'Total Assets', yr0, default=1)
        total_liab = get_val(bs, 'Total Liabilities Net Minority Interest', yr0)
        if total_liab == 0: total_liab = get_val(bs, 'Total Liabilities', yr0, 1)

        wc = get_val(bs, 'Current Assets', yr0) - get_val(bs, 'Current Liabilities', yr0)
        retained_earnings = get_val(bs, 'Retained Earnings', yr0)
        ebit = get_val(ist, 'EBIT', yr0)
        sales = get_val(ist, 'Total Revenue', yr0)

        try:
            market_cap = stock.fast_info.get('market_cap', 1)
        except:
            market_cap = total_assets 

        A = wc / total_assets
        B = retained_earnings / total_assets
        C = ebit / total_assets
        D = market_cap / total_liab
        E = sales / total_assets

        calculated_z = (1.2 * A) + (1.4 * B) + (3.3 * C) + (0.6 * D) + (1.0 * E)
        z_score = min(max(calculated_z, -5), 15) # Caps wild outliers

        # ---------------------------------------------------------
        # 2. PIOTROSKI F-SCORE (9-Point Accounting Health)
        # ---------------------------------------------------------
        f = 0

        # Yr 0 Data
        ni_0 = get_val(ist, 'Net Income', yr0)
        ocf_0 = get_val(cf, 'Operating Cash Flow', yr0)
        roa_0 = ni_0 / total_assets
        ltd_0 = get_val(bs, 'Long Term Debt', yr0)
        cr_0 = get_val(bs, 'Current Assets', yr0) / get_val(bs, 'Current Liabilities', yr0, 1)
        shares_0 = get_val(bs, 'Ordinary Shares Number', yr0)
        gp_0 = get_val(ist, 'Gross Profit', yr0)
        gm_0 = gp_0 / sales if sales > 0 else 0
        at_0 = sales / total_assets

        # Yr 1 Data
        ta_1 = get_val(bs, 'Total Assets', yr1, default=1)
        ni_1 = get_val(ist, 'Net Income', yr1)
        roa_1 = ni_1 / ta_1
        ltd_1 = get_val(bs, 'Long Term Debt', yr1)
        cr_1 = get_val(bs, 'Current Assets', yr1) / get_val(bs, 'Current Liabilities', yr1, 1)
        shares_1 = get_val(bs, 'Ordinary Shares Number', yr1)
        gp_1 = get_val(ist, 'Gross Profit', yr1)
        sales_1 = get_val(ist, 'Total Revenue', yr1, default=1)
        gm_1 = gp_1 / sales_1
        at_1 = sales_1 / ta_1

        # Profitability
        if roa_0 > 0: f += 1
        if ocf_0 > 0: f += 1
        if roa_0 > roa_1: f += 1
        if ocf_0 > ni_0: f += 1
        
        # Leverage, Liquidity, Source of Funds
        if (ltd_0 / total_assets) < (ltd_1 / ta_1): f += 1
        if cr_0 > cr_1: f += 1
        if shares_0 <= shares_1 and shares_0 > 0: f += 1
        
        # Operating Efficiency
        if gm_0 > gm_1: f += 1
        if at_0 > at_1: f += 1

        f_score = f

    except Exception:
        pass 

    return {
        "Altman_Z": round(z_score, 2),
        "Piotroski_F": f_score
    }

if __name__ == "__main__":
    test_result = calculate_shields("INTC") # Testing a known turnaround/distressed asset
    print(f"--- Forensics Test ---")
    print(f"Altman Z-Score (Safety > 1.8): {test_result['Altman_Z']}")
    print(f"Piotroski F-Score (Health > 5): {test_result['Piotroski_F']}")