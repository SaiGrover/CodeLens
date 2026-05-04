"""
app.py — CodeLens Streamlit Frontend
A polished, dark-themed code analysis dashboard.
"""

import streamlit as st
import requests
import json
import base64
from io import BytesIO

# ─────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────

BACKEND_URL = "http://localhost:8000"

st.set_page_config(
    page_title="CodeLens",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────
# Custom CSS
# ─────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');

:root {
    --bg-primary: #0a0a0f;
    --bg-card: #111118;
    --bg-card2: #15151f;
    --accent-red: #e94560;
    --accent-blue: #0f3460;
    --accent-cyan: #16c2d4;
    --accent-yellow: #f5c842;
    --accent-green: #2dce89;
    --text-primary: #e8e8f0;
    --text-muted: #7a7a9a;
    --border: #1e1e2e;
}

html, body, [class*="css"] {
    background-color: var(--bg-primary) !important;
    color: var(--text-primary) !important;
    font-family: 'DM Sans', sans-serif !important;
}

/* Header */
.codelens-header {
    background: linear-gradient(135deg, #0a0a0f 0%, #0f0f1a 50%, #0a0a0f 100%);
    border-bottom: 1px solid var(--accent-red);
    padding: 2rem 0 1.5rem 0;
    margin-bottom: 2rem;
    text-align: center;
    position: relative;
    overflow: hidden;
}
.codelens-header::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: radial-gradient(ellipse at 50% 0%, rgba(233,69,96,0.15) 0%, transparent 60%);
    pointer-events: none;
}
.codelens-logo {
    font-family: 'Space Mono', monospace;
    font-size: 3rem;
    font-weight: 700;
    background: linear-gradient(90deg, #e94560 0%, #16c2d4 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -1px;
}
.codelens-tagline {
    font-size: 0.9rem;
    color: var(--text-muted);
    font-family: 'Space Mono', monospace;
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-top: 0.25rem;
}
.lang-badge {
    display: inline-block;
    padding: 0.2rem 0.8rem;
    border-radius: 20px;
    font-family: 'Space Mono', monospace;
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-top: 0.5rem;
}
.lang-python { background: rgba(22,194,212,0.15); color: #16c2d4; border: 1px solid #16c2d430; }
.lang-java   { background: rgba(245,200,66,0.15);  color: #f5c842;  border: 1px solid #f5c84230; }

/* Metric Cards */
.metric-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    margin: 0.4rem 0;
    transition: border-color 0.2s;
    position: relative;
    overflow: hidden;
}
.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--accent-red), var(--accent-cyan));
}
.metric-card:hover { border-color: var(--accent-red); }
.metric-label {
    font-size: 0.7rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 2px;
    font-family: 'Space Mono', monospace;
    margin-bottom: 0.3rem;
}
.metric-value {
    font-size: 1.6rem;
    font-weight: 600;
    color: var(--text-primary);
    font-family: 'Space Mono', monospace;
}
.metric-sub {
    font-size: 0.75rem;
    color: var(--text-muted);
    margin-top: 0.2rem;
}

