import yfinance as yf
import pandas as pd
import statsmodels.api as sm
import urllib.request
import zipfile
import io
import datetime

def get_fama_french_5_factors():
    """Downloads and parses the Fama-French 5-Factor dataset directly from Dartmouth."""
    # NEW URL: Pointing to the 5-Factor 2x3 dataset
    url = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_5_Factors_2x3_CSV.zip"
    
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    response = urllib.request.urlopen(req)
    
    with zipfile.ZipFile(io.BytesIO(response.read())) as z:
        csv_name = z.namelist()[0]
        with z.open(csv_name) as f:
            # Skip the first 3 rows of header text
            df = pd.read_csv(f, skiprows=3)
    
    # Rename columns to match our regression logic
    df.rename(columns={df.columns[0]: 'Date', 'Mkt-RF': 'Market_Premium'}, inplace=True)
    
    # Clean the Date column 
    df['Date'] = pd.to_numeric(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date'])
    df = df[df['Date'] > 100000] 
    
    df['Date'] = pd.to_datetime(df['Date'].astype(int).astype(str), format='%Y%m').dt.to_period('M')
    df.set_index('Date', inplace=True)
    
    # Convert all 6 factor columns (including RMW and CMA) to numeric floats
    for col in ['Market_Premium', 'SMB', 'HML', 'RMW', 'CMA', 'RF']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
    return df

def calculate_fama_french_ke(ticker_symbol):
    print(f"Calculating Fama-French 5-Factor Cost of Equity for {ticker_symbol}...")
    
    end_date = datetime.datetime.today()
    start_date = end_date - datetime.timedelta(days=5*365)
    
    try:
        # 1. Fetch the new 5-Factor Data
        ff_data = get_fama_french_5_factors()
        ff_data = ff_data[(ff_data.index >= start_date.strftime('%Y-%m')) & (ff_data.index <= end_date.strftime('%Y-%m'))]
        
        # 2. Fetch Historical Stock Prices
        stock = yf.Ticker(ticker_symbol)
        prices = stock.history(start=start_date, end=end_date, interval='1mo')
        
        returns = prices['Close'].pct_change().dropna()
        returns.index = returns.index.tz_localize(None).to_period('M')
        
        # 3. Merge Data
        returns = returns * 100 
        dataset = pd.merge(returns, ff_data, left_index=True, right_index=True)
        dataset.rename(columns={'Close': 'Stock_Return'}, inplace=True)
        
        dataset['Excess_Return'] = dataset['Stock_Return'] - dataset['RF']
        
        # 4. Run the 5-Variable OLS Regression
        X = dataset[['Market_Premium', 'SMB', 'HML', 'RMW', 'CMA']]
        X = sm.add_constant(X)
        Y = dataset['Excess_Return']
        
        model = sm.OLS(Y, X).fit()
        betas = model.params
        
        # 5. Calculate Cost of Equity (Annualized across 5 dimensions)
        expected_mkt_premium = ff_data['Market_Premium'].mean() * 12
        expected_smb = ff_data['SMB'].mean() * 12
        expected_hml = ff_data['HML'].mean() * 12
        expected_rmw = ff_data['RMW'].mean() * 12
        expected_cma = ff_data['CMA'].mean() * 12
        
        tnx = yf.Ticker("^TNX")
        current_rf = tnx.history(period="1d")['Close'].iloc[-1]
        
        ke = current_rf + (betas['Market_Premium'] * expected_mkt_premium) + \
                          (betas['SMB'] * expected_smb) + \
                          (betas['HML'] * expected_hml) + \
                          (betas['RMW'] * expected_rmw) + \
                          (betas['CMA'] * expected_cma)
        
        return {
            "Ticker": ticker_symbol,
            "10-Yr Risk Free Rate (%)": round(current_rf, 2),
            "Market Beta": round(betas['Market_Premium'], 2),
            "Size Beta (SMB)": round(betas['SMB'], 2),
            "Value Beta (HML)": round(betas['HML'], 2),
            "Profitability Beta (RMW)": round(betas['RMW'], 2),
            "Investment Beta (CMA)": round(betas['CMA'], 2),
            "Cost of Equity (Ke) (%)": round(ke, 2),
            "R-Squared": round(model.rsquared, 2)
        }

    except Exception as e:
        return {"Error": f"Failed to calculate Cost of Equity: {e}"}

# Testing block
if __name__ == "__main__":
    target_ticker = "AMD"
    result = calculate_fama_french_ke(target_ticker)
    
    print("\n--- Fama-French 5-Factor Discount Rate ---")
    if "Error" not in result:
        for key, value in result.items():
            print(f"{key}: {value}")
    else:
        print(result["Error"])