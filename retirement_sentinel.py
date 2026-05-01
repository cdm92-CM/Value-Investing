import yfinance as yf
import smtplib
import schedule
import time
import os
from email.message import EmailMessage
from datetime import datetime
from dotenv import load_dotenv

# --- CORE LOGIC IMPORTS ---
from master_pipeline import get_major_indices_tickers, run_screener
from winning_tickets import generate_winning_tickets

# Load credentials from .env
load_dotenv()
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# Your 16 Optimized Assets and their Target Weights
TARGET_WEIGHTS = {
    "PGR": 0.0329, "GOOGL": 0.0235, "APH": 0.0162, "CASY": 0.10,
    "L.TO": 0.10, "LLY": 0.10, "MCK": 0.10, "TRGP": 0.10,
    "WN.TO": 0.10, "NVDA": 0.0962, "COR": 0.0914, "CF": 0.0081,
    "CME": 0.0071, "VLO": 0.0064, "SU.TO": 0.0635, "CNQ.TO": 0.0546
}

def send_morning_briefing():
    print(f"[{datetime.now().strftime('%H:%M')}] Generating morning briefing...")
    body = "Retirement Portfolio: Morning Market Intelligence\n" + "="*50 + "\n"
    for ticker in TARGET_WEIGHTS.keys():
        try:
            stock = yf.Ticker(ticker)
            news = stock.news[:2]
            if news:
                body += f"\n[{ticker}]"
                for item in news:
                    body += f"\n- {item['title']}\n  Source: {item['publisher']}\n"
        except: continue

    msg = EmailMessage()
    msg['Subject'] = f"Retirement Sentinel: Daily Briefing ({datetime.now().strftime('%Y-%m-%d')})"
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = EMAIL_ADDRESS
    msg.set_content(body)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
        print("Briefing dispatched.")
    except Exception as e: print(f"Email failed: {e}")

def run_weekly_market_sweep():
    print(f"\n--- WEEKLY MARKET SCAN: {datetime.now().strftime('%Y-%m-%d')} ---")
    tickers = get_major_indices_tickers()
    run_screener(tickers)
    generate_winning_tickets()
    print("Market Sweep Complete. New tickets updated.")

def run_rebalance_audit():
    print(f"\n--- WEEKLY REBALANCE AUDIT [{datetime.now().strftime('%Y-%m-%d')}] ---")
    total_value = 22000.00 
    body = "Weekly Portfolio Rebalance Audit\n" + "="*50 + f"\nTotal Baseline: ${total_value:,.2f}\n\n"
    body += f"{'Ticker':<8} | {'Target Weight':<15} | {'Target Value':<15}\n" + "-"*45 + "\n"

    for ticker, weight in TARGET_WEIGHTS.items():
        target_dollars = total_value * weight
        body += f"{ticker:<8} | {weight*100:>13.2f}% | ${target_dollars:>13,.2f}\n"

    msg = EmailMessage()
    msg['Subject'] = "Retirement Sentinel: Weekly Rebalance Plan"
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = EMAIL_ADDRESS
    msg.set_content(body)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
        print("Rebalance Plan dispatched.")
    except Exception as e: print(f"Email failed: {e}")

# SCHEDULE:
schedule.every().day.at("09:00").do(send_morning_briefing)
schedule.every().sunday.at("08:00").do(run_weekly_market_sweep)
schedule.every().sunday.at("18:00").do(run_rebalance_audit)

if __name__ == "__main__":
    print("\nRETIREMENT SENTINEL: OPERATIONAL")
    while True:
        schedule.run_pending()
        time.sleep(60)