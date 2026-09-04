"""
diagnosis.py -- RevIQ Phase 3: Diagnosis Layer

A hybrid diagnosis layer: deterministic rules handle clear-cut failure codes,
and Gemini reasoning handles ambiguous or context-dependent failures.

Responsibilities:
  1. Classify failures deterministically if possible (classify_failure_deterministic).
    2. Call the configured LLM provider for reasoning if ambiguous (diagnose_with_ai).
  3. Combine rules and AI for batch processing (diagnose_batch).
  4. Write structured audit trail entries via audit_log.log_event.
"""

import os
import sys
import json
import time
import pandas as pd
from google import genai
from google.genai.errors import ServerError

# Ensure src/ is in the python path
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from audit_log import log_event


def classify_failure_deterministic(row) -> dict:
    """Classify clear-cut cases deterministically.

    Args:
        row: Series or dict-like with failure_code and failure_category.

    Returns:
        dict: {category, confidence, explanation} or None if ambiguous.
    """
    code = row.get("failure_code")
    cat = row.get("failure_category")

    # Genuinely ambiguous cases in source data or codes
    if cat == "AMBIGUOUS":
        return None

    if code in ("CARD_DECLINED_SOFT", "INSUFFICIENT_FUNDS", "OTP_TIMEOUT", "RISK_FLAGGED"):
        return None

    if code in ("BANK_TIMEOUT", "ISSUER_UNAVAILABLE"):
        return {
            "category": "TEMPORARY",
            "confidence": 1.0,
            "explanation": f"Transient error '{code}' detected. The bank/issuer is temporarily unreachable."
        }
    elif code == "CARD_EXPIRED":
        return {
            "category": "CUSTOMER_ACTION_NEEDED",
            "confidence": 1.0,
            "explanation": "The customer's card has expired. Customer must update their payment credentials."
        }
    elif code == "CARD_DECLINED_HARD":
        return {
            "category": "PERMANENT",
            "confidence": 1.0,
            "explanation": "Hard decline received from payment gateway. Card is permanently blocked or invalid."
        }

    return None


def diagnose_with_ai(row) -> dict:
    """Fall back to Gemini reasoning for ambiguous/context-dependent cases.

    Args:
        row: Series or dict-like with row context.

    Returns:
        dict: {category, confidence, explanation}
    """
    fallback = {
        "category": "UNKNOWN",
        "confidence": 0.0,
        "explanation": "AI diagnosis failed, flagged for manual review"
    }

    payment_id = str(row.get("payment_id"))
    cache_path = os.path.join(
        os.path.dirname(_SRC_DIR), "data", "diagnosis_ai_cache.json"
    )
    try:
        with open(cache_path, "r", encoding="utf-8") as cache_file:
            cache = json.load(cache_file)
        if not isinstance(cache, dict):
            cache = {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        cache = {}

    if payment_id in cache and isinstance(cache[payment_id], dict):
        return cache[payment_id]

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return fallback

    try:
        client = genai.Client(api_key=api_key)

        prompt = f"""You are an AI subscription payment diagnosis agent. Analyze this payment failure context and classify the failure category.

Payment Context:
- Failure Code: {row.get('failure_code')}
- Failure Category (raw): {row.get('failure_category')}
- Previous Successful Renewals: {row.get('previous_successes')}
- Previous Failures: {row.get('previous_failures')}
- Retry Count: {row.get('retry_count')}
- Customer LTV: INR {row.get('customer_ltv')}
- Subscription Age (days): {row.get('subscription_age_days')}
- Days Since Last Payment: {row.get('days_since_last_payment')}

Based on the failure code and the customer's history, determine the most likely root-cause failure category.
The category must be one of: TEMPORARY, CUSTOMER_ACTION_NEEDED, PERMANENT, AMBIGUOUS.
Assign a confidence score between 0.0 and 1.0.
Provide a 1-2 sentence explanation in plain English suitable for an audit log.

You must respond ONLY with a raw JSON object and no other text, markdown formatting, or preamble. Example:
{{"category": "TEMPORARY", "confidence": 0.85, "explanation": "The payment failed due to insufficient funds, but this is a long-standing customer with 36 successful payments. We should retry later."}}
"""

        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=prompt,
                )
                break
            except ServerError:
                if attempt == 2:
                    raise
                time.sleep(2)

        content = response.text.strip()

        # Clean markdown fences if present
        if content.startswith("`"):
            lines = content.splitlines()
            if lines[0].startswith("`"):
                content = "\n".join(lines[1:-1]) if lines[-1].startswith("`") else "\n".join(lines[1:])
        content = content.strip()

        parsed = json.loads(content)

        result = {
            "category": str(parsed.get("category", "UNKNOWN")),
            "confidence": float(parsed.get("confidence", 0.0)),
            "explanation": str(parsed.get("explanation", "AI diagnosis completed."))
        }

        cache[payment_id] = result
        with open(cache_path, "w", encoding="utf-8") as cache_file:
            json.dump(cache, cache_file, indent=2)
        return result
    except Exception:
        return fallback


