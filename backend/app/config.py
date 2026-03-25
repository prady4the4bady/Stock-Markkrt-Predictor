"""
Market Oracle Backend Configuration
All settings for the prediction engine - Optimized for Speed & Accuracy
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file (works locally; on cloud hosts, env vars are set directly)
load_dotenv(Path(__file__).parent.parent / ".env")

# Base directories
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Database
DATABASE_URL = f"sqlite+aiosqlite:///{DATA_DIR}/cache.db"
CACHE_EXPIRY_HOURS = int(os.getenv('CACHE_EXPIRY_HOURS', 1))  # Default: refresh data every 1 hour (overridden for daily data)
# Daily cache TTL for non-intraday data (hours)
DAILY_CACHE_HOURS = int(os.getenv('DAILY_CACHE_HOURS', 24))

# API Settings
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))
_cors_env = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
CORS_ORIGINS = [o.strip() for o in _cors_env.split(",") if o.strip()]

# Model Cache Settings - Extended for reduced latency
MODEL_CACHE_HOURS = 6  # Cache trained models for 6 hours
PREDICTION_CACHE_SECONDS = 30  # Cache predictions for 30 seconds for fast refresh

# Model Settings - Optimized for speed and accuracy balance
LSTM_SEQUENCE_LENGTH = 30  # Optimal sequence for speed
LSTM_EPOCHS = 20  # Reduced for faster training, early stopping handles it
LSTM_BATCH_SIZE = 64  # Larger batch for faster training

XGBOOST_N_ESTIMATORS = 60  # Reduced for faster training
XGBOOST_MAX_DEPTH = 5  # Balanced depth for speed/accuracy

# Ensemble Weights (optimized based on backtesting)
DEFAULT_WEIGHTS = {
    "lstm": 0.30,      # LSTM for pattern recognition
    "prophet": 0.20,   # Prophet for seasonal trends
    "xgboost": 0.35,   # XGBoost is fast and accurate
    "arima": 0.15      # ARIMA for time series baseline
}

# =============================================================================
# EXCHANGE-SPECIFIC MODEL PARAMETERS
# Different markets have different behaviors - optimize models accordingly
# =============================================================================
EXCHANGE_MODEL_PARAMS = {
    "US": {  # NYSE, NASDAQ - Most efficient markets, less volatile
        "lstm_epochs": 20,
        "lstm_sequence": 30,
        "xgb_estimators": 80,
        "xgb_depth": 5,
        "weights": {"lstm": 0.30, "prophet": 0.20, "xgboost": 0.35, "arima": 0.15},
        "volatility_factor": 1.0,
        "trading_hours": "09:30-16:00 EST"
    },
    "INDIA": {  # NSE, BSE - Higher retail participation, momentum-driven
        "lstm_epochs": 25,
        "lstm_sequence": 25,
        "xgb_estimators": 80,
        "xgb_depth": 5,
        "weights": {"lstm": 0.35, "prophet": 0.15, "xgboost": 0.40, "arima": 0.10},
        "volatility_factor": 1.3,
        "trading_hours": "09:15-15:30 IST"
    },
    "CHINA": {  # SSE, SZSE - Policy-driven, high retail, T+1 settlement
        "lstm_epochs": 25,
        "lstm_sequence": 25,
        "xgb_estimators": 70,
        "xgb_depth": 6,
        "weights": {"lstm": 0.40, "prophet": 0.10, "xgboost": 0.40, "arima": 0.10},
        "volatility_factor": 1.5,
        "trading_hours": "09:30-15:00 CST"
    },
    "JAPAN": {  # TSE - Mature market, currency-sensitive
        "lstm_epochs": 20,
        "lstm_sequence": 30,
        "xgb_estimators": 80,
        "xgb_depth": 5,
        "weights": {"lstm": 0.30, "prophet": 0.25, "xgboost": 0.35, "arima": 0.10},
        "volatility_factor": 1.1,
        "trading_hours": "09:00-15:00 JST"
    },
    "HONGKONG": {  # HKEX - Gateway to China, high-beta
        "lstm_epochs": 25,
        "lstm_sequence": 25,
        "xgb_estimators": 70,
        "xgb_depth": 5,
        "weights": {"lstm": 0.35, "prophet": 0.15, "xgboost": 0.40, "arima": 0.10},
        "volatility_factor": 1.4,
        "trading_hours": "09:30-16:00 HKT"
    },
    "UK": {  # LSE - Global hub, diverse sectors
        "lstm_epochs": 20,
        "lstm_sequence": 30,
        "xgb_estimators": 80,
        "xgb_depth": 5,
        "weights": {"lstm": 0.30, "prophet": 0.20, "xgboost": 0.35, "arima": 0.15},
        "volatility_factor": 1.1,
        "trading_hours": "08:00-16:30 GMT"
    },
    "EUROPE": {  # Euronext - Multi-country, currency-mixed
        "lstm_epochs": 20,
        "lstm_sequence": 30,
        "xgb_estimators": 80,
        "xgb_depth": 5,
        "weights": {"lstm": 0.35, "prophet": 0.25, "xgboost": 0.30, "arima": 0.10},
        "volatility_factor": 1.15,
        "trading_hours": "09:00-17:30 CET"
    },
    "CANADA": {  # TSX - Resource-heavy, commodity-driven
        "lstm_epochs": 50,
        "lstm_sequence": 55,
        "xgb_estimators": 130,
        "xgb_depth": 6,
        "weights": {"lstm": 0.35, "prophet": 0.30, "xgboost": 0.25, "arima": 0.10},
        "volatility_factor": 1.2,
        "trading_hours": "09:30-16:00 EST"
    },
    "MIDDLE_EAST": {  # Tadawul, ADX, DFM, QSE - Oil-driven, less liquid
        "lstm_epochs": 55,
        "lstm_sequence": 50,
        "xgb_estimators": 110,
        "xgb_depth": 6,
        "weights": {"lstm": 0.35, "prophet": 0.30, "xgboost": 0.25, "arima": 0.10},
        "volatility_factor": 1.3,
        "trading_hours": "10:00-15:00 AST"
    },
    "KOREA": {  # KRX - Tech-heavy, high retail participation
        "lstm_epochs": 60,
        "lstm_sequence": 50,
        "xgb_estimators": 120,
        "xgb_depth": 7,
        "weights": {"lstm": 0.40, "prophet": 0.20, "xgboost": 0.30, "arima": 0.10},
        "volatility_factor": 1.4,
        "trading_hours": "09:00-15:30 KST"
    },
    "LATAM": {  # Brazil, Mexico - Commodity & Currency sensitive
        "lstm_epochs": 55,
        "lstm_sequence": 50,
        "xgb_estimators": 110,
        "xgb_depth": 6,
        "weights": {"lstm": 0.35, "prophet": 0.25, "xgboost": 0.30, "arima": 0.10},
        "volatility_factor": 1.5,
        "trading_hours": "10:00-17:00 Local"
    },
    "AFRICA": {  # JSE - Mining & commodity heavy
        "lstm_epochs": 50,
        "lstm_sequence": 55,
        "xgb_estimators": 100,
        "xgb_depth": 6,
        "weights": {"lstm": 0.35, "prophet": 0.30, "xgboost": 0.25, "arima": 0.10},
        "volatility_factor": 1.4,
        "trading_hours": "09:00-17:00 SAST"
    },
    "CRYPTO": {  # 24/7, highest volatility, sentiment-driven
        "lstm_epochs": 80,
        "lstm_sequence": 30,
        "xgb_estimators": 80,
        "xgb_depth": 10,
        "weights": {"lstm": 0.50, "prophet": 0.10, "xgboost": 0.30, "arima": 0.10},
        "volatility_factor": 3.0,
        "trading_hours": "24/7"
    },
    "FOREX": {  # 24/5, macro-driven
        "lstm_epochs": 60,
        "lstm_sequence": 50,
        "xgb_estimators": 120,
        "xgb_depth": 5,
        "weights": {"lstm": 0.30, "prophet": 0.30, "xgboost": 0.25, "arima": 0.15},
        "volatility_factor": 0.8,
        "trading_hours": "24/5"
    },
    "COMMODITIES": {  # Macro-driven, seasonal
        "lstm_epochs": 55,
        "lstm_sequence": 60,
        "xgb_estimators": 110,
        "xgb_depth": 6,
        "weights": {"lstm": 0.30, "prophet": 0.35, "xgboost": 0.25, "arima": 0.10},
        "volatility_factor": 1.5,
        "trading_hours": "Various"
    },
    "NORDICS": {  # Copenhagen, Helsinki, Stockholm, Oslo, Iceland - Stable, well-regulated
        "lstm_epochs": 25,
        "lstm_sequence": 35,
        "xgb_estimators": 90,
        "xgb_depth": 5,
        "weights": {"lstm": 0.30, "prophet": 0.25, "xgboost": 0.35, "arima": 0.10},
        "volatility_factor": 1.0,
        "trading_hours": "09:00-17:00 CET"
    },
    "EASTERN_EUROPE": {  # Prague, Warsaw, Budapest, Bucharest, Athens - Emerging, higher volatility
        "lstm_epochs": 40,
        "lstm_sequence": 40,
        "xgb_estimators": 100,
        "xgb_depth": 6,
        "weights": {"lstm": 0.35, "prophet": 0.20, "xgboost": 0.35, "arima": 0.10},
        "volatility_factor": 1.4,
        "trading_hours": "09:00-17:00 CET"
    },
    "BALTICS": {  # Tallinn, Riga, Vilnius - Small, less liquid
        "lstm_epochs": 35,
        "lstm_sequence": 30,
        "xgb_estimators": 80,
        "xgb_depth": 5,
        "weights": {"lstm": 0.30, "prophet": 0.25, "xgboost": 0.30, "arima": 0.15},
        "volatility_factor": 1.3,
        "trading_hours": "10:00-16:00 EET"
    },
    "SOUTHEAST_ASIA": {  # Vietnam, Philippines - High growth, retail-driven
        "lstm_epochs": 45,
        "lstm_sequence": 35,
        "xgb_estimators": 100,
        "xgb_depth": 6,
        "weights": {"lstm": 0.40, "prophet": 0.15, "xgboost": 0.35, "arima": 0.10},
        "volatility_factor": 1.5,
        "trading_hours": "09:00-15:00 Local"
    },
    "SOUTH_AMERICA": {  # Argentina, Chile, Colombia - Currency volatile, commodity-linked
        "lstm_epochs": 50,
        "lstm_sequence": 45,
        "xgb_estimators": 110,
        "xgb_depth": 6,
        "weights": {"lstm": 0.35, "prophet": 0.25, "xgboost": 0.30, "arima": 0.10},
        "volatility_factor": 1.8,
        "trading_hours": "10:00-17:00 Local"
    },
    "OCEANIA": {  # Australia, New Zealand - Commodity and finance heavy
        "lstm_epochs": 30,
        "lstm_sequence": 35,
        "xgb_estimators": 90,
        "xgb_depth": 5,
        "weights": {"lstm": 0.30, "prophet": 0.25, "xgboost": 0.35, "arima": 0.10},
        "volatility_factor": 1.1,
        "trading_hours": "10:00-16:00 AEST/NZST"
    },
    "SPAIN": {  # Madrid Stock Exchange - Eurozone, banking heavy
        "lstm_epochs": 25,
        "lstm_sequence": 30,
        "xgb_estimators": 85,
        "xgb_depth": 5,
        "weights": {"lstm": 0.30, "prophet": 0.25, "xgboost": 0.35, "arima": 0.10},
        "volatility_factor": 1.2,
        "trading_hours": "09:00-17:30 CET"
    },
    "TURKEY": {  # Borsa Istanbul - High inflation environment, volatile
        "lstm_epochs": 55,
        "lstm_sequence": 40,
        "xgb_estimators": 120,
        "xgb_depth": 7,
        "weights": {"lstm": 0.40, "prophet": 0.15, "xgboost": 0.35, "arima": 0.10},
        "volatility_factor": 2.0,
        "trading_hours": "10:00-18:00 TRT"
    }
}

def get_exchange_for_symbol(symbol: str) -> str:
    """Determine which exchange/market a symbol belongs to"""
    # India
    if symbol.endswith('.NS') or symbol.endswith('.BO'):
        return "INDIA"
    # China
    elif symbol.endswith('.SS') or symbol.endswith('.SZ'):
        return "CHINA"
    # Japan
    elif symbol.endswith('.T'):
        return "JAPAN"
    # Hong Kong
    elif symbol.endswith('.HK'):
        return "HONGKONG"
    # UK (London + Aquis + Cboe UK)
    elif symbol.endswith('.L') or symbol.endswith('.IL') or symbol.endswith('.AQ') or symbol.endswith('.XC'):
        return "UK"
    # Nordics (Copenhagen, Helsinki, Stockholm, Oslo, Iceland)
    elif symbol.endswith('.CO') or symbol.endswith('.HE') or symbol.endswith('.ST') or symbol.endswith('.OL') or symbol.endswith('.IC'):
        return "NORDICS"
    # Baltics (Tallinn, Riga, Vilnius)
    elif symbol.endswith('.TL') or symbol.endswith('.RG') or symbol.endswith('.VS'):
        return "BALTICS"
    # Eastern Europe (Prague, Warsaw, Budapest, Bucharest, Athens)
    elif symbol.endswith('.PR') or symbol.endswith('.WA') or symbol.endswith('.BD') or symbol.endswith('.RO') or symbol.endswith('.AT'):
        return "EASTERN_EUROPE"
    # Spain (Madrid)
    elif symbol.endswith('.MC'):
        return "SPAIN"
    # Turkey (Borsa Istanbul)
    elif symbol.endswith('.IS'):
        return "TURKEY"
    # Euronext (Amsterdam, Paris, Brussels, Lisbon, Dublin, Milan)
    elif symbol.endswith('.AS') or symbol.endswith('.PA') or symbol.endswith('.BR') or symbol.endswith('.LS') or symbol.endswith('.IR'):
        return "EUROPE"
    # Italy (Milan, EuroTLX)
    elif symbol.endswith('.MI') or symbol.endswith('.TI'):
        return "EUROPE"
    # Germany (Xetra + Regional: Berlin, Bremen, Dusseldorf, Frankfurt, Hamburg, Hanover, Munich, Stuttgart)
    elif symbol.endswith('.DE') or symbol.endswith('.BE') or symbol.endswith('.BM') or symbol.endswith('.DU') or symbol.endswith('.F') or symbol.endswith('.HM') or symbol.endswith('.HA') or symbol.endswith('.MU') or symbol.endswith('.SG'):
        return "EUROPE"
    # Switzerland
    elif symbol.endswith('.SW'):
        return "EUROPE"
    # Cboe Europe
    elif symbol.endswith('.XD') or symbol.endswith('.NX'):
        return "EUROPE"
    # Canada (TSX, TSXV, CSE, Cboe Canada)
    elif symbol.endswith('.TO') or symbol.endswith('.V') or symbol.endswith('.CN') or symbol.endswith('.NE'):
        return "CANADA"
    # Middle East (Saudi, UAE, Qatar, Kuwait)
    elif symbol.endswith('.SR') or symbol.endswith('.SAU'):
        return "MIDDLE_EAST"  # Saudi Tadawul
    elif symbol.endswith('.AE'):
        return "MIDDLE_EAST"  # UAE (ADX & DFM)
    elif symbol.endswith('.QA'):
        return "MIDDLE_EAST"  # Qatar QSE
    elif symbol.endswith('.KW'):
        return "MIDDLE_EAST"  # Kuwait
    # Israel
    elif symbol.endswith('.TA'):
        return "MIDDLE_EAST"  # Tel Aviv
    # Korea
    elif symbol.endswith('.KS') or symbol.endswith('.KQ'):
        return "KOREA"
    # Taiwan
    elif symbol.endswith('.TW') or symbol.endswith('.TWO'):
        return "ASIA"
    # Singapore
    elif symbol.endswith('.SI'):
        return "ASIA"
    # Australia (ASX + Cboe Australia)
    elif symbol.endswith('.AX') or symbol.endswith('.XA'):
        return "OCEANIA"
    # New Zealand
    elif symbol.endswith('.NZ'):
        return "OCEANIA"
    # Indonesia
    elif symbol.endswith('.JK'):
        return "ASIA"
    # Thailand
    elif symbol.endswith('.BK'):
        return "ASIA"
    # Philippines
    elif symbol.endswith('.PS'):
        return "SOUTHEAST_ASIA"
    # Vietnam
    elif symbol.endswith('.VN'):
        return "SOUTHEAST_ASIA"
    # Malaysia
    elif symbol.endswith('.KL'):
        return "ASIA"
    # Mexico
    elif symbol.endswith('.MX'):
        return "LATAM"
    # Brazil
    elif symbol.endswith('.SA'):
        return "LATAM"
    # Argentina
    elif symbol.endswith('.BA'):
        return "SOUTH_AMERICA"
    # Chile
    elif symbol.endswith('.SN'):
        return "SOUTH_AMERICA"
    # Colombia
    elif symbol.endswith('.CL'):
        return "SOUTH_AMERICA"
    # Venezuela
    elif symbol.endswith('.CR'):
        return "SOUTH_AMERICA"
    # South Africa
    elif symbol.endswith('.JO'):
        return "AFRICA"
    # Egypt (Cairo Stock Exchange)
    elif symbol.endswith('.CA'):
        return "AFRICA"
    # Austria (Vienna)
    elif symbol.endswith('.VI'):
        return "EUROPE"
    # Crypto
    elif '/' in symbol or 'USDT' in symbol:
        return "CRYPTO"
    # Forex
    elif '=X' in symbol:
        return "FOREX"
    # Commodities/Futures
    elif '=F' in symbol or symbol.endswith('.CBT') or symbol.endswith('.CME') or symbol.endswith('.CMX') or symbol.endswith('.NYM') or symbol.endswith('.NYB'):
        return "COMMODITIES"
    else:
        return "US"  # Default to US markets


def get_model_params(symbol: str) -> dict:
    """Get optimized model parameters for a symbol based on its exchange"""
    exchange = get_exchange_for_symbol(symbol)
    return EXCHANGE_MODEL_PARAMS.get(exchange, EXCHANGE_MODEL_PARAMS["US"])

# =============================================================================
# GLOBAL STOCK EXCHANGES - Major Listed Stocks
# =============================================================================

# -----------------------------------------------------------------------------
# NYSE - New York Stock Exchange (United States, USD, ~$44.7 trillion)
# -----------------------------------------------------------------------------
NYSE_STOCKS = [
    # Technology & Communication
    "IBM", "ORCL", "CRM", "SHOP", "SNOW", "PLTR", "UBER", "ABNB", "SQ", "TWLO",
    # Finance
    "JPM", "BAC", "WFC", "C", "GS", "MS", "AXP", "BLK", "SCHW", "USB",
    "PNC", "TFC", "BK", "STT", "COF", "AIG", "PRU", "MET", "ALL", "TRV",
    # Healthcare
    "JNJ", "UNH", "PFE", "MRK", "ABT", "TMO", "DHR", "BMY", "LLY", "AMGN",
    "GILD", "CVS", "CI", "HUM", "MCK", "CAH", "ABC", "ZTS", "VRTX", "REGN",
    # Consumer & Retail
    "WMT", "HD", "NKE", "MCD", "SBUX", "TGT", "LOW", "TJX", "COST", "DG",
    "KO", "PEP", "PG", "CL", "KMB", "EL", "GIS", "K", "HSY", "MO",
    # Industrial
    "BA", "CAT", "HON", "MMM", "GE", "LMT", "RTX", "DE", "UPS", "FDX",
    "EMR", "ITW", "PH", "ROK", "ETN", "CMI", "IR", "DOV", "SWK", "GD",
    # Energy
    "XOM", "CVX", "COP", "SLB", "EOG", "PXD", "MPC", "VLO", "PSX", "OXY",
    "HAL", "BKR", "DVN", "FANG", "APA", "MRO", "NOV", "KMI", "WMB",
    # Materials
    "LIN", "APD", "ECL", "SHW", "PPG", "DD", "NEM", "FCX", "NUE", "CLF",
    # Real Estate
    "AMT", "PLD", "CCI", "EQIX", "SPG", "PSA", "DLR", "O", "WELL", "AVB",
    # Utilities
    "NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "XEL", "PEG", "ED",
]

# -----------------------------------------------------------------------------
# NASDAQ - (United States, USD, ~$42.2 trillion)
# -----------------------------------------------------------------------------
NASDAQ_STOCKS = [
    # Big Tech (FAANG+)
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "NVDA", "TSLA",
    # Semiconductors
    "AMD", "INTC", "AVGO", "QCOM", "TXN", "MU", "AMAT", "LRCX", "KLAC", "MRVL",
    "ADI", "NXPI", "ON", "MCHP", "SWKS", "QRVO", "MPWR", "ENTG", "ASML",
    # Software & Cloud
    "ADBE", "CRM", "NOW", "INTU", "SNPS", "CDNS", "ANSS", "TEAM", "WDAY", "ZS",
    "DDOG", "CRWD", "OKTA", "MDB", "NET", "PANW", "FTNT", "ZM", "DOCU", "SPLK",
    # Internet & E-commerce
    "NFLX", "PYPL", "EBAY", "MELI", "BKNG", "EXPE", "TCOM", "TRIP", "ETSY", "W",
    "PINS", "SNAP", "ROKU", "TTD", "MTCH", "BMBL", "HOOD", "COIN", "RBLX", "U",
    # Biotech & Pharma
    "BIIB", "MRNA", "REGN", "VRTX", "GILD", "ILMN", "SGEN", "ALGN", "DXCM", "IDXX",
    # Consumer & Retail
    "SBUX", "COST", "PDD", "JD", "LULU", "ROST", "DLTR", "MAR", "ORLY", "AZO",
    # EV & Clean Energy
    "LCID", "RIVN", "NIO", "XPEV", "LI", "ENPH", "SEDG", "FSLR", "RUN",
    # Communication
    "CSCO", "CMCSA", "TMUS", "CHTR", "VOD", "LBRDK", "SIRI", "WBD", "PARA",
    # Financial Tech
    "SOFI", "AFRM", "UPST", "BILL", "FOUR", "GPN", "FIS", "FISV", "MA", "V",
]

# -----------------------------------------------------------------------------
# Shanghai Stock Exchange (SSE) - China, CNY, ~$8.92 trillion
# Suffix: .SS
# -----------------------------------------------------------------------------
SHANGHAI_STOCKS = [
    # Financial - Banks & Insurance
    "601398.SS",  # ICBC
    "601288.SS",  # Agricultural Bank of China
    "601939.SS",  # China Construction Bank
    "601988.SS",  # Bank of China
    "601328.SS",  # Bank of Communications
    "600036.SS",  # China Merchants Bank
    "601166.SS",  # Industrial Bank
    "600016.SS",  # Minsheng Bank
    "601318.SS",  # Ping An Insurance
    "601628.SS",  # China Life Insurance
    "600000.SS",  # Shanghai Pudong Development Bank
    "601601.SS",  # China Pacific Insurance
    # Energy & Petrochemical
    "601857.SS",  # PetroChina
    "600028.SS",  # Sinopec
    "601088.SS",  # China Shenhua Energy
    "600585.SS",  # Anhui Conch Cement
    "601225.SS",  # Shaanxi Coal
    # Technology & Telecom
    "600519.SS",  # Kweichow Moutai (Liquor but huge)
    "601012.SS",  # LONGi Green Energy
    "600900.SS",  # China Yangtze Power
    "600031.SS",  # Sany Heavy Industry
    "601888.SS",  # China Tourism Group
    "603259.SS",  # WuXi AppTec
    "688981.SS",  # Semiconductor Manufacturing International (STAR)
    "600050.SS",  # China Unicom
    "601728.SS",  # China Telecom
    # Consumer & Healthcare
    "600276.SS",  # Hengrui Medicine
    "600196.SS",  # Fosun Pharma
    "600887.SS",  # Inner Mongolia Yili
    "600690.SS",  # Haier Smart Home
    "603288.SS",  # Foshan Haitian
    # Industrial & Materials
    "600309.SS",  # Wanhua Chemical
    "601899.SS",  # Zijin Mining
    "600019.SS",  # Baoshan Iron & Steel
    "601668.SS",  # China State Construction
    "601186.SS",  # China Railway Construction
    "601390.SS",  # China Railway Group
    # Automotive
    "600104.SS",  # SAIC Motor
    "601238.SS",  # GAC Group
]

# -----------------------------------------------------------------------------
# Shenzhen Stock Exchange (SZSE) - China, CNY, ~$5.11 trillion
# Suffix: .SZ
# -----------------------------------------------------------------------------
SHENZHEN_STOCKS = [
    # Technology & Electronics
    "000858.SZ",  # Wuliangye Yibin (Liquor giant)
    "002594.SZ",  # BYD Company
    "000333.SZ",  # Midea Group
    "000651.SZ",  # Gree Electric
    "002415.SZ",  # Hikvision
    "002475.SZ",  # Luxshare Precision
    "300750.SZ",  # CATL (Contemporary Amperex)
    "300059.SZ",  # East Money Information
    "002352.SZ",  # S.F. Holding (SF Express)
    "000725.SZ",  # BOE Technology
    "002236.SZ",  # Dahua Technology
    # Finance
    "000001.SZ",  # Ping An Bank
    "000002.SZ",  # China Vanke
    "002142.SZ",  # Bank of Ningbo
    "000166.SZ",  # Shenwan Hongyuan
    # Healthcare & Pharma
    "300760.SZ",  # Mindray Medical
    "002007.SZ",  # Hualan Biological
    "000538.SZ",  # Yunnan Baiyao
    "002422.SZ",  # Kelun Pharma
    "300347.SZ",  # Hangzhou Tigermed
    # Consumer
    "002304.SZ",  # Yanghe Brewery
    "000568.SZ",  # Luzhou Laojiao
    "000895.SZ",  # Shuanghui Development
    "002714.SZ",  # Muyuan Foods
    "300498.SZ",  # WensUrbanization
    # Industrial & Materials
    "002460.SZ",  # Ganfeng Lithium
    "002466.SZ",  # Tianqi Lithium
    "000063.SZ",  # ZTE Corporation
    "000100.SZ",  # TCL Technology
    "002812.SZ",  # Yunnan Enneng
    # Real Estate
    "000069.SZ",  # Shenzhen Overseas Chinese Town
    "001979.SZ",  # China Merchants Shekou
]

# -----------------------------------------------------------------------------
# Tokyo Stock Exchange (TSE) - Japan, JPY, ~$7.59 trillion
# Suffix: .T
# -----------------------------------------------------------------------------
TOKYO_STOCKS = [
    # Automotive
    "7203.T",     # Toyota Motor
    "7267.T",     # Honda Motor
    "7201.T",     # Nissan Motor
    "7269.T",     # Suzuki Motor
    "7270.T",     # Subaru
    "7261.T",     # Mazda Motor
    # Technology & Electronics
    "6758.T",     # Sony Group
    "6861.T",     # Keyence
    "6501.T",     # Hitachi
    "6502.T",     # Toshiba
    "6503.T",     # Mitsubishi Electric
    "6752.T",     # Panasonic
    "6702.T",     # Fujitsu
    "6762.T",     # TDK
    "6963.T",     # Rohm
    "6857.T",     # Advantest
    "6146.T",     # Disco
    "8035.T",     # Tokyo Electron
    # Finance
    "8306.T",     # Mitsubishi UFJ Financial
    "8316.T",     # Sumitomo Mitsui Financial
    "8411.T",     # Mizuho Financial
    "8766.T",     # Tokio Marine
    "8750.T",     # Dai-ichi Life
    "8725.T",     # MS&AD Insurance
    # Trading & Industrial
    "8058.T",     # Mitsubishi Corporation
    "8031.T",     # Mitsui & Co
    "8001.T",     # ITOCHU
    "8002.T",     # Marubeni
    "8053.T",     # Sumitomo Corporation
    # Pharma & Healthcare
    "4502.T",     # Takeda Pharmaceutical
    "4503.T",     # Astellas Pharma
    "4519.T",     # Chugai Pharmaceutical
    "4568.T",     # Daiichi Sankyo
    "4523.T",     # Eisai
    # Retail & Consumer
    "9983.T",     # Fast Retailing (Uniqlo)
    "3382.T",     # Seven & i Holdings
    "8267.T",     # AEON
    "4911.T",     # Shiseido
    "4452.T",     # Kao Corporation
    # Telecom
    "9432.T",     # Nippon Telegraph (NTT)
    "9433.T",     # KDDI
    "9434.T",     # SoftBank Corp
    "9984.T",     # SoftBank Group
    # Industrial
    "6301.T",     # Komatsu
    "6305.T",     # Hitachi Construction
    "7011.T",     # Mitsubishi Heavy Industries
    "6902.T",     # DENSO
    "6954.T",     # Fanuc
    "7751.T",     # Canon
    "4063.T",     # Shin-Etsu Chemical
    "6367.T",     # Daikin Industries
]

# -----------------------------------------------------------------------------
# Hong Kong Stock Exchange (HKEX) - Hong Kong, HKD, ~$6.17 trillion
# Suffix: .HK
# -----------------------------------------------------------------------------
HONGKONG_STOCKS = [
    # Technology & Internet
    "0700.HK",    # Tencent Holdings
    "9988.HK",    # Alibaba Group
    "3690.HK",    # Meituan
    "9618.HK",    # JD.com
    "9999.HK",    # NetEase
    "1810.HK",    # Xiaomi
    "2382.HK",    # Sunny Optical
    "0268.HK",    # Kingdish Medical
    "0981.HK",    # SMIC
    "3888.HK",    # Kingsoft
    "6618.HK",    # JD Health
    # Finance
    "0005.HK",    # HSBC Holdings
    "1398.HK",    # ICBC
    "3988.HK",    # Bank of China
    "0939.HK",    # CCB
    "1288.HK",    # Agricultural Bank
    "2318.HK",    # Ping An Insurance
    "2628.HK",    # China Life
    "1299.HK",    # AIA Group
    "0388.HK",    # Hong Kong Exchanges
    "2388.HK",    # BOC Hong Kong
    # Property
    "0016.HK",    # Sun Hung Kai Properties
    "0012.HK",    # Henderson Land
    "0001.HK",    # CK Hutchison
    "0017.HK",    # New World Development
    "0688.HK",    # China Overseas Land
    "2007.HK",    # Country Garden
    # Energy & Utilities
    "0883.HK",    # CNOOC
    "0857.HK",    # PetroChina
    "0386.HK",    # Sinopec
    "0002.HK",    # CLP Holdings
    "0003.HK",    # Hong Kong & China Gas
    "0006.HK",    # Power Assets
    # Consumer
    "2020.HK",    # Anta Sports
    "1928.HK",    # Sands China
    "0027.HK",    # Galaxy Entertainment
    "0291.HK",    # China Resources Beer
    "0322.HK",    # Tingyi
    "0151.HK",    # Want Want China
    # Industrial
    "0175.HK",    # Geely Automobile
    "2333.HK",    # Great Wall Motor
    "1211.HK",    # BYD Company
    "1113.HK",    # CK Asset Holdings
    "0066.HK",    # MTR Corporation
    # Healthcare
    "1177.HK",    # Sino Biopharm
    "2269.HK",    # WuXi Biologics
]

# -----------------------------------------------------------------------------
# London Stock Exchange (LSE) - UK, GBP, ~$3.14 trillion
# Suffix: .L
# -----------------------------------------------------------------------------
LONDON_STOCKS = [
    # Finance & Banking
    "HSBA.L",     # HSBC Holdings
    "LLOY.L",     # Lloyds Banking
    "BARC.L",     # Barclays
    "NWG.L",      # NatWest Group
    "STAN.L",     # Standard Chartered
    "PRU.L",      # Prudential
    "LGEN.L",     # Legal & General
    "AV.L",       # Aviva
    "PHNX.L",     # Phoenix Group
    # Energy & Mining
    "SHEL.L",     # Shell
    "BP.L",       # BP
    "RIO.L",      # Rio Tinto
    "BHP.L",      # BHP Group
    "AAL.L",      # Anglo American
    "GLEN.L",     # Glencore
    "ANTO.L",     # Antofagasta
    # Pharma & Healthcare
    "GSK.L",      # GSK
    "AZN.L",      # AstraZeneca
    "HIK.L",      # Hikma Pharmaceuticals
    "SN.L",       # Smith & Nephew
    # Consumer & Retail
    "ULVR.L",     # Unilever
    "DGE.L",      # Diageo
    "RKT.L",      # Reckitt Benckiser
    "BATS.L",     # British American Tobacco
    "IMB.L",      # Imperial Brands
    "TSCO.L",     # Tesco
    "SBRY.L",     # Sainsbury's
    "MKS.L",      # Marks & Spencer
    "ABF.L",      # Associated British Foods
    "JD.L",       # JD Sports
    # Industrial & Aerospace
    "BA.L",       # BAE Systems
    "RR.L",       # Rolls-Royce
    "EXPN.L",     # Experian
    "REL.L",      # RELX
    "CRH.L",      # CRH
    "BNZL.L",     # Bunzl
    "DCC.L",      # DCC
    # Telecom & Media
    "VOD.L",      # Vodafone
    "BT-A.L",     # BT Group
    "WPP.L",      # WPP
    "ITV.L",      # ITV
    # Real Estate
    "LAND.L",     # Land Securities
    "BLND.L",     # British Land
    "SGRO.L",     # Segro
    # Utilities
    "NG.L",       # National Grid
    "SSE.L",      # SSE
    "CNA.L",      # Centrica
    "SVT.L",      # Severn Trent
    "UU.L",       # United Utilities
]

# -----------------------------------------------------------------------------
# Euronext - Multiple European Cities (Amsterdam, Paris, Brussels, Lisbon, Milan)
# Suffixes: .AS (Amsterdam), .PA (Paris), .BR (Brussels), .LS (Lisbon), .MI (Milan)
# -----------------------------------------------------------------------------
EURONEXT_STOCKS = [
    # Amsterdam (.AS) - Netherlands
    "ASML.AS",    # ASML Holding
    "ADYEN.AS",   # Adyen
    "PHIA.AS",    # Philips
    "INGA.AS",    # ING Group
    "ABN.AS",     # ABN AMRO
    "UNA.AS",     # Unilever
    "HEIA.AS",    # Heineken
    "AKZA.AS",    # Akzo Nobel
    "NN.AS",      # NN Group
    "RAND.AS",    # Randstad
    "WKL.AS",     # Wolters Kluwer
    "AD.AS",      # Ahold Delhaize
    "DSM.AS",     # DSM
    "ASM.AS",     # ASM International
    "BESI.AS",    # BE Semiconductor
    "PRX.AS",     # Prosus
    
    # Paris (.PA) - France
    "OR.PA",      # L'Oreal
    "MC.PA",      # LVMH
    "TTE.PA",     # TotalEnergies
    "SAN.PA",     # Sanofi
    "AIR.PA",     # Airbus
    "BNP.PA",     # BNP Paribas
    "ACA.PA",     # Credit Agricole
    "GLE.PA",     # Societe Generale
    "CS.PA",      # AXA
    "CAP.PA",     # Capgemini
    "DG.PA",      # Vinci
    "SGO.PA",     # Saint-Gobain
    "SU.PA",      # Schneider Electric
    "RMS.PA",     # Hermes
    "KER.PA",     # Kering
    "EL.PA",      # EssilorLuxottica
    "AI.PA",      # Air Liquide
    "ORA.PA",     # Orange
    "VIV.PA",     # Vivendi
    "EN.PA",      # Bouygues
    "RI.PA",      # Pernod Ricard
    "DSY.PA",     # Dassault Systemes
    "SAF.PA",     # Safran
    "STM.PA",     # STMicroelectronics
    
    # Brussels (.BR) - Belgium
    "ABI.BR",     # Anheuser-Busch InBev
    "UCB.BR",     # UCB
    "KBC.BR",     # KBC Group
    "SOLB.BR",    # Solvay
    "UMI.BR",     # Umicore
    "AGS.BR",     # Ageas
    
    # Milan (.MI) - Italy
    "ENI.MI",     # Eni
    "ENEL.MI",    # Enel
    "ISP.MI",     # Intesa Sanpaolo
    "UCG.MI",     # UniCredit
    "G.MI",       # Assicurazioni Generali
    "STM.MI",     # STMicroelectronics
    "TEN.MI",     # Tenaris
    "RACE.MI",    # Ferrari
    "PRY.MI",     # Prysmian
    "SRG.MI",     # Snam
    "TIT.MI",     # Telecom Italia
    "LDO.MI",     # Leonardo
]

# -----------------------------------------------------------------------------
# Toronto Stock Exchange (TSX) - Canada, CAD, ~$4 trillion
# Suffix: .TO
# -----------------------------------------------------------------------------
TORONTO_STOCKS = [
    # Financial Services
    "RY.TO",      # Royal Bank of Canada
    "TD.TO",      # Toronto-Dominion Bank
    "BNS.TO",     # Bank of Nova Scotia
    "BMO.TO",     # Bank of Montreal
    "CM.TO",      # CIBC
    "NA.TO",      # National Bank
    "MFC.TO",     # Manulife Financial
    "SLF.TO",     # Sun Life Financial
    "GWO.TO",     # Great-West Lifeco
    "POW.TO",     # Power Corporation
    "BN.TO",      # Brookfield Corporation
    "BAM.TO",     # Brookfield Asset Management
    # Energy
    "SU.TO",      # Suncor Energy
    "CNQ.TO",     # Canadian Natural Resources
    "CVE.TO",     # Cenovus Energy
    "IMO.TO",     # Imperial Oil
    "TRP.TO",     # TC Energy
    "ENB.TO",     # Enbridge
    "PPL.TO",     # Pembina Pipeline
    "ARX.TO",     # ARC Resources
    # Mining & Materials
    "ABX.TO",     # Barrick Gold
    "NTR.TO",     # Nutrien
    "FM.TO",      # First Quantum Minerals
    "TECK-B.TO",  # Teck Resources
    "AGI.TO",     # Alamos Gold
    "K.TO",       # Kinross Gold
    "CCO.TO",     # Cameco
    # Technology
    "SHOP.TO",    # Shopify
    "CSU.TO",     # Constellation Software
    "OTEX.TO",    # Open Text
    "BB.TO",      # BlackBerry
    "LSPD.TO",    # Lightspeed Commerce
    # Telecom
    "BCE.TO",     # BCE Inc
    "T.TO",       # TELUS
    "RCI-B.TO",   # Rogers Communications
    "QBR-B.TO",   # Quebecor
    # Consumer & Industrial
    "ATD.TO",     # Alimentation Couche-Tard
    "L.TO",       # Loblaw Companies
    "MG.TO",      # Magna International
    "DOL.TO",     # Dollarama
    "WSP.TO",     # WSP Global
    "CAE.TO",     # CAE Inc
    "CNR.TO",     # Canadian National Railway
    "CP.TO",      # Canadian Pacific Railway
    # Real Estate
    "REI-UN.TO",  # RioCan REIT
    "CAR-UN.TO",  # Canadian Apartment REIT
    "BPY-UN.TO",  # Brookfield Property Partners
    # Utilities
    "FTS.TO",     # Fortis
    "EMA.TO",     # Emera
    "H.TO",       # Hydro One
]

# -----------------------------------------------------------------------------
# NSE India (National Stock Exchange) - India, INR, ~$5.32 trillion
# Suffix: .NS
# -----------------------------------------------------------------------------
NSE_INDIA_STOCKS = [
    # Nifty 50 Major Stocks
    "RELIANCE.NS",    # Reliance Industries
    "TCS.NS",         # Tata Consultancy Services
    "HDFCBANK.NS",    # HDFC Bank
    "INFY.NS",        # Infosys
    "ICICIBANK.NS",   # ICICI Bank
    "HINDUNILVR.NS",  # Hindustan Unilever
    "SBIN.NS",        # State Bank of India
    "BHARTIARTL.NS",  # Bharti Airtel
    "ITC.NS",         # ITC Limited
    "KOTAKBANK.NS",   # Kotak Mahindra Bank
    "LT.NS",          # Larsen & Toubro
    "AXISBANK.NS",    # Axis Bank
    "ASIANPAINT.NS",  # Asian Paints
    "MARUTI.NS",      # Maruti Suzuki
    "HCLTECH.NS",     # HCL Technologies
    "SUNPHARMA.NS",   # Sun Pharmaceutical
    "TITAN.NS",       # Titan Company
    "BAJFINANCE.NS",  # Bajaj Finance
    "WIPRO.NS",       # Wipro
    "ULTRACEMCO.NS",  # UltraTech Cement
    "ONGC.NS",        # Oil & Natural Gas Corp
    "NTPC.NS",        # NTPC Limited
    "POWERGRID.NS",   # Power Grid Corp
    "TATAMOTORS.NS",  # Tata Motors
    "TATASTEEL.NS",   # Tata Steel
    "M&M.NS",         # Mahindra & Mahindra
    "JSWSTEEL.NS",    # JSW Steel
    "ADANIENT.NS",    # Adani Enterprises
    "ADANIPORTS.NS",  # Adani Ports
    "COALINDIA.NS",   # Coal India
    "BAJAJFINSV.NS",  # Bajaj Finserv
    "TECHM.NS",       # Tech Mahindra
    "DRREDDY.NS",     # Dr. Reddy's Labs
    "DIVISLAB.NS",    # Divi's Laboratories
    "CIPLA.NS",       # Cipla
    "EICHERMOT.NS",   # Eicher Motors
    "GRASIM.NS",      # Grasim Industries
    "INDUSINDBK.NS",  # IndusInd Bank
    "NESTLEIND.NS",   # Nestle India
    "BRITANNIA.NS",   # Britannia Industries
    "HEROMOTOCO.NS",  # Hero MotoCorp
    "APOLLOHOSP.NS",  # Apollo Hospitals
    "HINDALCO.NS",    # Hindalco Industries
    "BPCL.NS",        # Bharat Petroleum
    "TATACONSUM.NS",  # Tata Consumer Products
    "SBILIFE.NS",     # SBI Life Insurance
    "HDFCLIFE.NS",    # HDFC Life Insurance
    "UPL.NS",         # UPL Limited
    "SHREECEM.NS",    # Shree Cement
]

# -----------------------------------------------------------------------------
# BSE India (Bombay Stock Exchange) - India, INR, ~$5.25 trillion  
# Suffix: .BO
# Additional stocks not in NSE or different
# -----------------------------------------------------------------------------
BSE_INDIA_STOCKS = [
    # Major BSE Stocks (many overlap with NSE, these are additional/alternatives)
    "RELIANCE.BO",
    "TCS.BO",
    "HDFCBANK.BO",
    "INFY.BO",
    "ICICIBANK.BO",
    "BHARTIARTL.BO",
    "SBIN.BO",
    "LICI.BO",        # LIC India
    "ADANIGREEN.BO",  # Adani Green Energy
    "ADANITRANS.BO",  # Adani Transmission
    "HAL.BO",         # Hindustan Aeronautics
    "IRCTC.BO",       # IRCTC
    "DMART.BO",       # Avenue Supermarts (DMart)
    "PIDILITIND.BO",  # Pidilite Industries
    "SIEMENS.BO",     # Siemens India
    "HAVELLS.BO",     # Havells India
    "GODREJCP.BO",    # Godrej Consumer Products
    "DABUR.BO",       # Dabur India
    "MARICO.BO",      # Marico
    "BERGEPAINT.BO",  # Berger Paints
    "INDIGO.BO",      # InterGlobe Aviation (IndiGo)
    "ZOMATO.BO",      # Zomato
    "PAYTM.BO",       # One97 Communications (Paytm)
    "NYKAA.BO",       # FSN E-Commerce (Nykaa)
    "POLICYBZR.BO",   # PB Fintech (PolicyBazaar)
]
# -----------------------------------------------------------------------------
# Saudi Stock Exchange (Tadawul) - Saudi Arabia, SAR, ~$2.9 trillion
# Suffix: .SR (Yahoo Finance format)
# -----------------------------------------------------------------------------
TADAWUL_STOCKS = [
    # Banking & Finance
    "1180.SR",    # Al Rajhi Bank
    "1120.SR",    # Al Ahli Bank (SNB)
    "1150.SR",    # Alinma Bank
    "2010.SR",    # SABIC
    "1010.SR",    # Riyad Bank
    "1050.SR",    # SABB Bank
    "1060.SR",    # Bank AlJazira
    "1080.SR",    # Arab National Bank
    "1140.SR",    # Bank AlBilad
    # Energy & Petrochemicals
    "2222.SR",    # Saudi Aramco
    "2380.SR",    # Petro Rabigh
    "2350.SR",    # SABIC Agri-Nutrients
    "2330.SR",    # Advanced Petrochemical
    "2060.SR",    # National Industrialization (Tasnee)
    "2250.SR",    # SIIG (Saudi Industrial Investment)
    "2290.SR",    # Yanbu National Petrochemical
    # Telecommunications
    "7010.SR",    # STC (Saudi Telecom)
    "7020.SR",    # Etihad Etisalat (Mobily)
    "7030.SR",    # Zain KSA
    # Real Estate
    "4300.SR",    # Dar Al Arkan
    "4310.SR",    # Knowledge Economic City
    "4020.SR",    # Al-Khodari
    # Retail & Consumer
    "4190.SR",    # Jarir Marketing
    "4001.SR",    # Abdullah Al Othaim Markets
    "4003.SR",    # Extra
    "4002.SR",    # Mouwasat Medical Services
    # Industrials
    "1211.SR",    # Maaden (Saudi Arabian Mining)
    "3010.SR",    # Arabian Cement
    "3020.SR",    # Yamama Cement
    "3030.SR",    # Saudi Cement
    "3050.SR",    # Southern Province Cement
    # Insurance
    "8010.SR",    # Tawuniya Insurance
    "8020.SR",    # Malath Cooperative Insurance
    "8030.SR",    # Sanad Insurance
]

# -----------------------------------------------------------------------------
# Abu Dhabi Securities Exchange (ADX) - UAE, AED, ~$0.7 trillion
# Suffix: .AE (Yahoo Finance uses .AE for all UAE stocks)
# -----------------------------------------------------------------------------
ADX_STOCKS = [
    # Major UAE stocks available on Yahoo Finance
    "EMAAR.AE",   # Emaar Properties
    "DIB.AE",     # Dubai Islamic Bank
    "DFM.AE",     # Dubai Financial Market
    "DEWA.AE",    # Dubai Electricity & Water Authority
    "SALIK.AE",   # Salik Company
    "DU.AE",      # Emirates Integrated Telecommunications
    "FAB.AE",     # First Abu Dhabi Bank
    "ADCB.AE",    # Abu Dhabi Commercial Bank
    "ETISALAT.AE",# Emirates Telecommunications (Etisalat)
    "ADNOCDIST.AE", # ADNOC Distribution
    "ALDAR.AE",   # Aldar Properties
    "IHC.AE",     # International Holding Company
    "ADIB.AE",    # Abu Dhabi Islamic Bank
    "TAQA.AE",    # Abu Dhabi National Energy
]

# -----------------------------------------------------------------------------
# Dubai Financial Market (DFM) - UAE, AED, ~$0.1 trillion
# Suffix: .AE (Yahoo Finance uses .AE for all UAE stocks)
# -----------------------------------------------------------------------------
DFM_STOCKS = [
    # Banking & Finance
    "DIB.AE",     # Dubai Islamic Bank
    "DFM.AE",     # Dubai Financial Market
    "CBD.AE",     # Commercial Bank of Dubai
    "EIB.AE",     # Emirates NBD
    # Real Estate
    "EMAAR.AE",   # Emaar Properties
    "DAMAC.AE",   # DAMAC Properties
    "DEYAAR.AE",  # Deyaar Development
    "EMAARMALL.AE", # Emaar Malls
    # Utilities & Services
    "DEWA.AE",    # Dubai Electricity & Water Authority
    "SALIK.AE",   # Salik Company
    "PARKIN.AE",  # Parkin Company
    # Telecom
    "DU.AE",      # Emirates Integrated Telecommunications (du)
    # Insurance
    "SALAMA.AE",  # Islamic Arab Insurance
    "ORIENT.AE",  # Orient Insurance
]

# -----------------------------------------------------------------------------
# Qatar Stock Exchange (QSE) - Qatar, QAR, ~$0.15 trillion
# Suffix: .QA
# -----------------------------------------------------------------------------
QSE_STOCKS = [
    # Banking & Finance
    "QNBK.QA",    # Qatar National Bank
    "CBQK.QA",    # Commercial Bank of Qatar
    "MARK.QA",    # Masraf Al Rayan
    "DHBK.QA",    # Doha Bank
    "QIBK.QA",    # Qatar Islamic Bank
    "QIIK.QA",    # Qatar International Islamic Bank
    # Energy & Industry
    "IQCD.QA",    # Industries Qatar
    "QGTS.QA",    # Qatar Gas Transport (Nakilat)
    "MPHC.QA",    # Mesaieed Petrochemical
    # Telecommunications
    "ORDS.QA",    # Ooredoo
    # Real Estate
    "BLDN.QA",    # Barwa Real Estate
    "ERES.QA",    # Ezdan Holding
    "UDCD.QA",    # United Development
    # Insurance
    "QATI.QA",    # Qatar Insurance
    "QGRI.QA",    # Qatar General Insurance
    # Utilities
    "QAMC.QA",    # Qatar Aluminum Manufacturing
    "QEWS.QA",    # Qatar Electricity & Water
]

# -----------------------------------------------------------------------------
# Kuwait Stock Exchange (Boursa Kuwait) - Kuwait, KWD, ~$0.13 trillion
# Suffix: .KW
# -----------------------------------------------------------------------------
KUWAIT_STOCKS = [
    # Banking & Finance
    "NBK.KW",     # National Bank of Kuwait
    "KFH.KW",     # Kuwait Finance House
    "BURGAN.KW",  # Burgan Bank
    "ABK.KW",     # Al Ahli Bank of Kuwait
    "GBK.KW",     # Gulf Bank
    "CBK.KW",     # Commercial Bank of Kuwait
    "BOUBYAN.KW", # Boubyan Bank
    # Telecommunications
    "ZAIN.KW",    # Zain Group
    "OOREDOO.KW", # Ooredoo Kuwait
    "STC.KW",     # Kuwait Telecommunications (STC)
    # Real Estate
    "MABANEE.KW", # Mabanee Company
    "ALIMTIAZ.KW",# Al Imtiaz Investment
    "SALHIA.KW",  # Salhia Real Estate
    # Industrial
    "KIPCO.KW",   # Kuwait Projects Company
    "AGILITY.KW", # Agility Public Warehousing
    "EQUATE.KW",  # Equate Petrochemical
    # Insurance
    "KSE.KW",     # Kuwait Insurance
    "WETHAQ.KW",  # First Takaful Insurance
]

# -----------------------------------------------------------------------------
# Korea Exchange (KRX) - South Korea, KRW, ~$2.2 trillion
# Suffix: .KS (KOSPI), .KQ (KOSDAQ)
# -----------------------------------------------------------------------------
KRX_STOCKS = [
    # Technology & Electronics
    "005930.KS",  # Samsung Electronics
    "000660.KS",  # SK Hynix
    "035420.KS",  # NAVER
    "035720.KS",  # Kakao
    "051910.KS",  # LG Chem
    "006400.KS",  # Samsung SDI
    "373220.KS",  # LG Energy Solution
    "207940.KS",  # Samsung Biologics
    "000270.KS",  # Kia
    "005380.KS",  # Hyundai Motor
    # Finance
    "105560.KS",  # KB Financial
    "055550.KS",  # Shinhan Financial
    "086790.KS",  # Hana Financial
    "316140.KS",  # Woori Financial
    # Consumer & Industrial
    "034730.KS",  # SK
    "018260.KS",  # Samsung C&T
    "012330.KS",  # Hyundai Mobis
    "066570.KS",  # LG Electronics
    "003550.KS",  # LG Corp
    "028260.KS",  # Samsung C&T
]

# -----------------------------------------------------------------------------
# Taiwan Stock Exchange (TWSE) - Taiwan, TWD, ~$2 trillion
# Suffix: .TW
# -----------------------------------------------------------------------------
TWSE_STOCKS = [
    "2330.TW",    # TSMC
    "2317.TW",    # Hon Hai (Foxconn)
    "2454.TW",    # MediaTek
    "2412.TW",    # Chunghwa Telecom
    "2882.TW",    # Cathay Financial
    "2881.TW",    # Fubon Financial
    "2308.TW",    # Delta Electronics
    "1301.TW",    # Formosa Plastics
    "2002.TW",    # China Steel
    "2886.TW",    # Mega Financial
    "3711.TW",    # ASE Technology
    "2303.TW",    # United Microelectronics
    "1303.TW",    # Nan Ya Plastics
    "2891.TW",    # CTBC Financial
    "2884.TW",    # E.Sun Financial
]

# -----------------------------------------------------------------------------
# Singapore Exchange (SGX) - Singapore, SGD, ~$0.7 trillion
# Suffix: .SI
# -----------------------------------------------------------------------------
SGX_STOCKS = [
    "D05.SI",     # DBS Group
    "O39.SI",     # OCBC Bank
    "U11.SI",     # UOB
    "Z74.SI",     # Singtel
    "BN4.SI",     # Keppel
    "C6L.SI",     # Singapore Airlines
    "S68.SI",     # SGX
    "V03.SI",     # Venture Corporation
    "F34.SI",     # Wilmar International
    "C52.SI",     # ComfortDelGro
    "S58.SI",     # SATS
    "C09.SI",     # City Developments
    "U96.SI",     # Sembcorp Industries
    "A17U.SI",    # Ascendas REIT
    "C38U.SI",    # CapitaLand Integrated
]

# -----------------------------------------------------------------------------
# Australian Securities Exchange (ASX) - Australia, AUD, ~$2.5 trillion
# Suffix: .AX
# -----------------------------------------------------------------------------
ASX_STOCKS = [
    "BHP.AX",     # BHP Group
    "CBA.AX",     # Commonwealth Bank
    "CSL.AX",     # CSL Limited
    "NAB.AX",     # National Australia Bank
    "WBC.AX",     # Westpac Banking
    "ANZ.AX",     # ANZ Banking
    "WES.AX",     # Wesfarmers
    "MQG.AX",     # Macquarie Group
    "RIO.AX",     # Rio Tinto
    "WOW.AX",     # Woolworths Group
    "TLS.AX",     # Telstra
    "FMG.AX",     # Fortescue Metals
    "WDS.AX",     # Woodside Energy
    "TCL.AX",     # Transurban
    "STO.AX",     # Santos
    "NCM.AX",     # Newcrest Mining
    "ALL.AX",     # Aristocrat Leisure
    "COL.AX",     # Coles Group
    "REA.AX",     # REA Group
    "GMG.AX",     # Goodman Group
]

# -----------------------------------------------------------------------------
# New Zealand Exchange (NZX) - New Zealand, NZD, ~$0.1 trillion
# Suffix: .NZ
# -----------------------------------------------------------------------------
NZX_STOCKS = [
    "FPH.NZ",     # Fisher & Paykel Healthcare
    "SPK.NZ",     # Spark New Zealand
    "MFT.NZ",     # Mainfreight
    "ATM.NZ",     # A2 Milk Company
    "EBO.NZ",     # EBOS Group
    "AIR.NZ",     # Air New Zealand
    "SKC.NZ",     # SkyCity Entertainment
    "MEL.NZ",     # Meridian Energy
    "CEN.NZ",     # Contact Energy
    "AIA.NZ",     # Auckland International Airport
    "PCT.NZ",     # Precinct Properties
    "ARG.NZ",     # Argosy Property
    "GNE.NZ",     # Genesis Energy
    "VCT.NZ",     # Vector
    "NPX.NZ",     # NZX
    "RYM.NZ",     # Ryman Healthcare
    "WHS.NZ",     # Warehouse Group
    "SKT.NZ",     # Sky Network TV
    "IFT.NZ",     # Infratil
    "SUM.NZ",     # Summerset Group
    "KMD.NZ",     # KMD Brands
    "PFI.NZ",     # Property for Industry
    "CMO.NZ",     # Comvita
    "NZR.NZ",     # New Zealand Refining
    "THL.NZ",     # Tourism Holdings
]

# -----------------------------------------------------------------------------
# Indonesia Stock Exchange (IDX) - Indonesia, IDR, ~$0.7 trillion
# Suffix: .JK
# -----------------------------------------------------------------------------
IDX_STOCKS = [
    "BBCA.JK",    # Bank Central Asia
    "BBRI.JK",    # Bank Rakyat Indonesia
    "BMRI.JK",    # Bank Mandiri
    "TLKM.JK",    # Telkom Indonesia
    "ASII.JK",    # Astra International
    "UNVR.JK",    # Unilever Indonesia
    "ICBP.JK",    # Indofood CBP
    "GGRM.JK",    # Gudang Garam
    "HMSP.JK",    # HM Sampoerna
    "BBNI.JK",    # Bank Negara Indonesia
    "SMGR.JK",    # Semen Indonesia
    "INDF.JK",    # Indofood Sukses
    "KLBF.JK",    # Kalbe Farma
    "CPIN.JK",    # Charoen Pokphand
    "ADRO.JK",    # Adaro Energy
]

# -----------------------------------------------------------------------------
# Stock Exchange of Thailand (SET) - Thailand, THB, ~$0.6 trillion
# Suffix: .BK
# -----------------------------------------------------------------------------
SET_STOCKS = [
    "PTT.BK",     # PTT Public Company
    "PTTEP.BK",   # PTT Exploration
    "ADVANC.BK",  # Advanced Info Service
    "SCB.BK",     # SCB X
    "KBANK.BK",   # Kasikornbank
    "BBL.BK",     # Bangkok Bank
    "AOT.BK",     # Airports of Thailand
    "CPALL.BK",   # CP ALL
    "SCC.BK",     # Siam Cement
    "GULF.BK",    # Gulf Energy
    "BDMS.BK",    # Bangkok Dusit Medical
    "TRUE.BK",    # True Corporation
    "MINT.BK",    # Minor International
    "BEM.BK",     # Bangkok Expressway
    "IVL.BK",     # Indorama Ventures
]

# -----------------------------------------------------------------------------
# Bursa Malaysia (KLSE) - Malaysia, MYR, ~$0.4 trillion
# Suffix: .KL
# -----------------------------------------------------------------------------
KLSE_STOCKS = [
    "1155.KL",    # Maybank
    "1295.KL",    # Public Bank
    "4715.KL",    # Genting
    "6888.KL",    # Axiata Group
    "6012.KL",    # Maxis
    "3182.KL",    # Genting Malaysia
    "5347.KL",    # Tenaga Nasional
    "1082.KL",    # Hong Leong Bank
    "4707.KL",    # Nestle Malaysia
    "1023.KL",    # CIMB Group
    "5819.KL",    # Hong Leong Financial
    "6947.KL",    # DiGi.Com
    "4197.KL",    # Sime Darby
    "5183.KL",    # Petronas Chemicals
    "2445.KL",    # Kuala Lumpur Kepong
]

# -----------------------------------------------------------------------------
# Bolsa Mexicana de Valores (BMV) - Mexico, MXN, ~$0.5 trillion
# Suffix: .MX
# -----------------------------------------------------------------------------
BMV_STOCKS = [
    "WALMEX.MX",  # Walmart de Mexico
    "BIMBOA.MX",  # Grupo Bimbo
    "GFNORTEO.MX",# Banorte
    "AC.MX",      # Arca Continental
    "AMXB.MX",    # America Movil Series B
    "GCARSOA1.MX",# Grupo Carso
    "ALSEA.MX",   # Alsea
    "ASURB.MX",   # Grupo Aeroportuario del Sureste
    "GAPB.MX",    # Grupo Aeroportuario del Pacifico
    "GRUMAB.MX",  # Gruma
    "PINFRA.MX",  # Promotora y Operadora de Infraestructura
    "MEGACPO.MX", # Megacable
    "LABB.MX",    # Genomma Lab
    "OMAB.MX",    # Grupo Aeroportuario Centro Norte
    "VOLARA.MX",  # Controladora Vuela Compania de Aviacion
]

# -----------------------------------------------------------------------------
# B3 (Brasil Bolsa Balcão) - Brazil, BRL, ~$0.9 trillion
# Suffix: .SA
# -----------------------------------------------------------------------------
B3_STOCKS = [
    "PETR4.SA",   # Petrobras
    "VALE3.SA",   # Vale
    "ITUB4.SA",   # Itau Unibanco
    "BBDC4.SA",   # Bradesco
    "ABEV3.SA",   # Ambev
    "B3SA3.SA",   # B3 (Exchange)
    "WEGE3.SA",   # WEG
    "RENT3.SA",   # Localiza
    "JBSS3.SA",   # JBS
    "BBAS3.SA",   # Banco do Brasil
    "SUZB3.SA",   # Suzano
    "LREN3.SA",   # Lojas Renner
    "RAIL3.SA",   # Rumo
    "PRIO3.SA",   # PetroRio
    "ELET3.SA",   # Eletrobras
    "RADL3.SA",   # RD Saude
    "HAPV3.SA",   # Hapvida
    "MGLU3.SA",   # Magazine Luiza
    "VIVT3.SA",   # Telefonica Brasil
    "GGBR4.SA",   # Gerdau
]

# -----------------------------------------------------------------------------
# Johannesburg Stock Exchange (JSE) - South Africa, ZAR, ~$1 trillion
# Suffix: .JO
# -----------------------------------------------------------------------------
JSE_STOCKS = [
    "NPN.JO",     # Naspers
    "PRX.JO",     # Prosus
    "CFR.JO",     # Richemont
    "AGL.JO",     # Anglo American
    "BHP.JO",     # BHP Group
    "SOL.JO",     # Sasol
    "SBK.JO",     # Standard Bank
    "FSR.JO",     # FirstRand
    "ABG.JO",     # Absa Group
    "NED.JO",     # Nedbank
    "SHP.JO",     # Shoprite
    "VOD.JO",     # Vodacom
    "MTN.JO",     # MTN Group
    "BTI.JO",     # British American Tobacco
    "AMS.JO",     # Anglo American Platinum
    "IMP.JO",     # Impala Platinum
    "GFI.JO",     # Gold Fields
    "HAR.JO",     # Harmony Gold
    "SSW.JO",     # Sibanye Stillwater
    "DSY.JO",     # Discovery
]

# -----------------------------------------------------------------------------
# Egyptian Exchange (EGX) - Egypt, EGP, ~$45 billion
# Suffix: .CA (Cairo)
# -----------------------------------------------------------------------------
EGX_STOCKS = [
    # Banking & Finance
    "COMI.CA",    # Commercial International Bank (CIB)
    "HRHO.CA",    # Hermes Holding
    "EFIH.CA",    # EFG Hermes Holding
    "EKHOA.CA",   # El Khair Company
    # Real Estate
    "TMGH.CA",    # Talaat Moustafa Group Holding
    "PHDC.CA",    # Palm Hills Development
    "MNHD.CA",    # Madinet Nasr Housing
    "OCDI.CA",    # Orascom Development International
    "EMFD.CA",    # Emaar Misr
    # Telecom & Technology
    "ETEL.CA",    # Telecom Egypt
    "SWDY.CA",    # Saudi Watan Development
    "FWRY.CA",    # Fawry for Banking Technology
    # Consumer & Retail
    "EAST.CA",    # Eastern Company
    "JUFO.CA",    # Juhayna Food Industries
    "ORWE.CA",    # Oriental Weavers
    "EKHO.CA",    # El Khair Holding
    # Industrial & Materials
    "SKPC.CA",    # Sidi Kerir Petrochemicals
    "AMOC.CA",    # Alexandria Mineral Oils
    "IRON.CA",    # Egyptian Iron & Steel
    "EGAS.CA",    # Egypt Gas
    # Healthcare
    "CLHO.CA",    # Cleopatra Hospital Group
    "IBAG.CA",    # Ibnsina Pharma
    # Construction & Infrastructure
    "ABUK.CA",    # Abu Qir Fertilizers
    "GBCO.CA",    # GB Auto
    "HELI.CA",    # Heliopolis Housing
]

# -----------------------------------------------------------------------------
# Deutsche Börse Xetra - Germany, EUR, ~$2.3 trillion
# Suffix: .DE
# -----------------------------------------------------------------------------
XETRA_STOCKS = [
    "SAP.DE",     # SAP
    "SIE.DE",     # Siemens
    "ALV.DE",     # Allianz
    "DTE.DE",     # Deutsche Telekom
    "BAS.DE",     # BASF
    "BAYN.DE",    # Bayer
    "BMW.DE",     # BMW
    "MBG.DE",     # Mercedes-Benz
    "VOW3.DE",    # Volkswagen
    "MUV2.DE",    # Munich Re
    "ADS.DE",     # Adidas
    "DBK.DE",     # Deutsche Bank
    "IFX.DE",     # Infineon
    "HEN3.DE",    # Henkel
    "RWE.DE",     # RWE
    "DPW.DE",     # Deutsche Post DHL
    "LIN.DE",     # Linde
    "AIR.DE",     # Airbus
    "CON.DE",     # Continental
    "FRE.DE",     # Fresenius
]

# -----------------------------------------------------------------------------
# SIX Swiss Exchange - Switzerland, CHF, ~$1.7 trillion
# Suffix: .SW
# -----------------------------------------------------------------------------
SIX_STOCKS = [
    "NESN.SW",    # Nestle
    "ROG.SW",     # Roche
    "NOVN.SW",    # Novartis
    "UBSG.SW",    # UBS
    "CSGN.SW",    # Credit Suisse (now UBS)
    "ZURN.SW",    # Zurich Insurance
    "ABB.SW",     # ABB
    "SIKA.SW",    # Sika
    "GEBN.SW",    # Geberit
    "GIVN.SW",    # Givaudan
    "LONN.SW",    # Lonza
    "SREN.SW",    # Swiss Re
    "CFR.SW",     # Richemont
    "HOLN.SW",    # Holcim
    "SLHN.SW",    # Swiss Life
]

# -----------------------------------------------------------------------------
# Tel Aviv Stock Exchange (TASE) - Israel, ILS, ~$0.3 trillion
# Suffix: .TA
# -----------------------------------------------------------------------------
TASE_STOCKS = [
    "TEVA.TA",    # Teva Pharmaceutical
    "NICE.TA",    # NICE Systems
    "CHKP.TA",    # Check Point Software
    "LUMI.TA",    # Bank Leumi
    "POLI.TA",    # Bank Hapoalim
    "DSCT.TA",    # Discount Bank
    "ICL.TA",     # ICL Group
    "BEZQ.TA",    # Bezeq
    "ELCO.TA",    # Elco Holdings
    "AZRG.TA",    # Azrieli Group
    "ENLT.TA",    # Enlight Renewable Energy
    "SMTC.TA",    # Silicom
    "NVNI.TA",    # Novivi
    "FORTY.TA",   # Formula Systems
    "SELA.TA",    # Sela Sport
    "MGDL.TA",    # Migdal Insurance
    "MSBI.TA",    # Mizrahi Tefahot Bank
    "PRSK.TA",    # Poalim Real Estate
    "MZTF.TA",    # Mazor Robotics
    "ALLT.TA",    # Allot Communications
    "CEVA.TA",    # CEVA Inc.
    "FIBI.TA",    # First International Bank
    "RAHO.TA",    # Rak Holdings
    "BONS.TA",    # Bonus BioGroup
    "RTEN.TA",    # Rafael Advanced Defense
]

# -----------------------------------------------------------------------------
# Vienna Stock Exchange - Austria, EUR, ~$150 billion
# Suffix: .VI
# -----------------------------------------------------------------------------
VIENNA_STOCKS = [
    "ANDR.VI",    # Andritz
    "OMV.VI",     # OMV
    "VOE.VI",     # voestalpine
    "EBS.VI",     # Erste Group Bank
    "RBI.VI",     # Raiffeisen Bank International
    "VER.VI",     # Verbund
    "DOC.VI",     # Do & Co
    "TKA.VI",     # Telekom Austria
    "POST.VI",    # Österreichische Post
    "WIE.VI",     # Vienna Insurance Group
    "IIA.VI",     # Immofinanz
    "SBO.VI",     # Schoeller-Bleckmann Oilfield
    "UQA.VI",     # UNIQA Insurance Group
    "ATS.VI",     # ATS Automation Tooling Systems
    "FMT.VI",     # Frequentis
    "BTE.VI",     # Biotechmedics
    "NOEJ.VI",    # Novomatic
    "RDEV.VI",    # Rosenbauer International
    "ZAG.VI",     # Zumtobel Group
    "KTCG.VI",    # Kapsch TrafficCom
]

# -----------------------------------------------------------------------------
# Nasdaq OMX Copenhagen - Denmark, DKK, ~$600 billion
# Suffix: .CO
# -----------------------------------------------------------------------------
COPENHAGEN_STOCKS = [
    "NOVO-B.CO",  # Novo Nordisk
    "MAERSK-B.CO",# A.P. Moller-Maersk
    "DSV.CO",     # DSV
    "ORSTED.CO",  # Ørsted
    "CARL-B.CO",  # Carlsberg
    "VWS.CO",     # Vestas Wind
    "COLO-B.CO",  # Coloplast
    "PNDORA.CO",  # Pandora
    "GN.CO",      # GN Store Nord
    "TRYG.CO",    # Tryg
    "DNORD.CO",   # Danske Bank
    "FLS.CO",     # FLSmidth
]

# -----------------------------------------------------------------------------
# Nasdaq OMX Helsinki - Finland, EUR, ~$300 billion
# Suffix: .HE
# -----------------------------------------------------------------------------
HELSINKI_STOCKS = [
    "NOKIA.HE",   # Nokia
    "NESTE.HE",   # Neste
    "KNEBV.HE",   # Kone
    "FORTUM.HE",  # Fortum
    "SAMPO.HE",   # Sampo
    "UPM.HE",     # UPM-Kymmene
    "STERV.HE",   # Stora Enso
    "ELISA.HE",   # Elisa
    "TIETO.HE",   # TietoEVRY
    "METSO.HE",   # Metso
    "WRTBV.HE",   # Wartsila
    "ORION.HE",   # Orion
    "KEMIRA.HE",  # Kemira
    "OUT1V.HE",   # Outokumpu
    "SSABBH.HE",  # SSAB
    "CGCBV.HE",   # Cargotec
    "RAIVV.HE",   # Raisio
    "HUH1V.HE",   # Huhtamaki
    "ANORA.HE",   # Anora Group
    "PIHLIS.HE",  # Pihlajalinna
]

# -----------------------------------------------------------------------------
# Nasdaq OMX Stockholm - Sweden, SEK, ~$900 billion
# Suffix: .ST
# -----------------------------------------------------------------------------
STOCKHOLM_STOCKS = [
    "VOLV-B.ST",  # Volvo
    "HM-B.ST",    # H&M
    "ASSA-B.ST",  # Assa Abloy
    "ATCO-A.ST",  # Atlas Copco
    "SEB-A.ST",   # SEB
    "SWED-A.ST",  # Swedbank
    "SHB-A.ST",   # Svenska Handelsbanken
    "ERIC-B.ST",  # Ericsson
    "SAND.ST",    # Sandvik
    "SKA-B.ST",   # Skanska
    "TEL2-B.ST",  # Tele2
    "INVE-B.ST",  # Investor
    "ALFA.ST",    # Alfa Laval
    "HEXA-B.ST",  # Hexagon
]

# -----------------------------------------------------------------------------
# Oslo Stock Exchange - Norway, NOK, ~$350 billion
# Suffix: .OL
# -----------------------------------------------------------------------------
OSLO_STOCKS = [
    "EQNR.OL",    # Equinor
    "TEL.OL",     # Telenor
    "DNB.OL",     # DNB
    "MOWI.OL",    # Mowi
    "ORK.OL",     # Orkla
    "YAR.OL",     # Yara International
    "NHY.OL",     # Norsk Hydro
    "SALM.OL",    # SalMar
    "AKRBP.OL",   # Aker BP
    "TGS.OL",     # TGS-NOPEC
    "SUBC.OL",    # Subsea 7
    "STB.OL",     # Storebrand
]

# -----------------------------------------------------------------------------
# Prague Stock Exchange - Czech Republic, CZK, ~$60 billion
# Suffix: .PR
# -----------------------------------------------------------------------------
PRAGUE_STOCKS = [
    "CEZ.PR",     # CEZ Group
    "KOMB.PR",    # Komercni banka
    "MONET.PR",   # MONETA Money Bank
    "ERSTE.PR",   # Erste Group Bank
    "TABAK.PR",   # Philip Morris ČR
    "VIG.PR",     # Vienna Insurance Group
    "NOKIS.PR",   # Nokia (Prague listing)
    "CETV.PR",    # Central European Media Enterprises
    "DIGI.PR",    # DIGI Communications
    "RBAG.PR",    # Raiffeisen Bank International (Prague listing)
    "O2C.PR",     # O2 Czech Republic
    "AVST.PR",    # Avast
    "KOFOLA.PR",  # Kofola CeskoSlovensko
    "FOREG.PR",   # Fortuna Entertainment Group
    "PEGAS.PR",   # Pegas Nonwovens
]

# -----------------------------------------------------------------------------
# Warsaw Stock Exchange (GPW) - Poland, PLN, ~$180 billion
# Suffix: .WA
# -----------------------------------------------------------------------------
WARSAW_STOCKS = [
    "PKN.WA",     # PKN Orlen
    "PKO.WA",     # PKO Bank Polski
    "PZU.WA",     # PZU
    "PEO.WA",     # Bank Pekao
    "KGH.WA",     # KGHM Polska Miedz
    "PGE.WA",     # PGE Polska Grupa Energetyczna
    "LPP.WA",     # LPP
    "CDR.WA",     # CD Projekt
    "ALR.WA",     # Alior Bank
    "DNP.WA",     # Dino Polska
    "CPS.WA",     # Cyfrowy Polsat
    "SPL.WA",     # Santander Bank Polska
    "MBK.WA",     # mBank
]

# -----------------------------------------------------------------------------
# Budapest Stock Exchange - Hungary, HUF, ~$45 billion
# Suffix: .BD
# -----------------------------------------------------------------------------
BUDAPEST_STOCKS = [
    "OTP.BD",     # OTP Bank
    "MTELEKOM.BD",# Magyar Telekom
    "RICHTER.BD", # Gedeon Richter
    "MOL.BD",     # MOL Group
    "OPUS.BD",    # OPUS Global
    "PANNERGY.BD",# Pannergy
    "EGERVIN.BD", # Egervin Borgazdasagi ZRt
    "KONZUM.BD",  # Konzum SE
    "MASTERPLAST.BD", # Masterplast
    "DUNA.BD",    # Duna House Holding
    "MEGAKABEL.BD",   # Megakabel
    "APPENINN.BD",    # Appeninn Holding
    "ESTMEDIA.BD",    # Estmedia
    "GRAPHISOFT.BD",  # Graphisoft Park
    "LIQTECH.BD",     # LiqTech International
]

# -----------------------------------------------------------------------------
# Bucharest Stock Exchange (BVB) - Romania, RON, ~$50 billion
# Suffix: .RO
# -----------------------------------------------------------------------------
BUCHAREST_STOCKS = [
    "TLV.RO",     # Banca Transilvania
    "SNP.RO",     # OMV Petrom
    "SNG.RO",     # Romgaz
    "FP.RO",      # Fondul Proprietatea
    "BRD.RO",     # BRD-Groupe Societe Generale
    "TGN.RO",     # Transgaz
    "TEL.RO",     # Transelectrica
    "EL.RO",      # Electrica
    "H2O.RO",     # Hidroelectrica
    "ONE.RO",     # One United Properties
    "SFG.RO",     # Sphera Franchise Group
    "DIGI.RO",    # DIGI Communications
    "M.RO",       # MedLife
    "AQ.RO",      # Aquila Part Prod Com
    "EVER.RO",    # Evergent Investments
    "BVB.RO",     # Bursa de Valori Bucuresti
]

# -----------------------------------------------------------------------------
# Athens Stock Exchange (ATHEX) - Greece, EUR, ~$65 billion
# Suffix: .AT
# -----------------------------------------------------------------------------
ATHENS_STOCKS = [
    "ETE.AT",     # National Bank of Greece
    "OPAP.AT",    # OPAP
    "HTO.AT",     # Hellenic Telecommunications
    "EEE.AT",     # Public Power Corporation
    "ALPHA.AT",   # Alpha Bank
    "EUROB.AT",   # Eurobank Ergasias
    "PEIR.AT",    # Piraeus Bank
    "TENERGY.AT", # Terna Energy
    "MYTIL.AT",   # Mytilineos
    "EXAE.AT",    # Athens Stock Exchange
    "TITC.AT",    # Titan Cement
    "AEGN.AT",    # Aegean Airlines
    "LAMDA.AT",   # Lamda Development
    "INKAT.AT",   # Intracom
    "ELPE.AT",    # Hellenic Petroleum
    "GEK.AT",     # GEK Terna
    "BYXAR.AT",   # Byte Computer
    "MEVA.AT",    # Motor Oil
    "EYDAP.AT",   # Athens Water & Sewage
    "ΕΛΛΑΚΤΩΡ.AT",# Ellaktor
]

# -----------------------------------------------------------------------------
# Nasdaq OMX Iceland - Iceland, ISK, ~$25 billion
# Suffix: .IC
# -----------------------------------------------------------------------------
ICELAND_STOCKS = [
    "ICEAIR.IC",  # Icelandair Group
    "MAREL.IC",   # Marel
    "ARION.IC",   # Arion Bank
    "ISBK.IC",    # Islandsbanki
    "HAGA.IC",    # Hagar
    "SIMINN.IC",  # Síminn
    "BRIM.IC",    # Brim HF
    "KVIKA.IC",   # Kvika Bank
    "NGSF.IC",    # N1 / Orka Naturuorku
    "EIM.IC",     # Eimskipafelag Islands
    "SJOVA.IC",   # Sjova Insurance
    "VIS.IC",     # Vis Insurance
]

# -----------------------------------------------------------------------------
# Nasdaq OMX Riga - Latvia, EUR, ~$4 billion
# Suffix: .RG
# -----------------------------------------------------------------------------
RIGA_STOCKS = [
    "OLF1R.RG",   # Olainfarm
    "GRD1R.RG",   # Grindeks
    "SAF1R.RG",   # SAF Tehnika
    "BAL1R.RG",   # Baltika Group
    "DPK1R.RG",   # Ditton Pievadkezu Rupnica
    "ACB1R.RG",   # Akciju Komercbanka Baltikums
    "GZE1R.RG",   # Latvijas Gaze
    "LME1R.RG",   # Latvijas Mezu Ipasnieku Savieniba
    "VNF1R.RG",   # Ventspils Nafta
    "RKB1R.RG",   # Rietumu Banka
]

# -----------------------------------------------------------------------------
# Nasdaq OMX Vilnius - Lithuania, EUR, ~$6 billion
# Suffix: .VS
# -----------------------------------------------------------------------------
VILNIUS_STOCKS = [
    "TEO1L.VS",   # Telia Lietuva
    "SNG1L.VS",   # SNAIGE
    "APG1L.VS",   # Apranga Group
    "IVL1L.VS",   # Invalda INVL
    "GRG1L.VS",   # Grigeo
    "LGD1L.VS",   # Litgrid
    "PIK1L.VS",   # Pieno Zvaigzdes
    "KNF1L.VS",   # Klaipedos Nafta
    "ZMP1L.VS",   # Zemaiciu Keliai
    "LIAP.VS",    # Linas Agro Group
    "SAB1L.VS",   # Siauliu Bankas
    "VBL1L.VS",   # Vilniaus Baldai
    "CITY1L.VS",  # City Service
]

# -----------------------------------------------------------------------------
# Nasdaq OMX Tallinn - Estonia, EUR, ~$5 billion
# Suffix: .TL
# -----------------------------------------------------------------------------
TALLINN_STOCKS = [
    "TAL1T.TL",   # Tallink Grupp
    "MRK1T.TL",   # Merko Ehitus
    "TKM1T.TL",   # Tallinna Kaubamaja
    "EEG1T.TL",   # Enefit Green
    "PRF1T.TL",   # PRFoods
    "LHV1T.TL",   # LHV Group
    "TVEAT.TL",   # Tallinna Vesi
    "EFT1T.TL",   # Ekspress Grupp
    "ARC1T.TL",   # Arco Vara
    "NCN1T.TL",   # Nordecon
    "VEG1T.TL",   # Latvijas Fierieru
    "SKN1T.TL",   # Skano Group
]

# -----------------------------------------------------------------------------
# Madrid Stock Exchange (BME) - Spain, EUR, ~$600 billion
# Suffix: .MC
# -----------------------------------------------------------------------------
MADRID_STOCKS = [
    "SAN.MC",     # Banco Santander
    "BBVA.MC",    # BBVA
    "ITX.MC",     # Inditex
    "IBE.MC",     # Iberdrola
    "TEF.MC",     # Telefonica
    "REP.MC",     # Repsol
    "CABK.MC",    # CaixaBank
    "FER.MC",     # Ferrovial
    "AMS.MC",     # Amadeus IT
    "CLNX.MC",    # Cellnex Telecom
    "IAG.MC",     # International Airlines Group
    "ENG.MC",     # Enagas
    "REE.MC",     # Red Electrica
    "GRF.MC",     # Grifols
    "ACS.MC",     # ACS
    "MAP.MC",     # MAPFRE
]

# -----------------------------------------------------------------------------
# Borsa Istanbul - Turkey, TRY, ~$200 billion
# Suffix: .IS
# -----------------------------------------------------------------------------
ISTANBUL_STOCKS = [
    "THYAO.IS",   # Turkish Airlines
    "GARAN.IS",   # Garanti BBVA
    "AKBNK.IS",   # Akbank
    "YKBNK.IS",   # Yapi Kredi Bank
    "EREGL.IS",   # Erdemir
    "KCHOL.IS",   # Koc Holding
    "SAHOL.IS",   # Sabanci Holding
    "BIMAS.IS",   # BIM Magazalar
    "TUPRS.IS",   # Tupras
    "ASELS.IS",   # ASELSAN
    "PETKM.IS",   # Petkim
    "SISE.IS",    # Sisecam
    "TTKOM.IS",   # Turk Telekom
    "TCELL.IS",   # Turkcell
    "ARCLK.IS",   # Arcelik
]

# -----------------------------------------------------------------------------
# Buenos Aires Stock Exchange (BYMA) - Argentina, ARS, ~$60 billion
# Suffix: .BA
# -----------------------------------------------------------------------------
BUENOS_AIRES_STOCKS = [
    "GGAL.BA",    # Grupo Financiero Galicia
    "YPF.BA",     # YPF
    "BMA.BA",     # Banco Macro
    "PAMP.BA",    # Pampa Energia
    "BBAR.BA",    # BBVA Argentina
    "TECO2.BA",   # Telecom Argentina
    "CEPU.BA",    # Central Puerto
    "SUPV.BA",    # Grupo Supervielle
    "TXAR.BA",    # Ternium Argentina
    "ALUA.BA",    # Aluar Aluminio
    "CRES.BA",    # Banco de Credito y Securitizacion
    "HARG.BA",    # Holcim Argentina
    "IRSA.BA",    # IRSA Inversiones
    "LEDE.BA",    # Ledesma
    "MOLI.BA",    # Molinos Rio de la Plata
    "POLL.BA",    # Polledo
    "RICH.BA",    # Laboratorios Richmond
    "TGNO4.BA",   # Transportadora Gas del Norte
    "TGSU2.BA",   # Transportadora Gas del Sur
    "VALO.BA",    # Grupo Supervielle
]

# -----------------------------------------------------------------------------
# Santiago Stock Exchange - Chile, CLP, ~$200 billion
# Suffix: .SN
# -----------------------------------------------------------------------------
SANTIAGO_STOCKS = [
    "FALABELLA.SN",  # Falabella
    "CMPC.SN",       # Empresas CMPC
    "CENCOSUD.SN",   # Cencosud
    "SQM-B.SN",      # SQM
    "BSANTANDER.SN", # Banco Santander Chile
    "COPEC.SN",      # Empresas Copec
    "CHILE.SN",      # Banco de Chile
    "CCU.SN",        # CCU
    "ENELAM.SN",     # Enel Americas
    "COLBUN.SN",     # Colbun
    "BCHILE.SN",     # Banco de Chile (alt)
    "AGUAS-A.SN",    # Aguas Andinas
    "ITAUCORP.SN",   # Itaúsa
    "LTM.SN",        # LATAM Airlines Group
    "PARAUCO.SN",    # Parque Arauco
    "RIPLEY.SN",     # Ripley Corp
    "SMSAAM.SN",     # Soc. Minera El Indio
    "ENELCHILE.SN",  # Enel Chile
    "CAP.SN",        # CAP
    "BESALCO.SN",    # Besalco
]

# -----------------------------------------------------------------------------
# Colombia Stock Exchange (BVC) - Colombia, COP, ~$130 billion
# Suffix: .CL
# -----------------------------------------------------------------------------
COLOMBIA_STOCKS = [
    "PFBCOLOM.CL",   # Bancolombia
    "ECOPETROL.CL",  # Ecopetrol
    "GRUPOARGOS.CL", # Grupo Argos
    "ISA.CL",        # Interconexion Electrica
    "NUTRESA.CL",    # Grupo Nutresa
    "GRUPOSURA.CL",  # Grupo Sura
    "CELSIA.CL",     # Celsia
    "CEMARGOS.CL",   # Cementos Argos
]

# -----------------------------------------------------------------------------
# Ho Chi Minh Stock Exchange (HOSE) - Vietnam, VND, ~$180 billion
# Suffix: .VN
# -----------------------------------------------------------------------------
VIETNAM_STOCKS = [
    "VNM.VN",     # Vinamilk
    "VIC.VN",     # Vingroup
    "VHM.VN",     # Vinhomes
    "VCB.VN",     # Vietcombank
    "BID.VN",     # BIDV
    "CTG.VN",     # VietinBank
    "GAS.VN",     # PV Gas
    "SAB.VN",     # Sabeco
    "HPG.VN",     # Hoa Phat Group
    "MWG.VN",     # Mobile World
    "VRE.VN",     # Vincom Retail
    "PLX.VN",     # Petrolimex
    "FPT.VN",     # FPT Corporation
    "MBB.VN",     # MB Bank
    "MSN.VN",     # Masan Group
]

# -----------------------------------------------------------------------------
# Philippine Stock Exchange (PSE) - Philippines, PHP, ~$250 billion
# Suffix: .PS
# -----------------------------------------------------------------------------
PHILIPPINES_STOCKS = [
    "SM.PS",      # SM Investments
    "BDO.PS",     # BDO Unibank
    "ALI.PS",     # Ayala Land
    "AC.PS",      # Ayala Corporation
    "JFC.PS",     # Jollibee Foods
    "TEL.PS",     # PLDT
    "BPI.PS",     # Bank of Philippine Islands
    "MBT.PS",     # Metropolitan Bank & Trust
    "URC.PS",     # Universal Robina
    "GLO.PS",     # Globe Telecom
    "SMPH.PS",    # SM Prime Holdings
    "ICT.PS",     # International Container Terminal
    "MER.PS",     # Meralco
    "GTCAP.PS",   # GT Capital Holdings
]

# -----------------------------------------------------------------------------
# Euronext Dublin - Ireland, EUR, ~$100 billion
# Suffix: .IR
# -----------------------------------------------------------------------------
DUBLIN_STOCKS = [
    "RYA.IR",     # Ryanair
    "CRH.IR",     # CRH
    "AIB.IR",     # AIB Group
    "BIRG.IR",    # Bank of Ireland
    "KRX.IR",     # Kingspan Group
    "SMUR.IR",    # Smurfit Kappa
    "FL.IR",      # Flutter Entertainment
    "GLV.IR",     # Glanbia
    "ICAD.IR",    # Independent News & Media
    "FBD.IR",     # FBD Holdings
    "ICP.IR",     # Interceptor Pharmaceuticals
    "ORK.IR",     # Origin Enterprises
    "TPVG.IR",    # Total Produce
    "CPH2.IR",    # C&C Group
    "NWL.IR",     # Newpark Resources
    "AGN.IR",     # Aryzta
    "IPO.IR",     # Irish Continental Group
    "DHG.IR",     # Dalata Hotel Group
    "INM.IR",     # Independent News & Media
    "LRG.IR",     # Laird plc
]

# -----------------------------------------------------------------------------
# Euronext Lisbon - Portugal, EUR, ~$75 billion
# Suffix: .LS
# -----------------------------------------------------------------------------
LISBON_STOCKS = [
    "EDP.LS",     # EDP Energias
    "GALP.LS",    # Galp Energia
    "JMT.LS",     # Jeronimo Martins
    "BCP.LS",     # Banco Comercial Portugues
    "SON.LS",     # Sonae
    "NOS.LS",     # NOS SGPS
    "ALTR.LS",    # Altri
    "EGL.LS",     # Mota-Engil
    "RENE.LS",    # REN
    "CTT.LS",     # CTT
    "EDPR.LS",    # EDP Renovaveis
    "RAMA.LS",    # Ramada Investimentos
    "CFN.LS",     # Cofina
    "MDSO.LS",    # Mediobanca
    "SVNB.LS",    # Navigator Company
    "IPBR.LS",    # Pharol SGPS
    "THRE.LS",    # Teixeira Duarte
    "SLBEN.LS",   # Sport Lisboa e Benfica
    "BVLG.LS",    # Bolsas e Mercados
    "EDIA.LS",    # Empresa de Desenvolvimento
]

# =============================================================================
# Combined Lists for Easy Access
# =============================================================================

# All US Stocks (NYSE + NASDAQ)
DEFAULT_STOCKS = list(set(NYSE_STOCKS + NASDAQ_STOCKS))

# All Indian Stocks (NSE + BSE unique ones)
DEFAULT_INDIAN_STOCKS = NSE_INDIA_STOCKS

# Keep backward compatibility
DEFAULT_INDIAN_INDICES = [
    "^NSEI",          # Nifty 50
    "^BSESN",         # BSE Sensex
    "^NSEBANK",       # Nifty Bank
    "^CNXIT",         # Nifty IT
]

DEFAULT_CRYPTO = [
    # ── Tier 1: Top 30 by Market Cap (all major exchanges) ───────────────────
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
    "ADA/USDT", "DOGE/USDT", "TRX/USDT", "AVAX/USDT", "SHIB/USDT",
    "DOT/USDT", "LINK/USDT", "TON/USDT", "MATIC/USDT", "BCH/USDT",
    "LTC/USDT", "NEAR/USDT", "UNI/USDT", "XLM/USDT", "ATOM/USDT",
    "APT/USDT", "SUI/USDT", "HBAR/USDT", "ARB/USDT", "OP/USDT",
    "INJ/USDT", "ICP/USDT", "FIL/USDT", "KAS/USDT", "STX/USDT",

    # ── Tier 2: Top DeFi Protocols ────────────────────────────────────────────
    "AAVE/USDT", "MKR/USDT", "SNX/USDT", "CRV/USDT", "LDO/USDT",
    "COMP/USDT", "SUSHI/USDT", "1INCH/USDT", "YFI/USDT", "BAL/USDT",
    "FXS/USDT", "CAKE/USDT", "GMX/USDT", "DYDX/USDT", "PENDLE/USDT",
    "RDNT/USDT", "SSV/USDT", "RPL/USDT", "ENA/USDT", "ETHFI/USDT",
    "JUP/USDT", "RAY/USDT", "ORCA/USDT", "DRIFT/USDT", "PYTH/USDT",
    "JTO/USDT", "W/USDT", "ZEUS/USDT", "BONK/USDT", "WIF/USDT",

    # ── Tier 3: Layer 1 & Layer 2 Blockchains ────────────────────────────────
    "SEI/USDT", "FTM/USDT", "ALGO/USDT", "VET/USDT", "EOS/USDT",
    "IMX/USDT", "MANTA/USDT", "EGLD/USDT", "XTZ/USDT", "THETA/USDT",
    "STRK/USDT", "ZK/USDT", "ALT/USDT", "ZETA/USDT", "TIA/USDT",
    "BLAST/USDT", "MERLIN/USDT", "SCROLL/USDT", "LINEA/USDT", "MODE/USDT",
    "ZRO/USDT", "TAIKO/USDT", "METIS/USDT", "BOBA/USDT", "CELR/USDT",
    "ROSE/USDT", "KAVA/USDT", "CANTO/USDT", "EVMOS/USDT", "NEON/USDT",
    "OSMO/USDT", "JUNO/USDT", "SCRT/USDT", "IRIS/USDT", "BAND/USDT",
    "CKB/USDT", "IOTX/USDT", "ONE/USDT", "CELO/USDT", "CLV/USDT",
    "OKT/USDT", "KSM/USDT", "GLMR/USDT", "MOVR/USDT", "ASTR/USDT",
    "SGB/USDT", "CFX/USDT", "BTTC/USDT", "WIN/USDT", "SUN/USDT",

    # ── Tier 4: AI / Web3 Infrastructure ─────────────────────────────────────
    "RNDR/USDT", "FET/USDT", "AGIX/USDT", "OCEAN/USDT", "GRT/USDT",
    "TAO/USDT", "WLD/USDT", "ARKM/USDT", "NMR/USDT", "PAAL/USDT",
    "CGPT/USDT", "AIOZ/USDT", "PRIME/USDT", "0X0/USDT", "MYRIA/USDT",
    "AKT/USDT", "IO/USDT", "ATH/USDT", "GRASS/USDT", "NTRN/USDT",

    # ── Tier 5: Gaming, NFT & Metaverse ──────────────────────────────────────
    "AXS/USDT", "SAND/USDT", "MANA/USDT", "ENJ/USDT", "GALA/USDT",
    "ILV/USDT", "ALICE/USDT", "YGG/USDT", "APE/USDT", "GODS/USDT",
    "PIXEL/USDT", "PORTAL/USDT", "BEAM/USDT", "MAGIC/USDT", "TRB/USDT",
    "RONIN/USDT", "SLP/USDT", "LOKA/USDT", "PYR/USDT", "GHST/USDT",
    "AURORA/USDT", "SIDUS/USDT", "HERO/USDT", "BICO/USDT", "XETA/USDT",

    # ── Tier 6: Meme Coins (high volume, high volatility) ────────────────────
    "PEPE/USDT", "FLOKI/USDT", "MEME/USDT", "LUNC/USDT", "BABYDOGE/USDT",
    "NOT/USDT", "DOGS/USDT", "HMSTR/USDT", "CATI/USDT", "MAJOR/USDT",
    "BOME/USDT", "SLERF/USDT", "POPCAT/USDT", "MEW/USDT", "BRETT/USDT",
    "NEIRO/USDT", "MOG/USDT", "TURBO/USDT", "GIGA/USDT", "PNUT/USDT",
    "ACT/USDT", "GOAT/USDT", "MOODENG/USDT", "PONKE/USDT", "KMNO/USDT",

    # ── Tier 7: Exchange Tokens ───────────────────────────────────────────────
    "BGB/USDT", "OKB/USDT", "CRO/USDT", "LEO/USDT", "KCS/USDT",
    "GT/USDT", "MX/USDT", "HT/USDT", "FTT/USDT", "WOO/USDT",
    "BNX/USDT", "VELO/USDT",

    # ── Tier 8: Real World Assets (RWA) ──────────────────────────────────────
    "ONDO/USDT", "CFG/USDT", "MPL/USDT", "POLYX/USDT", "RIO/USDT",
    "CPOOL/USDT", "GFI/USDT", "TRADE/USDT", "PROPS/USDT",

    # ── Tier 9: Privacy Coins ────────────────────────────────────────────────
    "XMR/USDT", "ZEC/USDT", "DASH/USDT", "SCRT/USDT", "DUSK/USDT",

    # ── Tier 10: Infrastructure (Storage, Oracle, Bridge) ────────────────────
    "AR/USDT", "STORJ/USDT", "SC/USDT", "BTT/USDT", "HOT/USDT",
    "API3/USDT", "TLM/USDT", "RUNE/USDT", "WAXP/USDT", "LRC/USDT",
    "CELR/USDT", "SKL/USDT", "OMG/USDT", "DENT/USDT", "CHZ/USDT",
    "CHR/USDT", "CTSI/USDT", "PLA/USDT", "AUDIO/USDT", "RAD/USDT",

    # ── Tier 11: Bitcoin Ecosystem ───────────────────────────────────────────
    "ORDI/USDT", "SATS/USDT", "RATS/USDT", "TURT/USDT", "RUNE/USDT",

    # ── Tier 12: Staking / Liquid Staking ────────────────────────────────────
    "STETH/USDT", "RETH/USDT", "CBETH/USDT", "ANKR/USDT", "SWISE/USDT",
    "LSETH/USDT", "FRXETH/USDT", "PSTAKE/USDT", "QETH/USDT",

    # ── Tier 13: Base / Coinbase Ecosystem ───────────────────────────────────
    "TOSHI/USDT", "BALD/USDT", "AERC/USDT",

    # ── Tier 14: Polkadot Ecosystem ──────────────────────────────────────────
    "PARA/USDT", "PHA/USDT", "AZERO/USDT", "NODL/USDT",

    # ── Tier 15: Cosmos Ecosystem ─────────────────────────────────────────────
    "OSMO/USDT", "JUNO/USDT", "STARS/USDT", "EVMOS/USDT", "STRD/USDT",
    "HUAHUA/USDT", "CMDX/USDT",

    # ── Tier 16: Stablecoins & Yield ─────────────────────────────────────────
    "USDC/USDT", "DAI/USDT", "FRAX/USDT", "LUSD/USDT", "CRVUSD/USDT",

    # ── Tier 17: Newer / Trending (2025) ─────────────────────────────────────
    "LISTA/USDT", "TOKEN/USDT", "REZ/USDT", "SAGA/USDT", "OMNI/USDT",
    "MERL/USDT", "REI/USDT", "BB/USDT", "PORTAL/USDT", "AEVO/USDT",
    "MAVIA/USDT", "XAI/USDT", "VANRY/USDT", "NFP/USDT", "AI/USDT",
    "MAV/USDT", "CYBER/USDT", "HOOK/USDT", "COMBO/USDT", "NTRN/USDT",
    "WBETH/USDT", "LAZIO/USDT", "PORTO/USDT", "SANTOS/USDT",
]

# Forex pairs (Mapped to Yahoo Finance tickers)
DEFAULT_FOREX = [
    "EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X", "USDCHF=X",
    "NZDUSD=X", "EURGBP=X", "EURJPY=X", "GBPJPY=X", "USDINR=X", "USDCNY=X",
    "USDHKD=X", "USDSGD=X", "GBPINR=X", "EURINR=X"
]

# Global Indices - Comprehensive coverage of all major exchanges
DEFAULT_INDICES = [
    # US
    "^GSPC",      # S&P 500
    "^DJI",       # Dow Jones Industrial Average
    "^IXIC",      # NASDAQ Composite
    "^RUT",       # Russell 2000
    "^VIX",       # CBOE Volatility Index
    "^NDX",       # NASDAQ 100
    
    # India (Sensex)
    "^BSESN",     # BSE Sensex
    "^NSEI",      # NIFTY 50
    "^NSEBANK",   # NIFTY Bank
    "^CNXIT",     # NIFTY IT
    
    # UK & Europe
    "^FTSE",      # FTSE 100 (UK)
    "^GDAXI",     # DAX 40 (Germany)
    "^FCHI",      # CAC 40 (France)
    "^STOXX50E",  # Euro Stoxx 50
    "^AEX",       # AEX (Netherlands)
    "^IBEX",      # IBEX 35 (Spain)
    "^SSMI",      # SMI (Switzerland)
    "^ATX",       # ATX (Austria)
    "^BFX",       # BEL 20 (Belgium)
    "^PSI20",     # PSI 20 (Portugal)
    "^FTSEMIB.MI", # FTSE MIB (Italy)
    
    # Nordics
    "^OMXC25",    # OMX Copenhagen 25
    "^OMXS30",    # OMX Stockholm 30
    "^OMXH25",    # OMX Helsinki 25
    "^OSEAX",     # Oslo All-Share
    "^OMXI10.IC", # Iceland OMXI 10
    
    # Eastern Europe
    "^WIG20",     # WIG 20 (Poland)
    "^BUX",       # BUX (Hungary)
    "^PX",        # PX (Czech Republic)
    "^BET.RO",    # BET (Romania)
    "^ATG.AT",    # Athex (Greece)
    "^XU100.IS",  # BIST 100 (Turkey)
    
    # Asia Pacific
    "^N225",      # Nikkei 225 (Japan)
    "^HSI",       # Hang Seng (Hong Kong)
    "000001.SS",  # Shanghai Composite
    "399001.SZ",  # Shenzhen Component
    "^KS11",      # KOSPI (Korea)
    "^KQ11",      # KOSDAQ (Korea)
    "^TWII",      # TAIEX (Taiwan)
    "^STI",       # STI (Singapore)
    "^AORD",      # All Ordinaries (Australia)
    "^AXJO",      # S&P/ASX 200 (Australia)
    "^NZ50",      # NZX 50 (New Zealand)
    "^JKSE",      # Jakarta Composite (Indonesia)
    "^SET.BK",    # SET Index (Thailand)
    "^KLSE",      # KLCI (Malaysia)
    "^PSEI",      # PSEi (Philippines)
    "VN30.VN",    # VN30 (Vietnam)
    
    # Canada
    "^GSPTSE",    # S&P/TSX Composite
    "^GSPTSE60",  # S&P/TSX 60
    
    # Latin America
    "^BVSP",      # Bovespa (Brazil)
    "^MXX",       # IPC (Mexico)
    "^MERVAL",    # Merval (Argentina)
    "^IPSA",      # IPSA (Chile)
    "^COLCAP",    # COLCAP (Colombia)
    
    # Middle East & Africa
    "^TASI.SR",   # Tadawul All Share (Saudi)
    "^DFMGI",     # DFM General Index (Dubai)
    "^ADI",       # ADX General Index (Abu Dhabi)
    "^QSI",       # Qatar All Share
    "^TA125.TA",  # TA-125 (Israel)
    "^EGX30",     # EGX 30 (Egypt)
    "^J200.JO",   # JSE Top 40 (South Africa)
]


# Commodities (Gold, Silver, Oil, etc.)
DEFAULT_COMMODITIES = [
    "GC=F",   # Gold Futures
    "SI=F",   # Silver Futures  
    "CL=F",   # Crude Oil WTI
    "BZ=F",   # Brent Crude Oil
    "NG=F",   # Natural Gas
    "HG=F",   # Copper
    "PL=F",   # Platinum
    "PA=F",   # Palladium
    "ZC=F",   # Corn
    "ZW=F",   # Wheat
]

# Data fetch settings
STOCK_PERIOD = "5y"  # Increased to 5 years for better model training
CRYPTO_TIMEFRAME = "1d"
CRYPTO_LIMIT = 1825  # ~5 years of daily data
