# /usability-tasks — Usability Research Task Generator

Generates a complete moderator research script and structured task list from a research plan already in the session context. Designed to be called mid-session by a research orchestrator — the plan is already in the conversation, so the researcher doesn't have to restart or re-paste anything.

The output is two things: a full moderator script the researcher reads during sessions, and a saved plan file that `/sum-analysis` reads later to pre-populate correct paths without asking the researcher to re-enter them.

---

## When to invoke

This skill is called mid-session after a research orchestrator has produced a markdown research plan. The plan is already visible in the conversation. Do not ask the researcher to re-paste it.

---

## Phase 1 — Read plan from context

Extract the following from the research plan already in the conversation:

- **Product / feature / flow being tested**
- **User goals and research questions** — what the team wants to learn
- **Pre-identified flows or areas of concern** — screens, flows, or interactions flagged as priority areas
- **Participant criteria** — who should be in the study (if specified)
- **Number of tasks** — use the plan's stated number, or default to 3–5 if not specified

Do not ask the researcher to re-paste or summarize the plan. Read it directly from context.

---

## Phase 2 — Confirm scope (only if needed)

If the research plan does not clearly specify what to test, ask **at most two focused questions** before generating:

1. How many tasks? (default: 3–5)
2. Which flows should be prioritized if not all can be covered?

Skip this phase entirely if the plan is sufficiently detailed.

---

## Phase 3 — Generate tasks

For each task, produce:

**Task name** — a short label (2–4 words) used in the CSV and the SUM report. Example: "Find Balance", "Transfer Funds", "Update Profile".

**Scenario** — a realistic framing sentence that gives the participant context without revealing the correct path. Format: "Imagine you want to [realistic goal]..." Never embed navigation instructions in the scenario.

**Task instruction** — a specific, unambiguous directive with a clear observable end state. Example: "Find the current balance for your checking account and tell me what it is." The participant should know when they are done.

**Success criteria** — the observable outcome that codes the task as complete (what the moderator looks for). Example: "Participant reads the balance aloud or points to it on screen."

**Correct path(s)** — step-by-step navigation in the format `/sum-analysis` uses:
`Home → Accounts tab → Checking account → Balance overview`
List alternate correct paths on separate lines. These are written to the plan file so `/sum-analysis` can read them later.

Tasks must be:
- Observable and completable — not "explore the app" or "find out what you can do"
- Completable in approximately 2–5 minutes each in a moderated session
- Tied to a specific flow that can be measured by SUM (Completion, Satisfaction, Time)

---

## Phase 4 — Generate research script

Produce the complete moderator guide. This is a document the researcher reads aloud and follows during each session.

---

### Study introduction (read aloud to all participants before any tasks)

Write a verbatim introduction the moderator reads at the start of every session:

> "Thank you for joining us today. We're testing [product/feature area — do not name the specific flows being tested] to understand how well it works for people like you. We're testing the product, not you — there are no right or wrong answers, and anything that's confusing is useful feedback for us.
>
> As you work through each task, please think out loud — narrate what you're looking at, what you're considering, and what you're doing. It helps us understand your thought process, not just what you click.
>
> This session is being recorded for our team's use only. Do you have any questions before we begin?"

---

### Per-task script (repeat for each task)

For each task, include all five of the following elements:

**1. Scenario (read aloud)**
Read the scenario to the participant verbatim. Do not add navigation hints.

**2. Task instruction (display or hand to participant)**
Show this on a card, second screen, or document — the participant should be able to re-read it during the task without asking the moderator.

**3. Moderator observation prompt**
A private reminder for the moderator (not read aloud):
> *[Moderator note: Note the participant's first click. Watch for any hesitation, backtracking, or out-loud reasoning about navigation. Do not answer questions about where to find things — redirect with "What would you try?" or "What are you looking for?"]*

**4. Post-task SUM Likert questions (read aloud after every task)**
Ask these three questions in order after every task, regardless of whether the participant completed it:

1. "How easy or difficult was that task?" *(1 = Very difficult, 5 = Very easy)*
2. "How satisfied or dissatisfied are you with how that went?" *(1 = Very dissatisfied, 5 = Very satisfied)*
3. "Did that task take more or less time than you expected?" *(1 = Much more time than expected, 5 = Much less time than expected)*

Record the response as a number 1–5. Do not prompt or suggest a direction.

**5. Follow-up probes (2–3 open-ended questions per task)**
Generate task-specific probes that surface the participant's reasoning, not just outcomes. Examples:
- "What made you decide to go there first?"
- "What were you expecting to find when you tapped [element]?"
- "Was there a point where you weren't sure what to do next? Tell me about that."
- "What would have made that easier?"

Do not ask yes/no questions. Probes should encourage explanation, not confirmation.

---

### Closing debrief (read after all tasks are complete)

> "Those are all the tasks. I have a few final questions before we finish.
>
> Overall, how would you describe your experience using [product/feature area]?
>
> Was there anything that surprised you — either in a good way or a frustrating way?
>
> If you could change one thing about what you used today, what would it be?
>
> Is there anything you expected to find that you didn't see, or anything you'd like to add?"

Thank the participant and confirm any next steps (compensation, follow-up, etc.).

---

## Phase 5 — Save research plan file

Write `reports/research_plan_YYYY-MM-DD.md` using today's date. This file is read by `/sum-analysis` during Phase 3c to pre-populate correct paths.

Use the following structure exactly — the HTML comment markers are machine-readable and must not be modified:

```markdown
# Research Plan — [Study Name] — [YYYY-MM-DD]

**Product / feature:** [what is being tested]
**Research questions:** [key questions from the plan]
**Participant criteria:** [who should be recruited, if specified]

<!-- sum-analysis: task-context-start -->
## Tasks

### Task: [Task Name]
**Scenario:** Imagine you...
**Instruction:** Please...
**Success criteria:** [observable outcome]

#### Correct Path(s)
1. Home → [step] → [step] → [end state]
2. [Alternate path, if applicable]

#### Follow-up Probes
1. [Probe question]
2. [Probe question]
3. [Probe question]

---

[Repeat for each task]

<!-- sum-analysis: task-context-end -->

---

## Full Moderator Script

[Paste the complete script generated in Phase 4 here]
```

After writing the file, tell the researcher:

> I've saved the research plan to `reports/research_plan_YYYY-MM-DD.md`. When you return with your data, run `/sum-analysis` in this same project — it will automatically detect the plan file and pre-populate the correct paths for you, so you won't need to re-enter them.

---

## Phase 6 — Research tool export *(format TBD)*

This phase will export the task list in a format suitable for importing into the research platform. The format is pending — this is a placeholder. Once the platform's import format is confirmed, tasks will be structured accordingly (likely a CSV or structured list matching the platform's template).

For now, present the task list in plain text so the researcher can copy it manually:

```
Task 1: [Task Name]
Scenario: [scenario text]
Instruction: [task instruction text]

Task 2: [Task Name]
...
```
