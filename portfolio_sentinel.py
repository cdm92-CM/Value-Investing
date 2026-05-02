import yfinance as yf
import pandas as pd
from datetime import datetime
import xml.etree.ElementTree as ET
import urllib.request
from fpdf import FPDF

# --- TEXT SANITIZER (The Fix) ---
def sanitize_text(text):
    """Replaces Unicode typographic characters with standard Latin-1 equivalents for PDF rendering."""
    if not text:
        return ""
    replacements = {
        '’': "'",
        '‘': "'",
        '“': '"',
        '”': '"',
        '—': '-',
        '–': '-',
        '…': '...',
        '\u200b': ''  # Zero-width space
    }
    for search, replace in replacements.items():
        text = text.replace(search, replace)
        
    # Catch-all for any other unsupported characters (ignores them safely)
    return text.encode('latin-1', 'ignore').decode('latin-1')

# --- PDF REPORTING CLASS ---
class SentinelReport(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 16)
        self.set_text_color(0, 51, 102) 
        self.cell(0, 10, 'Morning Sentinel Intelligence Report', align='C', new_x="LMARGIN", new_y="NEXT")
        
        self.set_font('helvetica', 'I', 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, f'Intelligence Briefing: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', align='C', new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

# --- INTELLIGENCE ENGINE ---
def get_material_news(ticker):
    """Pulls from multiple RSS/Atom feeds and strictly filters for material corporate events."""
    raw_news = []
    filtered_news = []
    
    # Strip ".TO" for Canadian stocks so the SEC database doesn't get confused
    clean_ticker = ticker.split('.')[0] 
    
    # 1. WIDEN THE NET: Triple Data Sources
    yahoo_url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
    google_url = f"https://news.google.com/rss/search?q={ticker}+stock+when:7d" 
    sec_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={clean_ticker}&type=&dateb=&owner=exclude&start=0&count=10&output=atom"
    
    headers = {'User-Agent': 'QuantDesk Admin@investing.com'}
    
    for url in [yahoo_url, google_url, sec_url]:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as response:
                tree = ET.parse(response)
                root = tree.getroot()
                
                # PARSER A: Standard RSS 2.0 (Yahoo, Google)
                for item in root.findall('.//item')[:10]:
                    title_elem = item.find('title')
                    link_elem = item.find('link')
                    if title_elem is not None and link_elem is not None:
                        raw_news.append({"title": title_elem.text, "link": link_elem.text})
                        
                # PARSER B: Atom Feed (SEC EDGAR)
                ns = {'atom': 'http://www.w3.org/2005/Atom'}
                for entry in root.findall('.//atom:entry', ns)[:10]:
                    title_elem = entry.find('atom:title', ns)
                    link_elem = entry.find('atom:link', ns)
                    if title_elem is not None and link_elem is not None:
                        raw_news.append({"title": f"SEC FILING: {title_elem.text}", "link": link_elem.attrib.get('href', '')})
        except Exception:
            continue 
            
    # 2. TIGHTEN THE SIEVE: The Materiality Gateway
    material_keywords = [
        "EARNINGS", "Q1", "Q2", "Q3", "Q4", "GUIDANCE", "FORECAST",
        "DIVIDEND", "BUYBACK", "SPLIT", "OFFERING", 
        "MERGER", "ACQUISITION", "BUYOUT", "SPINOFF",
        "CEO", "CFO", "RESIGNS", "APPOINTS", "BOARD",
        "8-K", "10-Q", "10-K", "INVESTIGATION", "SUBPOENA",
        "LAWSUIT", "SETTLEMENT", "BANKRUPTCY", "CHAPTER 11",
        "LAYOFFS", "RESTRUCTURING", "CLINICAL TRIAL", "FDA", "DOWNGRADE", "SEC FILING:"
    ]
    
    seen_titles = set()
    
    for item in raw_news:
        if not item.get('title'):
            continue
            
        headline_upper = item['title'].upper()
        is_material = any(keyword in headline_upper for keyword in material_keywords)
        
        if is_material and item['title'] not in seen_titles:
            filtered_news.append(item)
            seen_titles.add(item['title'])
            
            # Stop once we have the top 4 material events
            if len(filtered_news) >= 4:
                break
                
    return filtered_news

# --- MAIN PIPELINE ---
def run_portfolio_sentinel(csv_input="Portfolio_Action_Plan_2026_05_02.csv"):
    try:
        df = pd.read_csv(csv_input)
        tickers = df['Ticker'].tolist()
    except Exception as e:
        print(f"Error reading CSV: {e}. Make sure {csv_input} is in the same folder.")
        return

    # Initialize PDF
    pdf = SentinelReport()
    pdf.add_page()
    
    # Calculate Macro Context (S&P 500 YTD)
    spy = yf.Ticker("^GSPC")
    spy_ytd_ret = 0
    spy_hist = spy.history(period="ytd")
    if not spy_hist.empty:
        spy_start = spy_hist['Close'].iloc[0]
        spy_now = spy_hist['Close'].iloc[-1]
        spy_ytd_ret = ((spy_now - spy_start) / spy_start) * 100

    pdf.set_font('helvetica', 'B', 11)
    pdf.cell(0, 10, f"S&P 500 Benchmark YTD: {spy_ytd_ret:+.2f}%", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    print(f"\n--- MORNING SENTINEL REPORT: {datetime.now().strftime('%Y-%m-%d')} ---")
    print(f"S&P 500 Benchmark YTD: {spy_ytd_ret:+.2f}%\n")
    
    # 3. CRITICAL SENTIMENT ALERTS
    critical_alerts = ["DOWNGRADE", "LAWSUIT", "INVESTIGATION", "FRAUD", "MISS", "SEC", "LEGAL", "RESIGNS", "BANKRUPTCY", "SUBPOENA"]

    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            price = stock.fast_info.get('last_price') or stock.history(period="1d")['Close'].iloc[-1]
            
            ytd_hist = stock.history(period="ytd")
            if not ytd_hist.empty:
                ytd_change = ((price - ytd_hist['Close'].iloc[0]) / ytd_hist['Close'].iloc[0]) * 100
                rel_strength = ytd_change - spy_ytd_ret
                ytd_str = f"{ytd_change:+.1f}% (Rel. Str: {rel_strength:+.1f}%)"
            else:
                ytd_change = 0
                ytd_str = "N/A"
            
            # PDF Asset Block Header
            pdf.set_fill_color(240, 245, 250)
            pdf.set_font('helvetica', 'B', 12)
            pdf.set_text_color(0, 51, 102)
            pdf.cell(0, 10, f" {ticker} | Price: ${price:.2f} | YTD: {ytd_str}", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
            
            print(f">>> Analyzing {ticker}...")
            print(f"Price: ${price:.2f} | YTD: {ytd_str}")
            
            news = get_material_news(ticker)
            if news:
                pdf.set_font('helvetica', '', 9)
                for item in news:
                    # ---> THIS IS THE FIX IN ACTION <---
                    headline = sanitize_text(item['title'])
                    
                    is_critical = any(word in headline.upper() for word in critical_alerts)
                    
                    if is_critical:
                        pdf.set_text_color(200, 0, 0) # RED
                        print(f"![CRITICAL RISK] {headline}")
                    else:
                        pdf.set_text_color(50, 50, 50) # DARK GREY
                        print(f"- {headline}")
                    
                    pdf.multi_cell(0, 6, f"- {headline}", new_x="LMARGIN", new_y="NEXT")
                    pdf.set_text_color(0, 100, 255)
                    pdf.set_font('helvetica', 'I', 8)
                    pdf.cell(0, 5, f"  Source: {item['link']}", new_x="LMARGIN", new_y="NEXT")
                    pdf.set_font('helvetica', '', 9)
                    pdf.ln(1)
            else:
                pdf.set_text_color(150, 150, 150)
                pdf.cell(0, 10, "  No material catalysts or statutory filings detected in the last 7 days.", new_x="LMARGIN", new_y="NEXT")
                print("No material events found.")
            
            pdf.ln(3)
            print("-" * 30)

        except Exception as e:
            print(f"Error with {ticker}: {e}")

    # Save Final PDF Document
    timestamp = datetime.now().strftime("%Y_%m_%d")
    filename = f"Sentinel_Intelligence_Report_{timestamp}.pdf"
    pdf.output(filename)
    print(f"\n[SUCCESS] Intelligence Report Exported: {filename}")

if __name__ == "__main__":
    run_portfolio_sentinel()