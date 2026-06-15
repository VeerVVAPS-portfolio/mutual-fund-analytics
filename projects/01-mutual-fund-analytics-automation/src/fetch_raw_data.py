"""
Step 0 of the pipeline: download the AMFI-derived scheme/AUM dataset that
fetch_schemes.py depends on.

Source: InertExpert2911/Mutual_Fund_Data on GitHub (AMFI data, processed
to one row per fund-plan with category and Average AUM).

Output: data/raw/mutual_fund_data.csv
"""

import os

import requests

URL = "https://raw.githubusercontent.com/InertExpert2911/Mutual_Fund_Data/main/mutual_fund_data.csv"
OUTPUT_PATH = "data/raw/mutual_fund_data.csv"


def main():
    if os.path.exists(OUTPUT_PATH):
        print(f"{OUTPUT_PATH} already exists, skipping download.")
        return

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    response = requests.get(URL, timeout=60)
    response.raise_for_status()

    with open(OUTPUT_PATH, "wb") as f:
        f.write(response.content)

    print(f"Saved {len(response.content) / 1_000_000:.2f} MB to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
