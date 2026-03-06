# ============================================================
# screener.py  –  Orchestrates per-ticker analysis
# ============================================================

import pandas as pd
import numpy as np

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import config
from src.metrics import (
    compute_event_reactions, summarise_reactions,
    compute_correlation, compute_beta,
    compute_setup_score, compute_liquidity_score,
)


def analyse_ticker(ticker: str,
                   df: pd.DataFrame,
                   tsla: pd.DataFrame,
                   event_dates: pd.DatetimeIndex) -> dict | None:
    """
    Full analysis for a single candidate ticker.
    Returns a dict of metrics, or None if data is insufficient.
    """
    if df is None or df.empty or len(df) < 60:
        return None

    close        = df["Close"].squeeze()
    tsla_close   = tsla["Close"].squeeze()

    # ── Event reactions ──────────────────────────────────────
    reactions = compute_event_reactions(close, tsla_close, event_dates)
    if reactions.empty:
        reaction_summary = {}
    else:
        reaction_summary = summarise_reactions(reactions)

    # ── Correlation & Beta ───────────────────────────────────
    corr = compute_correlation(close, tsla_close)
    beta = compute_beta(close, tsla_close)

    # ── Technical setup ──────────────────────────────────────
    setup = compute_setup_score(df)

    # ── Liquidity (raw ADV for later normalisation) ──────────
    raw_adv = compute_liquidity_score(df, {})

    # ── Assemble result ──────────────────────────────────────
    result = {"ticker": ticker}
    result.update(reaction_summary)
    result.update(corr)
    result["beta_to_tsla"]      = beta
    result["setup_score"]       = setup["setup_score"]
    result["rsi"]               = setup.get("rsi", np.nan)
    result["drawdown_52w"]      = setup.get("drawdown_52w", np.nan)
    result["above_ma20"]        = setup.get("above_ma20", False)
    result["above_ma60"]        = setup.get("above_ma60", False)
    result["volume_surge"]      = setup.get("volume_surge", np.nan)
    result["raw_adv"]           = raw_adv

    # Convenience aliases used in report
    result["avg_return_5d"]     = reaction_summary.get("avg_return_5d", np.nan)
    result["avg_return_10d"]    = reaction_summary.get("avg_return_10d", np.nan)
    result["outperform_rate_5d"]= reaction_summary.get("outperform_rate_5d", np.nan)
    result["n_events"]          = reaction_summary.get("n_events_5d", 0)

    return result


def run_screener(data: dict[str, pd.DataFrame],
                 event_dates: pd.DatetimeIndex) -> list[dict]:
    """
    Runs analyse_ticker() for every candidate and returns a list of result dicts.
    """
    tsla = data.get(config.TSLA_TICKER)
    if tsla is None or tsla.empty:
        raise ValueError("TSLA data not available.")

    print(f"\nAnalysing {len(config.CANDIDATE_TICKERS)} candidates against "
          f"{len(event_dates)} TSLA event dates …\n")

    results = []
    for ticker in config.CANDIDATE_TICKERS:
        df = data.get(ticker)
        r  = analyse_ticker(ticker, df, tsla, event_dates)
        if r is not None:
            results.append(r)
            print(f"  {ticker:<8} OK  "
                  f"events={r['n_events']:<3}  "
                  f"corr60={r.get('corr_60d', float('nan')):.2f}  "
                  f"setup={r['setup_score']:.0f}")
        else:
            print(f"  {ticker:<8} SKIP (insufficient data)")

    return results
