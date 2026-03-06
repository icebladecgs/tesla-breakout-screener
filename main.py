#!/usr/bin/env python
# ============================================================
# main.py  –  Tesla Breakout Companion Screener
#             Entry point
# ============================================================

import argparse
import sys
import os

# Make sure project root is on the path
sys.path.insert(0, os.path.dirname(__file__))

import config
from src.data_loader    import load_all
from src.event_detector import detect_events, get_event_dates, check_current_trigger
from src.screener       import run_screener
from src.scoring        import compute_total_scores
from src.report         import print_ranking, save_csv, plot_bar_chart, send_telegram_alert


def parse_args():
    p = argparse.ArgumentParser(description="Tesla Breakout Companion Screener")
    p.add_argument("--refresh",  action="store_true",
                   help="Force re-download all data (ignore cache)")
    p.add_argument("--no-chart", action="store_true",
                   help="Skip the bar-chart output")
    p.add_argument("--telegram", action="store_true",
                   help="Send Top-5 alert to Telegram")
    p.add_argument("--auto-only", action="store_true",
                   help="Only run if TSLA satisfies auto-trigger conditions")
    p.add_argument("--top",      type=int, default=20,
                   help="How many top stocks to display (default: 20)")
    p.add_argument("--events",   nargs="+",
                   default=["EVENT_A","EVENT_B","EVENT_C","EVENT_D","EVENT_E","EVENT_F"],
                   help="Which event types to include in analysis")
    return p.parse_args()


def main():
    args = parse_args()

    print("\n" + "=" * 60)
    print("  TESLA BREAKOUT COMPANION SCREENER")
    print("=" * 60 + "\n")

    # ── 1. Load data ─────────────────────────────────────────
    data = load_all(force_refresh=args.refresh)

    tsla = data.get(config.TSLA_TICKER)
    if tsla is None or tsla.empty:
        print("ERROR: Could not load TSLA data. Aborting.")
        sys.exit(1)

    # ── 2. Auto-trigger check ────────────────────────────────
    if args.auto_only:
        triggered = check_current_trigger(tsla)
        if not triggered:
            print("Auto-trigger conditions NOT met. Exiting.")
            print("  (TSLA needs ≥8% 5-day return AND 20-day high breakout)\n")
            sys.exit(0)
        else:
            print("Auto-trigger conditions MET — running full analysis.\n")

    # ── 3. Detect TSLA events ────────────────────────────────
    print("Detecting TSLA breakout events …")
    events     = detect_events(tsla)
    event_dates = get_event_dates(events, event_types=args.events)
    print(f"  Found {len(event_dates)} qualifying event dates "
          f"({args.events})\n")

    if len(event_dates) == 0:
        print("No events found for the selected event types. Aborting.")
        sys.exit(1)

    # ── 4. Run screener ──────────────────────────────────────
    results = run_screener(data, event_dates)

    if not results:
        print("No valid results. Aborting.")
        sys.exit(1)

    # ── 5. Score & rank ──────────────────────────────────────
    ranked = compute_total_scores(results)

    # ── 6. Output ────────────────────────────────────────────
    print_ranking(ranked, top_n=args.top)
    csv_path = save_csv(ranked)

    if not args.no_chart:
        plot_bar_chart(ranked, top_n=args.top, save=True, show=True)

    if args.telegram:
        send_telegram_alert(ranked)

    print("\nDone.\n")
    return ranked


if __name__ == "__main__":
    main()
