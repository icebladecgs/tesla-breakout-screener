# ============================================================
# data_loader.py  –  Download & cache OHLCV data via yfinance
# ============================================================

import os
import pickle
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import config


def _cache_path(ticker: str) -> str:
    try:
        os.makedirs(config.DATA_DIR, exist_ok=True)
        return os.path.join(config.DATA_DIR, f"{ticker}.pkl")
    except OSError:
        # 클라우드 환경 등 쓰기 불가 시 임시 디렉토리 사용
        import tempfile
        return os.path.join(tempfile.gettempdir(), f"tsla_screener_{ticker}.pkl")


def _is_cache_fresh(path: str, max_age_hours: int = 8) -> bool:
    if not os.path.exists(path):
        return False
    try:
        age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(path))
        return age < timedelta(hours=max_age_hours)
    except OSError:
        return False


def load_ticker(ticker: str, years: int = config.YEARS_HISTORY,
                force_refresh: bool = False) -> pd.DataFrame:
    """Return a DataFrame with columns: Open High Low Close Volume Adj Close.

    Data is cached as a pickle in data/ for speed.
    """
    path = _cache_path(ticker)
    if not force_refresh and _is_cache_fresh(path):
        with open(path, "rb") as f:
            return pickle.load(f)

    start = (datetime.now() - timedelta(days=365 * years)).strftime("%Y-%m-%d")
    print(f"  Downloading {ticker} ...", end=" ", flush=True)
    try:
        df = yf.download(ticker, start=start, auto_adjust=True, progress=False)
        if df.empty:
            print("NO DATA")
            return pd.DataFrame()
        # Flatten MultiIndex columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.index = pd.to_datetime(df.index)
        df.sort_index(inplace=True)
        with open(path, "wb") as f:
            pickle.dump(df, f)
        print(f"OK ({len(df)} rows)")
        return df
    except Exception as e:
        print(f"ERROR: {e}")
        return pd.DataFrame()


def load_all(tickers: list[str] = None,
             force_refresh: bool = False) -> dict[str, pd.DataFrame]:
    """Download TSLA + all candidate tickers. Returns {ticker: DataFrame}."""
    if tickers is None:
        tickers = [config.TSLA_TICKER] + config.CANDIDATE_TICKERS
    print("=" * 60)
    print("Loading market data …")
    print("=" * 60)
    data = {}
    for t in tickers:
        df = load_ticker(t, force_refresh=force_refresh)
        if not df.empty:
            data[t] = df
    print(f"\nLoaded {len(data)}/{len(tickers)} tickers successfully.\n")
    return data
