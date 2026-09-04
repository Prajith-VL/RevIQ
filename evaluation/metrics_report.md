# RevIQ Phase 9 Evaluation Report

Evaluation ran on the held-out set through the full existing pipeline. No thresholds, weights, or model parameters were tuned.

## Headline Metrics

| metric | value |
|---|---:|
| recovery rate | 70.48% |
| action accuracy | 6.06% |
| recoverability accuracy | 33.33% |
| recoverability ROC-AUC | 0.54 |
| AUTO_ESCALATED count | 1 |

## Recoverability Scoring

| metric | value |
| --- | --- |
| accuracy | 0.33 |
| precision | 0.31 |
| recall | 0.82 |
| ROC-AUC | 0.54 |

## Action Selection

Exact-match accuracy: **6.06%**

| ground_truth | ESCALATE_HUMAN | RETRY_NOW | SEND_UPDATE_LINK | STOP |
| --- | --- | --- | --- | --- |
| ESCALATE_HUMAN | 0 | 1 | 1 | 1 |
| RETRY_LATER | 1 | 7 | 2 | 0 |
| RETRY_NOW | 0 | 1 | 0 | 0 |
| SEND_UPDATE_LINK | 0 | 0 | 1 | 1 |
| STOP | 3 | 12 | 2 | 0 |

## Revenue Recovery

| metric | value |
| --- | --- |
| total_ltv_at_risk_INR | 5827770.91 |
| total_simulated_revenue_recovered_INR | 4107584.89 |
| recovery_rate | 70.48% |

## Governance

### Gate Status

| gate_status | count | percentage |
| --- | --- | --- |
| PASSED | 31 | 93.93939393939394 |
| AUTO_ESCALATED | 1 | 3.0303030303030303 |
| BLOCKED | 1 | 3.0303030303030303 |

### Compliance Status

| compliance_status | count | percentage |
| --- | --- | --- |
| OK | 33 | 100.0 |

AUTO_ESCALATED rows: **1**

## Diagnosis Reliability

| metric | value |
|---|---:|
| AI-path UNKNOWN count | 0 |
| AI-path UNKNOWN percentage | 0.00% |

COMPLETE: no AI-path UNKNOWN diagnoses remain.

## Planted Edge Cases

| payment_id | failure_code | conflict | ground_truth_best_action | final_action | gate_status | match |
| --- | --- | --- | --- | --- | --- | --- |
| PMT-00124 | INSUFFICIENT_FUNDS | INSUFFICIENT_FUNDS with 36 prior successes and 4 prior failures | RETRY_LATER | RETRY_NOW | PASSED | MISMATCH |
| PMT-00121 | BANK_TIMEOUT | BANK_TIMEOUT with retry_count=3 and previous_failures=5 | ESCALATE_HUMAN | RETRY_NOW | PASSED | MISMATCH |
| PMT-00122 | CARD_EXPIRED | CARD_EXPIRED with customer_ltv=INR 5,12,500 and 41 prior successes | ESCALATE_HUMAN | SEND_UPDATE_LINK | PASSED | MISMATCH |
| PMT-00123 | CARD_DECLINED_HARD | CARD_DECLINED_HARD with previous_failures=0 and 18 prior successes | SEND_UPDATE_LINK | STOP | BLOCKED | MISMATCH |
| PMT-00125 | RISK_FLAGGED | RISK_FLAGGED with customer_ltv=INR 149 and subscription_age_days=35 | STOP | SEND_UPDATE_LINK | PASSED | MISMATCH |

Correct final actions: **0 of 5**

## Evaluation Scope

The report is summary-only. No per-row prediction artifact was written.
