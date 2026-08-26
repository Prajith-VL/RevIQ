"""
generate_dataset.py — RevIQ Phase 1: Synthetic Data Generation

Generates two CSVs deterministically (fixed seed=42):
  data/reference_set.csv       — 70 records for development/tuning
  data/held_out_test_set.csv   — 50 records for final evaluation only
                                  (includes 5 planted ambiguous edge cases)

Run from repo root:
    python src/generate_dataset.py

Do NOT add diagnosis, scoring, or action-selection logic here.
This script produces DATA ONLY.
"""

import csv
import os
import random
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------
SEED = 42
random.seed(SEED)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TOTAL_RECORDS = 120
REFERENCE_SIZE = 70
HELD_OUT_SIZE = 50

MERCHANT_IDS = ["MER-001", "MER-002", "MER-003", "MER-004", "MER-005"]
PAYMENT_METHODS = ["UPI", "CARD", "NETBANKING", "WALLET"]
CONTACT_PREFS = ["EMAIL", "SMS", "WHATSAPP"]

FAILURE_CODES = [
    "BANK_TIMEOUT",
    "INSUFFICIENT_FUNDS",
    "CARD_EXPIRED",
    "CARD_DECLINED_SOFT",
    "CARD_DECLINED_HARD",
    "RISK_FLAGGED",
    "OTP_TIMEOUT",
    "ISSUER_UNAVAILABLE",
]

# Failure code to failure_category
FAILURE_CATEGORY = {
    "BANK_TIMEOUT":        "TEMPORARY",
    "ISSUER_UNAVAILABLE":  "TEMPORARY",
    "OTP_TIMEOUT":         "TEMPORARY",
    "INSUFFICIENT_FUNDS":  "AMBIGUOUS",
    "CARD_DECLINED_SOFT":  "AMBIGUOUS",
    "CARD_EXPIRED":        "CUSTOMER_ACTION_NEEDED",
    "CARD_DECLINED_HARD":  "PERMANENT",
    "RISK_FLAGGED":        "AMBIGUOUS",
}

# Amount tier: (low, high, weight)
AMOUNT_TIERS = [
    (99,    500,   0.40),
    (500,   5000,  0.45),
    (5000,  50000, 0.15),
]

NOW = datetime(2026, 8, 26, 12, 0, 0)
NINETY_DAYS_AGO = NOW - timedelta(days=90)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def random_amount():
    roll = random.random()
    cumulative = 0.0
    for lo, hi, weight in AMOUNT_TIERS:
        cumulative += weight
        if roll < cumulative:
            return round(random.uniform(lo, hi), 2)
    return round(random.uniform(99, 500), 2)


def random_timestamp():
    offset_seconds = random.randint(0, 90 * 24 * 3600)
    ts = NINETY_DAYS_AGO + timedelta(seconds=offset_seconds)
    return ts.strftime("%Y-%m-%dT%H:%M:%S")


def derive_ground_truth(failure_code, previous_failures, retry_count,
                        customer_ltv, noise_roll):
    """
    Apply correlation rules then noise.
    Returns (ground_truth_recoverable: bool, ground_truth_best_action: str)
    """
    # Rule 1: RISK_FLAGGED -> always ESCALATE_HUMAN
    if failure_code == "RISK_FLAGGED":
        recoverable = random.random() < 0.55
        return recoverable, "ESCALATE_HUMAN"

    # Rule 2: CARD_EXPIRED -> recoverable but needs update link
    if failure_code == "CARD_EXPIRED":
        if noise_roll < 0.10:          # 10% noise: card won't be updated
            return False, "STOP"
        return True, "SEND_UPDATE_LINK"

    # Rule 3: CARD_DECLINED_HARD
    if failure_code == "CARD_DECLINED_HARD":
        if previous_failures >= 3:
            if noise_roll < 0.15 and customer_ltv > 15000:
                return False, "ESCALATE_HUMAN"
            return False, "STOP"
        else:
            if noise_roll < 0.20:
                return False, "STOP"
            return True, "RETRY_LATER"

    # Rule 4: Transient codes -> RETRY_NOW (or RETRY_LATER if already retried)
    if failure_code in ("BANK_TIMEOUT", "ISSUER_UNAVAILABLE", "OTP_TIMEOUT"):
        if noise_roll < 0.15:          # 15% noise: transient that didn't resolve
            return False, "RETRY_LATER"
        if retry_count >= 2:
            return True, "RETRY_LATER"
        return True, "RETRY_NOW"

    # Rule 5: INSUFFICIENT_FUNDS
    if failure_code == "INSUFFICIENT_FUNDS":
        if previous_failures >= 4:
            if noise_roll < 0.20 and customer_ltv > 10000:
                return False, "ESCALATE_HUMAN"
            return False, "STOP"
        if noise_roll < 0.15:
            return False, "STOP"
        return True, "RETRY_LATER"

    # Rule 6: CARD_DECLINED_SOFT
    if failure_code == "CARD_DECLINED_SOFT":
        if previous_failures >= 3:
            if noise_roll < 0.25 and customer_ltv > 20000:
                return False, "ESCALATE_HUMAN"
            return False, "STOP"
        if noise_roll < 0.15:
            return False, "STOP"
        return True, "RETRY_LATER"

    return False, "ESCALATE_HUMAN"


