"""
detection.py -- RevIQ Phase 2: Detection Layer

Pure deterministic, rules-based filtering and tagging of failed payment
records.  No AI/LLM calls anywhere in this module.

Responsibilities:
  1. Load a batch CSV (reference_set or held_out_test_set).
  2. Filter to at-risk records (outcome == NOT_RECOVERED | PENDING).
  3. Tag each at-risk record with a severity level (HIGH/MEDIUM/LOW).
  4. Emit one audit log entry per record via audit_log.log_event().
  5. Return a summary dict for reporting.

Does NOT:
  - Diagnose why a payment failed   (Phase 3)
  - Score recoverability            (Phase 4)
  - Select or execute any action    (Phases 5-7)
"""

import os
import sys
import pandas as pd

# Allow running as a script from repo root or from src/
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from audit_log import log_event

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
LTV_HIGH_THRESHOLD    = 50_000.0
LTV_MEDIUM_LOW_BOUND  = 5_000.0
LTV_MEDIUM_HIGH_BOUND = 50_000.0
FAILURES_HIGH         = 3
FAILURES_MEDIUM_LOW   = 1
FAILURES_MEDIUM_HIGH  = 2
RETRY_HIGH            = 2

AT_RISK_OUTCOMES = {"NOT_RECOVERED", "PENDING"}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_batch(filepath: str) -> pd.DataFrame:
    """Load a RevIQ dataset CSV into a DataFrame.

    Args:
        filepath: Absolute or relative path to reference_set.csv or
                  held_out_test_set.csv.

    Returns:
        DataFrame with all original columns.  Boolean columns
        (ground_truth_recoverable, is_planted_edge_case) are
        coerced to Python bool.
    """
    df = pd.read_csv(filepath, encoding="utf-8")

    # Coerce boolean columns that arrive as strings from CSV
    for col in ("ground_truth_recoverable", "is_planted_edge_case"):
        if col in df.columns:
            df[col] = df[col].map({"True": True, "False": False, True: True, False: False})

    return df


def _compute_severity(row: pd.Series) -> str:
    """Deterministic severity classification for one at-risk record.

    Rules (evaluated in priority order):
      HIGH   if customer_ltv > 50,000
              OR previous_failures >= 3
              OR retry_count >= 2
      MEDIUM if customer_ltv in (5,000, 50,000]
              OR previous_failures in {1, 2}
      LOW    otherwise
    """
    ltv      = float(row["customer_ltv"])
    failures = int(row["previous_failures"])
    retries  = int(row["retry_count"])

    if ltv > LTV_HIGH_THRESHOLD or failures >= FAILURES_HIGH or retries >= RETRY_HIGH:
        return "HIGH"
    if (LTV_MEDIUM_LOW_BOUND <= ltv <= LTV_MEDIUM_HIGH_BOUND
            or FAILURES_MEDIUM_LOW <= failures <= FAILURES_MEDIUM_HIGH):
        return "MEDIUM"
    return "LOW"


def detect_at_risk(df: pd.DataFrame) -> pd.DataFrame:
    """Filter a loaded batch to at-risk records and tag them.

    At-risk = outcome in {NOT_RECOVERED, PENDING}.
    RECOVERED records are already resolved and excluded from all
    downstream pipeline processing.

    Adds columns:
      severity    (str)  HIGH | MEDIUM | LOW
      days_at_risk (int) same value as days_since_last_payment,
                         renamed for clarity in reporting

    Calls log_event() once per original record (both at-risk and
    resolved) for a complete audit trail.

    Args:
        df: DataFrame returned by load_batch().

    Returns:
        Filtered DataFrame containing only at-risk records, with
        severity and days_at_risk columns appended.  Index is reset.
    """
    at_risk_mask = df["outcome"].isin(AT_RISK_OUTCOMES)

    # Log every record for full auditability
    for _, row in df.iterrows():
        is_at_risk = bool(at_risk_mask.loc[row.name])
        detail = {
            "at_risk": is_at_risk,
            "outcome": row["outcome"],
        }
        if is_at_risk:
            detail["severity"] = _compute_severity(row)
        log_event(
            payment_id=str(row["payment_id"]),
            phase="DETECTION",
            detail=detail,
        )

    at_risk_df = df[at_risk_mask].copy().reset_index(drop=True)

    # Add derived columns
    at_risk_df["severity"]     = at_risk_df.apply(_compute_severity, axis=1)
    at_risk_df["days_at_risk"] = at_risk_df["days_since_last_payment"].astype(int)

    return at_risk_df


def summarize_batch(df: pd.DataFrame) -> dict:
    """Compute a reporting summary from the at-risk DataFrame.

    Args:
        df: DataFrame returned by detect_at_risk() -- at-risk records
            only, already tagged with severity.

    Returns:
        dict with keys:
          total_records_loaded       -- populated externally (see __main__)
          total_at_risk              -- len(df)
          total_revenue_at_risk_inr  -- sum of amount for at-risk records
          severity_counts            -- {HIGH: n, MEDIUM: n, LOW: n}
    """
    severity_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    if "severity" in df.columns:
        for level in ("HIGH", "MEDIUM", "LOW"):
            severity_counts[level] = int((df["severity"] == level).sum())

    return {
        "total_records_loaded":      None,   # filled in __main__
        "total_at_risk":             len(df),
        "total_revenue_at_risk_inr": round(float(df["amount"].sum()), 2),
        "severity_counts":           severity_counts,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import os

    repo_root = os.path.dirname(_SRC_DIR)
    ref_path  = os.path.join(repo_root, "data", "reference_set.csv")

    print("RevIQ Phase 2 - Detection Layer")
    print("=" * 45)
    print("Input:", ref_path)
    print()

    # 1. Load
    df_full = load_batch(ref_path)

    # 2. Detect
    df_at_risk = detect_at_risk(df_full)

    # 3. Summarize
    summary = summarize_batch(df_at_risk)
    summary["total_records_loaded"] = len(df_full)

    # 4. Print
    print("Detection Summary")
    print("-" * 45)
    print("  Total records loaded      :", summary["total_records_loaded"])
    print("  Total at-risk records     :", summary["total_at_risk"])
    print("  Revenue at risk (INR)     : Rs.", summary["total_revenue_at_risk_inr"])
    print("  Severity breakdown:")
    for level in ("HIGH", "MEDIUM", "LOW"):
        n = summary["severity_counts"][level]
        pct = n / summary["total_at_risk"] * 100 if summary["total_at_risk"] else 0
        bar = "#" * int(pct / 3)
        print("    {:<8} {:>3}  ({:5.1f}%)  {}".format(level, n, pct, bar))
    print()
    print("Audit entries written to: audit_log.jsonl")
    print()
    print("Phase 2 complete. Do NOT run on held_out_test_set.csv.")
    print("That file is reserved for final evaluation only.")
