"""
Step 1 of the pipeline: build a clean, one-row-per-fund scheme list.

Input:  data/raw/mutual_fund_data.csv (AMFI data, via InertExpert2911/Mutual_Fund_Data)
Output: data/processed/schemes.csv

What this does:
  1. Keep only active (non-closed) funds in our 10 target equity categories.
  2. Each "fund" appears as several rows (plans: Direct/Regular x Growth/IDCW/Bonus
     etc.) - group these into ONE row per fund.
  3. Total AUM for a fund = sum of Average_AUM_Cr across ALL its plans (used later
     as an eligibility filter - overall fund size, not which plan you'd invest in).
  4. Pick ONE "reference plan" per fund for NAV history / returns: prefer Direct
     Growth (no distributor commission -> cleaner read on manager performance),
     fall back to Regular Growth if no Direct Growth plan exists.
"""

import pandas as pd

TARGET_CATEGORIES = [
    "Equity Scheme - Large Cap Fund",
    "Equity Scheme - Large & Mid Cap Fund",
    "Equity Scheme - Mid Cap Fund",
    "Equity Scheme - Small Cap Fund",
    "Equity Scheme - Multi Cap Fund",
    "Equity Scheme - Flexi Cap Fund",
    "Equity Scheme - Value Fund",
    "Equity Scheme - Focused Fund",
    "Equity Scheme - Dividend Yield Fund",
    "Equity Scheme - ELSS",
]


def is_growth_plan(nav_name: str) -> bool:
    """A 'plain growth' plan: mentions Growth, but isn't a Bonus/IDCW/Institutional variant."""
    n = nav_name.lower()
    return "growth" in n and "bonus" not in n and "idcw" not in n and "institutional" not in n


def is_direct_plan(nav_name: str) -> bool:
    return "direct" in nav_name.lower()


def pick_reference_plan(fund_rows: pd.DataFrame) -> pd.Series | None:
    """From all plan-rows of one fund, pick the Direct Growth row, else Regular Growth."""
    growth_rows = fund_rows[fund_rows["Scheme_NAV_Name"].apply(is_growth_plan)]
    if growth_rows.empty:
        return None

    direct_rows = growth_rows[growth_rows["Scheme_NAV_Name"].apply(is_direct_plan)]
    candidates = direct_rows if not direct_rows.empty else growth_rows
    plan_type = "direct" if not direct_rows.empty else "regular"

    # If multiple candidates remain (rare), take the one with the largest AUM
    chosen = candidates.loc[candidates["Average_AUM_Cr"].fillna(0).idxmax()]
    return chosen, plan_type


def build_schemes_table(raw_csv: str) -> pd.DataFrame:
    df = pd.read_csv(raw_csv)

    active = df[df["Closure_Date"].isna()]
    target = active[active["Scheme_Category"].isin(TARGET_CATEGORIES)]

    records = []
    skipped_no_growth_plan = []

    # groupby splits the DataFrame into one group per (Scheme_Name, AMC, Category) -
    # each group is all the "plan rows" belonging to one fund.
    for (scheme_name, amc, category), fund_rows in target.groupby(
        ["Scheme_Name", "AMC", "Scheme_Category"], dropna=False
    ):
        total_aum = fund_rows["Average_AUM_Cr"].sum()  # NaN treated as 0 by .sum()

        result = pick_reference_plan(fund_rows)
        if result is None:
            skipped_no_growth_plan.append(scheme_name)
            continue
        ref_row, plan_type = result

        records.append({
            "scheme_code": ref_row["Scheme_Code"],
            "scheme_name": scheme_name,
            "amc": amc,
            "category": category,
            "total_aum_cr": round(total_aum, 2),
            "reference_plan": plan_type,
            "reference_plan_name": ref_row["Scheme_NAV_Name"],
            "nav": ref_row["NAV"],
            "launch_date": ref_row["Launch_Date"],
        })

    schemes = pd.DataFrame(records)
    schemes["launch_date"] = pd.to_datetime(schemes["launch_date"])
    schemes = schemes.sort_values(["category", "total_aum_cr"], ascending=[True, False])

    print(f"Funds processed: {len(records) + len(skipped_no_growth_plan)}")
    print(f"Funds with a usable Growth plan: {len(records)}")
    print(f"Funds skipped (no Growth plan found): {len(skipped_no_growth_plan)}")
    if skipped_no_growth_plan:
        print("  Skipped:", skipped_no_growth_plan)
    print(f"\nReference plan type counts:\n{schemes['reference_plan'].value_counts()}")
    print(f"\nFunds per category:\n{schemes['category'].value_counts()}")

    return schemes


if __name__ == "__main__":
    schemes = build_schemes_table("data/raw/mutual_fund_data.csv")
    schemes.to_csv("data/processed/schemes.csv", index=False)
    print(f"\nSaved {len(schemes)} funds to data/processed/schemes.csv")
    print("\nSample (Large Cap):")
    print(schemes[schemes["category"] == "Equity Scheme - Large Cap Fund"].head(5).to_string(index=False))
