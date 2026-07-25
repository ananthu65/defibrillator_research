# Rule-by-Rule Development Guide
### Defibrillation Assessment Pipeline — Working With AI Without Losing Control of the Logic

---

## Why this process exists

This system assigns Pass/Fail to real students on a clinical skill. If a rule's logic is subtly wrong,
the failure mode isn't a crashed script — it's a student getting graded incorrectly and nobody
noticing, because the code runs fine and produces a plausible-looking result either way.

Pasting the whole spec document into an AI and taking the generated code means you can't stand
behind any individual line — you'd be trusting the AI's interpretation of 17 pages of clinical rules,
untested. Working rule-by-rule, with your own reasoning written down *before* the AI writes code,
means every function is something you actually understand and can defend.

---

## Build Order

Build in this order — each stage only depends on stages above it, so nothing is blocked waiting on
something later:

1. **Event schema** (`core/events.py`) — done.
2. **Timeline Fusion Engine** — merge, normalize, sort, dedupe. Test with hand-crafted fake events;
   doesn't need real detections yet.
3. **Rule Evaluation Engine — visual rules, in physical procedure order:**
   `R1 → R2 → R3 → R4 → R5 → R6`
4. **Rule Evaluation Engine — audio rules, in physical procedure order:**
   `A1 → A2 → A3 → A4 → A5 → A6/R7 → A7`
   (A7 is a composite "was the whole sequence correct" rule — build it last since it depends on all
   the others already existing. A6 and R7 describe the same criterion from two angles in the doc —
   worth a quick sanity check with your team on whether that's intentional duplication or one
   supersedes the other, but you can build the logic either way without being blocked on the answer.)
5. **Clinical Logic Engine — inference layer.** This is where the R3/R4 "Pass–Inferred from R5/R6"
   logic lives, per our chosen split. Build this *after* R3, R4, R5, R6 exist, since it calls into
   their pass/fail logic.
6. **Scoring and Feedback Engine** — last, since it aggregates everything above.

One rule = one focused piece of work = one git commit. This is also your daily-progress story:
"R3 is done, tested, and committed" is a much stronger update than "I'm working on the rule engine."

---

## The Per-Rule Checklist (do this before opening any AI chat)

For every rule (R1, R2, ... A7), work through this on paper or in a scratch file first:

**1. Copy the exact rule text from the spec document.** Not a summary — the literal Detection /
Pass logic / Fail logic / Technical boundary / Clinical input rows.

**2. Restate it yourself, in plain English, as a decision rule:**
   - What event(s) does this need as input? (name them exactly as they'll appear in the Event schema)
   - What is the Pass condition, precisely?
   - What is the Fail condition, precisely?
   - Is there an Unable to Assess / Manual Review condition, and when does it apply?
   - Is there a Critical Error condition?

**3. Flag unconfirmed parameters.** Several rules depend on values the document marks as pending
   supervisor confirmation (e.g. R7's max delay, R3's approved chest regions). List them explicitly —
   these become named config values with placeholder defaults, never hardcoded magic numbers.

**4. Write 3–5 test cases before any implementation exists.** For each: a small list of fake `Event`
   objects (a timeline) and the `CriterionEvaluation` you expect back. Include at least one edge case
   (missing event, low confidence, wrong order, duplicate detection).

   This step is the actual safeguard. If AI-generated code doesn't pass tests *you* wrote from *your*
   own understanding of the rule, you have real signal that something's off — independent of how
   plausible the code looks.

**5. Only now, bring in AI** — using the prompt template below.

**6. Read every line the AI returns against your Step 2 restatement**, not just "does it run."

**7. Run your test cases.** If they fail, go back to Step 2 first — figure out whether your test was
   wrong or the logic was wrong, before asking AI to "fix" anything.

**8. Commit that one rule** (implementation + tests) as its own commit before moving to the next rule.

---

## The AI Prompt Template

Copy this for each rule, fill in the bracketed sections from your own Steps 1–4 above, and use it with
any AI model (ChatGPT, Claude, etc.). The structure forces the AI to work from your reasoning rather
than reinterpreting the spec from scratch.

```
I'm implementing one rule of a clinical assessment pipeline in Python. Implement ONLY this rule —
do not add logic, conditions, or event types beyond what's specified below, and do not assume
anything about other rules.

## Shared Event schema (already exists, do not redefine):
[paste your events.py contents here]

## The rule, as specified in our project document:
Rule ID: [e.g. R3]
[paste the exact Detection / Pass logic / Fail logic / Technical boundary rows from the doc]

## My own restatement of the pass/fail logic (this is the source of truth — if it conflicts
## with your reading of the spec text above, follow my restatement and tell me about the conflict):
[paste your Step 2 plain-English restatement]

## Parameters that are still unconfirmed by the clinical supervisor — use a config dict with
## clearly named placeholder values for these, never hardcode them:
[list them, e.g. "max_delay_seconds for R7 — placeholder 10.0"]

## Test cases this function must pass:
[paste your Step 4 test cases as input timeline -> expected CriterionEvaluation]

## Requirements:
- Write one pure function: takes a list of Events (the unified timeline) and a config dict,
  returns a CriterionEvaluation. No side effects, no global state.
- If you make any assumption not covered by my restatement or the spec text, state it explicitly
  as a comment AND in your reply — don't silently decide it.
- Show me the test file too, using my test cases above plus any additional edge cases you think
  I'm missing (but flag those as suggestions, don't assume I want them included).
```

---

## A note on the R3/R4 inference logic specifically

Since we've decided this lives in Clinical Logic Engine rather than Rule Evaluation Engine: when you
get to that stage, the prompt template above still applies, but the "rule" isn't R3 or R4 themselves —
it's a separate function like `resolve_paddle_placement_evidence(timeline, config)` that Clinical Logic
Engine calls *before* handing events to Rule Evaluation Engine. Rule Evaluation Engine's R3/R4 logic
then becomes simpler: it just checks whether that already-resolved fact says Pass, Fail, or Inferred —
it doesn't re-derive the inference itself.
