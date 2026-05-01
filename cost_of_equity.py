import yfinance as yf
import pandas as pd
import statsmodels.api as sm
import urllib.request
import zipfile
import io
import datetime

def get_fama_french_factors():
    """Downloads and parses the Fama-French 3-Factor dataset directly from Dartmouth."""
    url = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors_CSV.zip"
    
    # Download the ZIP file
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    response = urllib.request.urlopen(req)
    
    # Unzip in memory and read the CSV
    with zipfile.ZipFile(io.BytesIO(response.read())) as z:
        csv_name = z.namelist()[0]
        with z.open(csv_name) as f:
            # The first 3 rows of Kenneth French's CSV are header text we can skip
            df = pd.read_csv(f, skiprows=3)
    
    # Rename columns
    df.rename(columns={df.columns[0]: 'Date', 'Mkt-RF': 'Market_Premium'}, inplace=True)
    
    # Clean the Date column (this isolates the monthly data and drops the annual data at the bottom)
    df['Date'] = pd.to_numeric(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date'])
    df = df[df['Date'] > 100000] # Keeps only the 6-digit YYYYMM monthly dates
    
    # Set Date as the DataFrame index
    df['Date'] = pd.to_datetime(df['Date'].astype(int).astype(str), format='%Y%m').dt.to_period('M')
    df.set_index('Date', inplace=True)
    
    # Convert factor columns to numeric floats
    for col in ['Market_Premium', 'SMB', 'HML', 'RF']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
    return df

def calculate_fama_french_ke(ticker_symbol):
    print(f"Pulling 5-year data and calculating Fama-French Cost of Equity for {ticker_symbol}...")
    
    end_date = datetime.datetime.today()
    start_date = end_date - datetime.timedelta(days=5*365)
    
    try:
        # 1. Fetch our direct Fama-French Data
        ff_data = get_fama_french_factors()
        
        # Filter FF data to our trailing 5-year timeframe
        ff_data = ff_data[(ff_data.index >= start_date.strftime('%Y-%m')) & (ff_data.index <= end_date.strftime('%Y-%m'))]
        
        # 2. Fetch Historical Stock Prices
        stock = yf.Ticker(ticker_symbol)
        prices = stock.history(start=start_date, end=end_date, interval='1mo')
        
        # Calculate monthly percentage return
        returns = prices['Close'].pct_change().dropna()
        returns.index = returns.index.tz_localize(None).to_period('M')
        
        # 3. Merge Data
        returns = returns * 100 # Multiply by 100 to match the FF percentage format
        dataset = pd.merge(returns, ff_data, left_index=True, right_index=True)
        dataset.rename(columns={'Close': 'Stock_Return'}, inplace=True)
        
        # Calculate Excess Return (Return - Risk Free Rate)
        dataset['Excess_Return'] = dataset['Stock_Return'] - dataset['RF']
        
        # 4. Run the OLS Regression
        X = dataset[['Market_Premium', 'SMB', 'HML']]
        X = sm.add_constant(X)
        Y = dataset['Excess_Return']
        
        model = sm.OLS(Y, X).fit()
        betas = model.params
        
        # 5. Calculate Cost of Equity (Annualized)
        expected_mkt_premium = ff_data['Market_Premium'].mean() * 12
        expected_smb = ff_data['SMB'].mean() * 12
        expected_hml = ff_data['HML'].mean() * 12
        
        # Get live 10-Year Treasury Yield
        tnx = yf.Ticker("^TNX")
        current_rf = tnx.history(period="1d")['Close'].iloc[-1]
        
        ke = current_rf + (betas['Market_Premium'] * expected_mkt_premium) + \
                          (betas['SMB'] * expected_smb) + \
                          (betas['HML'] * expected_hml)
        
        return {
            "Ticker": ticker_symbol,
            "10-Yr Risk Free Rate (%)": round(current_rf, 2),
            "Market Beta": round(betas['Market_Premium'], 2),
            "Size Beta (SMB)": round(betas['SMB'], 2),
            "Value Beta (HML)": round(betas['HML'], 2),
            "Cost of Equity (Ke) (%)": round(ke, 2),
            "R-Squared": round(model.rsquared, 2)
        }

    except Exception as e:
        return {"Error": f"Failed to calculate Cost of Equity: {e}"}

if __name__ == "__main__":
    target_ticker = "AMD"
    result = calculate_fama_french_ke(target_ticker)
    
    print("\n--- Fama-French Discount Rate ---")
    for key, value in result.items():
        print(f"{key}: {value}")