def derive_outcome(recoverable, best_action):
    if recoverable:
        if best_action == "STOP":
            return "NOT_RECOVERED"
        roll = random.random()
        if roll < 0.80:
            return "RECOVERED"
        elif roll < 0.90:
            return "NOT_RECOVERED"
        else:
            return "PENDING"
    else:
        roll = random.random()
        if roll < 0.07:
            return "RECOVERED"
        elif roll < 0.85:
            return "NOT_RECOVERED"
        else:
            return "PENDING"


# ---------------------------------------------------------------------------
# Record builder
# ---------------------------------------------------------------------------

def build_record(payment_id):
    cust_num = random.randint(1, 999)
    customer_id = "CUST-{:04d}".format(cust_num)
    merchant_id = random.choice(MERCHANT_IDS)
    amount = random_amount()
    timestamp = random_timestamp()
    failure_code = random.choices(
        FAILURE_CODES,
        weights=[14, 12, 12, 14, 10, 8, 14, 16],
        k=1,
    )[0]
    failure_category = FAILURE_CATEGORY[failure_code]
    previous_successes = random.randint(0, 48)
    previous_failures = random.randint(0, 5)
    retry_count = random.randint(0, 3)
    subscription_age_days = random.randint(30, 1200)
    ltv_base = previous_successes * (amount * 0.9)
    customer_ltv = round(max(ltv_base + random.gauss(0, amount * 2), 0), 2)
    days_since_last_payment = random.randint(25, 45)
    payment_method = random.choices(
        PAYMENT_METHODS, weights=[35, 35, 20, 10], k=1
    )[0]
    contact_channel_pref = random.choices(
        CONTACT_PREFS, weights=[40, 35, 25], k=1
    )[0]
    noise_roll = random.random()
    recoverable, best_action = derive_ground_truth(
        failure_code, previous_failures, retry_count, customer_ltv, noise_roll
    )
    outcome = derive_outcome(recoverable, best_action)

    return {
        "payment_id":               payment_id,
        "customer_id":              customer_id,
        "merchant_id":              merchant_id,
        "amount":                   amount,
        "timestamp":                timestamp,
        "failure_code":             failure_code,
        "failure_category":         failure_category,
        "previous_successes":       previous_successes,
        "previous_failures":        previous_failures,
        "retry_count":              retry_count,
        "customer_ltv":             customer_ltv,
        "subscription_age_days":    subscription_age_days,
        "days_since_last_payment":  days_since_last_payment,
        "payment_method":           payment_method,
        "contact_channel_pref":     contact_channel_pref,
        "ground_truth_recoverable": recoverable,
        "ground_truth_best_action": best_action,
        "outcome":                  outcome,
        "is_planted_edge_case":     False,
    }


# ---------------------------------------------------------------------------
# Edge case builder
# ---------------------------------------------------------------------------

