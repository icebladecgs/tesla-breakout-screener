#!/usr/bin/env python
# ============================================================
# dashboard.py  –  Streamlit 대시보드 (모바일 최적화)
#   실행: streamlit run dashboard.py
# ============================================================

import os, sys
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

import config
from src.data_loader    import load_all
from src.event_detector import detect_events, get_event_dates, check_current_trigger
from src.screener       import run_screener
from src.scoring        import compute_total_scores

# ── 페이지 설정 ─────────────────────────────────────────────
st.set_page_config(
    page_title="Tesla Breakout Companion Screener",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ──────────────────────────────────────────────────────
st.markdown("""
<style>
/* 가로 스크롤 방지 */
.block-container {
    padding-top: 0.8rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    max-width: 100% !important;
    overflow-x: hidden !important;
}
section[data-testid="stMain"] > div {
    overflow-x: hidden !important;
}

.main-title {
    font-size: 22px; font-weight: 800; color: #E31937;
    margin-bottom: 2px;
}
.sub-title {
    font-size: 12px; color: #888; margin-bottom: 12px;
}

/* ── KPI 그리드 ── */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin-bottom: 12px;
}
.kpi-card {
    background: #1e1e2e;
    border-radius: 8px;
    padding: 10px 12px;
    min-width: 0;
}
.kpi-label {
    font-size: 11px;
    color: #888;
    margin-bottom: 3px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.kpi-value {
    font-size: 20px;
    font-weight: 700;
    color: white;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.kpi-pos { color: #00c853 !important; }
.kpi-neg { color: #E31937 !important; }

/* ── 트리거 배너 ── */
.trigger-active {
    background: #1b5e20;
    border: 1px solid #4caf50;
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 12px;
    font-size: 14px;
    color: #81c784;
    font-weight: 600;
}
.trigger-wait {
    background: #1a237e;
    border: 1px solid #3f51b5;
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 12px;
    font-size: 14px;
    color: #90caf9;
}

/* ── 모바일 ── */
@media screen and (max-width: 768px) {
    .block-container {
        padding-left: 0.4rem !important;
        padding-right: 0.4rem !important;
    }
    .kpi-grid {
        grid-template-columns: repeat(2, 1fr);
    }
    .main-title { font-size: 17px !important; }
    .kpi-value  { font-size: 16px !important; }
}

[data-testid="stSidebar"] { background-color: #111827; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# 데이터 로딩 / 분석 (캐시)
# ══════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600, show_spinner=False)
def run_analysis(event_types: tuple, force_refresh: bool = False):
    data        = load_all(force_refresh=force_refresh)
    tsla        = data.get(config.TSLA_TICKER)
    if tsla is None or tsla.empty:
        raise RuntimeError("TSLA_RATE_LIMITED")
    events      = detect_events(tsla)
    event_dates = get_event_dates(events, event_types=list(event_types))
    results     = run_screener(data, event_dates)
    ranked      = compute_total_scores(results)
    return ranked, tsla, len(event_dates)


# ══════════════════════════════════════════════════════════════
# 사이드바
# ══════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## ⚡ 설정")
    st.markdown("---")

    top_n = st.slider("Top N 표시", min_value=5, max_value=42, value=20, step=1)

    event_options = ["EVENT_A", "EVENT_B", "EVENT_C", "EVENT_D", "EVENT_E", "EVENT_F"]
    event_labels  = {
        "EVENT_A": "A: 20일 신고가",
        "EVENT_B": "B: 120일 신고가",
        "EVENT_C": "C: 52주 신고가",
        "EVENT_D": "D: ATH 돌파",
        "EVENT_E": "E: 5일 +10%",
        "EVENT_F": "F: 거래량 급증",
    }
    selected_events = st.multiselect(
        "이벤트 타입 선택",
        options=event_options,
        default=event_options,
        format_func=lambda x: event_labels[x],
    )

    st.markdown("---")
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        run_btn     = st.button("▶ 분석 실행", use_container_width=True, type="primary")
    with col_r2:
        refresh_btn = st.button("↺ 갱신", use_container_width=True)

    st.markdown("---")
    st.markdown("""
    **점수 가중치**
    - 30% 평균 초과수익률
    - 25% 상승 확률
    - 20% TSLA 상관성
    - 15% 기술적 셋업
    - 10% 유동성
    """)


# ══════════════════════════════════════════════════════════════
# 메인 헤더
# ══════════════════════════════════════════════════════════════

st.markdown('<div class="main-title">⚡ Tesla Breakout Companion Screener</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">TSLA 이벤트 발생 시 가장 크게 상승하는 동반 종목 탐색</div>', unsafe_allow_html=True)

# ── 세션 상태 ─────────────────────────────────────────────────
if "ranked" not in st.session_state:
    st.session_state["ranked"]      = None
    st.session_state["tsla"]        = None
    st.session_state["n_events"]    = 0
    st.session_state["last_events"] = tuple(event_options)

# ── 분석 실행 ─────────────────────────────────────────────────
if run_btn or refresh_btn or st.session_state["ranked"] is None:
    if not selected_events:
        st.warning("이벤트 타입을 최소 1개 이상 선택하세요.")
        st.stop()

    force = refresh_btn
    if force:
        run_analysis.clear()

    with st.spinner("데이터 로딩 및 분석 중..."):
        try:
            ranked, tsla, n_events = run_analysis(
                event_types=tuple(selected_events),
                force_refresh=force,
            )
        except RuntimeError as e:
            if "TSLA_RATE_LIMITED" in str(e):
                st.error("⚠️ Yahoo Finance 요청 한도 초과 — 1~2분 후 '↺ 갱신' 버튼을 눌러주세요.")
                st.stop()
            raise
    st.session_state["ranked"]   = ranked
    st.session_state["tsla"]     = tsla
    st.session_state["n_events"] = n_events

ranked   = st.session_state["ranked"]
tsla_df  = st.session_state["tsla"]
n_events = st.session_state["n_events"]

if ranked is None or ranked.empty:
    st.info("사이드바에서 '분석 실행' 버튼을 눌러주세요.")
    st.stop()

top = ranked.head(top_n).copy()


# ══════════════════════════════════════════════════════════════
# KPI 그리드 (HTML 카드)
# ══════════════════════════════════════════════════════════════

triggered   = check_current_trigger(tsla_df)
tsla_close  = tsla_df["Close"].squeeze()
tsla_5d_ret = (tsla_close.iloc[-1] / tsla_close.iloc[-6] - 1) * 100

ret_cls      = "kpi-pos" if tsla_5d_ret >= 0 else "kpi-neg"
top1_ticker  = top.iloc[0]["ticker"] if len(top) > 0 else "-"
top1_score   = f"{top.iloc[0]['Total_Score']:.1f}" if len(top) > 0 else "-"
trigger_icon = "🟢 트리거 활성!" if triggered else "🔴 대기"
trigger_cls  = "trigger-active" if triggered else "trigger-wait"
trigger_msg  = (
    "TSLA 5일 +8% 이상 & 20일 신고가 돌파"
    if triggered
    else f"TSLA 5일: {tsla_5d_ret:+.1f}%  (조건: ≥+8%)"
)

st.markdown(f"""
<div class="kpi-grid">
    <div class="kpi-card">
        <div class="kpi-label">TSLA 5일 수익률</div>
        <div class="kpi-value {ret_cls}">{tsla_5d_ret:+.1f}%</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">분석 종목 수</div>
        <div class="kpi-value">{len(ranked)}개</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">감지 이벤트</div>
        <div class="kpi-value">{n_events}개</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Top1 종목</div>
        <div class="kpi-value">{top1_ticker}</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Top1 Score</div>
        <div class="kpi-value">{top1_score}</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">트리거</div>
        <div class="kpi-value" style="font-size:13px;">{trigger_icon}</div>
    </div>
</div>
<div class="{trigger_cls}">{trigger_msg}</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# 랭킹 테이블 (전체 너비)
# ══════════════════════════════════════════════════════════════

st.markdown(f"### Top {top_n} 랭킹")
st.caption("행을 클릭하면 아래에 상세 정보가 표시됩니다.")

display_df = top[["ticker", "Total_Score", "avg_return_5d", "outperform_rate_5d",
                   "corr_60d", "beta_to_tsla", "setup_score"]].copy()
display_df.columns = ["Ticker", "Score", "Ret5D", "Win%", "Corr", "Beta", "Setup"]

for c in ["Ret5D", "Win%"]:
    display_df[c] = display_df[c].apply(
        lambda v: f"{v*100:+.1f}%" if pd.notna(v) else "N/A"
    )
for c in ["Corr", "Beta"]:
    display_df[c] = display_df[c].apply(
        lambda v: f"{v:.2f}" if pd.notna(v) else "N/A"
    )
display_df["Score"] = display_df["Score"].apply(lambda v: f"{v:.1f}" if pd.notna(v) else "N/A")
display_df["Setup"] = display_df["Setup"].apply(lambda v: f"{v:.0f}" if pd.notna(v) else "N/A")
display_df.index = [f"#{i}" for i in range(1, len(display_df) + 1)]

table_selection = st.dataframe(
    display_df,
    use_container_width=True,
    height=min(38 + len(display_df) * 35, 600),
    on_select="rerun",
    selection_mode="single-row",
)

selected_rows = table_selection.selection.get("rows", [])
if selected_rows:
    selected_ticker = top.iloc[selected_rows[0]]["ticker"]
    st.session_state["selected_ticker"] = selected_ticker
elif "selected_ticker" not in st.session_state:
    st.session_state["selected_ticker"] = top.iloc[0]["ticker"]
selected_ticker = st.session_state["selected_ticker"]


# ══════════════════════════════════════════════════════════════
# 선택 종목 상세 (테이블 아래 전체 너비)
# ══════════════════════════════════════════════════════════════

st.markdown("---")
row      = ranked[ranked["ticker"] == selected_ticker].iloc[0]
rank_num = (top["ticker"].tolist().index(selected_ticker) + 1
            if selected_ticker in top["ticker"].tolist() else "-")

st.markdown(f"### #{rank_num}  {selected_ticker}")

# ── 지표 2열 ──────────────────────────────────────────────────
m1, m2 = st.columns(2)
with m1:
    st.metric("Total Score",  f"{row.get('Total_Score', 0):.1f}")
    st.metric("Corr (60d)",   f"{row.get('corr_60d', float('nan')):.2f}")
    st.metric("RSI",          f"{row.get('rsi', float('nan')):.1f}")
    st.metric("Above MA20",   "Yes" if row.get("above_ma20") else "No")
with m2:
    st.metric("Setup Score",  f"{row.get('setup_score', 0):.0f}")
    st.metric("Beta to TSLA", f"{row.get('beta_to_tsla', float('nan')):.2f}")
    st.metric("DD 52W",       f"{row.get('drawdown_52w', float('nan'))*100:+.1f}%")
    st.metric("Vol Surge",    f"{row.get('volume_surge', float('nan')):.2f}x")

# ── 수익률 라인 차트 ──────────────────────────────────────────
windows  = [1, 3, 5, 10, 20]
avg_rets = [row.get(f"avg_return_{w}d", np.nan) for w in windows]
if any(pd.notna(v) for v in avg_rets):
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=[f"+{w}d" for w in windows],
        y=[v * 100 if pd.notna(v) else None for v in avg_rets],
        mode="lines+markers+text",
        text=[f"{v*100:+.1f}%" if pd.notna(v) else "" for v in avg_rets],
        textposition="top center",
        line=dict(color="#E31937", width=2),
        marker=dict(size=8),
        name=selected_ticker,
    ))
    fig2.add_hline(y=0, line_dash="dash", line_color="#555")
    fig2.update_layout(
        title=f"{selected_ticker} — TSLA 이벤트 후 평균 수익률",
        yaxis_title="수익률 (%)",
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        font=dict(color="white"),
        xaxis=dict(gridcolor="#333"),
        yaxis=dict(gridcolor="#333"),
        height=240,
        margin=dict(l=10, r=10, t=40, b=20),
    )
    st.plotly_chart(fig2, use_container_width=True)

