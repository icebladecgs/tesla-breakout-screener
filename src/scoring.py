# ============================================================
# scoring.py  –  Aggregate all metrics into a Total Score
# ============================================================

import numpy as np
import pandas as pd

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import config


def _minmax(series: pd.Series) -> pd.Series:
    """Min-max normalise to [0, 100]. NaN stays NaN."""
    mn, mx = series.min(), series.max()
    if mx == mn:
        return series.map(lambda x: 50.0 if pd.notna(x) else np.nan)
    return (series - mn) / (mx - mn) * 100


def compute_total_scores(results: list[dict]) -> pd.DataFrame:
    """
    Takes a list of per-ticker dicts (output of screener.py) and returns
    a ranked DataFrame with Total_Score.

    Weighting:
      30%  avg_excess_return  (avg excess return over 5D & 10D windows)
      25%  win_rate           (avg win-rate across 5D & 10D windows)
      20%  correlation        (corr_60d)
      15%  setup_score
      10%  liquidity_score
    """
    df = pd.DataFrame(results)
    if df.empty:
        return df

    # ── Component 1: Avg excess return (5D + 10D average) ───
    exc_cols = [c for c in df.columns if c.startswith("avg_excess_")]
    if exc_cols:
        df["_avg_excess"] = df[exc_cols].mean(axis=1)
    else:
        df["_avg_excess"] = 0.0

    # ── Component 2: Win rate ────────────────────────────────
    win_cols = [c for c in df.columns if c.startswith("win_rate_")]
    if win_cols:
        df["_win_rate"] = df[win_cols].mean(axis=1)
    else:
        df["_win_rate"] = 0.0

    # ── Component 3: Correlation ─────────────────────────────
    if "corr_60d" in df.columns:
        df["_corr"] = df["corr_60d"]
    else:
        df["_corr"] = 0.0

    # ── Component 4: Setup score (already 0-100) ─────────────
    df["_setup"] = df.get("setup_score", 0).fillna(0)

    # ── Component 5: Liquidity ───────────────────────────────
    if "raw_adv" in df.columns:
        df["_liquidity"] = _minmax(df["raw_adv"].apply(np.log1p))
    else:
        df["_liquidity"] = 50.0

    # ── Normalise components to 0-100 ───────────────────────
    df["_avg_excess_n"] = _minmax(df["_avg_excess"])
    df["_win_rate_n"]   = _minmax(df["_win_rate"])
    df["_corr_n"]       = _minmax(df["_corr"])
    df["_setup_n"]      = df["_setup"]           # already 0-100
    df["_liq_n"]        = df["_liquidity"]       # already 0-100

    # ── Weighted total ───────────────────────────────────────
    w = config
    df["Total_Score"] = (
        w.WEIGHT_AVG_EXCESS_RETURN * df["_avg_excess_n"].fillna(0) +
        w.WEIGHT_WIN_RATE          * df["_win_rate_n"].fillna(0)   +
        w.WEIGHT_CORRELATION       * df["_corr_n"].fillna(0)       +
        w.WEIGHT_SETUP_SCORE       * df["_setup_n"].fillna(0)      +
        w.WEIGHT_LIQUIDITY         * df["_liq_n"].fillna(0)
    )

    # Drop internal columns
    df.drop(columns=[c for c in df.columns if c.startswith("_")], inplace=True)

    df.sort_values("Total_Score", ascending=False, inplace=True)
    df.reset_index(drop=True, inplace=True)
    df.index += 1  # 1-based rank

    return df
