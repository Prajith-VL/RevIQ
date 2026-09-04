"""
RevIQ Phase 4: Recoverability Scoring.

Scores subscription renewal failures without executing a recovery action.
The model is deliberately small and numeric so its coefficients can be
explained to a judge; known diagnosis outcomes stay deterministic.
"""

import os
import sys
from typing import Dict, List, Tuple

import pandas as pd
from sklearn.linear_model import LogisticRegression

_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from audit_log import log_event


PHASE = "RECOVERABILITY_SCORING"
MINIMUM_LABELED_ROWS = 30
FEATURE_COLUMNS = [
    "previous_successes",
    "previous_failures",
    "retry_count",
    "subscription_age_days",
    "days_since_last_payment",
    "diagnosis_confidence",
    "historical_success_rate",
]
REQUIRED_INPUT_COLUMNS = [
    "payment_id",
    "failure_code",
    "diagnosis_category",
    "diagnosis_confidence",
    "previous_successes",
    "previous_failures",
    "retry_count",
    "customer_ltv",
    "subscription_age_days",
    "days_since_last_payment",
]


def _reference_path() -> str:
    """Return the only permitted training-data path."""
    repo_root = os.path.dirname(_SRC_DIR)
    return os.path.join(repo_root, "data", "reference_set.csv")


def _validate_reference_path(reference_path: str) -> None:
    # Restrict fitting to the development set so a production call cannot
    # accidentally contaminate the Phase 9 held-out evaluation.
    if os.path.basename(os.path.normpath(reference_path)).lower() != "reference_set.csv":
        raise ValueError("Recoverability scoring may fit only on data/reference_set.csv")


def _features(df: pd.DataFrame) -> pd.DataFrame:
    if "diagnosis_confidence" not in df.columns and "failure_category" in df.columns:
        # Phase 1 data has the diagnosis category but not Phase 3 confidence;
        # use category certainty only for fitting, while runtime data must
        # provide the actual diagnosis confidence.
        category_confidence = {
            "TEMPORARY": 0.95,
            "CUSTOMER_ACTION_NEEDED": 0.90,
            "PERMANENT": 0.95,
            "AMBIGUOUS": 0.55,
        }
        df = df.copy()
        df["diagnosis_confidence"] = df["failure_category"].map(category_confidence)
    features = df[
        [
            "previous_successes",
            "previous_failures",
            "retry_count",
            "subscription_age_days",
            "days_since_last_payment",
            "diagnosis_confidence",
        ]
    ].apply(pd.to_numeric, errors="coerce")
    features["historical_success_rate"] = (
        features["previous_successes"]
        / (features["previous_successes"] + features["previous_failures"] + 1)
    )
    return features[FEATURE_COLUMNS]


def _load_model(reference_path: str) -> Tuple[LogisticRegression, List[str]]:
    _validate_reference_path(reference_path)
    reference = pd.read_csv(reference_path, encoding="utf-8")

    label_column = "ground_truth_recoverable"
    if label_column not in reference.columns:
        raise ValueError(
            "reference_set.csv must contain ground_truth_recoverable for fitting"
        )

    training = _features(reference)
    labels = reference[label_column].map(
        {True: 1, False: 0, "True": 1, "False": 0, 1: 1, 0: 0}
    )
    usable = training.notna().all(axis=1) & labels.notna()
    training = training.loc[usable]
    labels = labels.loc[usable].astype(int)

    if len(training) < MINIMUM_LABELED_ROWS:
        raise RuntimeError(
            "Only {} usable labeled rows found; use the weighted-rule fallback "
            "instead of fitting an unstable logistic model.".format(len(training))
        )
    if labels.nunique() < 2:
        raise RuntimeError(
            "Reference labels contain only one class; use the weighted-rule "
            "fallback instead of fitting logistic regression."
        )

    model = LogisticRegression(max_iter=1000, random_state=42)
    model.fit(training, labels)
    coefficients = [
        "{}={:.4f}".format(name, coefficient)
        for name, coefficient in zip(FEATURE_COLUMNS, model.coef_[0])
    ]
    print("Recoverability logistic coefficients: " + ", ".join(coefficients))
    return model, FEATURE_COLUMNS