def build_edge_cases(start_idx):
    """Returns exactly 5 hand-crafted ambiguous records."""
    edge_cases = []

    # EC-1: BANK_TIMEOUT (TEMPORARY) but retry_count=3 and previous_failures=5
    ec1 = {
        "payment_id":               "PMT-{:05d}".format(start_idx),
        "customer_id":              "CUST-0711",
        "merchant_id":              "MER-002",
        "amount":                   2499.00,
        "timestamp":                (NOW - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S"),
        "failure_code":             "BANK_TIMEOUT",
        "failure_category":         "TEMPORARY",
        "previous_successes":       22,
        "previous_failures":        5,
        "retry_count":              3,
        "customer_ltv":             54978.00,
        "subscription_age_days":    710,
        "days_since_last_payment":  31,
        "payment_method":           "NETBANKING",
        "contact_channel_pref":     "EMAIL",
        "ground_truth_recoverable": True,
        "ground_truth_best_action": "ESCALATE_HUMAN",
        "outcome":                  "PENDING",
        "is_planted_edge_case":     True,
    }
    edge_cases.append(ec1)

    # EC-2: CARD_EXPIRED + LTV=512500 -> update-link rule conflicts with human-touch argument
    ec2 = {
        "payment_id":               "PMT-{:05d}".format(start_idx + 1),
        "customer_id":              "CUST-0422",
        "merchant_id":              "MER-001",
        "amount":                   12500.00,
        "timestamp":                (NOW - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S"),
        "failure_code":             "CARD_EXPIRED",
        "failure_category":         "CUSTOMER_ACTION_NEEDED",
        "previous_successes":       41,
        "previous_failures":        0,
        "retry_count":              0,
        "customer_ltv":             512500.00,
        "subscription_age_days":    1245,
        "days_since_last_payment":  30,
        "payment_method":           "CARD",
        "contact_channel_pref":     "EMAIL",
        "ground_truth_recoverable": True,
        "ground_truth_best_action": "ESCALATE_HUMAN",
        "outcome":                  "PENDING",
        "is_planted_edge_case":     True,
    }
    edge_cases.append(ec2)

    # EC-3: CARD_DECLINED_HARD (PERMANENT) but previous_failures=0 and long tenure
    ec3 = {
        "payment_id":               "PMT-{:05d}".format(start_idx + 2),
        "customer_id":              "CUST-0189",
        "merchant_id":              "MER-003",
        "amount":                   499.00,
        "timestamp":                (NOW - timedelta(days=12)).strftime("%Y-%m-%dT%H:%M:%S"),
        "failure_code":             "CARD_DECLINED_HARD",
        "failure_category":         "PERMANENT",
        "previous_successes":       18,
        "previous_failures":        0,
        "retry_count":              0,
        "customer_ltv":             8982.00,
        "subscription_age_days":    550,
        "days_since_last_payment":  30,
        "payment_method":           "CARD",
        "contact_channel_pref":     "SMS",
        "ground_truth_recoverable": True,
        "ground_truth_best_action": "SEND_UPDATE_LINK",
        "outcome":                  "PENDING",
        "is_planted_edge_case":     True,
    }
    edge_cases.append(ec3)

    # EC-4: INSUFFICIENT_FUNDS + 36 successes + 4 prior failures -> loyal vs distressed
    ec4 = {
        "payment_id":               "PMT-{:05d}".format(start_idx + 3),
        "customer_id":              "CUST-0567",
        "merchant_id":              "MER-004",
        "amount":                   999.00,
        "timestamp":                (NOW - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S"),
        "failure_code":             "INSUFFICIENT_FUNDS",
        "failure_category":         "AMBIGUOUS",
        "previous_successes":       36,
        "previous_failures":        4,
        "retry_count":              1,
        "customer_ltv":             35964.00,
        "subscription_age_days":    1100,
        "days_since_last_payment":  30,
        "payment_method":           "UPI",
        "contact_channel_pref":     "WHATSAPP",
        "ground_truth_recoverable": True,
        "ground_truth_best_action": "RETRY_LATER",
        "outcome":                  "PENDING",
        "is_planted_edge_case":     True,
    }
    edge_cases.append(ec4)

    # EC-5: RISK_FLAGGED + LTV=149 + new customer -> escalate rule conflicts with economics
    ec5 = {
        "payment_id":               "PMT-{:05d}".format(start_idx + 4),
        "customer_id":              "CUST-0034",
        "merchant_id":              "MER-005",
        "amount":                   149.00,
        "timestamp":                (NOW - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S"),
        "failure_code":             "RISK_FLAGGED",
        "failure_category":         "AMBIGUOUS",
        "previous_successes":       1,
        "previous_failures":        2,
        "retry_count":              0,
        "customer_ltv":             149.00,
        "subscription_age_days":    35,
        "days_since_last_payment":  35,
        "payment_method":           "WALLET",
        "contact_channel_pref":     "SMS",
        "ground_truth_recoverable": False,
        "ground_truth_best_action": "STOP",
        "outcome":                  "NOT_RECOVERED",
        "is_planted_edge_case":     True,
    }
    edge_cases.append(ec5)

    return edge_cases


# ---------------------------------------------------------------------------
# Column order
# ---------------------------------------------------------------------------
COLUMNS = [
    "payment_id",
    "customer_id",
    "merchant_id",
    "amount",
    "timestamp",
    "failure_code",
    "failure_category",
    "previous_successes",
    "previous_failures",
    "retry_count",
    "customer_ltv",
    "subscription_age_days",
    "days_since_last_payment",
    "payment_method",
    "contact_channel_pref",
    "ground_truth_recoverable",
    "ground_truth_best_action",
    "outcome",
    "is_planted_edge_case",
]


def write_csv(path, records):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(records)
    print("  Written {} records -> {}".format(len(records), path))


def print_dist(label, records, field):
    counts = {}
    for r in records:
        val = str(r[field])
        counts[val] = counts.get(val, 0) + 1
    total = len(records)
    print("  {}:".format(label))
    for val in sorted(counts):
        cnt = counts[val]
        bar = "#" * int(cnt / total * 30)
        print("    {:<32} {:>3} ({:5.1f}%)  {}".format(
            val, cnt, cnt / total * 100, bar))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("RevIQ Phase 1 - Synthetic Data Generator (seed={})".format(SEED))
    print("=" * 55)

    # Generate all 120 base records in one pass
    all_records = []
    for i in range(1, TOTAL_RECORDS + 1):
        pid = "PMT-{:05d}".format(i)
        all_records.append(build_record(pid))

    # Build 5 edge cases (IDs start after the last base record)
    edge_cases = build_edge_cases(start_idx=TOTAL_RECORDS + 1)

    # Split
    reference_records = all_records[:REFERENCE_SIZE]          # 70
    held_out_base     = all_records[REFERENCE_SIZE:]          # 50
    # Replace the last 5 of the held-out base with planted edge cases
    # Total remains 50: 45 regular + 5 planted
    held_out_records  = held_out_base[:-5] + edge_cases

    # Shuffle held-out so edge cases aren't trivially at the end
    random.shuffle(held_out_records)

    # Write files
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ref_path  = os.path.join(repo_root, "data", "reference_set.csv")
    held_path = os.path.join(repo_root, "data", "held_out_test_set.csv")

    write_csv(ref_path,  reference_records)
    write_csv(held_path, held_out_records)

    # Print distributions
    print()
    print_dist("Reference set  | failure_code",           reference_records, "failure_code")
    print()
    print_dist("Reference set  | ground_truth_best_action", reference_records, "ground_truth_best_action")
    print()
    print_dist("Held-out set   | failure_code",           held_out_records, "failure_code")
    print()
    print_dist("Held-out set   | ground_truth_best_action", held_out_records, "ground_truth_best_action")
    print()

    print("  Planted edge cases:")
    edge_reasons = [
        (edge_cases[0]["payment_id"],
         "BANK_TIMEOUT (TEMPORARY) + retry_count=3 + previous_failures=5 -> retry rule conflicts with exhausted retry budget"),
        (edge_cases[1]["payment_id"],
         "CARD_EXPIRED (SEND_UPDATE_LINK) + LTV=512500 -> clear action conflicts with white-glove human-outreach argument"),
        (edge_cases[2]["payment_id"],
         "CARD_DECLINED_HARD (PERMANENT) + previous_failures=0 + 18 successes -> terminal code conflicts with clean history"),
        (edge_cases[3]["payment_id"],
         "INSUFFICIENT_FUNDS (AMBIGUOUS) + 36 successes + 4 prior failures -> loyal customer history conflicts with repeated fund shortfalls"),
        (edge_cases[4]["payment_id"],
         "RISK_FLAGGED (escalate rule) + LTV=149 + new customer -> escalation rule conflicts with negative unit economics"),
    ]
    for pid, reason in edge_reasons:
        print("    {}: {}".format(pid, reason))

    print()
    print("Phase 1 complete. Do NOT proceed to Phase 2 until instructed.")


if __name__ == "__main__":
    main()