def diagnose_batch(df: pd.DataFrame) -> pd.DataFrame:
    """Process a batch, combining deterministic rules and AI diagnosis.

    Args:
        df: DataFrame containing at-risk payment records.

    Returns:
        DataFrame with columns diagnosis_category, diagnosis_confidence,
        diagnosis_explanation, and diagnosis_method appended.
    """
    df_out = df.copy()

    categories = []
    confidences = []
    explanations = []
    methods = []

    for idx, row in df.iterrows():
        res = classify_failure_deterministic(row)
        if res is not None:
            method = "RULE"
        else:
            res = diagnose_with_ai(row)
            method = "AI"

        categories.append(res["category"])
        confidences.append(res["confidence"])
        explanations.append(res["explanation"])
        methods.append(method)

        log_event(
            payment_id=str(row["payment_id"]),
            phase="DIAGNOSIS",
            detail={
                "diagnosis_category": res["category"],
                "diagnosis_confidence": res["confidence"],
                "diagnosis_explanation": res["explanation"],
                "diagnosis_method": method
            }
        )

        if method == "AI":
            time.sleep(4)

    df_out["diagnosis_category"] = categories
    df_out["diagnosis_confidence"] = confidences
    df_out["diagnosis_explanation"] = explanations
    df_out["diagnosis_method"] = methods

    return df_out


if __name__ == "__main__":
    from detection import load_batch, detect_at_risk

    repo_root = os.path.dirname(_SRC_DIR)
    ref_path = os.path.join(repo_root, "data", "reference_set.csv")

    print("RevIQ Phase 3 - Diagnosis Layer")
    print("=" * 45)
    print("Input:", ref_path)
    print()

    # 1. Load & detect
    df_full = load_batch(ref_path)
    df_at_risk = detect_at_risk(df_full)

    # 2. Diagnose
    df_diagnosed = diagnose_batch(df_at_risk)

    # 3. Report
    total = len(df_diagnosed)
    rule_count = (df_diagnosed["diagnosis_method"] == "RULE").sum()
    ai_count = (df_diagnosed["diagnosis_method"] == "AI").sum()

    rule_pct = rule_count / total * 100 if total else 0.0
    ai_pct = ai_count / total * 100 if total else 0.0

    print("Diagnosis Run Summary")
    print("-" * 45)
    print(f"  Total diagnosed records : {total}")
    print(f"  RULE-based diagnoses    : {rule_count} ({rule_pct:.1f}%)")
    print(f"  AI-based diagnoses      : {ai_count} ({ai_pct:.1f}%)")
    print()

    print("Example Diagnoses")
    print("-" * 45)

    # Find 1 rule-based example
    rule_examples = df_diagnosed[df_diagnosed["diagnosis_method"] == "RULE"]
    if not rule_examples.empty:
        r = rule_examples.iloc[0]
        print(f"  [RULE-based] Payment ID: {r['payment_id']} ({r['failure_code']})")
        print(f"    Category    : {r['diagnosis_category']}")
        print(f"    Confidence  : {r['diagnosis_confidence']}")
        print(f"    Explanation : {r['diagnosis_explanation']}")
        print()

    # Find up to 2 AI-based examples
    ai_examples = df_diagnosed[df_diagnosed["diagnosis_method"] == "AI"]
    for idx, r in enumerate(ai_examples.head(2).itertuples()):
        print(f"  [AI-based #{idx+1}] Payment ID: {r.payment_id} ({r.failure_code})")
        print(f"    Category    : {r.diagnosis_category}")
        print(f"    Confidence  : {r.diagnosis_confidence}")
        print(f"    Explanation : {r.diagnosis_explanation}")
        print()

    print("Phase 3 complete.")
