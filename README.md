# RevIQ — Governed AI Revenue Recovery Agent

> *Diagnose, score, gate, execute, prove — for every failed subscription payment.*

---

> "A governed AI agent that watches failed subscription payments, diagnoses why they failed, predicts whether they're recoverable, selects the recovery action with the highest expected value, executes it within strict policy bounds, and proves exactly how much revenue it recovered — while knowing when to stop and hand off to a human."

---

Built for **Razorpay AI Buildathon — Track 03: AI Revenue Recovery**

---

## The Problem

Merchants lose recoverable subscription revenue because failed renewal payments are treated identically regardless of cause, customer value, or true recoverability.

---

## The Solution

```
Failed Payment
  → Detect & classify (deterministic)
  → Diagnose root cause (AI)
  → Score recoverability (AI/ML)
  → Select action by expected value (AI)
  → Confidence gate (deterministic, escalate if below threshold)
  → Execute (simulated)
  → Audit trail + dashboard
```

---

## Scope

This build covers **subscription payment failures only**. No checkout abandonment, no B2B receivables, no live gateway calls, no real merchant data. For the full list of what is in and out of scope — and the rationale — see [SCOPE_LOCK.md](./SCOPE_LOCK.md).

---

## Results (Held-Out Test Set)

| Metric | Value |
|---|---|
| Revenue at risk | ₹[XX] |
| Revenue recovered | ₹[XX] |
| Recovery rate | [XX]% |
| Diagnosis accuracy | [XX]% |
| Action-selection accuracy | [XX]% |
| False intervention rate | [XX]% |
| Escalation rate | [XX]% |

*Values to be filled in after evaluation run.*

---

## Architecture

```
RevIQ/
├── src/
│   ├── detection.py              # Deterministic failure detection & classification
│   ├── diagnosis.py              # Rules + LLM root-cause diagnosis
│   ├── recoverability_scoring.py # AI/ML recoverability probability scoring
│   ├── action_selection.py       # Expected-value action selection
│   ├── confidence_gate.py        # Deterministic confidence threshold gate
│   ├── execution.py              # Simulated execution + mock API logging
│   ├── stopping_rules.py         # Retry caps, cool-down, opt-out enforcement
│   └── audit_log.py              # Full per-case audit trail
├── data/
│   ├── reference_set.csv         # Synthetic training/reference dataset
│   └── held_out_test_set.csv     # Held-out evaluation set with ground truth
├── evaluation/
│   ├── run_evaluation.py         # Batch evaluation runner
│   └── metrics_report.md         # Output metrics report
├── dashboard/                    # (Dashboard — coming in a later phase)
├── docs/                         # (Extended documentation — coming in a later phase)
├── requirements.txt
├── SCOPE_LOCK.md
└── README.md
```

---

## Setup

```bash
# 1. Clone the repository
git clone https://github.com/<your-org>/RevIQ.git
cd RevIQ

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the evaluation pipeline
python evaluation/run_evaluation.py
```

---

## Demo Highlights

- **Confident case walkthrough:** A failed subscription payment with a clear, diagnosable root cause and high recoverability score passes the confidence gate — the agent selects the optimal action, executes it (simulated), and logs the full audit trail showing revenue recovered.
- **Low-confidence case walkthrough:** A payment failure with ambiguous signals or a recoverability score below the confidence threshold is blocked by the gate — the agent does not act autonomously and instead escalates the case to a human, logging exactly why it stopped.

---

## Team

[names]

---

## License

MIT