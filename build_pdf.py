import pandas as pd
from fpdf import FPDF
from datetime import datetime

class FactorReport(FPDF):
    def header(self):
        # Professional Header Design
        self.set_font('helvetica', 'B', 16)
        self.set_text_color(0, 51, 102) # Institutional Dark Blue
        self.cell(0, 10, 'Quantitative Factor Exposure & Valuation Report', align='C', new_x="LMARGIN", new_y="NEXT")
        
        self.set_font('helvetica', 'I', 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, f'Market Sweep Date: {datetime.now().strftime("%Y-%m-%d")} | S&P 100 & TSX 60', align='C', new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

        # --- TABLE HEADERS (Repeats automatically on every page) ---
        self.set_font('helvetica', 'B', 8)
        self.set_text_color(255, 255, 255)
        self.set_fill_color(0, 51, 102)
        
        # 10 columns for Landscape orientation
        self.col_widths = [18, 18, 20, 20, 20, 25, 15, 15, 15, 80]
        headers = ['Ticker', 'Price ($)', 'Worst ($)', 'Base ($)', 'Best ($)', 'Margin of Safety', 'Ke (%)', 'Beta', 'HML', 'Growth Scenario']
        
        for i in range(len(headers)):
            self.cell(self.col_widths[i], 8, headers[i], border=1, align='C', fill=True)
        self.ln()

    def footer(self):
        # Page Numbers
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

def build_pdf():
    print("Reading data and formatting Institutional PDF...")
    
    try:
        df = pd.read_csv('weekly_factor_data.csv')
    except FileNotFoundError:
        print("Error: weekly_factor_data.csv not found. Run generate_report.py first.")
        return

    # --- 1. REMOVE OUTLIERS & GLITCHES ---
    original_count = len(df)
    # Filter out absurd upside (data errors) and extreme negative value traps
    df = df[(df['Margin_of_Safety_Pct'] <= 150.0) & (df['Margin_of_Safety_Pct'] >= -100.0)]
    # Filter out abnormally low discount rates
    df = df[df['Cost_of_Equity_Pct'] >= 5.0] 
    
    # Sort by value so the best deals remain at the top
    df = df.sort_values(by="Margin_of_Safety_Pct", ascending=False)
    
    print(f"Filtered out {original_count - len(df)} outliers. Rendering {len(df)} assets...")

    # Switch to Landscape ('L') to fit the Monte Carlo spread
    pdf = FactorReport(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    # --- LEGAL DISCLAIMER (Crucial for Ontario/OSC compliance) ---
    pdf.set_font('helvetica', 'B', 8)
    pdf.set_text_color(200, 0, 0)
    disclaimer = (
        "CONFIDENTIAL & PROPRIETARY. This report is generated algorithmically using Fama-French "
        "and Free Cash Flow to Equity (FCFE) modeling. It is provided for informational and educational "
        "purposes ONLY. This is NOT financial advice. Past performance is not indicative of future results. "
        "The author is not a registered investment advisor."
    )
    pdf.multi_cell(0, 5, disclaimer, border=1, align='L')
    pdf.ln(5)

    # --- TABLE DATA ROW BY ROW ---
    pdf.set_font('helvetica', '', 8)
    
    fill = False # Alternating row colors
    for index, row in df.iterrows():
        pdf.set_fill_color(240, 240, 240)
        
        # Format the numbers cleanly, pulling the new Best/Worst data
        ticker = str(row['Ticker'])
        price = f"{row['Current_Price']:.2f}"
        worst = f"{row.get('Intrinsic_Value_Worst', 0):.2f}"
        base = f"{row.get('Intrinsic_Value_Base', 0):.2f}"
        best = f"{row.get('Intrinsic_Value_Best', 0):.2f}"
        margin = f"{row['Margin_of_Safety_Pct']:.1f}%"
        ke = f"{row['Cost_of_Equity_Pct']:.1f}%"
        beta = f"{row['Market_Beta']:.2f}"
        hml = f"{row.get('Value_Factor_HML', 0):.2f}"
        scen = str(row['Used_Scenario'])
        
        # Print basic cells
        pdf.set_text_color(0, 0, 0)
        pdf.cell(pdf.col_widths[0], 6, ticker, border=1, align='C', fill=fill)
        pdf.cell(pdf.col_widths[1], 6, price, border=1, align='C', fill=fill)
        
        # The Monte Carlo Spread
        pdf.cell(pdf.col_widths[2], 6, worst, border=1, align='C', fill=fill)
        pdf.set_font('helvetica', 'B', 8) # Bold the Base Case
        pdf.cell(pdf.col_widths[3], 6, base, border=1, align='C', fill=fill)
        pdf.set_font('helvetica', '', 8)
        pdf.cell(pdf.col_widths[4], 6, best, border=1, align='C', fill=fill)
        
        # Color-code the Margin of Safety
        if row['Margin_of_Safety_Pct'] >= 15:
            pdf.set_text_color(0, 120, 0) 
        elif row['Margin_of_Safety_Pct'] < 0:
            pdf.set_text_color(200, 0, 0)
        else:
            pdf.set_text_color(0, 0, 0)
            
        pdf.cell(pdf.col_widths[5], 6, margin, border=1, align='C', fill=fill)
        
        # Risk Factors & Growth Assumptions
        pdf.set_text_color(0, 0, 0)
        pdf.cell(pdf.col_widths[6], 6, ke, border=1, align='C', fill=fill)
        pdf.cell(pdf.col_widths[7], 6, beta, border=1, align='C', fill=fill)
        pdf.cell(pdf.col_widths[8], 6, hml, border=1, align='C', fill=fill)
        pdf.cell(pdf.col_widths[9], 6, scen, border=1, align='L', fill=fill)
        
        pdf.ln()
        fill = not fill # Toggle row background color

    # Save the file
    output_name = f'Factor_Report_{datetime.now().strftime("%Y_%m_%d")}.pdf'
    pdf.output(output_name)
    print(f"Success! {output_name} generated.")

if __name__ == "__main__":
    build_pdf()