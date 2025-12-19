import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import urllib3

# Disable SSL warnings for the "Nuclear" IMF fix
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- PAGE CONFIG ---
st.set_page_config(page_title="FCAT Data Validator (Strict)", layout="wide")

st.title("Data Viability Tracker")
st.markdown("**Status:** Strict Mode (No Simulations). Validating real API endpoints.")

st.divider()

# ==========================================
# 1. THE DATA CATALOG
# ==========================================
DATA_CATALOG = {
    "FRED": {
        "datasets": {
            "US GDP": "GDP",
            "Tech Output": "IPB51222S",
            "Cloud Costs": "PCU518210518210",
            "Bitcoin": "CBBTCUSD"
        },
        "type": "fred"
    },
    "CoinGecko": {
        "datasets": {
            "Bitcoin History": "bitcoin"
        },
        "type": "coingecko"
    },
    "IMF": {
        "datasets": {
            "Real GDP Growth (Global)": "https://www.imf.org/external/datamapper/api/v1/NGDP_RPCH"
        },
        "type": "imf"
    },
    "OECD": {
        "datasets": {
            "Quarterly National Accounts (US GDP)": "https://stats.oecd.org/SDMX-JSON/data/QNA/USA.B1_GE.CQR.A/all?startTime=2022-Q1"
        },
        "type": "oecd_strict"
    }
}

# --- SIDEBAR ---
with st.sidebar:
    st.header("Configuration")
    
    selected_source = st.selectbox("Source:", list(DATA_CATALOG.keys()))
    source_config = DATA_CATALOG[selected_source]
    
    available_datasets = list(source_config["datasets"].keys())
    selected_label = st.selectbox("Dataset:", available_datasets)
    dataset_id = source_config["datasets"][selected_label]
    
    st.divider()
    
    api_key = None
    if source_config["type"] == "fred":
        if "FRED_API_KEY" in st.secrets:
            api_key = st.secrets["FRED_API_KEY"]
            st.success("🔑 Key Loaded")
        else:
            api_key = st.text_input("FRED API Key", type="password")

    run_test = st.button("Run Validation", type="primary")

# --- CORE LOGIC ---
if run_test:
    st.subheader(f"Validating: {selected_label}")
    
    df = None
    raw_json = None
    
    try:
        # ==========================================
        # PATH A: FRED
        # ==========================================
        if source_config["type"] == "fred":
            if not api_key:
                st.error("❌ FAIL: API Key Required")
                st.stop()
            url = f"https://api.stlouisfed.org/fred/series/observations?series_id={dataset_id}&api_key={api_key}&file_type=json"
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                st.success("✅ Connection Successful")
                df = pd.DataFrame(r.json()['observations'])
                df['date'] = pd.to_datetime(df['date'])
                df['value'] = pd.to_numeric(df['value'], errors='coerce')
                df = df.dropna()
            else:
                st.error(f"❌ FAIL: Status {r.status_code}")

        # ==========================================
        # PATH B: COINGECKO
        # ==========================================
        elif source_config["type"] == "coingecko":
            url = f"https://api.coingecko.com/api/v3/coins/{dataset_id}/market_chart?vs_currency=usd&days=30"
            r = requests.get(url, headers={'User-Agent': 'FCAT_Validator'}, timeout=10)
            if r.status_code == 200:
                st.success("✅ Connection Successful")
                data = r.json()
                df = pd.DataFrame(data['prices'], columns=['timestamp', 'value'])
                df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
            else:
                st.error(f"❌ FAIL: Status {r.status_code}")

        # ==========================================
        # PATH C: IMF (NUCLEAR FIX)
        # ==========================================
        elif source_config["type"] == "imf":
            url = dataset_id
            st.markdown(f"`Requesting: {url}`")
            # SSL Bypass + Long Timeout
            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, verify=False, timeout=45)
            
            if r.status_code == 200:
                st.success("✅ Connection Successful")
                raw_json = r.json()
                # Parse
                try:
                    indicator = "NGDP_RPCH" 
                    if indicator in raw_json['values']:
                        usa_data = raw_json['values'][indicator].get('USA', {})
                        df = pd.DataFrame(list(usa_data.items()), columns=['date', 'value'])
                        df['date'] = pd.to_datetime(df['date'], format='%Y')
                        df['value'] = pd.to_numeric(df['value'])
                except Exception as e:
                    st.warning("Parsing failed (Data structure mismatch).")
            else:
                st.error(f"❌ FAIL: Status {r.status_code}")

        # ==========================================
        # PATH D: OECD (STRICT)
        # ==========================================
        else:
            url = dataset_id
            st.markdown(f"`Requesting: {url}`")
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            r = requests.get(url, headers=headers, verify=False, timeout=15)
            
            if r.status_code == 200:
                st.success("✅ Connection Successful")
                raw_json = r.json()
                st.warning("⚠️ SDMX-JSON received. Parsing disabled in Strict Mode.")
            elif r.status_code == 403:
                st.error("❌ FAIL: Access Denied (403). Server blocked the script.")
            else:
                st.error(f"❌ FAIL: Status {r.status_code}")

    except Exception as e:
        st.error(f"❌ System Error: {e}")

    # ==========================================
    # 2. RESTORED COMPLETENESS TEST
    # ==========================================
    if df is not None and not df.empty:
        st.divider()
        st.subheader("2. Completeness Test (Dimensionality)")
        
        c1, c2, c3 = st.columns(3)
        
        # A. Temporal
        has_time = 'date' in df.columns or 'timestamp' in df.columns
        c1.metric("⏱️ Temporal", "Found" if has_time else "Missing", border=True)
        
        # B. Geospatial
        geo_cols = ['lat', 'long', 'latitude', 'country', 'geo_code']
        has_geo = any(col in df.columns for col in geo_cols)
        if has_geo: c2.success("🌍 **Geospatial: FOUND**") 
        else: c2.metric("🌍 Geospatial", "Missing", border=True)
        
        # C. Network
        net_cols = ['from', 'to', 'source', 'target']
        has_net = any(col in df.columns for col in net_cols)
        if has_net: c3.success("🕸️ **Network: FOUND**")
        else: c3.metric("🕸️ Network", "Missing", border=True)
        
        # VERDICT
        st.info(f"📝 **Verdict:** Validated schema: {list(df.columns)}")

        # ==========================================
        # 3. VISUAL POTENTIAL
        # ==========================================
        st.divider()
        st.subheader("3. Visual Potential")
        
        # Metrics
        m1, m2 = st.columns(2)
        m1.metric("Rows Returned", len(df))
        m2.metric("Latest Date", str(df['date'].max().date()) if 'date' in df.columns else "N/A")
        
        # Chart
        try:
            fig = px.line(df, x='date', y='value', title=f"Actual Data: {selected_label}")
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.warning("Chart generation failed.")
            st.dataframe(df.head())

    # ==========================================
    # RAW INSPECTOR
    # ==========================================
    elif raw_json is not None:
        st.divider()
        st.subheader("Raw Response Inspector")
        st.json(raw_json)