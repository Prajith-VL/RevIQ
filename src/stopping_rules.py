"""
RevIQ Phase 8: Stopping Rules and Compliance.

Applies simple row-level policy ceilings after simulated execution. This is
an additional governance layer, not a cross-row history or action executor.
"""

import math
import os
import sys

import pandas as pd

_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from audit_log import log_event


MAX_LIFETIME_RETRIES = 5
MAX_CONSECUTIVE_FAILURES = 3
ALLOWED_EXECUTION_RESULTS = {"SUCCESS", "FAILED", "NOT_APPLICABLE"}
ALLOWED_FINAL_ACTIONS = {
    "RETRY_NOW",
    "RETRY_LATER",
    "SEND_UPDATE_LINK",
    "ESCALATE_HUMAN",
    "STOP",
}
REQUIRED_INPUT_COLUMNS = [
    "payment_id",
    "final_action",
    "execution_result",
    "retry_count",
    "previous_failures",
    "customer_ltv",
]


def _validate_input(df: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_INPUT_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError("Missing required input columns: " + ", ".join(missing))

    invalid_actions = set(df["final_action"].astype(str)) - ALLOWED_FINAL_ACTIONS
    if invalid_actions:
        raise ValueError(
            "final_action contains unsupported actions: "
            + ", ".join(sorted(invalid_actions))
        )

    invalid_results = set(df["execution_result"].astype(str)) - ALLOWED_EXECUTION_RESULTS
    if invalid_results:
        raise ValueError(
            "execution_result contains unsupported results: "
            + ", ".join(sorted(invalid_results))
        )

    numeric_columns = ["retry_count", "previous_failures", "customer_ltv"]
    numeric_values = df[numeric_columns].apply(pd.to_numeric, errors="coerce")
    if numeric_values.isna().any(axis=None):
        raise ValueError(
            "retry_count, previous_failures, and customer_ltv must be numeric"
        )
    finite_values = numeric_values.apply(lambda column: column.map(math.isfinite))
    if not finite_values.all(axis=None):
        raise ValueError(
            "retry_count, previous_failures, and customer_ltv must be finite"
        )


def _check_row(row: pd.Series):
    retry_count = int(row["retry_count"])
    previous_failures = int(row["previous_failures"])
    execution_result = str(row["execution_result"])

    if retry_count > MAX_LIFETIME_RETRIES:
        return (
            "HALTED",
            "Retry count {} exceeds lifetime cap {}; further automated retries "
            "are policy-prohibited regardless of expected value.".format(
                retry_count,
                MAX_LIFETIME_RETRIES,
            ),
        )

    if (
        previous_failures >= MAX_CONSECUTIVE_FAILURES
        and execution_result == "FAILED"
    ):
        return (
            "HALTED",
            "{} prior failures plus this failed attempt exceeds the {} "
            "consecutive-failure threshold; halting further automation for "
            "this payment to avoid customer harassment risk.".format(
                previous_failures,
                MAX_CONSECUTIVE_FAILURES,
            ),
        )

    return "OK", ""


def apply_stopping_rules(df: pd.DataFrame) -> pd.DataFrame:
    """Append compliance results without mutating the input frame."""
    _validate_input(df)
    result = df.copy()

    statuses = []
    reasons = []

    for _, row in result.iterrows():
        status, reason = _check_row(row)
        statuses.append(status)
        reasons.append(reason)

    result["compliance_status"] = statuses
    result["compliance_reason"] = reasons

    for _, row in result.iterrows():
        log_event(
            payment_id=str(row["payment_id"]),
            phase="STOPPING_RULES",
            detail={
                "compliance_status": row["compliance_status"],
                "compliance_reason": row["compliance_reason"],
                "retry_count": row["retry_count"],
                "previous_failures": row["previous_failures"],
            },
        )

    return result


stopping_rules_batch = apply_stopping_rules
