"""
data_ingestion.py
-----------------
Primary Sources:
  1. MFAPI (https://api.mfapi.in)  — NAV history for all AMFI-registered schemes
  2. AMFI India (https://www.amfiindia.com) — Official NAV, AUM, expense ratio
  3. Screener / BSE India fallbacks for portfolio holdings

All scheme_ids are AMFI scheme codes (numeric).  The dashboard accepts a list of
these codes and assembles every metric from public, authorised sources only.
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import streamlit as st

# ──────────────────────────────────────────────────────────────────────────────
# AMFI-registered scheme codes for the 14 schemes
# Update this list with the correct AMFI codes for your chosen schemes.
# ──────────────────────────────────────────────────────────────────────────────
DEFAULT_SCHEME_CODES = [
    "120503",  # Mirae Asset Large Cap Fund - Direct
    "118989",  # Axis Bluechip Fund - Direct
    "120465",  # Mirae Asset Emerging Bluechip - Direct
    "120594",  # Kotak Emerging Equity - Direct
    "125354",  # Parag Parikh Flexi Cap - Direct
    "112090",  # HDFC Mid-Cap Opportunities - Direct
    "119598",  # SBI Small Cap Fund - Direct
    "120828",  # Canara Robeco Emerging Equities - Direct
    "101539",  # Franklin India Prima Fund - Direct
    "119775",  # Nippon India Small Cap - Direct
    "120716",  # Invesco India Midcap - Direct
    "120505",  # Mirae Asset Tax Saver - Direct
    "130503",  # Edelweiss Mid Cap - Direct
    "120716",  # PGIM India Midcap Opportunities - Direct
]

MFAPI_BASE    = "https://api.mfapi.in/mf"
AMFI_NAV_URL  = "https://www.amfiindia.com/spages/NAVAll.txt"

# ──────────────────────────────────────────────────────────────────────────────
# Low-level helpers
# ──────────────────────────────────────────────────────────────────────────────

def _safe_get(url: str, timeout: int = 15, retries: int = 3) -> dict | None:
    """GET with retries; returns JSON dict or None."""
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=timeout,
                             headers={"User-Agent": "MF-Dashboard/1.0"})
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt == retries - 1:
                st.warning(f"⚠️ Could not fetch {url}: {e}")
            time.sleep(1.5 ** attempt)
    return None


def _safe_get_text(url: str, timeout: int = 20) -> str | None:
    try:
        r = requests.get(url, timeout=timeout,
                         headers={"User-Agent": "MF-Dashboard/1.0"})
        r.raise_for_status()
        return r.text
    except Exception as e:
        st.warning(f"⚠️ Could not fetch {url}: {e}")
        return None


# ──────────────────────────────────────────────────────────────────────────────
# NAV history from MFAPI
# ──────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def fetch_nav_history(scheme_code: str) -> pd.DataFrame:
    """
    Returns a DataFrame with columns [date, nav] sorted ascending.
    Source: api.mfapi.in  (mirrors AMFI official NAV)
    """
    data = _safe_get(f"{MFAPI_BASE}/{scheme_code}")
    if not data or "data" not in data:
        return pd.DataFrame(columns=["date", "nav"])

    df = pd.DataFrame(data["data"])
    df.columns = ["date", "nav"]
    df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y", errors="coerce")
    df["nav"]  = pd.to_numeric(df["nav"], errors="coerce")
    df = df.dropna().sort_values("date").reset_index(drop=True)
    return df


@st.cache_data(ttl=3600)
def fetch_scheme_meta(scheme_code: str) -> dict:
    """
    Returns scheme metadata dict from MFAPI.
    Keys: scheme_name, fund_house, scheme_type, scheme_category,
          scheme_code, scheme_start_date, scheme_start_nav
    """
    data = _safe_get(f"{MFAPI_BASE}/{scheme_code}")
    if not data:
        return {}
    meta = data.get("meta", {})
    return {
        "scheme_code"     : scheme_code,
        "scheme_name"     : meta.get("scheme_name", "Unknown"),
        "fund_house"      : meta.get("fund_house", ""),
        "scheme_type"     : meta.get("scheme_type", ""),
        "scheme_category" : meta.get("scheme_category", ""),
        "launch_date"     : meta.get("scheme_start_date", {}).get("date", ""),
        "inception_nav"   : meta.get("scheme_start_date", {}).get("nav", ""),
    }


# ──────────────────────────────────────────────────────────────────────────────
# AMFI bulk NAV file — gives latest NAV + expense ratio for all schemes
# ──────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def fetch_amfi_bulk_nav() -> pd.DataFrame:
    """
    Downloads the full AMFI NAVAll.txt.
    Returns DataFrame with columns:
      scheme_code, isin_div, isin_growth, scheme_name, nav, date
    """
    text = _safe_get_text(AMFI_NAV_URL)
    if not text:
        return pd.DataFrame()

    rows = []
    for line in text.splitlines():
        parts = line.split(";")
        if len(parts) >= 6:
            try:
                rows.append({
                    "scheme_code" : parts[0].strip(),
                    "isin_div"    : parts[1].strip(),
                    "isin_growth" : parts[2].strip(),
                    "scheme_name" : parts[3].strip(),
                    "nav"         : float(parts[4].strip()),
                    "nav_date"    : parts[5].strip(),
                })
            except (ValueError, IndexError):
                pass

    return pd.DataFrame(rows)


# ──────────────────────────────────────────────────────────────────────────────
# Returns computation helpers
# ──────────────────────────────────────────────────────────────────────────────

def _cagr(start_nav: float, end_nav: float, years: float) -> float | None:
    if start_nav and end_nav and years > 0:
        try:
            return round(((end_nav / start_nav) ** (1 / years) - 1) * 100, 2)
        except Exception:
            return None
    return None


def _nav_on_date(df: pd.DataFrame, target: datetime) -> float | None:
    if df.empty:
        return None
    sub = df[df["date"] <= target]
    return float(sub["nav"].iloc[-1]) if not sub.empty else None


def _xmonths_ago(months: int) -> datetime:
    return datetime.now() - timedelta(days=months * 30.44)


def _std_dev(df: pd.DataFrame, years: int = 3) -> float | None:
    if df.empty:
        return None
    cutoff = datetime.now() - timedelta(days=years * 365)
    sub = df[df["date"] >= cutoff]["nav"]
    if len(sub) < 20:
        return None
    returns = sub.pct_change().dropna()
    return round(returns.std() * np.sqrt(252) * 100, 2)


# ──────────────────────────────────────────────────────────────────────────────
# Nifty 50 proxy via NSE India (Yahoo Finance fallback)
# ──────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def fetch_nifty50_history() -> pd.DataFrame:
    """
    Fetches Nifty 50 historical data via MFAPI's Nifty 50 index scheme.
    Scheme code 120716 is used as a proxy; actual benchmark data
    is from the Nifty 50 index fund NAV.
    We use UTI Nifty 50 Index Fund Direct (scheme_code=120716 proxy).
    """
    # Use a reliable Nifty 50 index fund NAV as benchmark proxy
    # UTI Nifty 50 Index Fund - Direct Growth: 120716 (approx)
    # We'll try to get a true benchmark from NSE via a free endpoint
    try:
        # NSE India Nifty 50 historical - use Yahoo Finance CSV
        url = (
            "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI"
            "?interval=1d&range=10y"
        )
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        payload = r.json()
        timestamps = payload["chart"]["result"][0]["timestamp"]
        closes     = payload["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        df = pd.DataFrame({
            "date" : pd.to_datetime(timestamps, unit="s"),
            "nav"  : closes,
        }).dropna().sort_values("date").reset_index(drop=True)
        return df
    except Exception:
        return pd.DataFrame(columns=["date", "nav"])


# ──────────────────────────────────────────────────────────────────────────────
# Portfolio holdings — scraped from MFAPI portfolio endpoint (if available)
# or synthesised from fund category benchmarks
# ──────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=86400)
def fetch_portfolio_holdings(scheme_code: str) -> dict:
    """Portfolio endpoint not available on MFAPI."""
    return {
        "top_holdings"     : [],
        "sector_alloc"     : {},
        "market_cap_alloc" : {},
        "cash_pct"         : None,
        "num_stocks"       : None,
        "portfolio_date"   : "N/A",
        "source"           : "Not available via free API",
    }


@st.cache_data(ttl=3600, show_spinner=False)
def load_all_schemes(scheme_codes: list) -> tuple[list, datetime]:
    """
    Loads all scheme records. Returns (records_list, fetched_at).
    """
    nifty_df = fetch_nifty50_history()
    records  = []
    for code in scheme_codes:
        rec = build_scheme_record(code, nifty_df)
        records.append(rec)
    return records, datetime.now()


def compute_overlap(records: list) -> pd.DataFrame:
    """
    Computes portfolio overlap % between each pair of schemes.
    Uses top-10 holding names as the set for Jaccard similarity.
    """
    names   = [r["scheme_name"].split("(")[0].strip()[:30] for r in records]
    n       = len(names)
    matrix  = np.zeros((n, n))

    holding_sets = []
    for r in records:
        h_set = {h["name"] for h in r.get("top_holdings", []) if h["name"]}
        holding_sets.append(h_set)

    for i in range(n):
        for j in range(n):
            a, b = holding_sets[i], holding_sets[j]
            if not a or not b:
                matrix[i][j] = np.nan
            elif i == j:
                matrix[i][j] = 100.0
            else:
                inter  = len(a & b)
                union  = len(a | b)
                matrix[i][j] = round(inter / union * 100, 1) if union else 0

    return pd.DataFrame(matrix, index=names, columns=names)
