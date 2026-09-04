"""RevIQ read-only evaluation dashboard for the prototype."""

import json
import re
from pathlib import Path

import pandas as pd
import streamlit as st
import altair as alt


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "evaluation" / "metrics_report.md"
AUDIT_PATH = ROOT / "audit_log.jsonl"
SCOPE_PATH = ROOT / "SCOPE_LOCK.md"

st.set_page_config(
    page_title="RevIQ | Evaluation Dashboard",
    page_icon="N",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root { --line: #2d3b53; --muted: #91a4bd; --surface: #1a2438; --teal: #10b981; --amber: #f59e0b; --red: #ef4444; --cyan: #38bdf8; }
    .block-container { max-width: 1360px; padding: 1.65rem 2.35rem 3rem; }
    .brand { display: flex; align-items: baseline; gap: 12px; margin-bottom: 0.8rem; }
    .brand-name { color: #f1f5f9; font-size: 1.55rem; font-weight: 800; letter-spacing: 0; }
    .brand-label { color: var(--muted); font-size: 0.86rem; font-weight: 600; }
    .warning { background: #211d16; border: 1px solid #725523; border-left: 4px solid var(--amber);
        border-radius: 4px; color: #fcd34d; padding: 0.7rem 0.9rem; margin: 0 0 1.6rem;
    }
    .warning strong { color: #fbbf24; }
    .hero { border-bottom: 1px solid var(--line); padding: 0.2rem 0 1.55rem; margin-bottom: 1.4rem; }
    .eyebrow { color: var(--teal); font-size: 0.75rem; font-weight: 750; letter-spacing: 0.08em; text-transform: uppercase; }
    .anchor { color: #e2e8f0; font-size: 1.25rem; line-height: 1.48; max-width: 980px; margin: 0.45rem 0 0; }
    .section { border-top: 1px solid var(--line); padding-top: 1.15rem; margin-top: 1.75rem; }
    .section h2 { color: #f1f5f9; font-size: 1.03rem; letter-spacing: 0.01em; margin: 0; }
    .section p { color: var(--muted); font-size: 0.82rem; margin: 0.3rem 0 0.8rem; }
    [data-testid="stMetric"] { background: var(--surface); border: 1px solid var(--line); border-radius: 4px; padding: 0.75rem 0.9rem; min-height: 106px; }
    [data-testid="stMetricLabel"] { color: var(--muted); }
    [data-testid="stMetricValue"] { color: var(--ink); }
    .mini-note { color: var(--muted); font-size: 0.8rem; margin-top: 0.65rem; }
    .audit-meta { color: var(--muted); font-size: 0.82rem; margin-bottom: 0.35rem; }
    .scope-box { background: var(--surface); border: 1px solid var(--line); border-radius: 4px; padding: 0.9rem 1rem; overflow-wrap: anywhere; color: #cbd5e1; font-size: 0.84rem; line-height: 1.55; }
    .side-brand { color: #f1f5f9; font-size: 1.25rem; font-weight: 800; margin-bottom: 0; }
    .side-kicker { color: var(--cyan); font-size: 0.63rem; font-weight: 800; letter-spacing: 0.12em; }
    .side-meta { border-top: 1px solid var(--line); color: var(--muted); font-family: monospace; font-size: 0.65rem; letter-spacing: 0.08em; line-height: 1.9; margin-top: 2rem; padding-top: 0.7rem; }
    .pipeline-stage { background: var(--surface); border: 1px solid var(--line); border-top: 2px solid var(--cyan); border-radius: 4px; min-height: 84px; padding: 0.65rem 0.7rem; }
    .pipeline-num { color: var(--cyan); font-family: monospace; font-size: 0.68rem; }
    .pipeline-title { color: #f1f5f9; font-size: 0.78rem; font-weight: 750; letter-spacing: 0.04em; margin-top: 0.3rem; }
    .pipeline-copy { color: var(--muted); font-size: 0.68rem; line-height: 1.35; margin-top: 0.25rem; }
    [data-testid="stDataFrame"] { border: 1px solid var(--line); }
    code { color: #7dd3fc; }
    .scope-header { align-items: end; border-bottom: 1px solid var(--line); display: flex; gap: 0.8rem; justify-content: space-between; padding-bottom: 1rem; }
    .scope-index { color: var(--cyan); font-family: monospace; font-size: 0.9rem; letter-spacing: 0.08em; }
    .scope-title { color: #f1f5f9; font-size: 1.55rem; font-weight: 760; line-height: 1.1; }
    .scope-subtitle { color: var(--muted); font-size: 0.83rem; margin-top: 0.42rem; }
    .source-card, .purpose-card, .boundary-panel { background: var(--surface); border: 1px solid var(--line); border-radius: 4px; padding: 0.85rem 0.95rem; }
    .source-label, .micro-label { color: var(--cyan); font-family: monospace; font-size: 0.65rem; font-weight: 800; letter-spacing: 0.11em; }
    .source-file { color: #e2e8f0; font-family: monospace; font-size: 0.9rem; margin-top: 0.4rem; }
    .source-time { color: var(--muted); font-family: monospace; font-size: 0.68rem; margin-top: 0.45rem; }
    .purpose-card { align-items: center; display: flex; gap: 1rem; justify-content: space-between; margin-top: 1.2rem; }
    .purpose-copy { color: #cbd5e1; font-size: 0.88rem; line-height: 1.5; margin-top: 0.35rem; }
    .ready-state { border-left: 1px solid var(--line); min-width: 150px; padding-left: 1rem; }
    .ready-value { color: var(--teal); font-family: monospace; font-size: 0.82rem; font-weight: 800; margin-top: 0.35rem; }
    .ready-dot { color: var(--teal); font-size: 0.75rem; }
    .scope-card { background: var(--surface); border: 1px solid var(--line); border-radius: 4px; border-top: 2px solid var(--cyan); min-height: 126px; padding: 0.75rem 0.8rem; }
    .scope-card:nth-child(4n+2) { border-top-color: var(--teal); }
    .scope-card:nth-child(4n+3) { border-top-color: var(--amber); }
    .scope-card:nth-child(4n+4) { border-top-color: #818cf8; }
    .scope-card-number { color: var(--muted); font-family: monospace; font-size: 0.67rem; }
    .scope-card-title { color: #f1f5f9; font-size: 0.77rem; font-weight: 800; letter-spacing: 0.06em; margin: 0.55rem 0 0.45rem; }
    .scope-card-copy { color: #b8c5d6; font-size: 0.74rem; line-height: 1.42; }
    .boundary-panel { height: 100%; }
    .boundary-panel.in-scope { border-top: 2px solid var(--teal); }
    .boundary-panel.out-scope { border-top: 2px solid var(--red); }
    .boundary-heading { color: #f1f5f9; font-size: 0.78rem; font-weight: 800; letter-spacing: 0.08em; }
    .boundary-heading.in { color: var(--teal); }
    .boundary-heading.out { color: #fca5a5; }
    .boundary-row { border-top: 1px solid #2d3b53; padding: 0.58rem 0; }
    .boundary-category { color: var(--muted); font-family: monospace; font-size: 0.67rem; letter-spacing: 0.04em; }
    .boundary-copy { color: #cbd5e1; font-size: 0.76rem; line-height: 1.35; margin-top: 0.18rem; }
    .scope-caption { color: var(--muted); font-family: monospace; font-size: 0.68rem; letter-spacing: 0.08em; margin-top: 1rem; }
    @media (max-width: 700px) {
        .block-container { padding: 1.25rem 1rem 3rem; }
        .anchor { font-size: 1.15rem; }
        .brand { gap: 8px; }
        .pipeline-stage { min-height: 76px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def _read_report() -> str:
    return REPORT_PATH.read_text(encoding="utf-8")


def _metric(report: str, label: str) -> str:
    match = re.search(r"\|\s*" + re.escape(label) + r"\s*\|\s*([^|]+)\|", report)
    return match.group(1).strip() if match else "Unavailable"


def _read_audit() -> list[dict]:
    entries = []
    if not AUDIT_PATH.exists():
        return entries
    with AUDIT_PATH.open(encoding="utf-8") as audit_file:
        for line in audit_file:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def _audit_frame(entries: list[dict]) -> pd.DataFrame:
    rows = []
    for entry in entries:
        rows.append(
            {
                "timestamp": entry.get("timestamp", ""),
                "payment_id": entry.get("payment_id", ""),
                "phase": entry.get("phase", ""),
                "detail": json.dumps(entry.get("detail", {}), ensure_ascii=False),
            }
        )
    return pd.DataFrame(rows)


def _report_table(report: str, heading: str) -> pd.DataFrame:
    section = report.split(heading, 1)[1] if heading in report else ""
    section = section.split("\n## ", 1)[0]
    rows = re.findall(r"\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", section)
    return pd.DataFrame(
        [(left.strip(), right.strip()) for left, right in rows if left.strip() != "metric"],
        columns=["metric", "value"],
    )


def _scope_rows(scope_text: str) -> pd.DataFrame:
    """Parse the existing scope boundary table without changing its content."""
    boundary = scope_text.split("## Scope: In / Out Boundary", 1)[-1]
    boundary = boundary.split("## Explicitly Excluded From This Build", 1)[0]
    rows = []
    for line in boundary.splitlines():
        if not line.startswith("|") or line.startswith("| Component") or line.startswith("|---"):
            continue
        values = [value.strip() for value in line.strip("|").split("|")]
        if len(values) == 3:
            rows.append(values)
    return pd.DataFrame(rows, columns=["category", "in_scope", "out_of_scope"])


report = _read_report()
audit_df = _audit_frame(_read_audit())

st.sidebar.markdown('<div class="side-brand">RevIQ</div><div class="side-kicker">GOVERNED REVENUE RECOVERY</div>', unsafe_allow_html=True)
st.sidebar.markdown('<div class="side-meta">READ-ONLY<br>SIMULATION MODE<br>EVALUATION PHASE</div>', unsafe_allow_html=True)
view = st.sidebar.radio(
    "Navigate",
    ["01 / Overview", "02 / Evaluation", "03 / Governance", "04 / Planted Edge Cases", "05 / Audit Trail", "06 / Scope & Methodology"],
    label_visibility="collapsed",
)

st.markdown('<div class="brand"><span class="brand-name">RevIQ</span><span class="brand-label">Governed Revenue Recovery</span></div>', unsafe_allow_html=True)
st.markdown('<div class="warning"><strong>SIMULATED SYSTEM</strong> Phase 7 performs no real payment gateway calls and moves no real money.</div>', unsafe_allow_html=True)

if view.endswith("Overview"):
    st.markdown('<div class="hero"><div class="eyebrow">RevIQ / governed revenue recovery</div><div class="anchor">An AI agent that detects failed subscription payments, diagnoses failure causes, predicts recoverability, selects governed recovery actions, and proves the outcome through an immutable audit trail.</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="section"><h2>Evaluation Snapshot</h2><p>Official Phase 9 results from the held-out evaluation report.</p></div>', unsafe_allow_html=True)
    metric_columns = st.columns(4)
    metric_columns[0].metric("Recovery rate", _metric(report, "recovery rate"), "vs 0% no-action baseline")
    metric_columns[1].metric("Action accuracy", _metric(report, "action accuracy"), "Exact match")
    metric_columns[2].metric("Recoverability ROC-AUC", _metric(report, "recoverability ROC-AUC"), "Raw score")
    metric_columns[3].metric("AUTO_ESCALATED", _metric(report, "AUTO_ESCALATED count"), "of 33 gated rows")
    st.markdown('<div class="section"><h2>Financial Impact</h2><p>Simulated value recovered from the evaluated subscription renewal failures.</p></div>', unsafe_allow_html=True)
    impact = st.columns(3)
    impact[0].metric("LTV at risk", "INR 58.28L", "INR 5,827,770.91 exact")
    impact[1].metric("Simulated recovered", "INR 41.08L", "INR 4,107,584.89 exact")
    impact[2].metric("Recovery rate", "70.48%", "vs 0% no-action baseline")
    st.markdown('<div class="section"><h2>System Pipeline</h2><p>Every renewal failure follows the same inspectable path.</p></div>', unsafe_allow_html=True)
    pipeline = st.columns(7)
    stages = [("01", "DETECT", "Payment failure detected"), ("02", "DIAGNOSE", "Determine failure cause"), ("03", "PREDICT", "Estimate recoverability"), ("04", "DECIDE", "Select recovery action"), ("05", "GOVERN", "Apply policy constraints"), ("06", "EXECUTE", "Simulated action dispatch"), ("07", "AUDIT", "Record immutable evidence")]
    for column, (number, title, copy) in zip(pipeline, stages):
        with column:
            st.markdown('<div class="pipeline-stage"><div class="pipeline-num">{}</div><div class="pipeline-title">{}</div><div class="pipeline-copy">{}</div></div>'.format(number, title, copy), unsafe_allow_html=True)

elif view.endswith("Evaluation"):
    st.markdown('<div class="section"><h2>Evaluation Results</h2><p>Read-only metrics from the official Phase 9 report.</p></div>', unsafe_allow_html=True)
    metric_columns = st.columns(4)
    metric_columns[0].metric("Recovery rate", _metric(report, "recovery rate"))
    metric_columns[1].metric("Action accuracy", _metric(report, "action accuracy"))
    metric_columns[2].metric("Recoverability accuracy", _metric(report, "recoverability accuracy"))
    metric_columns[3].metric("Recoverability ROC-AUC", _metric(report, "recoverability ROC-AUC"))
    st.markdown("### Revenue recovery")
    st.dataframe(_report_table(report, "## Revenue Recovery"), hide_index=True, width="stretch")
    st.info("Action accuracy is 6.06%; the report documents a systematic optimistic recovery bias and 0 of 5 planted edge cases matched.")

elif view.endswith("Governance"):
    st.markdown('<div class="section"><h2>Governance Evidence</h2><p>Gate outcomes and compliance status, with native chart hover details.</p></div>', unsafe_allow_html=True)
    gate_data = pd.DataFrame({"status": ["PASSED", "AUTO_ESCALATED", "BLOCKED"], "rows": [31, 1, 1], "percentage": [93.9, 3.0, 3.0]})
    chart = alt.Chart(gate_data).mark_bar().encode(
        x=alt.X("status:N", sort=["PASSED", "AUTO_ESCALATED", "BLOCKED"], title=None),
        y=alt.Y("rows:Q", title="Rows"),
        color=alt.Color("status:N", scale=alt.Scale(domain=["PASSED", "AUTO_ESCALATED", "BLOCKED"], range=["#10B981", "#F59E0B", "#EF4444"]), legend=None),
        tooltip=[alt.Tooltip("status:N", title="Status"), alt.Tooltip("rows:Q", title="Count"), alt.Tooltip("percentage:Q", title="Percent", format=".1f")],
    ).properties(height=300)
    st.altair_chart(chart, width="stretch")
    st.caption("PASSED and OK use teal; AUTO_ESCALATED uses amber; BLOCKED and HALTED use muted red.")
    st.dataframe(pd.DataFrame({"compliance_status": ["OK"], "count": [33], "percentage": ["100.0%"]}), hide_index=True, width="stretch")

elif view.endswith("Planted Edge Cases"):
    st.markdown('<div class="section"><h2>Planted Edge Cases</h2><p>Complete five-row table from the official evaluation report.</p></div>', unsafe_allow_html=True)
    edge_start = report.split("## Planted Edge Cases", 1)[1] if "## Planted Edge Cases" in report else ""
    edge_match = re.search(r"(\| payment_id .*?)(?:\n\nCorrect final actions:|\Z)", edge_start, re.S)
    if edge_match:
        edge_rows = re.findall(r"\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", edge_match.group(1))
        if edge_rows:
            edge_frame = pd.DataFrame(edge_rows[1:], columns=["payment_id", "failure_code", "conflict", "ground_truth_best_action", "final_action", "gate_status", "match"])
            def color_match(value):
                return "color: #10B981; font-weight: 700" if value == "MATCH" else "color: #EF4444; font-weight: 700"
            st.dataframe(edge_frame.style.map(color_match, subset=["match"]), hide_index=True, width="stretch")
    st.caption("0 of 5 planted edge cases matched the ground-truth final action.")

elif view.endswith("Audit Trail"):
    st.markdown('<div class="section"><h2>Audit Trail Explorer</h2><p>Read-only evidence from the append-only audit log.</p></div>', unsafe_allow_html=True)
    filter_left, filter_right = st.columns([1, 1])
    phases = ["All phases"] + sorted(audit_df["phase"].dropna().unique().tolist()) if not audit_df.empty else ["All phases"]
    with filter_left:
        selected_phase = st.selectbox("Phase", phases)
    with filter_right:
        payment_query = st.text_input("Search payment ID or phase", placeholder="e.g. PMT-00081 or CONFIDENCE_GATE")
    filtered_audit = audit_df.copy()
    if selected_phase != "All phases":
        filtered_audit = filtered_audit[filtered_audit["phase"] == selected_phase]
    if payment_query:
        query_mask = filtered_audit["payment_id"].str.contains(payment_query, case=False, na=False) | filtered_audit["phase"].str.contains(payment_query, case=False, na=False)
        filtered_audit = filtered_audit[query_mask]
    st.caption("{} audit entries shown.".format(len(filtered_audit)))
    for _, entry in filtered_audit.head(100).iterrows():
        with st.expander("{} · {} · {}".format(entry["phase"], entry["payment_id"], entry["timestamp"])):
            st.caption("Phase: {}   |   Payment: {}".format(entry["phase"], entry["payment_id"]))
            st.code(entry["detail"], language="json")

elif view.endswith("Scope & Methodology"):
    if SCOPE_PATH.exists():
        scope_text = SCOPE_PATH.read_text(encoding="utf-8")
        scope_rows = _scope_rows(scope_text)
        scope_updated = pd.Timestamp(SCOPE_PATH.stat().st_mtime, unit="s").strftime("%Y-%m-%d %H:%M:%S")

        st.markdown(
            '<div class="scope-header"><div><div class="scope-index">06 / SCOPE &amp; METHODOLOGY</div><div class="scope-title">Scope &amp; Methodology</div><div class="scope-subtitle">What this evaluation covers, how it works, and the boundaries of the system.</div></div><div class="source-card"><div class="source-label">▣ &nbsp; SOURCE OF TRUTH</div><div class="source-file">SCOPE_LOCK.md</div><div class="source-time">LAST UPDATED / {}</div></div></div>'.format(scope_updated),
            unsafe_allow_html=True,
        )

        ready = "COMPLETE: no AI-path UNKNOWN diagnoses remain." in report
        st.markdown(
            '<div class="purpose-card"><div><div class="micro-label">PURPOSE</div><div class="purpose-copy">This document is the single source of truth for what RevIQ does and does not do. It defines the locked scope, evaluation boundaries, and compliance surface for subscription payment recovery.</div></div><div class="ready-state"><div class="micro-label">EVALUATION STATUS</div><div class="ready-value"><span class="ready-dot">●</span> {}</div></div></div>'.format("EVALUATION READY" if ready else "EVALUATION STATUS"),
            unsafe_allow_html=True,
        )

        st.markdown('<div class="section"><h2>Scope at a glance</h2><p>Eight locked dimensions of the recovery system.</p></div>', unsafe_allow_html=True)
        card_columns = st.columns(4)
        for index, row in scope_rows.iterrows():
            with card_columns[index % 4]:
                st.markdown(
                    '<div class="scope-card"><div class="scope-card-number">{:02d}</div><div class="scope-card-title">{} &nbsp; {}</div><div class="scope-card-copy">{}</div></div>'.format(index + 1, "◆", row["category"].upper(), row["in_scope"]),
                    unsafe_allow_html=True,
                )

        st.markdown('<div class="section"><h2>In-scope / out-of-scope boundary</h2><p>The same locked distinctions, presented for fast review.</p></div>', unsafe_allow_html=True)
        boundary_columns = st.columns(2)
        with boundary_columns[0]:
            st.markdown('<div class="boundary-panel in-scope"><div class="boundary-heading in">IN SCOPE</div>', unsafe_allow_html=True)
            for _, row in scope_rows.iterrows():
                st.markdown('<div class="boundary-row"><div class="boundary-category">{}</div><div class="boundary-copy">{}</div></div>'.format(row["category"].upper(), row["in_scope"]), unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with boundary_columns[1]:
            st.markdown('<div class="boundary-panel out-scope"><div class="boundary-heading out">OUT OF SCOPE</div>', unsafe_allow_html=True)
            for _, row in scope_rows.iterrows():
                st.markdown('<div class="boundary-row"><div class="boundary-category">{}</div><div class="boundary-copy">{}</div></div>'.format(row["category"].upper(), row["out_of_scope"]), unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="section"><h2>Detailed scope definition</h2><p>Complete source table preserved from SCOPE_LOCK.md.</p></div>', unsafe_allow_html=True)
        st.dataframe(scope_rows, hide_index=True, width="stretch")
        st.markdown('<div class="scope-caption">LAST GENERATED / {}</div>'.format(pd.Timestamp(REPORT_PATH.stat().st_mtime, unit="s").strftime("%Y-%m-%d %H:%M:%S")), unsafe_allow_html=True)
    else:
        st.warning("SCOPE_LOCK.md is unavailable.")

st.caption("Last regenerated: {}".format(pd.Timestamp(REPORT_PATH.stat().st_mtime, unit="s").strftime("%Y-%m-%d %H:%M:%S")))
