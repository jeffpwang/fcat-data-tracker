DATA_CATALOG = {
    "FRED": {
        "type": "fred",
        "datasets": {
            "US GDP": "GDP",
            "Tech Output": "IPB51222S",
            "Cloud Costs": "PCU518210518210",
            "Bitcoin": "CBBTCUSD"
        }
    },
    "BLS": {
        "type": "bls",
        "datasets": {
            "US CPI (Inflation)": "CUSR0000SA0",
            "US Unemployment": "LNS14000000"
        }
    },
    "CoinGecko": {
        "type": "coingecko",
        "datasets": {
            "Bitcoin History": "bitcoin",
            "Ethereum History": "ethereum"
        }
    },
    "IMF": {
        "type": "imf",
        "datasets": {
            "Paste API Link": "" 
        }
    },
    "OECD": {
        "type": "oecd",
        "datasets": {
            # 1. SCIENTIFIC COLLABORATION (Network Data)
            # Optimized: Fetches "all" countries but ONLY for 2021 to keep it fast (~1MB).
            # This fills your "Network" criteria perfectly.
            "Scientific Collaboration (2021)": "https://sdmx.oecd.org/public/rest/data/OECD.STI.STP,DSD_BIBLIO@DF_BIBLIO_COLLAB,1.1/all?startPeriod=2021&endPeriod=2021&dimensionAtObservation=AllDimensions",
            
            # 2. USA GDP (Time Series Data)
            # Optimized: Fetches only "USA" and "B1GQ" (GDP) to prevent app freeze.
            # Replaces the broken "Quarterly National Accounts" link.
            "USA GDP (Quarterly)": "https://sdmx.oecd.org/public/rest/data/OECD.SDD.NAD,DSD_NAMAIN1@DF_QNA,1.1/Q.USA.B1GQ...?startPeriod=2015-Q1&dimensionAtObservation=AllDimensions",
            
            # 3. GLOBAL TRUST (Geospatial Data)
            # Good for your "Map" criteria. 
            "Trust in Government (Map)": "https://sdmx.oecd.org/public/rest/data/OECD.GOV.GG,DSD_GOV_TRUST@DF_TRUST_INST,1.0/.......?startPeriod=2020&dimensionAtObservation=AllDimensions"
        }
    },
    "ECB": {
        "type": "ecb",
        "datasets": {
            "Eurozone Inflation (HICP)": "ICP.M.U2.N.000000.4.ANR",
            "USD/EUR Exchange Rate": "EXR.D.USD.EUR.SP00.A"
        }
    },
}