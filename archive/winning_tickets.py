import pandas as pd
import os

def generate_winning_tickets(input_file="valuation_results.csv", output_file="winning_tickets.csv", top_n=25):
    """
    Scrubs the raw pipeline data, removes outliers, 
    and saves the 'Sane Winners' to a new CSV.
    """
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found. Run master_pipeline.py first.")
        return []

    print("--- Running Glitch-Removal Automation ---")
    df = pd.read_csv(input_file)
    original_count = len(df)

    # 1. REMOVE GLITCHES (The 'Too Good to be True' Filter)
    # We remove anything with a Margin of Safety over 150%
    clean_df = df[df['Margin of Safety (%)'] <= 150.0]
    
    # 2. REMOVE TRAPS (The 'Buy Zone' Floor)
    # We only want high-conviction stuff (15% discount or better)
    clean_df = clean_df[clean_df['Margin of Safety (%)'] >= 15.0]

    # 3. REMOVE CALCULATED ERRORS
    # Cost of Equity shouldn't realistically be lower than 6% 
    clean_df = clean_df[clean_df['Cost of Equity (%)'] >= 6.0]

    glitches_removed = original_count - len(clean_df)
    
    # Sort by Margin of Safety (Best deals at the top)
    clean_df = clean_df.sort_values(by='Margin of Safety (%)', ascending=False)

    # Save ALL valid candidates (all 72 you found) to the CSV
    clean_df.to_csv(output_file, index=False)
    
    print(f"Scrubbing Complete:")
    print(f"  -> Total Stocks Analyzed: {original_count}")
    print(f"  -> Outliers/Glitches Removed: {glitches_removed}")
    print(f"  -> Valid 'Winning Tickets' Found: {len(clean_df)}")
    
    print(f"\nFinal Winning List (Top {top_n}) saved to {output_file}:")
    
    # FIX: Corrected variable name to top_25 to match your portfolio size
    top_25 = clean_df.head(top_n)
    print(top_25[['Ticker', 'Intrinsic Value', 'Margin of Safety (%)']].to_string(index=False))
    
    return top_25['Ticker'].tolist()

if __name__ == "__main__":
    winners = generate_winning_tickets()