# ── 이벤트 반응 상세 테이블 ───────────────────────────────────
with st.expander("TSLA 이벤트 후 수익률 상세", expanded=False):
    react_data = []
    for w in windows:
        react_data.append({
            "기간":          f"+{w}일",
            "평균수익률":     f"{row.get(f'avg_return_{w}d', float('nan'))*100:+.1f}%"
                              if pd.notna(row.get(f'avg_return_{w}d')) else "N/A",
            "최대수익률":     f"{row.get(f'max_return_{w}d', float('nan'))*100:+.1f}%"
                              if pd.notna(row.get(f'max_return_{w}d')) else "N/A",
            "상승확률":       f"{row.get(f'win_rate_{w}d', float('nan'))*100:.0f}%"
                              if pd.notna(row.get(f'win_rate_{w}d')) else "N/A",
            "TSLA 초과수익":  f"{row.get(f'avg_excess_{w}d', float('nan'))*100:+.1f}%"
                              if pd.notna(row.get(f'avg_excess_{w}d')) else "N/A",
        })
    st.dataframe(pd.DataFrame(react_data).set_index("기간"), use_container_width=True)

# ── 상관계수 차트 ─────────────────────────────────────────────
st.markdown("**TSLA 상관계수**")
corr_vals = [
    row.get("corr_60d", np.nan),
    row.get("corr_120d", np.nan),
    row.get("corr_250d", np.nan),
]
fig3 = go.Figure(go.Bar(
    x=["60일", "120일", "250일"],
    y=corr_vals,
    marker_color=["#2E5FAC", "#4A90D9", "#7EC8E3"],
    text=[f"{v:.2f}" if pd.notna(v) else "N/A" for v in corr_vals],
    textposition="outside",
))
fig3.update_layout(
    yaxis=dict(range=[0, 1.1], gridcolor="#333"),
    plot_bgcolor="#0e1117",
    paper_bgcolor="#0e1117",
    font=dict(color="white"),
    height=200,
    margin=dict(l=10, r=10, t=10, b=20),
)
st.plotly_chart(fig3, use_container_width=True)

# ── Top 랭킹 비교 차트 ────────────────────────────────────────
st.markdown("**Top 랭킹 비교**")
colors_bar = ["#E31937" if t == selected_ticker else "#2E5FAC"
               for t in top["ticker"].tolist()]
fig4 = go.Figure(go.Bar(
    x=top["ticker"].tolist(),
    y=top["Total_Score"].tolist(),
    marker_color=colors_bar,
    text=[f"{s:.0f}" for s in top["Total_Score"].tolist()],
    textposition="outside",
))
fig4.update_layout(
    yaxis=dict(range=[0, 105], gridcolor="#333"),
    plot_bgcolor="#0e1117",
    paper_bgcolor="#0e1117",
    font=dict(color="white", size=9),
    height=220,
    margin=dict(l=10, r=10, t=10, b=40),
    xaxis=dict(tickangle=-45),
)
st.plotly_chart(fig4, use_container_width=True)
