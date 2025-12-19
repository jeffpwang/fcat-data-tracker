import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import urllib3
from datetime import datetime
from typing import Optional, Tuple, Dict, Any

# --- CONFIGURATION ---
# Disable SSL warnings for the "Nuclear" IMF fix
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
    "BLS": {
        "datasets": {
            "US CPI (Inflation)": "CUSR0000SA0",
            "US Unemployment Rate": "LNS14000000",
            "Labor Force Participation": "LNS11300000"
        },
        "type": "bls"
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
    },
    "ECB": {
        "datasets": {
            "Eurozone Inflation (HICP)": "ICP.M.U2.N.000000.4.ANR",
            "USD/EUR Exchange Rate": "EXR.D.USD.EUR.SP00.A"
        },
        "type": "ecb"
    }
}

# --- DATA FETCHING LOGIC ---

def fetch_fred(dataset_id: str, api_key: Optional[str]) -> Tuple[Optional[pd.DataFrame], Optional[Dict], Optional[str]]:
    if not api_key:
        return None, None, "API Key Required"
    
    url = f"https://api.stlouisfed.org/fred/series/observations?series_id={dataset_id}&api_key={api_key}&file_type=json"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            df = pd.DataFrame(r.json()['observations'])
            df['date'] = pd.to_datetime(df['date'])
            df['value'] = pd.to_numeric(df['value'], errors='coerce')
            return df.dropna(), r.json(), None
        return None, None, f"Status {r.status_code}"
    except Exception as e:
        return None, None, str(e)

def fetch_bls(dataset_id: str, api_key: Optional[str]) -> Tuple[Optional[pd.DataFrame], Optional[Dict], Optional[str]]:
    """
    Fetches data from US Bureau of Labor Statistics (BLS) Public Data API V2.
    """
    url = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
    
    # BLS allows 20 years max per call. We'll fetch the last 19 years to be safe.
    current_year = datetime.now().year
    start_year = str(current_year - 19)
    end_year = str(current_year)
    
    headers = {'Content-type': 'application/json'}
    
    # Construct Payload
    payload = {
        "seriesid": [dataset_id],
        "startyear": start_year,
        "endyear": end_year
    }
    
    # Add API Key if provided (increases limit from 25 to 500 calls/day)
    if api_key:
        payload["registrationkey"] = api_key

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if r.status_code == 200:
            raw_json = r.json()
            
            # Check for API-level errors (BLS returns 200 even if request fails logically)
            if raw_json['status'] != 'REQUEST_SUCCEEDED':
                 return None, raw_json, f"BLS Error: {raw_json.get('message', 'Unknown Error')}"
            
            # Parsing Logic
            try:
                series_data = raw_json['Results']['series'][0]['data']
                df = pd.DataFrame(series_data)
                
                # Create Date Column from 'year' and 'period' (e.g., 2023 M01)
                # Filter out non-monthly periods like "M13" (Annual Average)
                df = df[df['period'].str.contains("M")]
                df['date_str'] = df['year'] + "-" + df['period'].str.replace("M", "") + "-01"
                df['date'] = pd.to_datetime(df['date_str'])
                
                df['value'] = pd.to_numeric(df['value'], errors='coerce')
                
                # Sort chronologically
                df = df.sort_values('date')
                
                return df[['date', 'value']], raw_json, None
            except (KeyError, IndexError):
                return None, raw_json, "No data found for this Series ID."
                
        return None, None, f"Status {r.status_code}"
    except Exception as e:
        return None, None, str(e)

