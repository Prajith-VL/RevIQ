# RevIQ Pitch Deck Outline

## 1. The Problem

**Slide structure:** One sentence problem statement, then a two-column contrast.

**Talking points:**
- Subscription renewal failures quietly turn otherwise healthy subscriptions into lost revenue.
- Fully manual recovery is expensive and difficult to scale.
- Fully automated recovery is risky when the system cannot explain, gate, stop, or prove what it did.
- The opportunity is governed automation for recurring renewal failures, not checkout abandonment or general receivables.

**Evidence:** `src/detection.py`, `src/confidence_gate.py`, `src/execution.py`.

## 2. The Anchor Sentence

**Slide structure:** The sentence fills the slide. No competing headline.

> "A governed AI agent that watches failed subscription payments, diagnoses why they failed, predicts whether they're recoverable, selects the recovery action with the highest expected value, executes it within strict policy bounds, and proves exactly how much revenue it recovered — while knowing when to stop and hand off to a human."

**Talking point:** This is the product definition and the standard every phase must satisfy.

**Evidence:** `README.md`, `SCOPE_LOCK.md`, and the phase modules in `src/`.

## 3. Architecture

**Slide structure:** Left-to-right pipeline diagram.

```text
[Detect] -> [Diagnose: rules + Gemini] -> [Score: rules + LogisticRegression]
    -> [Select Action: EV] -> [Gate: deterministic policy]
    -> [Execute: simulated] -> [Stop/Comply: deterministic] -> [Evaluate]
```

**Phase labels:**
- Detect: deterministic
- Diagnose: hybrid; deterministic rules first, Gemini only for ambiguous cases
- Score: deterministic short-circuits plus explainable logistic regression
- Select Action: deterministic expected-value arithmetic
- Gate: deterministic thresholds and ML confidence override
- Execute: deterministic seeded simulation, no real payment rail
- Stop/Comply: deterministic row-level policy checks
- Evaluate: deterministic metrics and audit summary

**Evidence:** `src/detection.py`, `src/diagnosis.py`, `src/recoverability_scoring.py`, `src/action_selection.py`, `src/confidence_gate.py`, `src/execution.py`, `src/stopping_rules.py`, `evaluation/run_evaluation.py`.

## 4. The Hybrid Principle

**Slide structure:** Rules on the left, AI on the right, with a measured split beneath.

**Talking points:**
- Clear-cut gateway outcomes are handled by rules: no model call, no unnecessary ambiguity.
- Gemini is reserved for genuinely ambiguous or context-dependent failures.
- The reference-set run recorded 9 RULE diagnoses and 10 AI-path diagnoses, roughly 47% and 53% of the 19 at-risk rows respectively.
- This is a hybrid system with an observable routing decision, not an AI label pasted onto every row.

**Evidence:** `audit_log.jsonl` and the reference-set diagnosis run output.

## 5. The Governance Moment

**Slide structure:** Three large states: `PASSED` | `BLOCKED` | `AUTO_ESCALATED`.

**Talking points:**
- The confidence gate is the checkpoint before an automated action reaches execution.
- It checks diagnosis confidence, recoverability, and expected value.
- `AUTO_ESCALATED` is the key policy: an ML-scored path with diagnosis confidence below 0.85 is routed to `ESCALATE_HUMAN` even when the EV math says automate.
- Low diagnosis confidence escalates because the system may misunderstand the failure. Low recoverability or low EV stops because human effort is not justified by the likely value.
- Real audit evidence for `PMT-00090`: chosen `RETRY_NOW`, ML path, all base thresholds passed, but confidence did not clear the stricter ML bar; final action became `ESCALATE_HUMAN`.

**Evidence:** `src/confidence_gate.py`, `audit_log.jsonl`.

## 6. Results on Held-Out Data

**Slide structure:** Three metric tiles, one honesty note, and the five-case edge-case result.

**Reported snapshot from `evaluation/metrics_report.md` (generated before the later Phase 5 CUSTOMER_ACTION_NEEDED eligibility fix):**
- Recovery rate: **31.77%**
- Action accuracy: **3.03%**
- Recoverability ROC-AUC: **0.63**
- Planted edge cases correct: **0 of 5**

**Honesty note:** The report also records **20 AI-path UNKNOWN diagnoses** and is explicitly marked incomplete because of Gemini quota/API failures. These numbers are a baseline snapshot, not pitch-deck-final metrics after the Phase 5 fix. Rerun Phase 9 after quota reset before presenting them as final.

**Evidence:** `evaluation/metrics_report.md`, `audit_log.jsonl`.

## 7. What We'd Build Next

**Slide structure:** Three deliberate extensions, each with a boundary.

- Real gateway integration behind the existing Phase 6 and Phase 8 controls; the current Phase 7 is intentionally simulation-only.
- A scoped customer-update channel for cases such as expired payment credentials, with consent, delivery, and audit policy defined before launch.
- Operational monitoring and quota-aware model operations, including cache observability and evaluation reruns after the diagnosis cache is populated.

**Talking point:** These are sequenced extensions, not permissions to bypass governance or expand beyond recurring renewal failures.

**Evidence:** `src/execution.py`, `src/confidence_gate.py`, `src/stopping_rules.py`, `src/diagnosis.py`.

## 8. Why This Matters for Razorpay

**Slide structure:** Razorpay context plus an internal-tooling proposition.

**Talking points:**
- Razorpay processes subscription renewals, where a failed recurring payment is a recovery decision rather than a one-off checkout event.
- RevIQ demonstrates an architecture Razorpay could evaluate for internal revenue-recovery tooling: explainable diagnosis, expected-value action selection, confidence gating, stopping rules, and audit proof.
- The prototype makes the boundary explicit: simulated execution today, governed integration only as a future extension.
- The pitch is about disciplined decision infrastructure for real renewal operations, not a claim of production deployment or live merchant access.

**Evidence:** `SCOPE_LOCK.md`, `src/execution.py`, `audit_log.jsonl`, `evaluation/metrics_report.md`.
