# Rule engine output contract

**Report version:** 7
**Contract date:** 2026-10-14 · **Owner:** Arnikan · **For:** Sanjeevan (feedback module and app)

This is what the rule engine hands over: the structure of its JSON report, every possible overall
result and rule result, and every flag and code the feedback module may receive. It is
**versioned** (D-070):
- `report_version` (in `rules/render.py`) and this document's version go up together, with a
  line in the changelog below, whenever a report field or a code (overall result, rule kind,
  flag, anomaly, failure code or rejection) is **added, removed or renamed**, or its **meaning
  changes**.
- A code listed here as **planned** becoming built does **not** change the version; only its
  status here changes.

A test fails if the two versions disagree, or if a code exists in the engine or in
decision_flow.yaml but not here.

**Status of this rule:** interim until Sanjeevan confirms it (OQ-045).

Related: [decision_flow.yaml](decision_flow.yaml) (where each code is produced),
[anomalies.md](anomalies.md) (the technical code catalogue), [pathways.md](pathways.md) (worked
examples), [open_questions.md](open_questions.md) (undecided items).

## Changelog

| Version | Date | Change |
|---|---|---|
| 1 | 2026-10-14 | First version (Increment 9) |
| 2 | 2026-10-14 | Two timeline anomalies added (Increment 9a, D-071): `count_violation` and `paddle_identity_conflict`. Both may appear in `overall.timeline_anomalies` and make the overall result Incomplete (D-072). The settings `expected_counts.*` appear in `configuration.placeholders` and `configuration.undecided`. No field was added, removed or renamed |
| 3 | 2026-10-17 | `context.header` gains two fields (Increment 10): `visibility` (each placement zone's visible intervals in seconds, `{"region:apical_zone": [[start, end], ...]}`, D-092) and `flags` (a list; `annotation_coverage_assumed` for annotation data). The rule flag `annotation_coverage_assumed` is now built: every result of an annotation timeline carries it, and `development_data` is then true (D-066). `context.zone_visibility` is unchanged (the whole-recording status) |
| 4 | 2026-10-17 | **Meaning changed:** `no_shock` now means no shock seen on the screen. The shock time is never inferred (D-093), so a paddle removal no longer gives a shock time. `shock_time_from_removal` and `command_before_removal` appear only if `shock_time_fallback` is set to `removal`, which is not the decided setting. **New region:** `screen` (the defibrillator screen, D-094) appears in `context.zone_visibility`, `context.header.coverage` and `context.header.visibility`. R2 is implemented (Increment 11), so `simultaneous` and `taken_before_first_placed` are now built. **New failure code** `first_placement_not_observed` (R2, D-097). It replaces the planned "first missing" code, which is removed, because R2 never produces it. R2 still reports `pending` until it is approved |
| 5 | 2026-10-17 | **Two rule flags added** (R8, Increment 12): `possible_parallel_placement` is the **shared cause flag**. One parallel placement fails both R2 and R8 with `simultaneous`, and both results carry it, so the feedback can explain that one action caused both (D-098). `derived_placement` marks a result resting on placements derived from the boxes (D-088). R8 is implemented, so `wrong_order` (R8), `placement_missing`, `contradictory` and `inferred_fail_policy_undecided` are now built. R8 still reports `pending` until it is approved |
| 6 | 2026-10-17 | **Rule flag added** (R5, Increment 13): `order_not_checked`. R5 checked the shock's presence but not its order, because the steps that must precede it are not set yet (OQ-013), or one of them was not observed. Like `timing_not_checked`, it makes the overall result Incomplete, never Pass, under the new category "order not checked" in `overall.incomplete` (D-100). R5 is implemented, so `missing` (R5) and `wrong_order` (R5) are now built. R5 still reports `pending` until it is approved |
| 7 | 2026-10-17 | **Field added:** each entry of `configuration.timing_limits` gains `no_limit` (true or false). `no_limit: true` with an approver is a decision that no time limit applies: the rule passes fully, without `timing_not_checked` (D-103). `value: null` with `no_limit: false` still means "not decided yet" (D-062). R6 is implemented (Increment 14), so `removed_before_shock`, `missing` (R6) and `too_late` (R6, only once an approved limit is exceeded) are now built. `paddles_removed_after_shock` doesn't prove a shock (D-104). R6 still reports `pending` until it is approved |

## How to get the report

- **Python:** `from rules.engine import assess; from rules.render import report` then
  `report(assess(events, config, header=header))`.
- **Command line:** `python -m rules.run --events timeline.json [--header header.json]
  [--output report.json]`. Exit code 0 means a report was written. Exit code 2 means no
  assessment was possible (see "Errors" below), and no report is written.
- **The pipeline:** `pipeline/run.py` still uses the shared `RuleResult` list (one entry per rule,
  as before). It will include this report once it calls `assess()` (OQ-017).

## Structure

| Key | Type | Meaning |
|---|---|---|
| `report_version` | int | The version of this contract (1) |
| `kind` | string | Always `rule_engine_report` |
| `development_data` | bool | `true` when the results come from annotation data and are **not a real assessment** (D-066). Feedback must not be shown to a learner as an assessment |
| `overall` | object | The overall result and its explanation (below) |
| `rules` | list | One entry per enabled rule, in report (display) order |
| `timeline` | object | The evidence used: events, excluded low-confidence events, anomalies, unknown/unused/unresolved labels, sources |
| `context` | object | Header, key times (`anchors`: shock, placements, commands), command resolutions, zone visibility |
| `configuration` | object | Placeholder and undecided settings, clinical limits with approval, rule statuses. Each `timing_limits` entry has `value`, `no_limit` (v7: an approved "no limit", D-103), the approval fields and `approved` |

**`overall`:**
- `result`;
- `summary`: one plain sentence;
- `decided_by`: the policy step or setting;
- `flags`;
- `timeline_anomalies`;
- `deciding`: the rules that decided the result;
- `mistakes`: every Fail, each a named mistake with its `failure_code` and `title`;
- `incomplete`: each rule keeping the result from being complete, with its `category`;
- `unverified`.

Each entry in these lists has `rule_ids` (R7 and A6 appear once, as `["R7", "A6"]`), `kind`,
`reason`, `failure_code`, `title` and `category`.

**Each `rules` entry:**
- `rule_id`, `title`;
- `kind`;
- `status`: the shared `RuleResult` status;
- `evaluated`, `passed`;
- `reason`;
- `shared_reason`: the reason with code, kind and flags appended, as in the pipeline;
- `failure_code`;
- `evidence`: event IDs;
- `timestamps`;
- `flags`;
- `blocked_by`: for not evaluable;
- `timing_checked`: `true`, `false`, or `null` when the rule has no time limit.

### Example (trimmed)

Generated by a real engine run. A1, A3, R7/A6 and A7 were approved for the example; the other
rules are pending. Audio was analysed, the shock was at 30 s, "stand clear" was said at 26.5 s,
the restart command at 33 s, and there was no "oxygen away" command.

```json
{
  "report_version": 7,
  "kind": "rule_engine_report",
  "development_data": false,
  "overall": {
    "result": "fail",
    "summary": "Fail: A1 failed",
    "decided_by": "any evaluated rule Fail (D-001)",
    "flags": [],
    "timeline_anomalies": [],
    "deciding": [
      {"rule_ids": ["A1"], "kind": "fail", "failure_code": "missing", "title": "Oxygen away", "...": "..."}
    ],
    "mistakes": [
      {"rule_ids": ["A1"], "kind": "fail", "failure_code": "missing", "title": "Oxygen away",
       "reason": "oxygen away: no confident oxygen_away_command (coverage covered, header.analyses_run; decided by coverage_policy.outcomes.covered)",
       "category": ""}
    ],
    "incomplete": [
      {"rule_ids": ["R1"], "kind": "pending", "category": "rules not yet approved", "...": "..."},
      {"rule_ids": ["R7", "A6"], "kind": "pass_direct", "category": "timing not checked",
       "reason": "shock to restart: timing not checked: no approved limit", "...": "..."}
    ],
    "unverified": [
      {"rule_ids": ["A7"], "kind": "not_evaluable", "reason": "not evaluable because of A1 (fail)", "...": "..."}
    ]
  },
  "rules": [
    {"rule_id": "A1", "title": "Oxygen away", "kind": "fail", "status": "fail", "evaluated": true,
     "passed": false, "failure_code": "missing", "evidence": [], "flags": [], "blocked_by": null,
     "timing_checked": null, "reason": "oxygen away: no confident oxygen_away_command (...)",
     "shared_reason": "oxygen away: no confident oxygen_away_command (...) [failure code: missing]",
     "timestamps": {}},
    {"rule_id": "R7", "title": "Compressions restarted promptly after shock", "kind": "pass_direct",
     "status": "pass_direct", "evaluated": true, "passed": true, "failure_code": null,
     "evidence": ["ev_restart"], "timestamps": {"seconds": 3.0}, "flags": ["timing_not_checked"],
     "blocked_by": null, "timing_checked": false,
     "reason": "shock to restart: timing not checked: no approved limit",
     "shared_reason": "shock to restart: timing not checked: no approved limit [timing not checked; flags: timing_not_checked]"},
    {"rule_id": "A7", "title": "Correct sequence of audio commands", "kind": "not_evaluable",
     "status": "unable_to_assess", "evaluated": true, "passed": false, "failure_code": null,
     "evidence": [], "flags": [], "blocked_by": "A1", "timing_checked": null,
     "reason": "not evaluable because of A1 (fail)", "timestamps": {},
     "shared_reason": "not evaluable because of A1 (fail) [not evaluable]"}
  ],
  "timeline": {"events": ["..."], "excluded": [], "anomalies": [], "unknown_labels": [],
               "unused_labels": [], "unresolved_labels": [], "sources": ["audio", "video"]},
  "context": {"header": {"recording_id": "P03_LL", "camera_angle": "LL", "duration_seconds": 95.0,
                         "analyses_run": {"video": true, "audio": true}, "coverage": {},
                         "visibility": {}, "flags": []},
              "anchors": {"shock": {"time": 30.0, "event_id": "ev_shock", "flags": [], "...": "..."}},
              "resolutions": [], "zone_visibility": {"...": "..."}},
  "configuration": {"placeholders": ["..."], "undecided": ["..."], "timing_limits": {"...": "..."}, "rules": ["..."]}
}
```

## Overall results

| Result | Status | Meaning for feedback |
|---|---|---|
| `pass` | decided | Every rule was evaluated and passed, with timing checked, and the timeline needs no review |
| `fail` | decided | At least one evaluated rule failed. `mistakes` lists each one. Also produced by the Unable-to-Verify setting once it is decided as Fail; then `mistakes` is empty and `decided_by` names the setting |
| `incomplete` | decided | Not everything could be assessed: pending rules, an assumed result, an engine error, timing not checked, a timeline needing review, or no rule evaluated. `incomplete` lists each rule and why. **Never present as Pass** |
| `faculty_review` | undecided (OQ-002) | Only once `unable_to_verify_outcome` is decided as `faculty_review`: no Fail and nothing incomplete, but some steps could not be verified |
| `unable_to_verify` | interim (OQ-002) | The same situation while that setting is still undecided. It will become `fail` or `faculty_review` when decided |

## Rule result kinds

| Kind | Shared status | Status | Meaning |
|---|---|---|---|
| `pass_direct` | `pass_direct` | decided | The step was observed and is correct |
| `pass_inferred` | `pass_inferred` | decided | Accepted through an approved inference (for example R3 from the shock or removal); `evidence` names the supporting event |
| `fail` | `fail` | decided | The evidence clearly shows the mistake; `failure_code` names it |
| `unable_to_verify` | `unable_to_assess` | decided | The evidence is missing, unclear or low-confidence; not the learner's fault (D-004) |
| `not_evaluable` | `unable_to_assess` | decided | Could not be judged because of another step; `blocked_by` names it (one mistake reported once, D-003) |
| `pending` | `unable_to_assess` | decided | The rule is not yet approved by the supervisor |
| `assumed` | `unable_to_assess` | decided | R8 by the apical-first fallback: to be checked by the evaluator (D-060) |
| `engine_error` | `unable_to_assess` | decided | The rule crashed; `reason` holds the error. A software problem, never feedback for the learner (D-063) |

## Codes

**Status:**
- **built:** produced today.
- **planned:** produced once the rule or step that raises it is built.
- **interim:** the current behaviour until a decision.
- **undecided:** marks a case whose policy is still open.

### Flags on rule results (`rules[].flags`)

| Code | Status | Meaning for feedback |
|---|---|---|
| `low_confidence_evidence` | built | The event may have happened, but was detected with low confidence. Unable to Verify, never Fail |
| `coverage_policy_undecided` | undecided (OQ-001) | Whether the event could be observed is unknown; interim Unable to Verify |
| `timing_not_checked` | built | No approved time limit, so only presence and order were checked. The overall result cannot be Pass (D-062). Never raised for an approved "no limit" (D-103) |
| `limit_not_approved` | built | A time limit exists but is not approved, so it was not used (D-061) |
| `order_not_checked` | built (v6) | Only presence was checked, not the order. For R5: the shock was seen, but the steps that must come before it are not set yet (OQ-013), or one of them was not observed. The overall result cannot be Pass (D-100) |
| `shock_time_from_removal` | built (only with `shock_time_fallback: removal`, not the decided setting) | No shock on screen; the shock time comes from paddle removal, so delays look shorter than they were (D-023) |
| `no_shock` | built (meaning changed in v4) | No shock was seen on the screen, so there is no shock time; it is never inferred (D-093). Shock-dependent rules are Not evaluable because of R5 |
| `multiple_shocks` | built | Two or more shocks; no shock time was chosen (also a timeline anomaly) |
| `multiple_candidates` | built | Several events could give a key time; the earliest was used |
| `command_near_shock` | built | A "resume compressions" command was too close to the shock to tell continue from restart |
| `command_before_removal` | built (only with `shock_time_fallback: removal`) | Under the removal fallback, a command before the removal may have been the restart (D-053, D-059) |
| `no_shock_time` | built | No shock time, so a command or the restart could not be placed |
| `unresolved_commands` | built | An ambiguous command could not be classified, so the continue or restart time may be incomplete |
| `start_command_before_shock` | built | "Start compressions" was said before a confirmed shock; it does not count as the restart (D-025) |
| `placement_missing` | built (R8) | R8: a paddle's zone was in view during the placement phase but its placement was not observed, so the order cannot be judged; R3 reports the missing placement (D-058) |
| `contradictory` | built (R8) | R8: the only visible paddle was placed clearly before the first placement; the evidence contradicts itself, so Unable to Verify |
| `inferred_fail_policy_undecided` | undecided (OQ-005) | R8: the one-zone inference shows the sternal paddle first, an inferred mistake; reported as Unable to Verify until it is decided whether an inferred mistake is a Fail |
| `possible_parallel_placement` | built (v5) | **Shared cause flag.** Both paddles were placed at the same time, a learner mistake seen in the derived placements (only once the gate is approved). It appears on **both R2 and R8**, each failed with `simultaneous`. They are separate checklist criteria, but **one action caused both failures**, so the feedback can say so (D-098). Whether this counts as one mistake or two is OQ-059 |
| `derived_placement` | built (v5) | The result rests on a paddle placement derived from the annotated boxes by the exporter (direct evidence, method recorded), not on a tag (D-081, D-088) |
| `annotation_coverage_assumed` | built (v3) | The timeline comes from annotation data (its header is flagged so). Every result carries it, and the report is development data, not an assessment (D-066) |

### Flags on the overall result (`overall.flags`)

| Code | Status | Meaning for feedback |
|---|---|---|
| `timeline_needs_review` | built | The recording's data has a problem (`overall.timeline_anomalies`). The result is never Pass (D-065, D-069) |
| `development_data` | built | Not a real assessment (D-066) |
| `overall_policy_undecided` | interim (OQ-002) | `unable_to_verify` because the policy is not decided yet |
| `no_rules_evaluated` | built | No rule was evaluated; Incomplete (D-068) |

### Timeline anomalies (`timeline.anomalies[].code`, `overall.timeline_anomalies`)

| Code | Status | Meaning for feedback |
|---|---|---|
| `mixed_evidence_sources` | built | One event comes from both human annotation and a model |
| `unknown_labels_present` | built | Some labels are not recognised (a possible naming mismatch) |
| `count_violation` | built (v2) | An event appeared more (or fewer) times than expected, for example two paddle removals. `details` gives the `event`, `expected` and `found` counts. For events expected once, `possible_duplicates` lists pairs "possibly the same incident detected twice". **Not a learner mistake**: no rule fails because of it. It blocks an overall Pass (`timeline_needs_review`, D-072) |
| `paddle_identity_conflict` | built (v2) | Two or more placements of one paddle and none of the other: the paddle identity was probably swapped or lost. Not a learner mistake. It blocks an overall Pass (`timeline_needs_review`, D-072) |

(`multiple_shocks` is listed above.)

### Failure codes (`rules[].failure_code`, `overall.mistakes[].failure_code`)

All are **planned**: they appear once the rule that raises them is built (Increments 11 to 23,
[rules_status.md](rules_status.md)).

| Code | Status | Rules | Meaning for feedback |
|---|---|---|---|
| `missing` | built (R5, R6; the others planned) | R1, R5, R6, A1–A5, R7/A6 | The required step or command was not done. For R5: no shock on the screen while the screen was visible throughout the window from paddles firmly on chest to paddles removed (D-101). For R6: no paddle removal while both placement zones were visible from the shock to the end of the recording (D-104) |
| `applied_once` | planned | R1 | Gel applied only once |
| `outside_time_period` | planned | R1 | The two gel applications were not within the approved period |
| `simultaneous` | built (R2, R8) | R2, R8 | Two actions happened at the same time where order matters. A parallel placement gives it on **both** R2 and R8, each carrying the cause flag `possible_parallel_placement` (D-091, D-098) |
| `taken_before_first_placed` | built (R2) | R2 | The second paddle was taken before the first was placed |
| `first_placement_not_observed` | built (R2, v4) | R2 | No first placement was seen between taking the first and the second paddle, although both placement zones were in view throughout. **Either the paddles were placed in parallel, or the second paddle was taken before the first was placed** (A-019, D-097). Once the derived-placement gate is approved, a parallel placement is reported as `simultaneous` instead (D-091) |
| `wrong_order` | built (R5, R8; A4, A7 planned) | R5, R8, A4, A7 | Steps or commands in the wrong order. For R5: the shock came before one of the preceding steps (once they are set, D-100). For R8: the sternal paddle was placed before the apical (directly, or by inference once `inferred_fail_outcome` is decided as fail) |
| `not_in_zone` | planned | R3 | A paddle was outside its approved zone |
| `placed_after_shock` | planned | R3 | Paddles placed after the shock |
| `before_placement` | planned | R4 | Buttons pressed before the paddles were placed |
| `not_pressed` | planned | R4 | Buttons not pressed |
| `removed_before_shock` | built (R6) | R6 | Paddles removed before the shock on the screen: a removal tagged more than the simultaneous window before it, or (once the gate is approved) a derived placement that ended before it, flagged `derived_placement` (D-104) |
| `after_shock` | planned | A1, A3, A4 | The command came after the shock |
| `wrong_stage` | planned | A2 | "Continue compressions" at the wrong stage |
| `before_shock` | planned | R7/A6 | The restart command came before the shock |
| `too_late` | built (R6; R7/A6 planned) | R6, R7/A6 | Done after the approved delay. For R6: the paddles were removed later than an approved `shock_to_removal_seconds` (unset now, so not produced yet). For R7/A6: the restart command came after the approved delay |
| `pre_shock_pause` | planned | A8 | "Stop CPR" to "Start CPR" took longer than 5 s; mistake label "Pre-Shock Pause" |
| `unspecified` | built | shared-contract path rules | A rule plugged in through the old `module:function` path reported a Fail without a code |

### Errors: no report is produced

These stop the run, so the feedback module never receives them in a report. `rules.run` prints
them and exits with code 2. It does the same, without a code, when a file cannot be read or is
not valid JSON. In Python, they are raised as `rules.errors.TimelineError` or
`rules.errors.RegistryError` (a `ConfigError`), each with a `.code`. Other configuration errors
are `ConfigError` with a message and no code.

| Code | Status | Meaning |
|---|---|---|
| `not_a_list` | built | The timeline is not a list of events |
| `not_an_event` | built | An item is not a valid event |
| `missing_event_id` | built | An event has no ID |
| `duplicate_event_id` | built | Two events share an ID |
| `multiple_camera_angles` | built | Events from more than one camera angle |
| `multiple_recordings` | built | Events from more than one recording |
| `no_confidence_threshold` | built | An event's source has no confidence threshold |
| `invalid_header` | built | The timeline header is malformed |
| `header_mismatch` | built | The header contradicts the events |
| `approved_rule_not_registered` | built | An approved rule has no implementation |
| `registered_rule_not_in_config` | built | A registered rule ID is not in the catalogue |
| `duplicate_rule_registration` | built | Two implementations for one rule ID |
| `unknown_required_event` | built | A rule needs an event that is not in the vocabulary |
