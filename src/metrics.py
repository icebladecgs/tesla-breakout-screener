# ============================================================
# metrics.py  –  Reaction analysis, correlation, beta, setup score
# ============================================================

import pandas as pd
import numpy as np
from scipy import stats

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import config


# ────────────────────────────────────────────────────────────
# 1. Forward-return reaction after TSLA events
# ────────────────────────────────────────────────────────────

def _forward_return(close: pd.Series, date, window: int) -> float | None:
    """Return from `date` close to `date + window` bars close."""
    try:
        idx = close.index.get_loc(date)
    except KeyError:
        return None
    future_idx = idx + window
    if future_idx >= len(close):
        return None
    return close.iloc[future_idx] / close.iloc[idx] - 1


def compute_event_reactions(ticker_close: pd.Series,
                             tsla_close: pd.Series,
                             event_dates: pd.DatetimeIndex,
                             windows: list[int] = config.FORWARD_WINDOWS
                             ) -> pd.DataFrame:
    """
    For each event date, compute forward returns for ticker and TSLA.
    Returns a DataFrame rows=event_dates, cols=window labels.
    """
    records = []
    for d in event_dates:
        row = {"date": d}
        for w in windows:
            t_ret  = _forward_return(ticker_close, d, w)
            ts_ret = _forward_return(tsla_close,   d, w)
            row[f"ticker_{w}d"]  = t_ret
            row[f"tsla_{w}d"]    = ts_ret
            if t_ret is not None and ts_ret is not None:
                row[f"excess_{w}d"] = t_ret - ts_ret
            else:
                row[f"excess_{w}d"] = None
        records.append(row)
    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records).set_index("date")


def summarise_reactions(reactions: pd.DataFrame,
                        windows: list[int] = config.FORWARD_WINDOWS) -> dict:
    """Aggregate reaction stats across all event dates."""
    summary = {}
    for w in windows:
        ticker_col = f"ticker_{w}d"
        excess_col = f"excess_{w}d"
        if ticker_col not in reactions.columns:
            continue
        series = reactions[ticker_col].dropna()
        excess = reactions[excess_col].dropna()
        summary[f"avg_return_{w}d"]      = series.mean()
        summary[f"max_return_{w}d"]      = series.max()
        summary[f"win_rate_{w}d"]        = (series > 0).mean()
        summary[f"avg_excess_{w}d"]      = excess.mean()
        summary[f"outperform_rate_{w}d"] = (excess > 0).mean()
        summary[f"n_events_{w}d"]        = len(series)
    return summary


# ────────────────────────────────────────────────────────────
# 2. Correlation & Beta
# ────────────────────────────────────────────────────────────

def compute_correlation(ticker_close: pd.Series,
                         tsla_close: pd.Series,
                         windows: list[int] = config.CORR_WINDOWS) -> dict:
    """Rolling correlation at the END of the series (current snapshot)."""
    t_ret  = ticker_close.pct_change().dropna()
    ts_ret = tsla_close.pct_change().dropna()
    aligned = pd.concat([t_ret, ts_ret], axis=1, join="inner")
    aligned.columns = ["ticker", "tsla"]

    result = {}
    for w in windows:
        if len(aligned) >= w:
            window_data = aligned.tail(w)
            result[f"corr_{w}d"] = window_data["ticker"].corr(window_data["tsla"])
        else:
            result[f"corr_{w}d"] = np.nan
    return result


def compute_beta(ticker_close: pd.Series,
                  tsla_close: pd.Series,
                  window: int = 120) -> float:
    """OLS beta of ticker returns vs TSLA returns over last `window` days."""
    t_ret  = ticker_close.pct_change().dropna()
    ts_ret = tsla_close.pct_change().dropna()
    aligned = pd.concat([t_ret, ts_ret], axis=1, join="inner").tail(window).dropna()
    if len(aligned) < 20:
        return np.nan
    slope, *_ = stats.linregress(aligned.iloc[:, 1], aligned.iloc[:, 0])
    return slope


# ────────────────────────────────────────────────────────────
# 3. Technical Setup Score
# ────────────────────────────────────────────────────────────

def _rsi(close: pd.Series, period: int = 14) -> float:
    delta = close.diff().dropna()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, np.nan)
    rsi   = 100 - 100 / (1 + rs)
    return rsi.iloc[-1]


def compute_setup_score(df: pd.DataFrame) -> dict:
    """
    Calculates technical setup metrics and returns a 0-100 setup score.

    Components:
      - 52-week drawdown  (lower drawdown = better, max 25 pts)
      - Price vs MA20     (above MA20 = positive momentum, max 20 pts)
      - Price vs MA60     (above MA60 = trend confirmation, max 20 pts)
      - Volume surge      (recent avg vol vs 60d avg, max 20 pts)
      - RSI zone          (40-70 sweet-spot, max 15 pts)
    """
    close  = df["Close"].squeeze()
    volume = df["Volume"].squeeze()

    metrics = {}

    # 52-week drawdown
    high_52w = close.rolling(252).max().iloc[-1]
    cur_close = close.iloc[-1]
    drawdown  = (cur_close - high_52w) / high_52w  # negative number
    metrics["drawdown_52w"] = drawdown

    # MA positions
    ma20 = close.rolling(20).mean().iloc[-1]
    ma60 = close.rolling(60).mean().iloc[-1]
    metrics["above_ma20"] = cur_close > ma20
    metrics["above_ma60"] = cur_close > ma60
    metrics["pct_from_ma20"] = (cur_close - ma20) / ma20

    # Volume surge: 5-day avg vs 60-day avg
    vol_5d  = volume.tail(5).mean()
    vol_60d = volume.tail(60).mean()
    metrics["volume_surge"] = vol_5d / vol_60d if vol_60d > 0 else 1.0

    # RSI
    if len(close) >= 20:
        metrics["rsi"] = _rsi(close)
    else:
        metrics["rsi"] = 50.0

    # ── Score calculation ────────────────────────────────────
    score = 0.0

    # Drawdown component (0-25 pts): less drawdown → higher score
    # 0% drawdown = 25, -50% drawdown = 0
    dd_score = max(0, min(25, 25 * (1 + drawdown / 0.50)))
    score += dd_score

    # MA20 (0-20 pts)
    if metrics["above_ma20"]:
        pct = metrics["pct_from_ma20"]
        score += min(20, 10 + pct * 200)   # extra points for strong positioning

    # MA60 (0-20 pts)
    if metrics["above_ma60"]:
        score += 20

    # Volume surge (0-20 pts)
    vol_score = min(20, (metrics["volume_surge"] - 1) * 20)
    score += max(0, vol_score)

    # RSI (0-15 pts): sweet-spot 40-70 = 15 pts, overbought/oversold = 0
    rsi = metrics["rsi"]
    if 40 <= rsi <= 70:
        score += 15
    elif 30 <= rsi < 40 or 70 < rsi <= 80:
        score += 7
    else:
        score += 0

    metrics["setup_score"] = min(100, max(0, score))
    return metrics


# ────────────────────────────────────────────────────────────
# 4. Liquidity Score
# ────────────────────────────────────────────────────────────

def compute_liquidity_score(df: pd.DataFrame,
                             universe_data: dict[str, pd.DataFrame]) -> float:
    """
    Returns 0-100 based on average daily dollar volume relative to universe.
    Uses log-normalisation across the universe.
    """
    adv = (df["Close"].squeeze() * df["Volume"].squeeze()).tail(20).mean()
    return adv  # raw value; normalised later in scoring.py
