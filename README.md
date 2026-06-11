# 📊 Mutual Fund Intelligence Dashboard

A professional, live, one-page Streamlit dashboard for monitoring 14 Indian mutual fund schemes with real-time data from authentic SEBI/AMFI-authorised sources.

---

## 🏗️ Folder Structure

```
mf_dashboard/
├── app.py                        # Main Streamlit dashboard
├── requirements.txt              # Python dependencies
├── README.md
├── .streamlit/
│   └── config.toml              # Dark theme + server config
└── modules/
    ├── __init__.py
    ├── data_ingestion.py         # Fetches NAV, meta, portfolio from MFAPI + AMFI
    └── data_cleaning.py          # Type coercion, formatting, KPI computation
```

---

## 📡 Data Sources (Authentic & Free)

| Source | What it provides | Update frequency |
|--------|-----------------|-----------------|
| **MFAPI** (`api.mfapi.in`) | Complete NAV history for every AMFI-registered scheme | Daily (post-market) |
| **AMFI India** (`amfiindia.com/spages/NAVAll.txt`) | Official daily NAV for all schemes | Daily |
| **MFAPI Portfolio** (`api.mfapi.in/mf/{code}/portfolio`) | Top holdings, sector, market-cap allocation | Monthly (AMFI disclosure) |
| **Yahoo Finance** (Nifty 50 — `^NSEI`) | Nifty 50 benchmark prices | Daily |

> **Why these?** MFAPI mirrors AMFI's official NAV submissions — it is the most reliable free API for Indian MF NAV history. AMFI India is the SEBI-mandated disclosure authority. Portfolio data is published monthly by fund houses per SEBI circular.

---

## ⚙️ Setup & Installation

### Prerequisites
- Python 3.10 or higher
- pip

### Step 1 — Clone / download the folder

```bash
cd mf_dashboard
```

### Step 2 — Create virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate       # Mac/Linux
venv\Scripts\activate          # Windows
```

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4 — Configure your 14 schemes

Edit the `DEFAULT_SCHEME_CODES` list in `modules/data_ingestion.py`:

```python
DEFAULT_SCHEME_CODES = [
    "120503",   # Mirae Asset Large Cap Fund - Direct
    "118989",   # Axis Bluechip Fund - Direct
    # ... add your 14 AMFI scheme codes
]
```

**How to find AMFI scheme codes:**
1. Visit https://api.mfapi.in/mf  → lists all schemes
2. Search by fund name at https://www.mfapi.in/
3. The numeric code in the URL is the AMFI scheme code

### Step 5 — Run the dashboard

```bash
streamlit run app.py
```

Open your browser at **http://localhost:8501**

---

## 🚀 Deployment

### Option A — Streamlit Community Cloud (Free)

1. Push this folder to a GitHub repository
2. Go to https://share.streamlit.io
3. Connect your GitHub repo → select `app.py`
4. Deploy — auto-restarts on code changes

### Option B — Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

```bash
docker build -t mf-dashboard .
docker run -p 8501:8501 mf-dashboard
```

### Option C — AWS / GCP / Azure VM

```bash
# Install requirements
pip install -r requirements.txt

# Run in background with nohup
nohup streamlit run app.py --server.port 8501 --server.headless true &

# Or use screen
screen -S mf-dashboard
streamlit run app.py
# Ctrl+A then D to detach
```

### Option D — Render.com (Free tier)

1. Push to GitHub
2. Create a new **Web Service** on render.com
3. Build command: `pip install -r requirements.txt`
4. Start command: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`

---

## 🔄 Live Refresh Logic

- **Streamlit `st.cache_data(ttl=3600)`** caches all API calls for 1 hour
- **Auto-refresh** is set via an HTML meta-refresh tag — configurable in the sidebar (15 min / 30 min / 1 hour / 6 hours)
- **Force Refresh** button in sidebar clears all caches and reloads immediately
- Portfolio data is cached for **24 hours** (monthly AMFI cadence)

---

## 📋 Dashboard Sections

| Section | Description |
|---------|-------------|
| **A — Summary KPIs** | Total schemes, avg 1Y/3Y/5Y returns, avg alpha vs Nifty 50 |
| **B — Scheme Table** | All 14 schemes with all return metrics, sortable |
| **C — Portfolio** | Sector, market cap, holdings chart per scheme |
| **E — Stock Movements** | Highest/smallest holdings, 1Y NAV trend |
| **F — Overlap** | Jaccard overlap heatmap for all 14×14 pairs |
| **G — Benchmark** | 1Y/3Y/5Y vs Nifty 50, alpha bars, alpha table |
| **H — Risk** | Risk-return scatter, volatility ranking, risk label |
| **I — Charts** | CAGR comparison, multi-scheme NAV trend, category pie |

---

## ⚠️ Notes & Limitations

- **AUM and expense ratio** are not published in AMFI's free NAV file. For these, consider subscribing to a data provider like **Morningstar India**, **Value Research**, or the **NSE MF Analytics** portal.
- **Fund flows (inflows/outflows)** are published by AMFI monthly. For live data, AMFI's monthly publication at `amfiindia.com/research-information/aum-data` can be scraped and integrated.
- **Beta** requires benchmark price series aligned to NAV dates — this can be added using the Nifty 50 series already fetched.
- **Category rank** requires cross-scheme percentile ranking within each category — calculated internally once all schemes are loaded.
- **Portfolio holdings** are published monthly; MFAPI serves the latest available disclosure.

---

## 📞 Support

For AMFI scheme code lookup: https://www.amfiindia.com/nav-history  
For MFAPI documentation: https://www.mfapi.in/
