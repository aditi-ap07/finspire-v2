import os
import requests
import pandas as pd


NSE_URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
OUTPUT_PATH = "data/companies.csv"


def update_companies():
    try:
        # Download CSV
        response = requests.get(NSE_URL, timeout=10)
        response.raise_for_status()

        # Load into DataFrame
        from io import StringIO
        df = pd.read_csv(StringIO(response.text))

        # Basic validation
        if df.empty:
            print("Downloaded CSV is empty. Aborting update.")
            return

        # Keep only EQ series (main equities)
        if "SERIES" in df.columns:
            df = df[df["SERIES"] == "EQ"]

        # Rename columns
        df = df.rename(columns={
            "SYMBOL": "symbol",
            "NAME OF COMPANY": "name"
        })

        # Keep only required columns
        df = df[["symbol", "name"]]

        # Drop missing / duplicates
        df = df.dropna(subset=["symbol", "name"])
        df = df.drop_duplicates(subset=["symbol"])

        # Clean text
        df["symbol"] = df["symbol"].astype(str).str.strip()
        df["name"] = df["name"].astype(str).str.strip()

        # Final validation
        if df.empty:
            print("Processed DataFrame is empty. Aborting overwrite.")
            return

        # Ensure directory exists
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

        # Save
        df.to_csv(OUTPUT_PATH, index=False)

        print(f"Updated companies.csv with {len(df)} entries.")

    except Exception as e:
        print(f"Failed to update companies list: {e}")


if __name__ == "__main__":
    print("Updating companies list from NSE...")
    update_companies()
    print("Done.")
