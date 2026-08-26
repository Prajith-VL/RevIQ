# SCOPE_LOCK.md — RevIQ · Phase 0

> **This document is the single source of truth for what RevIQ does and does not do.**
> Once locked, no feature may be added to the build without a revision to this file.

---

## Anchor Sentence

> "A governed AI agent that watches failed subscription payments, diagnoses why they failed, predicts whether they're recoverable, selects the recovery action with the highest expected value, executes it within strict policy bounds, and proves exactly how much revenue it recovered — while knowing when to stop and hand off to a human."

---

## Problem Statement

Merchants lose recoverable subscription revenue because failed renewal payments are treated identically regardless of cause, customer value, or true recoverability.

---

## Scope: In / Out Boundary

| Component | IN SCOPE | OUT OF SCOPE |
|---|---|---|
| Failure type | Subscription/recurring renewal failures only | One-time checkout failures, cart abandonment |
| Data | Synthetic dataset, 50-100+ records with ground truth | Live/real Razorpay transaction data |
| Diagnosis | Rules + LLM reasoning on failure code + context | Full NLP on unstructured support tickets |
| Action set | Fixed list: retry now / retry later / send update link / escalate / stop | Free-form AI-generated novel actions |
| Execution | Simulated (logged, mock API response) | Real payment gateway calls, real SMS/email sends |
| Channels | Single channel simulation (text-based) | Voice, WhatsApp, multi-channel orchestration |
| Evaluation | Held-out test set with ground truth labels | Live A/B testing on real merchants |
| Compliance | Retry caps, cool-down periods, opt-out respect | Full regulatory/legal review, RBI filing simulation |

---

## Explicitly Excluded From This Build

The following are **strict out-of-scope** items. None of these will be implemented, prototyped, or partially included in the Phase 0–demo build.

| Exclusion | Rationale |
|---|---|
| Checkout abandonment recovery | Different failure type, different signal set; would dilute focus |
| B2B receivables / invoice chasing | Different domain, different compliance surface |
| Mandate retry sequencing for non-subscription payment types | Out of target failure class |
| Voice / Hinglish outreach channels | Multi-modal complexity out of scope for this build |
| Live payment gateway calls | All execution must be **SIMULATED only** |
| Multi-channel orchestration | Single channel simulation only |
| Real Razorpay merchant data | Synthetic dataset only |

### Scope-Question Rebuttal

> "We scoped deliberately to subscription payment recovery to go deep rather than wide. The same architecture — diagnose, score, optimize, gate, execute, measure — extends to abandonment and receivables, but we chose to prove it completely on one failure type rather than partially on three."

---

## Definition of Done

All items below must be demonstrable before the build is considered complete.

- [ ] Total revenue at risk (₹) reported
- [ ] Total revenue recovered (₹) reported
- [ ] Recovery rate (%) reported
- [ ] Diagnosis accuracy (%) vs ground truth reported
- [ ] Action-selection accuracy (%) vs ground truth reported
- [ ] False intervention rate (%) reported
- [ ] Escalation rate (%) reported
- [ ] One live case walkthrough: confident, full pipeline, action executed
- [ ] One live case walkthrough: low-confidence, blocked, escalated to human
- [ ] Full audit trail visible for every case in the batch
- [ ] Scope-exclusion answer rehearsed and ready

---

## Future Work

> **The items below are explicitly NOT part of the current build.** They are listed here only to show the extension path of this architecture.

- Extend to checkout abandonment recovery
- Extend to B2B receivables chasing
- Add voice/Hinglish outreach channel
- Live gateway integration
- Multi-merchant deployment