"""Northstar read-only evaluation dashboard for the RevIQ prototype."""

import json
import re
from pathlib import Path

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "evaluation" / "metrics_report.md"
AUDIT_PATH = ROOT / "audit_log.jsonl"
SCOPE_PATH = ROOT / "SCOPE_LOCK.md"

st.set_page_config(
    page_title="RevIQ | Evaluation Dashboard",
    page_icon="N",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    :root {
        --ink: #17202a;
        --muted: #697586;
        --line: #e5e7eb;
        --surface: #f7f8fa;
        --blue: #2563eb;
        --blue-soft: #eff6ff;
        --warning: #92400e;
        --warning-bg: #fff7ed;
    }
    .stApp { background: #ffffff; color: var(--ink); }
    [data-testid="stHeader"] { background: rgba(255,255,255,0.94); }
    .block-container { max-width: 1180px; padding: 2rem 2.5rem 4rem; }
    .brand { display: flex; align-items: baseline; gap: 12px; margin-bottom: 1.25rem; }
    .brand-name { color: var(--ink); font-size: 1.55rem; font-weight: 750; letter-spacing: 0; }
    .brand-label { color: var(--muted); font-size: 0.86rem; font-weight: 600; }
    .warning {
        background: var(--warning-bg); border: 1px solid #fed7aa; border-left: 4px solid #f59e0b;
        border-radius: 6px; color: var(--warning); padding: 0.85rem 1rem; margin: 0 0 2rem;
    }
    .warning strong { color: #78350f; }
    .hero { border-bottom: 1px solid var(--line); padding: 0.5rem 0 2rem; margin-bottom: 2rem; }
    .eyebrow { color: var(--blue); font-size: 0.75rem; font-weight: 750; letter-spacing: 0.08em; text-transform: uppercase; }
    .anchor { color: var(--ink); font-size: 1.45rem; line-height: 1.45; max-width: 950px; margin: 0.45rem 0 0; }
    .section { border-top: 1px solid var(--line); padding-top: 1.6rem; margin-top: 2.6rem; }
    .section h2 { color: var(--ink); font-size: 1.18rem; margin: 0; }
    .section p { color: var(--muted); font-size: 0.92rem; margin: 0.35rem 0 1.1rem; }
    [data-testid="stMetric"] { background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 1rem 1.1rem; }
    [data-testid="stMetricLabel"] { color: var(--muted); }
    [data-testid="stMetricValue"] { color: var(--ink); }
    .mini-note { color: var(--muted); font-size: 0.8rem; margin-top: 0.65rem; }
    .audit-meta { color: var(--muted); font-size: 0.82rem; margin-bottom: 0.35rem; }
    .scope-box { background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 1rem 1.15rem; }
    @media (max-width: 700px) {
        .block-container { padding: 1.25rem 1rem 3rem; }
        .anchor { font-size: 1.15rem; }
        .brand { gap: 8px; }
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


report = _read_report()
audit_entries = _read_audit()
audit_df = _audit_frame(audit_entries)

st.markdown(
    '<div class="brand"><span class="brand-name">Northstar</span><span class="brand-label">Evaluation Dashboard</span></div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="warning"><strong>Simulation only.</strong> Phase 7 performs no real payment gateway calls and moves no real money.</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="hero"><div class="eyebrow">Governed revenue recovery</div><div class="anchor">A governed AI agent that watches failed subscription payments, diagnoses why they failed, predicts whether they\'re recoverable, selects the recovery action with the highest expected value, executes it within strict policy bounds, and proves exactly how much revenue it recovered — while knowing when to stop and hand off to a human.</div></div>',
    unsafe_allow_html=True,
)

st.markdown('<div class="section"><h2>Evaluation Snapshot</h2><p>Official Phase 9 results from the held-out evaluation report.</p></div>', unsafe_allow_html=True)
metric_columns = st.columns(4)
metric_columns[0].metric("Recovery rate", _metric(report, "recovery rate"), "INR 41,07,584.89 recovered")
metric_columns[1].metric("Action accuracy", _metric(report, "action accuracy"), "Exact match")
metric_columns[2].metric("Recoverability ROC-AUC", _metric(report, "recoverability ROC-AUC"), "Raw score")
metric_columns[3].metric("AUTO_ESCALATED", _metric(report, "AUTO_ESCALATED count"), "of 33 gated rows")

st.markdown('<div class="section"><h2>Governance Evidence</h2><p>Gate outcomes and compliance status remain visible without editorial interpretation.</p></div>', unsafe_allow_html=True)
governance_left, governance_right = st.columns([1.35, 1])
with governance_left:
    gate_data = pd.DataFrame(
        {"status": ["PASSED", "AUTO_ESCALATED", "BLOCKED"], "rows": [31, 1, 1]}
    ).set_index("status")
    st.bar_chart(gate_data, y="rows", color="#2563eb", height=260)
    st.caption("Gate status distribution: 31 PASSED, 1 AUTO_ESCALATED, 1 BLOCKED.")
with governance_right:
    st.dataframe(
        pd.DataFrame({"compliance_status": ["OK"], "percentage": ["100.0%"]}),
        hide_index=True,
        use_container_width=True,
    )
    st.markdown('<div class="mini-note">AUTO_ESCALATED sends an ML-scored moderate-confidence path to human review before execution.</div>', unsafe_allow_html=True)

st.markdown('<div class="section"><h2>Planted Edge Cases</h2><p>All five conflicting-signal cases from the official evaluation report.</p></div>', unsafe_allow_html=True)
edge_start = report.split("## Planted Edge Cases", 1)[1] if "## Planted Edge Cases" in report else ""
edge_match = re.search(r"(\| payment_id .*?)(?:\n\nCorrect final actions:|\Z)", edge_start, re.S)
if edge_match:
    edge_rows = re.findall(r"\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", edge_match.group(1))
    if edge_rows:
        edge_frame = pd.DataFrame(edge_rows[1:], columns=["payment_id", "failure_code", "conflict", "ground_truth_best_action", "final_action", "gate_status", "match"])
        st.dataframe(edge_frame, hide_index=True, use_container_width=True)
else:
    st.info("Planted edge-case table unavailable in the report.")

st.markdown('<div class="section"><h2>Audit Trail Explorer</h2><p>Read-only evidence from the append-only audit log.</p></div>', unsafe_allow_html=True)
filter_left, filter_right = st.columns([1, 1])
phases = ["All phases"] + sorted(audit_df["phase"].dropna().unique().tolist()) if not audit_df.empty else ["All phases"]
with filter_left:
    selected_phase = st.selectbox("Phase", phases, label_visibility="collapsed")
with filter_right:
    payment_query = st.text_input("Payment ID", placeholder="Search payment ID", label_visibility="collapsed")
filtered_audit = audit_df.copy()
if selected_phase != "All phases":
    filtered_audit = filtered_audit[filtered_audit["phase"] == selected_phase]
if payment_query:
    filtered_audit = filtered_audit[filtered_audit["payment_id"].str.contains(payment_query, case=False, na=False)]
st.caption("{} audit entries shown.".format(len(filtered_audit)))
for index, entry in filtered_audit.head(100).iterrows():
    label = "{} · {} · {}".format(entry["phase"], entry["payment_id"], entry["timestamp"])
    with st.expander(label):
        st.markdown('<div class="audit-meta">Phase: <strong>{}</strong> &nbsp; Payment: <strong>{}</strong></div>'.format(entry["phase"], entry["payment_id"]), unsafe_allow_html=True)
        st.code(entry["detail"], language="json")

st.markdown('<div class="section"><h2>Scope and Methodology</h2><p>Source of truth: SCOPE_LOCK.md.</p></div>', unsafe_allow_html=True)
if SCOPE_PATH.exists():
    scope_text = SCOPE_PATH.read_text(encoding="utf-8")
    scope_start = scope_text.find("## Scope: In / Out Boundary")
    scope_end = scope_text.find("## Explicitly Excluded From This Build")
    scope_excerpt = scope_text[scope_start:scope_end if scope_end != -1 else None]
    st.markdown('<div class="scope-box">{}</div>'.format(scope_excerpt.replace("\n", "<br>")), unsafe_allow_html=True)
else:
    st.warning("SCOPE_LOCK.md is unavailable.")
