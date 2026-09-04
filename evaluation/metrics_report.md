# RevIQ Phase 9 Evaluation Report

Evaluation ran on the held-out set through the full existing pipeline. No thresholds, weights, or model parameters were tuned.

## Headline Metrics

| metric | value |
|---|---:|
| recovery rate | 31.77% |
| action accuracy | 3.03% |
| recoverability accuracy | 39.39% |
| recoverability ROC-AUC | 0.63 |
| AUTO_ESCALATED count | 0 |

## Recoverability Scoring

| metric | value |
| --- | --- |
| accuracy | 0.39 |
| precision | 0.33 |
| recall | 0.82 |
| ROC-AUC | 0.63 |

## Action Selection

Exact-match accuracy: **3.03%**

| ground_truth | ESCALATE_HUMAN | RETRY_LATER | RETRY_NOW | SEND_UPDATE_LINK | STOP |
| --- | --- | --- | --- | --- | --- |
| ESCALATE_HUMAN | 0 | 1 | 1 | 0 | 1 |
| RETRY_LATER | 6 | 0 | 4 | 0 | 0 |
| RETRY_NOW | 0 | 0 | 1 | 0 | 0 |
| SEND_UPDATE_LINK | 0 | 1 | 0 | 0 | 1 |
| STOP | 16 | 0 | 0 | 1 | 0 |

## Revenue Recovery

| metric | value |
| --- | --- |
| total_ltv_at_risk_INR | 5827770.91 |
| total_simulated_revenue_recovered_INR | 1851388.39 |
| recovery_rate | 31.77% |

## Governance

### Gate Status

| gate_status | count | percentage |
| --- | --- | --- |
| PASSED | 18 | 54.54545454545455 |
| BLOCKED | 15 | 45.45454545454545 |

### Compliance Status

| compliance_status | count | percentage |
| --- | --- | --- |
| OK | 33 | 100.0 |

AUTO_ESCALATED rows: **0**

## Diagnosis Reliability

| metric | value |
|---|---:|
| AI-path UNKNOWN count | 20 |
| AI-path UNKNOWN percentage | 60.61% |

INCOMPLETE: 20 AI-path UNKNOWN diagnoses remain; affected payment_ids: PMT-00114, PMT-00124, PMT-00115, PMT-00085, PMT-00107, PMT-00090, PMT-00080, PMT-00106, PMT-00125, PMT-00083, PMT-00099, PMT-00098, PMT-00105, PMT-00101, PMT-00089, PMT-00093, PMT-00086, PMT-00100, PMT-00096, PMT-00072. Do not treat these final metrics as pitch-deck complete until quota permits a rerun.

## Planted Edge Cases

| payment_id | failure_code | conflict | ground_truth_best_action | final_action | gate_status | match |
| --- | --- | --- | --- | --- | --- | --- |
| PMT-00124 | INSUFFICIENT_FUNDS | INSUFFICIENT_FUNDS with 36 prior successes and 4 prior failures | RETRY_LATER | ESCALATE_HUMAN | BLOCKED | MISMATCH |
| PMT-00121 | BANK_TIMEOUT | BANK_TIMEOUT with retry_count=3 and previous_failures=5 | ESCALATE_HUMAN | RETRY_NOW | PASSED | MISMATCH |
| PMT-00122 | CARD_EXPIRED | CARD_EXPIRED with customer_ltv=INR 5,12,500 and 41 prior successes | ESCALATE_HUMAN | RETRY_LATER | PASSED | MISMATCH |
| PMT-00123 | CARD_DECLINED_HARD | CARD_DECLINED_HARD with previous_failures=0 and 18 prior successes | SEND_UPDATE_LINK | STOP | BLOCKED | MISMATCH |
| PMT-00125 | RISK_FLAGGED | RISK_FLAGGED with customer_ltv=INR 149 and subscription_age_days=35 | STOP | ESCALATE_HUMAN | BLOCKED | MISMATCH |

Correct final actions: **0 of 5**

## Evaluation Scope

The report is summary-only. No per-row prediction artifact was written.
