"""
Step 2 of the pipeline: download historical NAV data for every fund in
schemes.csv and cache it locally so we never have to hit the API twice
for the same fund.

Input:  data/processed/schemes.csv (from fetch_schemes.py)
Output: data/raw/nav_history/{scheme_code}.json  (one file per fund)

What this does:
  1. Read the list of scheme_codes we care about (184 funds).
  2. For each one, check if we already downloaded it (cache file exists).
     If yes, skip - this makes the script resumable if it's interrupted.
  3. If not cached, call mfapi.in/mf/{scheme_code} and save the raw JSON
     response as-is. We save the RAW response (not a cleaned-up version)
     so metrics.py can re-process it however it needs without re-downloading.
  4. Be polite to the free API: small delay between requests.
"""

import json
import os
import time

import pandas as pd
import requests

CACHE_DIR = "data/raw/nav_history"
API_URL = "https://api.mfapi.in/mf/{}"
DELAY_SECONDS = 0.3  # be polite to the free API between requests


def fetch_one(scheme_code: int) -> dict:
    """Call mfapi.in for one scheme and return the parsed JSON response."""
    url = API_URL.format(scheme_code)
    response = requests.get(url, timeout=30)
    response.raise_for_status()  # raises an error if the request failed (e.g. 404, 500)
    return response.json()


def main():
    os.makedirs(CACHE_DIR, exist_ok=True)

    schemes = pd.read_csv("data/processed/schemes.csv")

    already_cached = 0
    downloaded = 0
    failed = []

    # itertuples() loops over rows of a DataFrame as lightweight objects
    # (row.scheme_code, row.scheme_name, etc.) - faster and cleaner than iterrows()
    for row in schemes.itertuples():
        cache_path = os.path.join(CACHE_DIR, f"{row.scheme_code}.json")

        if os.path.exists(cache_path):
            already_cached += 1
            continue

        try:
            data = fetch_one(row.scheme_code)
        except requests.RequestException as e:
            print(f"  FAILED: {row.scheme_code} ({row.scheme_name}) - {e}")
            failed.append((row.scheme_code, row.scheme_name))
            continue

        with open(cache_path, "w") as f:
            json.dump(data, f)

        downloaded += 1
        if downloaded % 20 == 0:
            print(f"  ...downloaded {downloaded} so far")

        time.sleep(DELAY_SECONDS)

    print(f"\nAlready cached: {already_cached}")
    print(f"Newly downloaded: {downloaded}")
    print(f"Failed: {len(failed)}")
    if failed:
        for code, name in failed:
            print(f"  {code}: {name}")


if __name__ == "__main__":
    main()
