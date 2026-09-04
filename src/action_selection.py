"""
RevIQ Phase 5: Expected-Value Action Selection.

Selects the highest-value eligible recovery action from an already-scored
subscription renewal failure. This phase only selects; it does not execute
an action or apply the Phase 6 confidence gate.
"""

import math
import os
import sys
from typing import Dict, List, Tuple

import pandas as pd

_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from audit_log import log_event


# Named costs keep the business assumptions visible and easy to tune.
COST_RETRY_NOW = 2.0
COST_RETRY_LATER = 2.0
COST_SEND_UPDATE_LINK = 5.0
COST_ESCALATE_HUMAN = 150.0
COST_STOP = 0.0
MAX_RETRIES = 3

ACTIONS = [
    "RETRY_NOW",
    "RETRY_LATER",
    "SEND_UPDATE_LINK",
    "ESCALATE_HUMAN",
    "STOP",
]
REQUIRED_INPUT_COLUMNS = [
    "payment_id",
    "diagnosis_category",
    "recoverability_score",
    "recoverability_method",
    "customer_ltv",
    "retry_count",
    "previous_failures",
]


def _validate_input(df: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_INPUT_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError("Missing required input columns: " + ", ".join(missing))

    numeric_columns = ["recoverability_score", "customer_ltv", "retry_count"]
    numeric_values = df[numeric_columns].apply(pd.to_numeric, errors="coerce")
    if numeric_values.isna().any(axis=None):
        raise ValueError("recoverability_score, customer_ltv, and retry_count must be numeric")
    finite_values = numeric_values.apply(lambda column: column.map(math.isfinite))
    if not finite_values.all(axis=None):
        raise ValueError("recoverability_score, customer_ltv, and retry_count must be finite")
    if not numeric_values["recoverability_score"].between(0.0, 1.0).all():
        raise ValueError("recoverability_score must be between 0.0 and 1.0")


def _candidate_evs(row: pd.Series) -> Dict[str, float]:
    score = float(row["recoverability_score"])
    ltv = float(row["customer_ltv"])
    retries = int(row["retry_count"])
    category = str(row["diagnosis_category"])

    def value(cost: float) -> float:
        return (score * ltv) - cost

    return {
        "RETRY_NOW": value(COST_RETRY_NOW) if category == "TEMPORARY" else None,
        "RETRY_LATER": value(COST_RETRY_LATER) if retries < MAX_RETRIES else None,
        "SEND_UPDATE_LINK": (
            value(COST_SEND_UPDATE_LINK)
            if category == "CUSTOMER_ACTION_NEEDED"
            else None
        ),
        "ESCALATE_HUMAN": value(COST_ESCALATE_HUMAN),
        "STOP": -COST_STOP,
    }


def _choose_action(candidate_evs: Dict[str, float]) -> Tuple[str, float, str]:
    # Ties favor the least invasive action in this fixed order. This avoids
    # escalating a case merely because human review tied with automation.
    tie_priority = [
        "RETRY_NOW",
        "RETRY_LATER",
        "SEND_UPDATE_LINK",
        "STOP",
        "ESCALATE_HUMAN",
    ]
    eligible = [action for action in tie_priority if candidate_evs[action] is not None]
    chosen_action = eligible[0]

    for action in eligible[1:]:
        if candidate_evs[action] > candidate_evs[chosen_action]:
            chosen_action = action

    return chosen_action, float(candidate_evs[chosen_action]), tie_priority


def _rationale(
    row: pd.Series,
    chosen_action: str,
    chosen_ev: float,
    candidate_evs: Dict[str, float],
    tie_priority: List[str],
) -> str:
    eligible = [action for action in tie_priority if candidate_evs[action] is not None]
    runner_up = next((action for action in eligible if action != chosen_action), None)
    score = float(row["recoverability_score"])

    if runner_up is None:
        runner_up_text = "no alternative"
    else:
        runner_up_text = "{} (EV=INR {:.2f})".format(
            runner_up, candidate_evs[runner_up]
        )

    return (
        "{} chosen (EV=INR {:.2f}) over {}: recoverability {:.2f} drives "
        "the highest eligible expected value."
    ).format(chosen_action, chosen_ev, runner_up_text, score)


def select_actions(df: pd.DataFrame) -> pd.DataFrame:
    """Append the EV-based action decision without mutating the input frame."""
    _validate_input(df)
    result = df.copy()

    chosen_actions = []
    expected_values = []
    rationales = []
    all_candidate_evs = []

    for _, row in result.iterrows():
        candidate_evs = _candidate_evs(row)
        chosen_action, chosen_ev, tie_priority = _choose_action(candidate_evs)
        rationale = _rationale(
            row,
            chosen_action,
            chosen_ev,
            candidate_evs,
            tie_priority,
        )

        chosen_actions.append(chosen_action)
        expected_values.append(chosen_ev)
        rationales.append(rationale)
        all_candidate_evs.append(candidate_evs)

    result["chosen_action"] = chosen_actions
    result["expected_value"] = expected_values
    result["action_rationale"] = rationales

    for index, row in result.iterrows():
        log_event(
            payment_id=str(row["payment_id"]),
            phase="ACTION_SELECTION",
            detail={
                "chosen_action": row["chosen_action"],
                "expected_value": row["expected_value"],
                "action_rationale": row["action_rationale"],
                "candidate_action_expected_values": all_candidate_evs[index],
            },
        )

    return result


# Descriptive alias matching the phase's pipeline language.
action_selection_batch = select_actions
