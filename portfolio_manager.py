import pandas as pd
import yfinance as yf

def rebalance_holdings(current_holdings_csv="current_holdings.csv", target_plan_csv="Portfolio_Action_Plan_2026_05_02.csv"):
    """
    Expects 'current_holdings.csv' with columns: Ticker, Quantity
    """
    targets = pd.read_csv(target_plan_csv)
    try:
        current = pd.read_csv(current_holdings_csv)
    except:
        print("Create 'current_holdings.csv' with columns: Ticker, Quantity")
        return

    total_market_value = 0
    holdings_data = []

    # 1. Get Live Market Values
    for _, row in current.iterrows():
        price = yf.Ticker(row['Ticker']).fast_info['last_price']
        value = price * row['Quantity']
        total_market_value += value
        holdings_data.append({"Ticker": row['Ticker'], "Value": value})

    # 2. Calculate Drift
    print(f"\nTotal Portfolio Market Value: ${total_market_value:,.2f}")
    print("REBALANCING ORDERS:")
    
    for _, t_row in targets.iterrows():
        ticker = t_row['Ticker']
        target_weight = float(t_row['Weight (%)'].strip('%')) / 100
        target_dollars = total_market_value * target_weight
        
        current_val = next((item['Value'] for item in holdings_data if item['Ticker'] == ticker), 0)
        diff = target_dollars - current_val
        
        if abs(diff) > 50: # Only trade if difference > $50
            action = "BUY" if diff > 0 else "SELL"
            print(f"{ticker}: {action} ${abs(diff):,.2f} (Target: {target_weight*100:.1f}%)")

if __name__ == "__main__":
    rebalance_holdings()