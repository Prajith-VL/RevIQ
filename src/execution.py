"""
RevIQ Phase 7: Simulated Execution.

COMPLIANCE GUARDRAIL: this module performs NO real payment gateway calls,
initiates NO real money movement, and contacts NO external service. It only
creates deterministic, auditable outcomes for downstream evaluation.
"""

import hashlib
import math
import os
import random
import sys
from typing import Tuple

import pandas as pd

_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from audit_log import log_event


AUTOMATED_ACTIONS = {
    "RETRY_NOW",
    "RETRY_LATER",
    "SEND_UPDATE_LINK",
}
NON_EXECUTING_ACTIONS = {"STOP", "ESCALATE_HUMAN"}
ALLOWED_EXECUTION_RESULTS = {"SUCCESS", "FAILED", "NOT_APPLICABLE"}
ALLOWED_ACTIONS = AUTOMATED_ACTIONS | NON_EXECUTING_ACTIONS
REQUIRED_INPUT_COLUMNS = [
    "payment_id",
    "final_action",
    "gate_status",
    "recoverability_score",
    "customer_ltv",
]


def _deterministic_random(payment_id: str) -> float:
    """Return a stable pseudo-random value derived from one payment ID."""
    digest = hashlib.sha256(str(payment_id).encode("utf-8")).digest()
    payment_id_hash = int.from_bytes(digest[:8], byteorder="big")
    return random.Random(payment_id_hash).random()


def _validate_input(df: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_INPUT_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError("Missing required input columns: " + ", ".join(missing))

    invalid_actions = set(df["final_action"].astype(str)) - ALLOWED_ACTIONS
    if invalid_actions:
        raise ValueError(
            "final_action contains unsupported actions: "
            + ", ".join(sorted(invalid_actions))
        )

    numeric_columns = ["recoverability_score", "customer_ltv"]
    numeric_values = df[numeric_columns].apply(pd.to_numeric, errors="coerce")
    if numeric_values.isna().any(axis=None):
        raise ValueError("recoverability_score and customer_ltv must be numeric")
    finite_values = numeric_values.apply(lambda column: column.map(math.isfinite))
    if not finite_values.all(axis=None):
        raise ValueError("recoverability_score and customer_ltv must be finite")
    if not numeric_values["recoverability_score"].between(0.0, 1.0).all():
        raise ValueError("recoverability_score must be between 0.0 and 1.0")


def _simulate_row(row: pd.Series) -> Tuple[str, float, str]:
    final_action = str(row["final_action"])
    score = float(row["recoverability_score"])
    customer_ltv = float(row["customer_ltv"])

    if final_action == "STOP":
        return (
            "NOT_APPLICABLE",
            0.0,
            "No action taken per policy; payment marked as unrecovered.",
        )

    if final_action == "ESCALATE_HUMAN":
        return (
            "NOT_APPLICABLE",
            0.0,
            "Handed off to human agent; outcome pending outside this system's "
            "automated scope.",
        )

    random_value = _deterministic_random(str(row["payment_id"]))
    if random_value < score:
        return (
            "SUCCESS",
            customer_ltv,
            "Simulated {} succeeded (P={:.2f}).".format(final_action, score),
        )

    return (
        "FAILED",
        0.0,
        "Simulated {} failed (P={:.2f}).".format(final_action, score),
    )


def execute_simulation(df: pd.DataFrame) -> pd.DataFrame:
    """Append simulated outcomes without mutating or executing real actions."""
    _validate_input(df)
    result = df.copy()

    execution_results = []
    recovered_revenue = []
    execution_notes = []

    for _, row in result.iterrows():
        outcome, revenue, note = _simulate_row(row)
        execution_results.append(outcome)
        recovered_revenue.append(revenue)
        execution_notes.append(note)

    result["execution_result"] = execution_results
    result["simulated_revenue_recovered"] = recovered_revenue
    result["execution_note"] = execution_notes

    for index, row in result.iterrows():
        log_event(
            payment_id=str(row["payment_id"]),
            phase="EXECUTION",
            detail={
                "final_action": row["final_action"],
                "execution_result": row["execution_result"],
                "simulated_revenue_recovered": (
                    row["simulated_revenue_recovered"]
                ),
                "execution_note": row["execution_note"],
                "simulated": True,
            },
        )

    return result


execution_batch = execute_simulation


if __name__ == "__main__":
    print("SAFETY: Phase 7 performs NO real payment gateway calls or money movement.")
    print("Use execute_simulation(df) with the DataFrame returned by Phase 6.")
