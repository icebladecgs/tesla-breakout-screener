# ============================================================
# Tesla Breakout Companion Screener — Configuration
# ============================================================

import os

# ── Data Settings ────────────────────────────────────────────
TSLA_TICKER = "TSLA"
YEARS_HISTORY = 10          # years of historical data to download
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")

# ── Candidate Universe ───────────────────────────────────────
CANDIDATE_TICKERS = [
    # EV Makers
    "RIVN", "LCID", "NIO", "XPEV", "LI", "PSNY", "FSR",
    # Battery / Energy Storage
    "QS", "SLDP", "FREY", "SES", "ENVX",
    # Lithium / Materials
    "ALB", "LAC", "SQM", "PLL", "SLI", "SGML", "MP",
    # Charging Infrastructure
    "CHPT", "BLNK", "EVGO", "WBX",
    # LiDAR / Sensors
    "LAZR", "INVZ", "OUST", "AEVA", "CPTN",
    # Auto Suppliers
    "APTV", "BWA", "MGA", "MBLY",
    # Semiconductors
    "ON", "STM", "NXPI", "TXN", "IFNNY",
    # Solar / Grid
    "ENPH", "SEDG", "FLNC", "STEM",
    # Automation / Robotics
    "PATH", "TER", "SYM",
    # Air Mobility
    "JOBY", "ACHR", "BLDE",
]

# ── Event Detection Thresholds ───────────────────────────────
EVENT_A_WINDOW = 20          # 20-day high breakout
EVENT_B_WINDOW = 120         # 120-day high breakout
EVENT_C_WINDOW = 252         # 52-week high breakout
EVENT_E_RETURN_THRESHOLD = 0.10   # 5-day return > 10%
EVENT_E_DAYS = 5
EVENT_F_VOLUME_MULTIPLIER = 1.5   # volume > 1.5x 20-day avg

# ── Reaction Windows (calendar days after event) ─────────────
FORWARD_WINDOWS = [1, 3, 5, 10, 20]

# ── Correlation Windows ──────────────────────────────────────
CORR_WINDOWS = [60, 120, 250]

# ── Scoring Weights ──────────────────────────────────────────
WEIGHT_AVG_EXCESS_RETURN   = 0.30
WEIGHT_WIN_RATE            = 0.25
WEIGHT_CORRELATION         = 0.20
WEIGHT_SETUP_SCORE         = 0.15
WEIGHT_LIQUIDITY           = 0.10

# ── Auto-trigger thresholds ──────────────────────────────────
AUTO_TRIGGER_5D_RETURN     = 0.08   # 8% in 5 days
AUTO_TRIGGER_20D_HIGH      = True   # AND 20-day high breakout

# ── Telegram Alerts (optional) ──────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")
TELEGRAM_TOP_N     = 5