def _fallback_score(row: pd.Series) -> float:
    """Use a transparent score when reference data cannot support a fit."""
    successes = float(row["previous_successes"])
    failures = float(row["previous_failures"])
    retries = float(row["retry_count"])
    confidence = float(row["diagnosis_confidence"])
    historical_rate = successes / (successes + failures + 1.0)
    score = (
        0.45 * historical_rate
        + 0.20 * min(successes / 10.0, 1.0)
        + 0.15 * (1.0 - min(failures / 5.0, 1.0))
        + 0.15 * (1.0 - min(retries / 3.0, 1.0))
        + 0.05 * confidence
    )
    return max(0.0, min(1.0, score))


def _top_factors(row: pd.Series, method: str, score: float) -> str:
    successes = int(row["previous_successes"])
    failures = int(row["previous_failures"])
    retries = int(row["retry_count"])
    category = str(row["diagnosis_category"])

    if category == "PERMANENT":
        return "permanent failure category, effectively unrecoverable"
    if category == "TEMPORARY" and retries == 0:
        return "temporary failure, first-time failure"

    factors = [
        "{} prior successful renewals".format(successes),
        "{} prior failed renewals".format(failures),
        "{} retries already attempted".format(retries),
    ]
    if method == "RULE":
        factors.append("weighted fallback used because the reference fit was insufficient")
    return ", ".join(factors[:3])


def _validate_input(df: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_INPUT_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError("Missing required input columns: " + ", ".join(missing))


def recoverability_score_batch(
    df: pd.DataFrame, reference_path: str = None
) -> pd.DataFrame:
    """Append recoverability score and method while preserving the input frame.

    Rules handle objectively resolved diagnoses first. Only the remaining
    cases use ML, because re-modeling a certain diagnosis adds complexity
    without adding judgment value.
    """
    _validate_input(df)
    result = df.copy()
    reference_path = reference_path or _reference_path()

    model = None
    fit_note = ""
    try:
        model, _ = _load_model(reference_path)
    except RuntimeError as error:
        fit_note = str(error)
        print("Recoverability scoring: " + fit_note)

    scores = []
    methods = []
    explanations = []
    ml_mask = []

    for _, row in result.iterrows():
        category = str(row["diagnosis_category"])
        retries = int(row["retry_count"])
        if category == "PERMANENT":
            score, method = 0.05, "RULE"
        elif category == "TEMPORARY" and retries == 0:
            score, method = 0.90, "RULE"
        elif model is None:
            score, method = _fallback_score(row), "RULE"
        else:
            score, method = None, "ML"
        scores.append(score)
        methods.append(method)
        ml_mask.append(score is None)
        explanations.append(_top_factors(row, method, score or 0.0))

    if model is not None and any(ml_mask):
        ml_rows = result.loc[ml_mask]
        ml_features = _features(ml_rows)
        if ml_features.isna().any(axis=None):
            raise ValueError("Input feature columns must contain numeric values")
        ml_scores = model.predict_proba(ml_features)[:, 1]
        ml_index = 0
        for index, is_ml in enumerate(ml_mask):
            if is_ml:
                scores[index] = float(ml_scores[ml_index])
                explanations[index] = _top_factors(
                    result.iloc[index], "ML", scores[index]
                )
                ml_index += 1

    result["recoverability_score"] = [max(0.0, min(1.0, float(score))) for score in scores]
    result["recoverability_method"] = methods

    for index, row in result.iterrows():
        detail = {
            "recoverability_score": row["recoverability_score"],
            "recoverability_method": row["recoverability_method"],
            "top_contributing_factors": explanations[index],
        }
        if fit_note:
            detail["fit_note"] = fit_note
        log_event(
            payment_id=str(row["payment_id"]),
            phase=PHASE,
            detail=detail,
        )

    return result


# Short alias for callers that prefer the phase name as a verb.
score_recoverability = recoverability_score_batch