/* Score Ring */
.score-container {
    text-align: center;
    padding: 1rem;
}
.score-ring {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 120px;
    height: 120px;
    border-radius: 50%;
    border: 6px solid;
    font-family: 'Space Mono', monospace;
    font-size: 2rem;
    font-weight: 700;
}
.score-good  { border-color: #2dce89; color: #2dce89; box-shadow: 0 0 20px rgba(45,206,137,0.3); }
.score-med   { border-color: #f5c842; color: #f5c842; box-shadow: 0 0 20px rgba(245,200,66,0.3); }
.score-bad   { border-color: #e94560; color: #e94560; box-shadow: 0 0 20px rgba(233,69,96,0.3); }

/* Issue items */
.issue-item {
    background: var(--bg-card);
    border-left: 3px solid;
    border-radius: 0 8px 8px 0;
    padding: 0.7rem 1rem;
    margin: 0.5rem 0;
}
.issue-critical { border-color: #e94560; }
.issue-warning  { border-color: #f5c842; }
.issue-info     { border-color: #16c2d4; }
.issue-header {
    font-size: 0.8rem;
    font-family: 'Space Mono', monospace;
    font-weight: 700;
    margin-bottom: 0.2rem;
}
.issue-critical .issue-header { color: #e94560; }
.issue-warning  .issue-header { color: #f5c842; }
.issue-info     .issue-header { color: #16c2d4; }
.issue-msg  { font-size: 0.85rem; color: var(--text-primary); }
.issue-fix  { font-size: 0.78rem; color: var(--text-muted); margin-top: 0.2rem; }
.issue-fix span { color: #2dce89; }

/* Progress bar */
.prog-bar-track {
    background: var(--border);
    border-radius: 4px;
    height: 8px;
    margin-top: 0.4rem;
    overflow: hidden;
}
.prog-bar-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.5s ease;
}

/* Label pills */
.label-pill {
    display: inline-block;
    padding: 0.15rem 0.7rem;
    border-radius: 20px;
    font-size: 0.7rem;
    font-weight: 700;
    font-family: 'Space Mono', monospace;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}
.pill-good   { background: rgba(45,206,137,0.15);  color: #2dce89; border: 1px solid rgba(45,206,137,0.3); }
.pill-medium { background: rgba(245,200,66,0.15);  color: #f5c842; border: 1px solid rgba(245,200,66,0.3); }
.pill-bad    { background: rgba(233,69,96,0.15);   color: #e94560; border: 1px solid rgba(233,69,96,0.3); }

/* Section headings */
.section-title {
    font-family: 'Space Mono', monospace;
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 3px;
    color: var(--text-muted);
    border-bottom: 1px solid var(--border);
    padding-bottom: 0.5rem;
    margin: 1.5rem 0 1rem 0;
}

/* Streamlit overrides */
.stTextArea textarea {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-primary) !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.82rem !important;
    border-radius: 8px !important;
}
.stTextArea textarea:focus {
    border-color: var(--accent-red) !important;
    box-shadow: 0 0 0 2px rgba(233,69,96,0.2) !important;
}
.stButton > button {
    background: linear-gradient(135deg, #e94560 0%, #c73652 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.85rem !important;
    font-weight: 700 !important;
    letter-spacing: 1px !important;
    padding: 0.6rem 2rem !important;
    transition: all 0.2s !important;
    text-transform: uppercase !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 15px rgba(233,69,96,0.4) !important;
}
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: var(--bg-card) !important;
    border-radius: 8px !important;
    padding: 0.3rem !important;
    gap: 0.2rem !important;
    border: 1px solid var(--border) !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    background: transparent !important;
    color: var(--text-muted) !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.75rem !important;
    border-radius: 6px !important;
    padding: 0.4rem 1rem !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
    background: var(--accent-red) !important;
    color: white !important;
}
[data-testid="stExpander"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
}
.stCodeBlock { border-radius: 8px !important; }
div[data-testid="stMarkdownContainer"] p { color: var(--text-primary) !important; }
.stDownloadButton > button {
    background: rgba(22,194,212,0.1) !important;
    color: #16c2d4 !important;
    border: 1px solid rgba(22,194,212,0.3) !important;
    border-radius: 8px !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.75rem !important;
}
hr { border-color: var(--border) !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────

def pill(label: str) -> str:
    cls = {"Good": "pill-good", "Medium": "pill-medium", "Bad": "pill-bad"}.get(label, "pill-medium")
    return f'<span class="label-pill {cls}">{label}</span>'


def metric_card(label: str, value: str, sub: str = "") -> str:
    return f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        {"<div class='metric-sub'>"+sub+"</div>" if sub else ""}
    </div>"""


def score_ring(score: int) -> str:
    cls = "score-good" if score >= 70 else ("score-med" if score >= 40 else "score-bad")
    return f"""
    <div class="score-container">
        <div class="score-ring {cls}">{score}</div>
        <div style="margin-top:0.5rem; font-size:0.7rem; color:var(--text-muted);
             font-family:'Space Mono',monospace; letter-spacing:2px; text-transform:uppercase;">
             Optimization Score
        </div>
    </div>"""


def render_issue(issue: dict) -> str:
    sev = issue["severity"]
    icon = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(sev, "•")
    return f"""
    <div class="issue-item issue-{sev}">
        <div class="issue-header">{icon} [{issue['category']}] — Line {issue['line']}</div>
        <div class="issue-msg">{issue['message']}</div>
        <div class="issue-fix"><span>💡 Fix:</span> {issue['suggestion']}</div>
    </div>"""


def progress_bar(value: float, max_val: float = 10, color: str = "#e94560") -> str:
    pct = min(100, (value / max_val) * 100)
    return f"""
    <div class="prog-bar-track">
        <div class="prog-bar-fill" style="width:{pct}%; background:{color};"></div>
    </div>"""


# ─────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────

st.markdown("""
<div class="codelens-header">
    <div class="codelens-logo">🔬 CodeLens</div>
    <div class="codelens-tagline">Static Code Analysis · Metrics · Visualization</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# Input Panel
# ─────────────────────────────────────────────────────────────

col_input, col_right = st.columns([1.1, 0.9])

with col_input:
    st.markdown('<div class="section-title">Paste Your Code</div>', unsafe_allow_html=True)
    code_input = st.text_area(
        "",
        height=300,
        placeholder="# Paste Python or Java code here…\n# Language is auto-detected.\n\ndef fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)",
        label_visibility="collapsed",
    )

    c1, c2, _ = st.columns([1, 1, 2])
    with c1:
        analyze_btn = st.button("⚡ Analyze", use_container_width=True)
    with c2:
        reset_btn = st.button("↺ Reset", use_container_width=True)

    if reset_btn:
        st.session_state.pop("analysis", None)
        st.rerun()

with col_right:
    st.markdown('<div class="section-title">How It Works</div>', unsafe_allow_html=True)
    st.markdown("""
<div class="metric-card" style="border-top-color: #16c2d4;">
<div style="font-size:0.82rem; color: var(--text-muted); line-height: 1.8;">
<span style="color:#e94560; font-family:'Space Mono',monospace;">01</span> &nbsp;Paste Python or Java code<br>
<span style="color:#e94560; font-family:'Space Mono',monospace;">02</span> &nbsp;Language auto-detected<br>
<span style="color:#e94560; font-family:'Space Mono',monospace;">03</span> &nbsp;AST + regex parsing<br>
<span style="color:#e94560; font-family:'Space Mono',monospace;">04</span> &nbsp;Halstead &amp; COCOMO formulas<br>
<span style="color:#e94560; font-family:'Space Mono',monospace;">05</span> &nbsp;Sequence diagram via PlantUML<br>
<span style="color:#e94560; font-family:'Space Mono',monospace;">06</span> &nbsp;Rule-based optimization report<br>
</div>
</div>
<br>
<div style="padding: 0.8rem 1rem; background: rgba(233,69,96,0.05); border: 1px dashed rgba(233,69,96,0.25);
     border-radius: 8px; font-size:0.78rem; color:var(--text-muted);">
⚡ <strong style="color:var(--text-primary);">100% offline</strong> — no AI API, no internet needed for analysis.<br>
Only the sequence diagram fetches from PlantUML's free public server.
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# Analysis
# ─────────────────────────────────────────────────────────────

if analyze_btn:
    if not code_input.strip():
        st.error("⚠️ Please paste some code first.")
    else:
        with st.spinner("Analyzing code…"):
            try:
                resp = requests.post(
                    f"{BACKEND_URL}/analyze",
                    json={"code": code_input},
                    timeout=30,
                )
                if resp.status_code == 200:
                    st.session_state["analysis"] = resp.json()
                    st.session_state["raw_code"] = code_input
                else:
                    st.error(f"Backend error {resp.status_code}: {resp.text[:300]}")
            except requests.ConnectionError:
                st.error(
                    "⚠️ Cannot connect to the backend. "
                    "Start it with: `cd codelens && uvicorn backend.main:app --reload`"
                )

# ─────────────────────────────────────────────────────────────
# Results
# ─────────────────────────────────────────────────────────────

if "analysis" in st.session_state:
    data = st.session_state["analysis"]
    raw_code = st.session_state.get("raw_code", "")

    lang = data["language"]
    lang_class = "lang-python" if lang == "python" else "lang-java"
    st.markdown(
        f'<div style="text-align:center; margin-bottom:1.5rem;">'
        f'<span class="lang-badge {lang_class}">🌐 {lang.capitalize()} detected</span>'
        f'&nbsp;&nbsp;<span style="color:var(--text-muted); font-size:0.82rem;">'
        f'{data["loc"]} lines of code &nbsp;·&nbsp; {data["total_lines"]} total lines</span></div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # ── Tabs ──
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Halstead", "📐 COCOMO", "🔗 Coupling", "🔁 Diagram", "⚡ Optimizer"
    ])

    # ────────────── TAB 1: Halstead ──────────────
    with tab1:
        h = data["halstead"]
        st.markdown('<div class="section-title">Halstead Software Metrics</div>', unsafe_allow_html=True)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(metric_card("Unique Operators (n₁)", str(h["n1"])), unsafe_allow_html=True)
            st.markdown(metric_card("Total Operators (N₁)", str(h["N1"])), unsafe_allow_html=True)
        with c2:
            st.markdown(metric_card("Unique Operands (n₂)", str(h["n2"])), unsafe_allow_html=True)
            st.markdown(metric_card("Total Operands (N₂)", str(h["N2"])), unsafe_allow_html=True)
        with c3:
            st.markdown(metric_card("Vocabulary (n)", str(h["vocabulary"]),
                                    "n₁ + n₂"), unsafe_allow_html=True)
            st.markdown(metric_card("Program Length (N)", str(h["length"]),
                                    "N₁ + N₂"), unsafe_allow_html=True)
        with c4:
            st.markdown(metric_card("Volume (V)", f"{h['volume']:,.1f}",
                                    "N × log₂(n)"), unsafe_allow_html=True)
            st.markdown(metric_card("Difficulty (D)", f"{h['difficulty']:,.2f}",
                                    "(n₁/2) × (N₂/n₂)"), unsafe_allow_html=True)

        st.markdown('<div class="section-title" style="margin-top:1.5rem;">Derived Estimates</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(metric_card("Effort (E)", f"{h['effort']:,.0f}",
                                    "D × V"), unsafe_allow_html=True)
        with c2:
            mins = h["time_minutes"]
            time_str = f"{mins:.1f} min" if mins < 60 else f"{mins/60:.1f} hrs"
            st.markdown(metric_card("Time to Code (T)", time_str,
                                    "E ÷ 18 seconds"), unsafe_allow_html=True)
        with c3:
            bug_color = "#2dce89" if h["predicted_bugs"] < 1 else ("#f5c842" if h["predicted_bugs"] < 3 else "#e94560")
            st.markdown(metric_card("Predicted Bugs (B)", f"{h['predicted_bugs']:.3f}",
                                    "V ÷ 3000"), unsafe_allow_html=True)

        st.markdown("""
<div style="margin-top:1rem; padding: 0.8rem 1rem; background: rgba(22,194,212,0.05);
     border: 1px solid rgba(22,194,212,0.15); border-radius: 8px;
     font-size:0.78rem; color:var(--text-muted);">
ℹ️ <strong style="color:var(--text-primary);">About Halstead Metrics</strong>
 — These are purely mathematical properties of the source code, computed from operator/operand counts.
<b>Volume</b> measures information content, <b>Difficulty</b> measures how hard it is to understand,
and <b>Effort</b> combines both. Higher volume with lower difficulty = well-structured code.
</div>
""", unsafe_allow_html=True)

    # ────────────── TAB 2: COCOMO ──────────────
    with tab2:
        co = data["cocomo"]
        st.markdown('<div class="section-title">COCOMO I — Basic Effort Estimation</div>', unsafe_allow_html=True)

        type_colors = {"Organic": "#2dce89", "Semi-detached": "#f5c842", "Embedded": "#e94560"}
        tc = type_colors.get(co["project_type"], "#16c2d4")
        st.markdown(f"""
<div style="text-align:center; margin: 0.5rem 0 1.5rem 0;">
    <span style="font-family:'Space Mono',monospace; font-size:1.1rem;
         color:{tc}; letter-spacing:2px; text-transform:uppercase;
         padding: 0.3rem 1.2rem; border: 1px solid {tc}40;
         border-radius: 20px; background: {tc}15;">
        {co['project_type']} Project
    </span>
    <div style="margin-top:0.5rem; font-size:0.75rem; color:var(--text-muted);">
        Classified by LOC count
    </div>
</div>
""", unsafe_allow_html=True)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(metric_card("Lines of Code", f"{co['loc']:,}",
                                    f"{co['kloc']:.3f} KLOC"), unsafe_allow_html=True)
        with c2:
            st.markdown(metric_card("Effort", f"{co['effort_person_months']:.2f} PM",
                                    "Person-months"), unsafe_allow_html=True)
        with c3:
            st.markdown(metric_card("Dev Time", f"{co['dev_time_months']:.2f} mo",
                                    "Calendar months"), unsafe_allow_html=True)
        with c4:
            st.markdown(metric_card("Team Size", f"{co['team_size']:.1f}",
                                    "Developers"), unsafe_allow_html=True)

        st.markdown(metric_card("Productivity", f"{int(co['productivity_loc_per_pm']):,} LOC/PM",
                                "Lines of code per person-month"), unsafe_allow_html=True)

        st.markdown("""
<div style="margin-top:1rem; padding: 0.8rem 1rem; background: rgba(245,200,66,0.05);
     border: 1px solid rgba(245,200,66,0.15); border-radius: 8px;
     font-size:0.78rem; color:var(--text-muted);">
ℹ️ <strong style="color:var(--text-primary);">COCOMO Classification</strong>
 — <b>Organic</b> (&lt;50K LOC): small teams, familiar domain.
 <b>Semi-detached</b> (50K–300K LOC): mixed experience, some constraints.
 <b>Embedded</b> (&gt;300K LOC): tight constraints, complex requirements.
</div>
""", unsafe_allow_html=True)

    # ────────────── TAB 3: Coupling & Cohesion ──────────────
    with tab3:
        cc = data["coupling_cohesion"]
        st.markdown('<div class="section-title">Coupling &amp; Cohesion Analysis</div>', unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"""
<div class="metric-card">
    <div class="metric-label">Coupling Score (lower = better)</div>
    <div style="display:flex; align-items:center; gap:1rem; margin:0.3rem 0;">
        <div class="metric-value">{cc['coupling_score']}<span style="font-size:0.9rem;color:var(--text-muted)">/10</span></div>
        {pill(cc['coupling_label'])}
    </div>
    {progress_bar(cc['coupling_score'], 10, '#e94560')}
    <div class="metric-sub" style="margin-top:0.5rem;">How much classes depend on each other</div>
</div>
""", unsafe_allow_html=True)

        with c2:
            st.markdown(f"""
<div class="metric-card">
    <div class="metric-label">Cohesion Score (higher = better)</div>
    <div style="display:flex; align-items:center; gap:1rem; margin:0.3rem 0;">
        <div class="metric-value">{cc['cohesion_score']}<span style="font-size:0.9rem;color:var(--text-muted)">/10</span></div>
        {pill(cc['cohesion_label'])}
    </div>
    {progress_bar(cc['cohesion_score'], 10, '#2dce89')}
    <div class="metric-sub" style="margin-top:0.5rem;">How focused each class is on one responsibility</div>
</div>
""", unsafe_allow_html=True)

        if cc["class_details"]:
            st.markdown('<div class="section-title" style="margin-top:1.5rem;">Per-Class Breakdown</div>', unsafe_allow_html=True)
            for cls_info in cc["class_details"]:
                with st.expander(f"📦 {cls_info['class']}  —  {cls_info['methods']} methods, {cls_info['attributes']} attributes"):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f"""
<div class="metric-card">
    <div class="metric-label">Coupling</div>
    <div style="display:flex; align-items:center; gap:0.8rem;">
        <span class="metric-value">{cls_info['coupling']}</span>
        {pill(cls_info['coupling_label'])}
    </div>
    {progress_bar(cls_info['coupling'], 10, '#e94560')}
    <div class="metric-sub" style="margin-top:0.4rem;">
        External deps: {', '.join(cls_info['external_deps'][:5]) or 'None'}
    </div>
</div>""", unsafe_allow_html=True)
                    with c2:
                        st.markdown(f"""
<div class="metric-card">
    <div class="metric-label">Cohesion</div>
    <div style="display:flex; align-items:center; gap:0.8rem;">
        <span class="metric-value">{cls_info['cohesion']}</span>
        {pill(cls_info['cohesion_label'])}
    </div>
    {progress_bar(cls_info['cohesion'], 10, '#2dce89')}
</div>""", unsafe_allow_html=True)
        else:
            st.markdown("""
<div style="padding:1rem; background:rgba(22,194,212,0.05); border:1px solid rgba(22,194,212,0.15);
     border-radius:8px; font-size:0.83rem; color:var(--text-muted); margin-top:1rem;">
ℹ️ No class definitions found — this appears to be procedural/script code.
Coupling &amp; cohesion metrics are most meaningful for object-oriented code.
</div>""", unsafe_allow_html=True)

    # ────────────── TAB 4: Sequence Diagram ──────────────
    with tab4:
        st.markdown('<div class="section-title">Sequence Diagram — PlantUML</div>', unsafe_allow_html=True)

        plantuml_url    = data.get("plantuml_url", "")
        plantuml_syntax = data.get("plantuml_syntax", "")

        if plantuml_url:
            col_diag, col_syntax = st.columns([1.3, 0.7])

            with col_diag:
                st.markdown(
                    '<div class="metric-label" style="margin-bottom:0.6rem;">Rendered diagram</div>',
                    unsafe_allow_html=True,
                )
                try:
                    png_resp = requests.get(plantuml_url, timeout=12)
                    if (
                        png_resp.status_code == 200
                        and "image" in png_resp.headers.get("content-type", "")
                    ):
                        st.image(png_resp.content, use_column_width=True)
                        st.download_button(
                            "⬇️ Download PNG",
                            data=png_resp.content,
                            file_name="codelens_diagram.png",
                            mime="image/png",
                        )
                    else:
                        # Fallback: render via <img> tag (browser fetches directly)
                        st.markdown(
                            f'<a href="{plantuml_url}" target="_blank">'
                            f'<img src="{plantuml_url}" style="max-width:100%;'
                            f'border-radius:8px;border:1px solid #1e293b;" /></a>',
                            unsafe_allow_html=True,
                        )
                except Exception:
                    # If requests fails (offline/firewall) show link + inline img
                    st.markdown(
                        f"""
<div style="padding:0.8rem 1rem; background:rgba(233,69,96,0.06);
     border:1px solid rgba(233,69,96,0.25); border-radius:8px;
     font-size:0.82rem; color:var(--text-muted); margin-bottom:0.6rem;">
⚠️ Could not fetch diagram — check your internet connection.<br>
<a href="{plantuml_url}" target="_blank" style="color:#16c2d4;">
Open in browser ↗</a>
</div>
<img src="{plantuml_url}" style="max-width:100%; border-radius:8px;" />
""",
                        unsafe_allow_html=True,
                    )

            with col_syntax:
                st.markdown(
                    '<div class="metric-label" style="margin-bottom:0.6rem;">PlantUML source</div>',
                    unsafe_allow_html=True,
                )
                st.code(plantuml_syntax, language="text")
                st.download_button(
                    "⬇️ Download .puml",
                    data=plantuml_syntax,
                    file_name="codelens_diagram.puml",
                    mime="text/plain",
                )

            st.markdown("""
<div style="margin-top:0.8rem; font-size:0.75rem; color:var(--text-muted);">
💡 Diagram rendered by the free
<a href="https://plantuml.com" target="_blank" style="color:#16c2d4;">PlantUML public server</a>.
Paste the .puml source into
<a href="https://www.plantuml.com/plantuml/uml/" target="_blank" style="color:#16c2d4;">plantuml.com/uml</a>
to edit interactively.
</div>""", unsafe_allow_html=True)

        else:
            st.markdown("""
<div style="padding:1.5rem; text-align:center; color:var(--text-muted); font-size:0.85rem;">
    No diagram data returned. Re-run the analysis.
</div>""", unsafe_allow_html=True)

    # ────────────── TAB 5: Optimizer ──────────────
    with tab5:
        opt = data["optimization"]
        st.markdown('<div class="section-title">Static Analysis &amp; Optimization</div>', unsafe_allow_html=True)

        c1, c2, c3, c4 = st.columns([1.2, 1, 1, 1])
        with c1:
            st.markdown(score_ring(opt["score"]), unsafe_allow_html=True)
        with c2:
            st.markdown(metric_card("🔴 Critical", str(opt["summary"]["critical"]),
                                    "High-impact issues"), unsafe_allow_html=True)
        with c3:
            st.markdown(metric_card("🟡 Warnings", str(opt["summary"]["warning"]),
                                    "Should fix"), unsafe_allow_html=True)
        with c4:
            st.markdown(metric_card("🔵 Info", str(opt["summary"]["info"]),
                                    "Suggestions"), unsafe_allow_html=True)

        if opt["issues"]:
            st.markdown('<div class="section-title" style="margin-top:1.5rem;">Issues Found</div>', unsafe_allow_html=True)

            # Filter controls
            filter_col1, filter_col2 = st.columns([1, 3])
            with filter_col1:
                filter_sev = st.selectbox(
                    "Filter by severity",
                    ["All", "critical", "warning", "info"],
                    label_visibility="collapsed",
                )

            issues = opt["issues"]
            if filter_sev != "All":
                issues = [i for i in issues if i["severity"] == filter_sev]

            if issues:
                for issue in issues:
                    st.markdown(render_issue(issue), unsafe_allow_html=True)
            else:
                st.info(f"No {filter_sev} issues found.")
        else:
            st.markdown("""
<div style="text-align:center; padding:2rem; color:var(--text-muted);">
    <div style="font-size:2rem; margin-bottom:0.5rem;">✅</div>
    <div style="font-family:'Space Mono',monospace; font-size:0.85rem;">No issues found — clean code!</div>
</div>""", unsafe_allow_html=True)

        # Download cleaned code
        if opt.get("cleaned_code"):
            st.markdown('<div class="section-title" style="margin-top:1.5rem;">Annotated Code</div>', unsafe_allow_html=True)
            with st.expander("Preview annotated code"):
                st.code(opt["cleaned_code"], language=data["language"])
            ext = ".py" if data["language"] == "python" else ".java"
            st.download_button(
                "⬇️ Download Annotated Code",
                data=opt["cleaned_code"],
                file_name=f"codelens_annotated{ext}",
                mime="text/plain",
            )
