"""Run the final RevIQ evaluation once against the held-out test set.

This script reads the held-out CSV exactly once, runs the unchanged pipeline,
and writes a read-only markdown summary. It never writes per-row predictions.
"""

import os
import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from src.detection import detect_at_risk
from src.diagnosis import diagnose_batch
from src.recoverability_scoring import recoverability_score_batch
from src.action_selection import select_actions
from src.confidence_gate import apply_confidence_gate
from src.execution import execute_simulation
from src.stopping_rules import apply_stopping_rules
from src.audit_log import log_event


REPORT_PATH = REPO_ROOT / "evaluation" / "metrics_report.md"

EDGE_CASE_CONFLICTS = {
    "PMT-00121": "BANK_TIMEOUT with retry_count=3 and previous_failures=5",
    "PMT-00122": "CARD_EXPIRED with customer_ltv=INR 5,12,500 and 41 prior successes",
    "PMT-00123": "CARD_DECLINED_HARD with previous_failures=0 and 18 prior successes",
    "PMT-00124": "INSUFFICIENT_FUNDS with 36 prior successes and 4 prior failures",
    "PMT-00125": "RISK_FLAGGED with customer_ltv=INR 149 and subscription_age_days=35",
}


def _format_number(value: float) -> str:
    return "{:.2f}".format(float(value))


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    columns = [str(column) for column in frame.columns]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in frame.itertuples(index=False, name=None):
        cells = [str(value).replace("|", "\\|") for value in row]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _distribution(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    counts = frame[column].value_counts(dropna=False)
    total = len(frame)
    return pd.DataFrame(
        {
            column: counts.index.astype(str),
            "count": counts.values,
            "percentage": [100.0 * count / total if total else 0.0 for count in counts.values],
        }
    )


def _run_pipeline(held_out: pd.DataFrame) -> pd.DataFrame:
    at_risk = detect_at_risk(held_out)
    diagnosed = diagnose_batch(at_risk)
    scored = recoverability_score_batch(diagnosed)
    selected = select_actions(scored)
    gated = apply_confidence_gate(selected)
    executed = execute_simulation(gated)
    return apply_stopping_rules(executed)


def _build_report(held_out: pd.DataFrame, final_df: pd.DataFrame) -> tuple[str, dict]:
    ground_truth = held_out[
        ["payment_id", "ground_truth_recoverable", "ground_truth_best_action"]
    ]
    evaluated = final_df.copy()
    if "ground_truth_recoverable" not in evaluated.columns:
        evaluated = evaluated.merge(ground_truth, on="payment_id", how="left")

    actual_recoverable = evaluated["ground_truth_recoverable"].astype(bool)
    predicted_recoverable = evaluated["recoverability_score"] >= 0.5
    recoverability_accuracy = accuracy_score(actual_recoverable, predicted_recoverable)
    recoverability_precision = precision_score(
        actual_recoverable, predicted_recoverable, zero_division=0
    )
    recoverability_recall = recall_score(
        actual_recoverable, predicted_recoverable, zero_division=0
    )
    try:
        recoverability_auc = roc_auc_score(
            actual_recoverable, evaluated["recoverability_score"]
        )
    except ValueError:
        recoverability_auc = float("nan")

    action_accuracy = accuracy_score(
        evaluated["ground_truth_best_action"], evaluated["final_action"]
    )
    action_confusion = pd.crosstab(
        evaluated["ground_truth_best_action"],
        evaluated["final_action"],
        rownames=["ground_truth"],
        colnames=["final_action"],
    ).reset_index()

    total_ltv_at_risk = float(held_out["customer_ltv"].sum())
    total_recovered = float(final_df["simulated_revenue_recovered"].sum())
    recovery_rate = total_recovered / total_ltv_at_risk if total_ltv_at_risk else 0.0

    gate_distribution = _distribution(final_df, "gate_status")
    compliance_distribution = _distribution(final_df, "compliance_status")
    auto_escalated_count = int((final_df["gate_status"] == "AUTO_ESCALATED").sum())

    unknown = final_df[
        (final_df["diagnosis_method"] == "AI")
        & (final_df["diagnosis_category"] == "UNKNOWN")
    ]
    unknown_count = len(unknown)
    unknown_percentage = 100.0 * unknown_count / len(final_df) if len(final_df) else 0.0

    edge_columns = [
        "payment_id",
        "failure_code",
        "ground_truth_best_action",
        "final_action",
        "gate_status",
    ]
    edges = final_df[final_df["is_planted_edge_case"] == True].copy()
    if "ground_truth_best_action" not in edges.columns:
        edges = edges.merge(ground_truth, on="payment_id", how="left")
    if not edges.empty:
        edge_report = edges[edge_columns].copy()
        edge_report.insert(
            2,
            "conflict",
            edge_report["payment_id"].map(EDGE_CASE_CONFLICTS).fillna("Not specified"),
        )
        edge_report["match"] = (
            edge_report["final_action"] == edge_report["ground_truth_best_action"]
        ).map({True: "MATCH", False: "MISMATCH"})
    else:
        edge_report = pd.DataFrame(
            columns=["payment_id", "failure_code", "conflict", "ground_truth_best_action", "final_action", "gate_status", "match"]
        )
    edge_correct = int((edge_report["match"] == "MATCH").sum())

    headline_metrics = {
        "recovery_rate": recovery_rate,
        "action_accuracy": action_accuracy,
        "recoverability_accuracy": recoverability_accuracy,
        "recoverability_auc": recoverability_auc,
        "auto_escalated_count": auto_escalated_count,
        "unknown_diagnosis_count": unknown_count,
        "total_ltv_at_risk": total_ltv_at_risk,
        "total_simulated_revenue_recovered": total_recovered,
        "planted_edge_cases_correct": edge_correct,
    }
    log_event(
        payment_id="BATCH",
        phase="EVALUATION",
        detail=headline_metrics,
    )

    recoverability_metrics = pd.DataFrame(
        {
            "metric": ["accuracy", "precision", "recall", "ROC-AUC"],
            "value": [
                _format_number(recoverability_accuracy),
                _format_number(recoverability_precision),
                _format_number(recoverability_recall),
                "N/A" if pd.isna(recoverability_auc) else _format_number(recoverability_auc),
            ],
        }
    )
    revenue_metrics = pd.DataFrame(
        {
            "metric": [
                "total_ltv_at_risk_INR",
                "total_simulated_revenue_recovered_INR",
                "recovery_rate",
            ],
            "value": [
                _format_number(total_ltv_at_risk),
                _format_number(total_recovered),
                "{:.2%}".format(recovery_rate),
            ],
        }
    )
    unknown_ids = ", ".join(unknown["payment_id"].astype(str).tolist()) or "None"
    completeness = (
        "COMPLETE: no AI-path UNKNOWN diagnoses remain."
        if unknown_count == 0
        else "INCOMPLETE: {} AI-path UNKNOWN diagnoses remain; affected payment_ids: {}. "
        "Do not treat these final metrics as pitch-deck complete until quota permits a rerun."
        .format(unknown_count, unknown_ids)
    )

    sections = [
        "# RevIQ Phase 9 Evaluation Report",
        "",
        "Evaluation ran on the held-out set through the full existing pipeline. No thresholds, weights, or model parameters were tuned.",
        "",
        "## Headline Metrics",
        "",
        "| metric | value |\n|---|---:|",
        "| recovery rate | {:.2%} |".format(recovery_rate),
        "| action accuracy | {:.2%} |".format(action_accuracy),
        "| recoverability accuracy | {:.2%} |".format(recoverability_accuracy),
        "| recoverability ROC-AUC | {} |".format("N/A" if pd.isna(recoverability_auc) else _format_number(recoverability_auc)),
        "| AUTO_ESCALATED count | {} |".format(auto_escalated_count),
        "",
        "## Recoverability Scoring",
        "",
        _markdown_table(recoverability_metrics),
        "",
        "## Action Selection",
        "",
        "Exact-match accuracy: **{:.2%}**".format(action_accuracy),
        "",
        _markdown_table(action_confusion),
        "",
        "## Revenue Recovery",
        "",
        _markdown_table(revenue_metrics),
        "",
        "## Governance",
        "",
        "### Gate Status",
        "",
        _markdown_table(gate_distribution),
        "",
        "### Compliance Status",
        "",
        _markdown_table(compliance_distribution),
        "",
        "AUTO_ESCALATED rows: **{}**".format(auto_escalated_count),
        "",
        "## Diagnosis Reliability",
        "",
        "| metric | value |\n|---|---:|",
        "| AI-path UNKNOWN count | {} |".format(unknown_count),
        "| AI-path UNKNOWN percentage | {:.2f}% |".format(unknown_percentage),
        "",
        completeness,
        "",
        "## Planted Edge Cases",
        "",
        _markdown_table(edge_report),
        "",
        "Correct final actions: **{} of {}**".format(edge_correct, len(edge_report)),
        "",
        "## Evaluation Scope",
        "",
        "The report is summary-only. No per-row prediction artifact was written.",
    ]
    return "\n".join(sections) + "\n", headline_metrics


def main() -> None:
    # This is the sole held-out read in the project lifecycle.
    held_out = pd.read_csv(REPO_ROOT / "data" / "held_out_test_set.csv", encoding="utf-8")
    final_df = _run_pipeline(held_out)
    report, metrics = _build_report(held_out, final_df)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(report)
    print("Evaluation report written to: {}".format(REPORT_PATH))
    print("Headline metrics:", metrics)


if __name__ == "__main__":
    main()
