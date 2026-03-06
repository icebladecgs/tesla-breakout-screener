# ============================================================
# event_detector.py  –  Detect TSLA breakout / momentum events
# ============================================================

import pandas as pd
import numpy as np

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import config


def _rolling_high(close: pd.Series, window: int) -> pd.Series:
    return close.shift(1).rolling(window).max()


def detect_events(tsla: pd.DataFrame) -> pd.DataFrame:
    """
    Returns a DataFrame indexed by date with boolean columns for each event type.

    EVENT_A  – 20-day high breakout
    EVENT_B  – 120-day high breakout
    EVENT_C  – 52-week (252-day) high breakout
    EVENT_D  – All-Time High breakout
    EVENT_E  – 5-day return > 10%
    EVENT_F  – Volume surge (≥1.5× 20-day avg) AND 20-day high breakout
    """
    close  = tsla["Close"].squeeze()
    volume = tsla["Volume"].squeeze()

    events = pd.DataFrame(index=tsla.index)

    # ── Breakout events ──────────────────────────────────────
    events["EVENT_A"] = close > _rolling_high(close, config.EVENT_A_WINDOW)
    events["EVENT_B"] = close > _rolling_high(close, config.EVENT_B_WINDOW)
    events["EVENT_C"] = close > _rolling_high(close, config.EVENT_C_WINDOW)

    # ATH breakout: today's close > max of ALL prior closes
    ath = close.shift(1).expanding().max()
    events["EVENT_D"] = close > ath

    # ── Momentum event ───────────────────────────────────────
    ret_5d = close.pct_change(config.EVENT_E_DAYS)
    events["EVENT_E"] = ret_5d > config.EVENT_E_RETURN_THRESHOLD

    # ── Volume + breakout combo ──────────────────────────────
    vol_ma20    = volume.rolling(20).mean()
    vol_surge   = volume > vol_ma20 * config.EVENT_F_VOLUME_MULTIPLIER
    events["EVENT_F"] = vol_surge & events["EVENT_A"]

    # ── Composite: any event ─────────────────────────────────
    events["ANY_EVENT"] = events[
        ["EVENT_A", "EVENT_B", "EVENT_C", "EVENT_D", "EVENT_E", "EVENT_F"]
    ].any(axis=1)

    return events.dropna(how="all")


def get_event_dates(events: pd.DataFrame,
                    event_types=None,
                    min_gap_days: int = 5) -> pd.DatetimeIndex:
    """
    Return dates where at least one of the specified event types occurred.
    min_gap_days enforces a cooldown so clustered signals don't double-count.
    """
    if event_types is None:
        event_types = ["EVENT_A", "EVENT_B", "EVENT_C", "EVENT_D", "EVENT_E", "EVENT_F"]

    cols = [c for c in event_types if c in events.columns]
    mask = events[cols].any(axis=1)
    raw_dates = events.index[mask].sort_values()

    # Enforce cooldown
    filtered = []
    last_date = None
    for d in raw_dates:
        if last_date is None or (d - last_date).days >= min_gap_days:
            filtered.append(d)
            last_date = d

    return pd.DatetimeIndex(filtered)


def check_current_trigger(tsla: pd.DataFrame) -> bool:
    """
    Returns True if TSLA currently satisfies the auto-trigger conditions:
      - 5-day return ≥ 8%
      - 20-day high breakout
    """
    close = tsla["Close"].squeeze()
    ret_5d = close.iloc[-1] / close.iloc[-6] - 1
    high_20d = close.iloc[-21:-1].max()
    breakout = close.iloc[-1] > high_20d
    return ret_5d >= config.AUTO_TRIGGER_5D_RETURN and breakout
