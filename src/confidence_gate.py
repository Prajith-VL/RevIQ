"""
RevIQ Phase 6: Confidence Gate and Escalation.

Provides the deterministic checkpoint before Phase 7 execution. This module
only approves, blocks, or escalates a selected action; it never executes it.
"""

import math
import os
import sys
from typing import Dict, Tuple

import pandas as pd

_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from audit_log import log_event


MIN_DIAGNOSIS_CONFIDENCE = 0.70
MIN_RECOVERABILITY_FOR_AUTO_ACTION = 0.60
MIN_EXPECTED_VALUE_FOR_AUTO_ACTION = 10.0
MIN_CONFIDENCE_FOR_ML_AUTOACTION = 0.85

SAFE_ACTIONS = {"ESCALATE_HUMAN", "STOP"}
ALLOWED_GATE_STATUSES = {"PASSED", "BLOCKED", "AUTO_ESCALATED"}
REQUIRED_INPUT_COLUMNS = [
    "payment_id",
    "diagnosis_category",
    "diagnosis_confidence",
    "recoverability_score",
    "recoverability_method",
    "chosen_action",
    "expected_value",
]


def _validate_input(df: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_INPUT_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError("Missing required input columns: " + ", ".join(missing))

    numeric_columns = [
        "diagnosis_confidence",
        "recoverability_score",
        "expected_value",
    ]
    numeric_values = df[numeric_columns].apply(pd.to_numeric, errors="coerce")
    if numeric_values.isna().any(axis=None):
        raise ValueError(
            "diagnosis_confidence, recoverability_score, and expected_value "
            "must be numeric"
        )
    finite_values = numeric_values.apply(lambda column: column.map(math.isfinite))
    if not finite_values.all(axis=None):
        raise ValueError(
            "diagnosis_confidence, recoverability_score, and expected_value "
            "must be finite"
        )
    if not numeric_values["diagnosis_confidence"].between(0.0, 1.0).all():
        raise ValueError("diagnosis_confidence must be between 0.0 and 1.0")
    if not numeric_values["recoverability_score"].between(0.0, 1.0).all():
        raise ValueError("recoverability_score must be between 0.0 and 1.0")


def _threshold_checks(row: pd.Series) -> Dict[str, bool]:
    diagnosis_confidence = float(row["diagnosis_confidence"])
    recoverability_score = float(row["recoverability_score"])
    expected_value = float(row["expected_value"])

    return {
        "diagnosis_confidence_pass": (
            diagnosis_confidence >= MIN_DIAGNOSIS_CONFIDENCE
        ),
        "recoverability_pass": (
            recoverability_score >= MIN_RECOVERABILITY_FOR_AUTO_ACTION
        ),
        "expected_value_pass": (
            expected_value >= MIN_EXPECTED_VALUE_FOR_AUTO_ACTION
        ),
        "ml_confidence_pass": (
            diagnosis_confidence >= MIN_CONFIDENCE_FOR_ML_AUTOACTION
        ),
    }


def _gate_row(row: pd.Series) -> Tuple[str, str, str, Dict[str, bool]]:
    chosen_action = str(row["chosen_action"])
    diagnosis_confidence = float(row["diagnosis_confidence"])
    recoverability_score = float(row["recoverability_score"])
    expected_value = float(row["expected_value"])
    method = str(row["recoverability_method"])
    checks = _threshold_checks(row)

    if chosen_action in SAFE_ACTIONS:
        return (
            "PASSED",
            chosen_action,
            "No confidence gate required: action does not move money or "
            "requires human judgment already.",
            checks,
        )

    if not checks["diagnosis_confidence_pass"]:
        return (
            "BLOCKED",
            "ESCALATE_HUMAN",
            "Diagnosis confidence {:.2f} below threshold {:.2f}; too "
            "uncertain to automate.".format(
                diagnosis_confidence,
                MIN_DIAGNOSIS_CONFIDENCE,
            ),
            checks,
        )

    if not checks["recoverability_pass"]:
        return (
            "BLOCKED",
            "STOP",
            "Recoverability {:.2f} below threshold {:.2f}; not worth "
            "pursuing automatically.".format(
                recoverability_score,
                MIN_RECOVERABILITY_FOR_AUTO_ACTION,
            ),
            checks,
        )

    if not checks["expected_value_pass"]:
        return (
            "BLOCKED",
            "STOP",
            "Expected value INR {:.2f} below threshold INR {:.2f}; not "
            "worth the action cost.".format(
                expected_value,
                MIN_EXPECTED_VALUE_FOR_AUTO_ACTION,
            ),
            checks,
        )

    if (
        method == "ML"
        and not checks["ml_confidence_pass"]
        and chosen_action not in SAFE_ACTIONS
    ):
        return (
            "AUTO_ESCALATED",
            "ESCALATE_HUMAN",
            "ML-scored recovery path with moderate confidence routed to "
            "human review as an extra precaution, per policy.",
            checks,
        )

    return (
        "PASSED",
        chosen_action,
        "All thresholds cleared: diagnosis confidence {:.2f}, "
        "recoverability {:.2f}, expected value INR {:.2f}.".format(
            diagnosis_confidence,
            recoverability_score,
            expected_value,
        ),
        checks,
    )


def apply_confidence_gate(df: pd.DataFrame) -> pd.DataFrame:
    """Append the governed final action without mutating the input frame."""
    _validate_input(df)
    result = df.copy()

    statuses = []
    reasons = []
    final_actions = []
    audit_checks = []

    for _, row in result.iterrows():
        status, final_action, reason, checks = _gate_row(row)
        statuses.append(status)
        reasons.append(reason)
        final_actions.append(final_action)
        audit_checks.append(checks)

    result["gate_status"] = statuses
    result["gate_reason"] = reasons
    result["final_action"] = final_actions

    for index, row in result.iterrows():
        log_event(
            payment_id=str(row["payment_id"]),
            phase="CONFIDENCE_GATE",
            detail={
                "chosen_action": row["chosen_action"],
                "gate_status": row["gate_status"],
                "gate_reason": row["gate_reason"],
                "final_action": row["final_action"],
                "thresholds": {
                    "MIN_DIAGNOSIS_CONFIDENCE": MIN_DIAGNOSIS_CONFIDENCE,
                    "MIN_RECOVERABILITY_FOR_AUTO_ACTION": (
                        MIN_RECOVERABILITY_FOR_AUTO_ACTION
                    ),
                    "MIN_EXPECTED_VALUE_FOR_AUTO_ACTION": (
                        MIN_EXPECTED_VALUE_FOR_AUTO_ACTION
                    ),
                    "MIN_CONFIDENCE_FOR_ML_AUTOACTION": (
                        MIN_CONFIDENCE_FOR_ML_AUTOACTION
                    ),
                },
                "threshold_checks": audit_checks[index],
            },
        )

    return result


confidence_gate_batch = apply_confidence_gate
