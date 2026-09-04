# RevIQ

## Governed Revenue Recovery for Subscription Renewals

RevIQ is a governed AI agent for failed recurring subscription payments. It diagnoses why a renewal failed, estimates whether recovery is likely, selects the highest-value permitted action, applies a deterministic confidence gate, simulates execution, and records the evidence needed to explain every decision.

**Live dashboard:** [rev-iq.streamlit.app](https://rev-iq.streamlit.app/)

> A governed AI agent that watches failed subscription payments, diagnoses why they failed, predicts whether they're recoverable, selects the recovery action with the highest expected value, executes it within strict policy bounds, and proves exactly how much revenue it recovered — while knowing when to stop and hand off to a human.

Built for the **Razorpay AI Buildathon, Track 03: AI Revenue Recovery**.

## Why RevIQ

Failed subscription renewals are not all the same. A transient issuer timeout, an expired card, and a hard decline require different responses. Treating every failure identically either leaves recoverable revenue untouched or creates risky, unaccountable automation.

RevIQ combines explainable automation with explicit governance:

- Rules handle objectively clear failure types.
- Gemini is reserved for ambiguous, context-dependent diagnosis.
- Logistic regression provides an explainable recoverability score.
- Expected-value arithmetic chooses among a fixed action set.
- A confidence gate can block or escalate an otherwise attractive action.
- Stopping rules prevent excessive retries and repeated failed attempts.
- An append-only audit log records the decision path and outcome.

## Product Flow

```text
Failed subscription renewal
        |
        v
Detect -> Diagnose -> Score -> Select action -> Confidence gate
                                                   |
                                  +----------------+----------------+
                                  v                                 v
                         Execute (simulated)                 Escalate / stop
                                  |                                 |
                                  +-------------> Audit -> Evaluate
```

### Pipeline phases

| Phase | Module | Responsibility | Approach |
|---|---|---|---|
| 1 | `generate_dataset.py` | Create reproducible synthetic development and evaluation data | Deterministic |
| 2 | `detection.py` | Identify at-risk renewal failures and assign severity | Rules |
| 3 | `diagnosis.py` | Classify root cause and explain the diagnosis | Rules + Gemini fallback |
| 4 | `recoverability_scoring.py` | Estimate recovery probability | Rules + explainable logistic regression |
| 5 | `action_selection.py` | Select the action with the highest expected value | Deterministic arithmetic |
| 6 | `confidence_gate.py` | Enforce diagnosis, recoverability, EV, and ML-confidence thresholds | Deterministic policy |
| 7 | `execution.py` | Produce reproducible simulated outcomes | Deterministic simulation |
| 8 | `stopping_rules.py` | Enforce lifetime retry and consecutive-failure ceilings | Deterministic policy |
| 9 | `evaluation/run_evaluation.py` | Measure recovery, scoring, actions, and governance | Read-only evaluation |
| 10 | `dashboard/app.py` | Present metrics and audit evidence | Read-only Streamlit UI |

## Governance by Design

The confidence gate is the boundary between an AI-influenced recommendation and a final action. It uses named, inspectable thresholds:

- Diagnosis confidence must be at least `0.70`.
- Recoverability must be at least `0.60`.
- Expected value must be at least INR `10.00`.
- ML-scored paths face a stricter diagnosis-confidence bar of `0.85`.

Rows can be `PASSED`, `BLOCKED`, or `AUTO_ESCALATED`. Low diagnosis confidence escalates to a human because the system may misunderstand the failure. Low recoverability or low expected value stops because human intervention is not justified by the likely value.

Phase 8 adds portfolio-safe row-level ceilings: more than five lifetime retries halts automation, and three or more prior failures followed by another failed attempt halts further automation.

Every phase writes structured events through the shared `audit_log.log_event()` function. The dashboard exposes this evidence in a searchable, read-only explorer.

## Official Evaluation Results

Results below are from the final held-out evaluation recorded in [evaluation/metrics_report.md](evaluation/metrics_report.md). Execution is simulated; no real payment rail is involved.

| Metric | Result |
|---|---:|
| Total LTV at risk | INR 58,27,770.91 |
| Simulated revenue recovered | INR 41,07,584.89 |
| Recovery rate | **70.48%** |
| Recoverability accuracy | 33.33% |
| Recoverability recall | 0.82 |
| Recoverability ROC-AUC | 0.54 |
| Action-selection exact-match accuracy | 6.06% |
| AUTO_ESCALATED | 1 of 33 gated rows |
| Compliance status | 100% OK |
| Planted edge cases correct | 0 of 5 |

The evaluation also exposed a specific calibration finding: the system is systematically optimistic about attempting recovery, choosing `RETRY_NOW` or `RETRY_LATER` in cases where ground truth preferred `STOP` or `ESCALATE_HUMAN`. With more reference data, the recoverability model's conservatism can be tuned through the same logistic regression without changing the governance architecture.

## Dashboard

The deployed Streamlit dashboard presents:

- Headline recovery and model-performance metrics.
- Financial impact: revenue at risk, simulated revenue recovered, and recovery rate.
- The seven-stage operational pipeline.
- Gate and compliance distributions with semantic status colors.
- All five planted edge cases, including expected versus actual actions.
- A read-only audit explorer with phase filtering, payment-ID search, and expandable JSON evidence.
- Scope and methodology sourced from `SCOPE_LOCK.md`.

Open the application at [https://rev-iq.streamlit.app/](https://rev-iq.streamlit.app/).

## Running Locally

### Requirements

- Python 3.10+
- Streamlit
- pandas
- scikit-learn
- google-genai
- Altair

Install the runtime packages in a virtual environment:

```bash
python -m venv .venv

# macOS/Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1

pip install streamlit pandas scikit-learn google-genai altair
```

### Dashboard

```bash
streamlit run dashboard/app.py
```

### Evaluation

```bash
python evaluation/run_evaluation.py
```

The evaluation runner reads the held-out set once per run and writes only the summary report at `evaluation/metrics_report.md`. It does not create a per-row prediction artifact.

For Gemini-backed diagnosis, set `GEMINI_API_KEY` in the environment. Successful AI diagnoses are cached by `payment_id` in `data/diagnosis_ai_cache.json`; fallback `UNKNOWN` results are not cached. If the provider is unavailable or quota is exhausted, the system preserves the explicit manual-review fallback rather than fabricating a diagnosis.

## Data and Scope

RevIQ is intentionally limited to **subscription and recurring renewal failures**.

### In scope

- Synthetic payment-failure data with ground-truth labels.
- Rules and LLM reasoning over failure codes and customer context.
- Fixed recovery actions: retry now, retry later, send update link, escalate to a human, or stop.
- Simulated execution and read-only held-out evaluation.
- Retry ceilings, compliance checks, and full audit logging.

### Out of scope

- One-time checkout failures and cart abandonment.
- B2B receivables or invoice chasing.
- Real merchant or live Razorpay transaction data.
- Real gateway calls or real SMS/email sends.
- Voice, Hinglish, and multi-channel orchestration.
- Live A/B testing or a full regulatory/legal review.

The authoritative boundary is [SCOPE_LOCK.md](SCOPE_LOCK.md).

## Repository Layout

```text
RevIQ/
├── src/
│   ├── detection.py
│   ├── diagnosis.py
│   ├── recoverability_scoring.py
│   ├── action_selection.py
│   ├── confidence_gate.py
│   ├── execution.py
│   ├── stopping_rules.py
│   └── audit_log.py
├── data/
│   ├── reference_set.csv
│   ├── held_out_test_set.csv
│   └── diagnosis_ai_cache.json
├── evaluation/
│   ├── run_evaluation.py
│   └── metrics_report.md
├── dashboard/
│   ├── app.py
│   └── .streamlit/config.toml
├── pitch/
│   ├── DECK_OUTLINE.md
│   └── DEMO_SCRIPT.md
├── SCOPE_LOCK.md
└── README.md
```

## Safety Statement

Phase 7 is simulation-only. It performs no real payment gateway calls, sends no real messages, and moves no real money. The confidence gate and stopping rules are designed to remain in front of any future execution integration.

## License

MIT
