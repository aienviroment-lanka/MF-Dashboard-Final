"""
data_cleaning.py
----------------
Cleans and normalises raw records from data_ingestion.py.
Produces a clean DataFrame suitable for the dashboard.
"""

import pandas as pd
import numpy as np


def fmt_pct(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    return round(float(v), 2)


def clean_records(records: list) -> pd.DataFrame:
    """
    Converts a list of raw scheme dicts into a clean display DataFrame.
    Applies type coercion, rounding, and handles missing values.
    """
    rows = []
    for r in records:
        rows.append({
            "Scheme Name"          : r.get("scheme_name", ""),
            "Fund House"           : r.get("fund_house", ""),
            "Category"             : r.get("category", ""),
            "Launch Date"          : r.get("launch_date", "N/A"),
            "Latest NAV (₹)"       : r.get("latest_nav"),
            "Inception Return (%)" : fmt_pct(r.get("ret_inception")),
            "1M Return (%)"        : fmt_pct(r.get("ret_1m")),
            "3M Return (%)"        : fmt_pct(r.get("ret_3m")),
            "6M Return (%)"        : fmt_pct(r.get("ret_6m")),
            "1Y Return (%)"        : fmt_pct(r.get("ret_1y")),
            "3Y CAGR (%)"          : fmt_pct(r.get("cagr_3y")),
            "5Y CAGR (%)"          : fmt_pct(r.get("cagr_5y")),
            "Std Dev (%)"          : fmt_pct(r.get("std_dev")),
            "Num Stocks"           : r.get("num_stocks"),
            "Cash (%)"             : fmt_pct(r.get("cash_pct")),
            "Nifty 1Y (%)"         : fmt_pct(r.get("nifty_1y")),
            "Nifty 3Y (%)"         : fmt_pct(r.get("nifty_3y")),
            "Nifty 5Y (%)"         : fmt_pct(r.get("nifty_5y")),
            "Alpha 1Y (%)"         : fmt_pct(r.get("alpha_1y")),
            "Alpha 3Y (%)"         : fmt_pct(r.get("alpha_3y")),
            "Alpha 5Y (%)"         : fmt_pct(r.get("alpha_5y")),
            "_code"                : r.get("scheme_code"),
        })

    df = pd.DataFrame(rows)
    return df


def build_summary(df: pd.DataFrame) -> dict:
    """Derives KPI summary from the clean DataFrame."""
    return {
        "total_schemes"  : len(df),
        "avg_1y"         : df["1Y Return (%)"].mean(),
        "avg_3y"         : df["3Y CAGR (%)"].mean(),
        "avg_5y"         : df["5Y CAGR (%)"].mean(),
        "avg_std"        : df["Std Dev (%)"].mean(),
        "avg_alpha_1y"   : df["Alpha 1Y (%)"].mean(),
    }
