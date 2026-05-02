import pandas as pd
import yfinance as yf
import numpy as np
from scipy.optimize import minimize
import os
import time
from fpdf import FPDF
from datetime import datetime

# --- PDF REPORTING CLASS ---
class PortfolioReport(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 16)
        self.set_text_color(0, 51, 102) 
        self.cell(0, 10, 'Efficient Frontier Deployment Action Plan', align='C', new_x="LMARGIN", new_y="NEXT")
        
        self.set_font('helvetica', 'I', 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, f'Execution Date: {datetime.now().strftime("%Y-%m-%d")} | 10% Max Cap', align='C', new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

# --- STAGE 1: THE SCRUBBER ---
def get_clean_winners(input_file="weekly_factor_data.csv"):
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found. Run generate_report.py first.")
        return pd.DataFrame() 

    df = pd.read_csv(input_file)
    
    clean_df = df[
        (df['Margin_of_Safety_Pct'] <= 150.0) & 
        (df['Margin_of_Safety_Pct'] >= 0.0) &  
        (df['Cost_of_Equity_Pct'] >= 6.0) &
        (df['Altman_Z_Score'] >= 1.8) &       
        (df['Piotroski_F_Score'] >= 6)        
    ]
    
    clean_df = clean_df.sort_values(by='Margin_of_Safety_Pct', ascending=False)
    
    cad_count = sum(1 for t in clean_df['Ticker'] if str(t).endswith(".TO"))
    print(f"Forensic Scrubber passed {len(clean_df)} chemically clean assets ({cad_count} are Canadian).")
    
    return clean_df

# --- STAGE 2: THE OPTIMIZER & DIVIDEND TRACKER ---
def optimize_deployment(clean_df, current_holdings, new_capital):
    tickers = clean_df['Ticker'].tolist()
    
    if "NVDA" not in tickers:
        tickers.append("NVDA") 
        
    print(f"--- Stage 2: Optimizing {len(tickers)} Assets on the Efficient Frontier ---")
    print("Fetching 5-year daily returns cautiously to avoid rate limits. Please wait...")
    
    data = pd.DataFrame()
    for ticker in tickers:
        try:
            stock_data = yf.download(ticker, period="5y", interval="1d", auto_adjust=True, progress=False)
            
            if not stock_data.empty:
                if isinstance(stock_data.columns, pd.MultiIndex):
                    data[ticker] = stock_data['Close'][ticker]
                else:
                    data[ticker] = stock_data['Close']
            time.sleep(0.5) 
            
        except Exception:
            pass

    if data.empty:
        print("\n🚨 CRITICAL ERROR: Yahoo Finance Rate Limit Reached.")
        print("Your IP address is blocked. Please wait 15 minutes.")
        return
        
    data = data.dropna(thresh=len(data) * 0.5, axis=1) 
    data = data.ffill().dropna() 
    
    num_assets = len(data.columns)
    if num_assets == 0:
        print("Error: No stocks survived the data cleaning process.")
        return

    returns = data.pct_change().dropna()
    mean_returns = returns.mean() * 252           
    annual_volatility = returns.std() * np.sqrt(252) 
    cov_matrix = returns.cov() * 252
    rf_rate = 0.043 
    
    def negative_sharpe(weights):
        p_ret = np.sum(mean_returns * weights)
        p_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        return -(p_ret - rf_rate) / (p_vol + 1e-9)

    constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
    
    # THE SPREAD FIX: Changed bounds to 10% maximum per stock
    bounds = tuple((0.0, 0.10) for _ in range(num_assets)) 
    init_guess = num_assets * [1. / num_assets,]
    
    print("Running quadratic programming to find the optimal Sharpe Ratio...")
    opt_result = minimize(negative_sharpe, init_guess, method='SLSQP', bounds=bounds, constraints=constraints)
    
    if not opt_result.success:
        print("\n🚨 WARNING: The Math Engine failed to converge.")
        weights = init_guess
        portfolio_sharpe = 0.0
    else:
        weights = opt_result.x
        portfolio_sharpe = -opt_result.fun 
    
    print("Calculating expected dividend yield...")
    div_yields = {}
    for t in data.columns:
        try:
            info = yf.Ticker(t).info
            div_dollar = info.get('trailingAnnualDividendRate', 0)
            if div_dollar is None:
                div_dollar = 0
                
            current_price = data[t].iloc[-1]
            raw_yield = div_dollar / current_price
            div_yields[t] = raw_yield
            time.sleep(0.2)
        except:
            div_yields[t] = 0

    mos_dict = dict(zip(clean_df['Ticker'], clean_df['Margin_of_Safety_Pct']))

    # --- FINAL REPORTING COMPILATION ---
    total_val = sum(current_holdings.values()) + new_capital
    orders = []
    total_annual_div = 0
    
    for ticker, weight in zip(data.columns, weights):
        target_dollars = total_val * weight
        current_dollars = current_holdings.get(ticker, 0.0)
        diff = target_dollars - current_dollars
        
        annual_div = target_dollars * div_yields.get(ticker, 0)
        total_annual_div += annual_div
        
        if target_dollars > 10.0: 
            mos = mos_dict.get(ticker, 0.0) 
            h_ret = mean_returns[ticker] * 100
            h_vol = annual_volatility[ticker] * 100
            ind_sharpe = (mean_returns[ticker] - rf_rate) / (annual_volatility[ticker] + 1e-9)
            
            orders.append({
                "Ticker": ticker,
                "Weight (%)": f"{weight*100:.1f}%",
                "Target Value ($)": f"${target_dollars:,.2f}",
                "ACTION": f"BUY ${diff:,.2f}" if diff > 1.0 else f"HOLD/SELL ${abs(diff):,.2f}",
                "MoS (%)": f"{mos:.1f}%",
                "Hist. Ret (%)": f"{h_ret:.1f}%",
                "Hist. Vol (%)": f"{h_vol:.1f}%",
                "Ind. Sharpe": f"{ind_sharpe:.2f}",
                "Div Yield (%)": f"{div_yields.get(ticker, 0)*100:.2f}%"
            })
            
    order_df = pd.DataFrame(orders).sort_values(by="Weight (%)", ascending=False)
    
    # 1. PRINT TO TERMINAL
    print("\n" + "="*110)
    print("                                      EFFICIENT FRONTIER ACTION PLAN                                           ")
    print("="*110 + "\n")
    print(order_df.to_string(index=False))
    print("\n--- PORTFOLIO HEALTH SUMMARY ---")
    print(f"Total Target Value:       ${total_val:,.2f}")
    print(f"Target Portfolio Sharpe:  {portfolio_sharpe:.2f}")
    print(f"Est. Annual Dividends:    ${total_annual_div:,.2f}")
    print(f"Avg Portfolio Yield:      {(total_annual_div/total_val)*100:.2f}%")
    print("="*110 + "\n")

    # 2. GENERATE CSV
    timestamp = datetime.now().strftime("%Y_%m_%d")
    csv_filename = f"Portfolio_Action_Plan_{timestamp}.csv"
    order_df.to_csv(csv_filename, index=False)
    print(f"[SUCCESS] CSV Exported: {csv_filename}")

    # 3. GENERATE INSTITUTIONAL PDF
    print("Generating PDF Report...")
    pdf = PortfolioReport(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    pdf.set_font('helvetica', 'B', 9)
    pdf.set_fill_color(0, 51, 102)
    pdf.set_text_color(255, 255, 255)
    
    headers = ['Ticker', 'Weight', 'Target Value', 'ACTION', 'MoS (%)', 'Return', 'Vol.', 'Sharpe', 'Yield']
    widths = [20, 20, 30, 40, 25, 25, 25, 25, 25] 
    
    for h, w in zip(headers, widths):
        pdf.cell(w, 8, h, border=1, align='C', fill=True)
    pdf.ln()

    pdf.set_font('helvetica', '', 9)
    fill = False
    for _, row in order_df.iterrows():
        pdf.set_fill_color(240, 240, 240)
        pdf.set_text_color(0, 0, 0)
        
        pdf.cell(widths[0], 7, str(row['Ticker']), border=1, align='C', fill=fill)
        pdf.cell(widths[1], 7, str(row['Weight (%)']), border=1, align='C', fill=fill)
        pdf.cell(widths[2], 7, str(row['Target Value ($)']), border=1, align='R', fill=fill)
        
        if "BUY" in str(row['ACTION']):
            pdf.set_text_color(0, 120, 0)
        else:
            pdf.set_text_color(200, 0, 0)
        pdf.cell(widths[3], 7, str(row['ACTION']), border=1, align='C', fill=fill)
        
        pdf.set_text_color(0, 0, 0)
        pdf.cell(widths[4], 7, str(row['MoS (%)']), border=1, align='C', fill=fill)
        pdf.cell(widths[5], 7, str(row['Hist. Ret (%)']), border=1, align='C', fill=fill)
        pdf.cell(widths[6], 7, str(row['Hist. Vol (%)']), border=1, align='C', fill=fill)
        pdf.cell(widths[7], 7, str(row['Ind. Sharpe']), border=1, align='C', fill=fill)
        pdf.cell(widths[8], 7, str(row['Div Yield (%)']), border=1, align='C', fill=fill)
        
        pdf.ln()
        fill = not fill

    pdf.ln(10)
    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(0, 6, '--- PORTFOLIO HEALTH SUMMARY ---', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('helvetica', '', 10)
    pdf.cell(0, 6, f"Total Target Value: ${total_val:,.2f}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Target Portfolio Sharpe Ratio: {portfolio_sharpe:.2f}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Estimated Annual Dividends: ${total_annual_div:,.2f}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Estimated Monthly Passive Income: ${total_annual_div/12:,.2f}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Average Portfolio Yield: {(total_annual_div/total_val)*100:.2f}%", new_x="LMARGIN", new_y="NEXT")
    
    # Adding the specific rationale for the 10% cap to the PDF
    pdf.ln(5)
    pdf.set_font('helvetica', 'I', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 5, "Diversification Note: A strict 10% maximum allocation cap has been applied to this portfolio. This forces the optimization engine to spread capital across a minimum of 10-15 distinctly uncorrelated assets, heavily reducing idiosyncratic firm risk while maintaining exposure to deep value FCFE generation.")

    pdf_filename = f"Portfolio_Action_Plan_{timestamp}.pdf"
    pdf.output(pdf_filename)
    print(f"[SUCCESS] PDF Report Exported: {pdf_filename}")

if __name__ == "__main__":
    winning_df = get_clean_winners("weekly_factor_data.csv")
    
    if not winning_df.empty:
        # UPDATE THIS: Put your actual current portfolio amounts here
        my_holdings = {
            "NVDA": 2000.00,
        }
        # UPDATE THIS: How much new cash are you injecting this week?
        new_cash = 20000.00 
        
        optimize_deployment(winning_df, my_holdings, new_cash)