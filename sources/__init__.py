from .fred import get_fred_data
from .bls import get_bls_data
from .coingecko import get_crypto_data
from .imf import get_imf_data
from .oecd import get_oecd_data       
from .ecb import get_ecb_data
from .generic import get_generic_json

STRATEGY_MAP = {
    "fred": get_fred_data,
    "bls": get_bls_data,
    "coingecko": get_crypto_data,
    "imf": get_imf_data,
    "oecd": get_oecd_data,           
    "ecb": get_ecb_data, 
    "generic": get_generic_json
}

def fetch_data(source_type, dataset_id, api_key=None):
    strategy = STRATEGY_MAP.get(source_type)
    if not strategy:
        if "http" in str(dataset_id):
             return get_generic_json(dataset_id)
        return None, None, f"No connector found for type: {source_type}"
    
    return strategy(dataset_id, api_key=api_key)