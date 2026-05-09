# Research Plan — Personal Finance Concept Study

**Method:** concept_testing

<!--
Worked example for /concept-testing. See ./README.md for what each
file in this folder represents and how to run the verification harness.
-->

## Needs

### N1
- **Statement:** Track recurring expenses across all my accounts
- **Source:** manual
- **Importance:** 4.2
- **Current satisfaction:** 2.1
- **Evaluation criteria:**
  - See all subscriptions and recurring charges in one place
  - Notice when a recurring charge changes amount or frequency

### N2
- **Statement:** Catch fraudulent or anomalous charges quickly
- **Source:** manual
- **Importance:** 4.6
- **Current satisfaction:** 2.5
- **Evaluation criteria:**
  - Get notified within 1 hour of an unusual charge
  - Distinguish fraud from legitimate-but-unusual spending

### N3
- **Statement:** Share day-to-day financial state with my partner
- **Source:** manual
- **Importance:** 3.8
- **Current satisfaction:** 1.9
- **Evaluation criteria:**
  - Both partners see the same view of recent activity
  - Either partner can categorize or annotate transactions

---

## Concepts

### C1: Weekly auto-digest
- **Description:** A weekly email that automatically categorizes the past week's spending and shows changes from the prior week. No interaction required.
- **Target needs:**
  - N1 — Auto-categorization makes recurring spend visible without manual work
  - N2 — Weekly review surfaces anomalies the user might otherwise miss
- **Assets:**
  - "A mocked email screenshot showing a 'Your Week in Money' digest with categorized totals and change-from-last-week indicators."

### C2: Manual transaction tagger
- **Description:** Users tag every transaction with a custom category as it comes in. Tags are sharable with a partner who sees the same tagged feed.
- **Target needs:**
  - N1 — Manual control yields cleaner, user-defined categories
  - N3 — Shared tags align partners on what counts as what
- **Assets:**
  - "A mocked mobile screen showing a transaction list with tag-input affordances and a 'shared with' avatar."

### C3: Smart spend alerts
- **Description:** Real-time push notifications when an algorithm detects a transaction that looks unusual relative to your normal spend. User can dismiss, confirm-fraud, or mark-as-expected.
- **Target needs:**
  - N2 — Real-time anomaly detection catches fraud at the moment it happens
- **Assets:**
  - "A mocked phone lock-screen showing a 'Heads up: $89 at FuelStop is 4x your usual gas spend' notification with three quick actions."

---

## Participants

- P01
- P02
- P03
- P04
- P05