def fetch_coingecko(dataset_id: str, **kwargs) -> Tuple[Optional[pd.DataFrame], Optional[Dict], Optional[str]]:
    url = f"https://api.coingecko.com/api/v3/coins/{dataset_id}/market_chart?vs_currency=usd&days=30"
    try:
        r = requests.get(url, headers={'User-Agent': 'FCAT_Validator'}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            df = pd.DataFrame(data['prices'], columns=['timestamp', 'value'])
            df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df, data, None
        return None, None, f"Status {r.status_code}"
    except Exception as e:
        return None, None, str(e)

def fetch_imf(dataset_id: str, **kwargs) -> Tuple[Optional[pd.DataFrame], Optional[Dict], Optional[str]]:
    st.markdown(f"`Requesting: {dataset_id}`")
    try:
        # SSL Bypass + Long Timeout
        r = requests.get(dataset_id, headers={'User-Agent': 'Mozilla/5.0'}, verify=False, timeout=45)
        if r.status_code == 200:
            raw_json = r.json()
            try:
                indicator = "NGDP_RPCH"
                if indicator in raw_json.get('values', {}):
                    usa_data = raw_json['values'][indicator].get('USA', {})
                    df = pd.DataFrame(list(usa_data.items()), columns=['date', 'value'])
                    df['date'] = pd.to_datetime(df['date'], format='%Y')
                    df['value'] = pd.to_numeric(df['value'])
                    return df, raw_json, None
                return None, raw_json, "Data structure mismatch (Parsing failed)"
            except Exception as parse_error:
                return None, raw_json, f"Parsing Error: {parse_error}"
        return None, None, f"Status {r.status_code}"
    except Exception as e:
        return None, None, str(e)

def fetch_oecd(dataset_id: str, **kwargs) -> Tuple[Optional[pd.DataFrame], Optional[Dict], Optional[str]]:
    st.markdown(f"`Requesting: {dataset_id}`")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        r = requests.get(dataset_id, headers=headers, verify=False, timeout=15)
        if r.status_code == 200:
            return None, r.json(), "SDMX-JSON received. Parsing disabled in Strict Mode."
        elif r.status_code == 403:
            return None, None, "Access Denied (403). Server blocked the script."
        return None, None, f"Status {r.status_code}"
    except Exception as e:
        return None, None, str(e)

def fetch_ecb(dataset_id: str, **kwargs) -> Tuple[Optional[pd.DataFrame], Optional[Dict], Optional[str]]:
    """
    Fetches data from ECB Data Portal using SDMX-JSON.
    Base URL: https://data-api.ecb.europa.eu/service/data/
    """
    # Fix URL structure if user provided raw series key
    if "." in dataset_id and "/" not in dataset_id:
        flow_ref, key = dataset_id.split(".", 1)
        resource_path = f"{flow_ref}/{key}"
    else:
        resource_path = dataset_id

    url = f"https://data-api.ecb.europa.eu/service/data/{resource_path}"
    st.markdown(f"`Requesting: {url}`")
    
    # Use generic JSON header to avoid 406 errors
    headers = {
        "Accept": "application/json",
        "User-Agent": "FCAT_Validator"
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            raw_json = r.json()
            try:
                if 'dataSets' not in raw_json or not raw_json['dataSets']:
                    return None, raw_json, "Empty dataSets in response"
                
                dataset = raw_json['dataSets'][0]
                if 'series' in dataset:
                    series_dict = dataset['series']
                    key = list(series_dict.keys())[0]
                    observations = series_dict[key]['observations']
                else:
                    return None, raw_json, "Could not locate 'series' in SDMX response"

                time_dim = raw_json['structure']['dimensions']['observation'][0]['values']
                
                data_list = []
                for time_idx, obs_data in observations.items():
                    date_str = time_dim[int(time_idx)]['name']
                    val = obs_data[0]
                    data_list.append({'date': date_str, 'value': val})
                
                df = pd.DataFrame(data_list)
                df['date'] = pd.to_datetime(df['date'], errors='coerce') 
                df['value'] = pd.to_numeric(df['value'])
                return df.dropna(), raw_json, None
                
            except Exception as parse_e:
                return None, raw_json, f"SDMX Parsing Failed: {parse_e}"
        elif r.status_code == 406:
             return None, None, "406 Error: Server rejected headers."
        else:
            return None, None, f"Status {r.status_code}"
    except Exception as e:
        return None, None, str(e)

# Dispatcher for fetching strategies
FETCH_STRATEGIES = {
    "fred": fetch_fred,
    "bls": fetch_bls,
    "coingecko": fetch_coingecko,
    "imf": fetch_imf,
    "oecd_strict": fetch_oecd,
    "ecb": fetch_ecb
}

# --- UI COMPONENT FUNCTIONS ---

def render_completeness_test(df: pd.DataFrame):
    st.divider()
    st.subheader("2. Completeness Test (Dimensionality)")
    
    c1, c2, c3 = st.columns(3)
    
    has_time = 'date' in df.columns or 'timestamp' in df.columns
    c1.metric("⏱️ Temporal", "Found" if has_time else "Missing", border=True)
    
    geo_cols = {'lat', 'long', 'latitude', 'country', 'geo_code'}
    has_geo = bool(geo_cols.intersection(df.columns))
    if has_geo: c2.success("🌍 **Geospatial: FOUND**") 
    else: c2.metric("🌍 Geospatial", "Missing", border=True)
    
    net_cols = {'from', 'to', 'source', 'target'}
    has_net = bool(net_cols.intersection(df.columns))
    if has_net: c3.success("🕸️ **Network: FOUND**")
    else: c3.metric("🕸️ Network", "Missing", border=True)
    
    st.info(f"📝 **Verdict:** Validated schema: {list(df.columns)}")

def render_visual_potential(df: pd.DataFrame, label: str):
    st.divider()
    st.subheader("3. Visual Potential")
    
    m1, m2 = st.columns(2)
    m1.metric("Rows Returned", len(df))
    latest_date = df['date'].max().date() if 'date' in df.columns else "N/A"
    m2.metric("Latest Date", str(latest_date))
    
    try:
        fig = px.line(df, x='date', y='value', title=f"Actual Data: {label}")
        st.plotly_chart(fig, use_container_width=True)
    except Exception:
        st.warning("Chart generation failed - invalid data format.")
        st.dataframe(df.head())

# --- MAIN APP ---

def main():
    st.set_page_config(page_title="FCAT Data Validator", layout="wide")
    st.title("Data Viability Tracker")
    st.divider()

    # Sidebar
    with st.sidebar:
        st.header("Configuration")
        selected_source = st.selectbox("Source:", list(DATA_CATALOG.keys()))
        source_config = DATA_CATALOG[selected_source]
        
        available_datasets = list(source_config["datasets"].keys())
        selected_label = st.selectbox("Dataset:", available_datasets)
        dataset_id = source_config["datasets"][selected_label]
        
        st.divider()
        
        api_key = None
        # Handle API Keys for different sources
        if source_config["type"] == "fred":
            if "FRED_API_KEY" in st.secrets:
                api_key = st.secrets["FRED_API_KEY"]
                st.success("🔑 FRED Key Loaded")
            else:
                api_key = st.text_input("FRED API Key", type="password")
        
        elif source_config["type"] == "bls":
            if "BLS_API_KEY" in st.secrets:
                api_key = st.secrets["BLS_API_KEY"]
                st.success("🔑 BLS Key Loaded")
            else:
                api_key = st.text_input("BLS API Key (Optional)", type="password", help="Leave empty for limited access (25 calls/day).")

        run_test = st.button("Run Validation", type="primary")

    # Core Execution
    if run_test:
        st.subheader(f"Validating: {selected_label}")
        
        strategy = FETCH_STRATEGIES.get(source_config["type"])
        
        if strategy:
            df, raw_json, error = strategy(dataset_id, api_key=api_key)
            
            if error and not raw_json:
                st.error(f"❌ FAIL: {error}")
            elif error and raw_json:
                st.success("✅ Connection Successful")
                st.warning(f"⚠️ {error}")
            else:
                st.success("✅ Connection Successful")

            # Render Results
            if df is not None and not df.empty:
                render_completeness_test(df)
                render_visual_potential(df, selected_label)
            elif raw_json:
                st.divider()
                st.subheader("Raw Response Inspector")
                st.json(raw_json)
        else:
            st.error("❌ Configuration Error: Unknown source type.")

if __name__ == "__main__":
    main()