# ============================================================
# report.py  –  Console + CSV + Chart output, Telegram alerts
# ============================================================

import os
import pandas as pd
import numpy as np

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import config


# ────────────────────────────────────────────────────────────
# Console output
# ────────────────────────────────────────────────────────────

_DISPLAY_COLS = [
    ("ticker",              "Ticker"),
    ("corr_60d",            "Corr_60"),
    ("corr_120d",           "Corr_120"),
    ("beta_to_tsla",        "Beta_TSLA"),
    ("avg_return_5d",       "AvgRet_5D"),
    ("avg_return_10d",      "AvgRet_10D"),
    ("outperform_rate_5d",  "Outprf_Rate"),
    ("drawdown_52w",        "DD_52W"),
    ("setup_score",         "Setup"),
    ("Total_Score",         "Total"),
]


def _fmt_pct(v) -> str:
    if pd.isna(v):
        return "  N/A "
    return f"{v*100:+6.1f}%"


def _fmt_float(v, decimals=2) -> str:
    if pd.isna(v):
        return "  N/A "
    return f"{v:.{decimals}f}"


def print_ranking(ranked: pd.DataFrame, top_n: int = 20) -> None:
    top = ranked.head(top_n)

    header_fmt = "{:>4}  {:<7}  {:>7}  {:>7}  {:>7}  {:>9}  {:>9}  {:>10}  {:>8}  {:>6}  {:>7}"
    row_fmt    = "{:>4}  {:<7}  {:>7}  {:>7}  {:>7}  {:>9}  {:>9}  {:>10}  {:>8}  {:>6}  {:>7}"

    sep = "=" * 95

    print(f"\n{sep}")
    print(f"  TOP {top_n}  TESLA BREAKOUT COMPANION STOCKS")
    print(sep)
    print(header_fmt.format(
        "Rank", "Ticker",
        "Corr60", "Corr120", "Beta",
        "AvgRet5D", "AvgRet10D", "OutprfRate",
        "DD_52W", "Setup", "Total"
    ))
    print("-" * 95)

    for rank, row in top.iterrows():
        print(row_fmt.format(
            f"#{rank}",
            row.get("ticker", ""),
            _fmt_float(row.get("corr_60d")),
            _fmt_float(row.get("corr_120d")),
            _fmt_float(row.get("beta_to_tsla")),
            _fmt_pct(row.get("avg_return_5d")),
            _fmt_pct(row.get("avg_return_10d")),
            _fmt_pct(row.get("outperform_rate_5d")),
            _fmt_pct(row.get("drawdown_52w")),
            _fmt_float(row.get("setup_score"), 1),
            _fmt_float(row.get("Total_Score"), 1),
        ))

    print(sep + "\n")


# ────────────────────────────────────────────────────────────
# CSV export
# ────────────────────────────────────────────────────────────

def save_csv(ranked: pd.DataFrame, filename: str = "results.csv") -> str:
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    path = os.path.join(config.OUTPUT_DIR, filename)
    ranked.to_csv(path)
    print(f"Results saved → {path}")
    return path


# ────────────────────────────────────────────────────────────
# Bar chart (Top 20 Total Score)
# ────────────────────────────────────────────────────────────

def plot_bar_chart(ranked: pd.DataFrame, top_n: int = 20,
                   save: bool = True, show: bool = True) -> None:
    try:
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
    except ImportError:
        print("matplotlib not installed – skipping chart.")
        return

    top = ranked.head(top_n).copy()
    tickers = top["ticker"].tolist()
    scores  = top["Total_Score"].tolist()
    colors  = ["#E31937" if i == 0 else "#2E5FAC" for i in range(len(tickers))]

    fig, ax = plt.subplots(figsize=(14, 6))
    bars = ax.barh(tickers[::-1], scores[::-1], color=colors[::-1], edgecolor="white", height=0.7)

    for bar, score in zip(bars, scores[::-1]):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                f"{score:.1f}", va="center", fontsize=9)

    ax.set_xlabel("Total Score (0–100)", fontsize=11)
    ax.set_title("Tesla Breakout Companion Screener – Top Rankings", fontsize=13, fontweight="bold")
    ax.set_xlim(0, 105)
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    plt.tight_layout()

    if save:
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)
        path = os.path.join(config.OUTPUT_DIR, "ranking_chart.png")
        plt.savefig(path, dpi=150)
        print(f"Chart saved → {path}")

    if show:
        plt.show()

    plt.close()


# ────────────────────────────────────────────────────────────
# Telegram alerts
# ────────────────────────────────────────────────────────────

def send_telegram_alert(ranked: pd.DataFrame,
                         top_n: int = config.TELEGRAM_TOP_N) -> bool:
    """Send top_n results to Telegram. Returns True on success."""
    token   = config.TELEGRAM_BOT_TOKEN
    chat_id = config.TELEGRAM_CHAT_ID

    if not token or not chat_id:
        print("Telegram not configured (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set).")
        return False

    try:
        import requests
    except ImportError:
        print("requests library not installed.")
        return False

    top  = ranked.head(top_n)
    rows = []
    for rank, row in top.iterrows():
        rows.append(
            f"#{rank} {row.get('ticker','?'):<6}  "
            f"Score={row.get('Total_Score',0):.1f}  "
            f"Corr60={row.get('corr_60d', float('nan')):.2f}  "
            f"Setup={row.get('setup_score',0):.0f}"
        )

    msg = (
        "🚀 *Tesla Breakout Companion Screener*\n"
        f"Top {top_n} companion stocks:\n\n"
        + "\n".join(rows)
    )

    url  = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(url, json={"chat_id": chat_id, "text": msg,
                                     "parse_mode": "Markdown"}, timeout=10)
    if resp.status_code == 200:
        print("Telegram alert sent successfully.")
        return True
    else:
        print(f"Telegram error: {resp.text}")
        return False
