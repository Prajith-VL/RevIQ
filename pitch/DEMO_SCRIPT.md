# RevIQ 90-Second Demo Script

## 0:00-0:15: Anchor and Problem

"Subscription renewal failures are where recurring revenue quietly leaks. Manual recovery is expensive; blind automation is risky. RevIQ is built around one sentence: **A governed AI agent that watches failed subscription payments, diagnoses why they failed, predicts whether they're recoverable, selects the recovery action with the highest expected value, executes it within strict policy bounds, and proves exactly how much revenue it recovered — while knowing when to stop and hand off to a human.**"

"I will show one real audit trail, then the governance checkpoint that prevents a plausible score from becoming an unreviewed action."

## 0:15-0:45: One Real Row Through the Pipeline

**Show the entries for `PMT-00081` in `audit_log.jsonl`.**

"First, Detect marks `PMT-00081` at risk with HIGH severity. Diagnose takes the deterministic route: this is a `BANK_TIMEOUT`, so it is classified `TEMPORARY` with confidence 1.00."

"Score then produces a recoverability score of **0.9721** using the explainable scoring layer. Action Selection compares the eligible actions and chooses `RETRY_NOW`, with expected value **INR 901,216.10**."

"The gate passes it because diagnosis confidence is 1.00, recoverability is 0.97, and expected value is above the policy threshold. Execution is explicitly simulated: `RETRY_NOW` succeeds with P=0.97 and reports simulated recovered revenue of **INR 927,069.45**. Finally, Stopping Rules records compliance `OK`. Nothing touched a real payment rail."

**Traceability:** `audit_log.jsonl` entries for `PMT-00081` across DETECTION, DIAGNOSIS, RECOVERABILITY_SCORING, ACTION_SELECTION, CONFIDENCE_GATE, EXECUTION, and STOPPING_RULES.

## 0:45-1:15: The Governance Moment

**Show the CONFIDENCE_GATE entry for `PMT-00090`.**

"Now the important part. `PMT-00090` has an ML-scored recovery path. Its base checks pass: diagnosis confidence clears 0.70, recoverability clears 0.60, and expected value clears INR 10. But its diagnosis confidence is below the stricter ML bar of 0.85."

"So the gate changes the status to `AUTO_ESCALATED` and the final action to `ESCALATE_HUMAN`. The math may favor automation, but the policy refuses to trust a moderate-confidence ML path with money. That is the governed checkpoint."

"The final held-out evaluation recorded 1 AUTO_ESCALATED row out of 33 gated rows; this real audit entry shows that governance path in the system's audit history."

**Traceability:** `src/confidence_gate.py` and the `PMT-00090` CONFIDENCE_GATE entry in `audit_log.jsonl`.

## 1:15-1:30: Results and Close

"The final held-out results show **70.48% simulated recovery rate**: INR 41,07,584.89 recovered of INR 58,27,770.91 at risk. Recoverability scoring reached **33.33% accuracy**, **0.82 recall**, and **0.54 ROC-AUC**. Action selection exact-match accuracy was **6.06%**, and all five planted edge cases were mismatches."

"The specific calibration finding is that the system is systematically biased toward attempting recovery, through RETRY_NOW or RETRY_LATER, where ground truth preferred STOP or ESCALATE_HUMAN. With more reference data, the recoverability model's conservatism could be tuned via the same logistic regression, without touching the governance architecture."

"The takeaway is not unaccountable autonomy. It is a recovery pipeline that can explain its choice, block it, escalate it, stop it, and prove what happened."

## Q&A Prep

### 1. Is execution real?

No. Phase 7 is a deterministic simulation with a stable per-payment seed. It makes no gateway calls and moves no money. That boundary is intentional for the hackathon; real integration would sit behind the existing confidence gate and stopping rules.

**Evidence:** `src/execution.py`.

### 2. Why is your action accuracy so low if recovery rate is high?

The system recovers a substantial amount in simulation, but its action policy is systematically optimistic: it attempts `RETRY_NOW` or `RETRY_LATER` even in cases where ground truth preferred `STOP` or `ESCALATE_HUMAN`. That bias appears in the confusion matrix and all five planted edge cases. With more reference data, the recoverability model's conservatism could be tuned via the same logistic regression, without touching the governance architecture.

**Evidence:** `evaluation/metrics_report.md`, `src/recoverability_scoring.py`.

### 3. Why did the AI results include UNKNOWN rows?

The Gemini free-tier quota was exhausted during development, and the provider path required a swap from Anthropic to Gemini. The system preserves the mandated fallback rather than inventing a diagnosis, adds retry handling for transient 503s, and caches only genuine successful diagnoses by `payment_id`. The final evaluation completed with 0 AI-path UNKNOWN diagnoses.

**Evidence:** `src/diagnosis.py`, `evaluation/metrics_report.md`, `audit_log.jsonl`.

### 4. Why use AI at all if rules can classify failures?

Rules handle objectively clear cases. AI is reserved for ambiguous, multi-signal cases. The reference at-risk run recorded 9 RULE and 10 AI-path diagnoses. That split is inspectable in the audit log, and the fallback remains safe when the provider is unavailable.

**Evidence:** `src/diagnosis.py`, `audit_log.jsonl`.

### 5. Why was action selection changed after evaluation?

Held-out inspection exposed a real EV bug: `SEND_UPDATE_LINK` had the same recoverability score as `RETRY_LATER` but a higher cost, making it mathematically unreachable. The fix makes `RETRY_LATER` ineligible for `CUSTOMER_ACTION_NEEDED` cases because those failures require customer action. The final report reflects that fix.

**Evidence:** `src/action_selection.py`, `evaluation/metrics_report.md`.

### 6. What prevents a low-confidence model output from triggering money movement?

Phase 6 is the deterministic checkpoint. It blocks diagnosis confidence below 0.70, recoverability below 0.60, or expected value below INR 10. ML-scored actions face a stricter 0.85 diagnosis-confidence bar and become `AUTO_ESCALATED` when they miss it. Phase 7 only receives `final_action`; it does not bypass the gate.

**Evidence:** `src/confidence_gate.py`, `audit_log.jsonl`.
