# Rule engine: assumptions

Things the rule engine currently takes as true without proof. Each entry gives the reason, what
would change if it is wrong, how we would notice, and the related open question.

**Status:** `active` (relied on now), `development only` (acceptable while testing with
annotation data, not for real assessments), `confirmed`, or `retired`.

---

### A-001 Annotation timelines fully cover the video
- **Assumption:** In a timeline built from CVAT annotations, the video counts as fully observed
  (`analyses_run: {video: true}`). A missing tag is treated as "did not happen".
- **Why:** Annotators watched the whole recording, and it is the only way to test the rules
  before the video models are ready.
- **Status:** development only. Results carry `annotation_coverage_assumed` (D-035).
- **If wrong:** Annotators tag only what is visible from that camera angle, so a missing tag may
  mean "not visible". A Fail could then be wrong.
- **Detected by:** comparing annotation-based results with faculty assessment; zone visibility
  data once available (OQ-007).
- **Related:** D-035, OQ-007, OQ-028.

### A-002 Engineering values are placeholders
- **Assumption:** These values are reasonable until pilot validation:
  - confidence thresholds: annotation 1.0, video 0.5, audio 0.5;
  - simultaneous window: 0.5 s;
  - minimum gap between two gel applications: 0.4 s (1.0 s until 2026-10-17, OQ-018);
  - R8 placement-match window: removed with the one-zone inference (D-116);
  - header duration tolerance: 0.5 s;
  - R6 removal-before-screen tolerance: 0.5 s (D-105).
- **Why:** The brief says engineering values are chosen in pilot validation, not given by the
  supervisor.
- **Status:** active (all marked `placeholder: true` in `engine.yaml`).
- **If wrong:** Events may be wrongly kept or excluded, two events may be wrongly treated as
  simultaneous, or a recording may be wrongly rejected. No rule logic changes; only values do.
- **Detected by:** pilot precision and recall against faculty assessment.
- **Related:** OQ-018, OQ-019.

### A-003 Command names are provisional
- **Assumption:** The six command names (oxygen away, continue, stand clear, stop, shock,
  start) and the phrases behind them match what the supervisor will accept.
- **Why:** They follow the wording of the proposal document (A1–A6).
- **Status:** active, provisional (D-017).
- **If wrong:** Names or phrases change in `vocabulary.yaml` and the audio phrase list. Rule
  logic is unchanged.
- **Detected by:** supervisor review.
- **Related:** OQ-010, OQ-009.

### A-004 CVAT has exactly eight event tags
- **Assumption:** The seven tags in the annotation audit list, plus
  `first_paddle_firmly_on_the_chest`.
- **Why:** Confirmed by Arnikan from the current CVAT project.
- **Status:** active.
- **If wrong:** A new tag is reported as `unknown_labels_present` until it is added to the
  vocabulary.
- **Detected by:** the vocabulary sync test, and the `unknown_labels_present` anomaly.
- **Related:** OQ-008.

### A-005 Raw object detections are not evidence
- **Assumption:** "A paddle is visible" (`object_visible:*`) is not evidence that it was placed
  correctly, nor that a shock was delivered.
- **Why:** README and team agreement.
- **Status:** active.
- **If wrong:** Rules would need semantic events built from raw detections. That is upstream
  work.
- **Related:** OQ-004, OQ-012.

### A-006 One event per real action
- **Assumption:** Upstream sends one event per real action or command. Duplicate detections are
  merged upstream (D-021).
- **Why:** Merging is part of detection quality, which upstream owns.
- **Status:** active.
- **If wrong:** Two events for one shock produce `multiple_shocks`, and shock-dependent rules
  become Unable to Verify.
- **Detected by:** `multiple_shocks` with `within_simultaneous_window: true`.
- **Related:** D-030, OQ-019.

### A-007 "Analysis ran" means the whole recording was usable
- **Assumption:** If the header says audio (or video) analysis ran, that modality is covered for
  the whole recording.
- **Why:** Upstream sends no finer coverage information yet.
- **Status:** active.
- **If wrong:** A missing command during an unusable stretch could become a wrong Fail.
  Upstream would need to send explicit `coverage` entries or time windows.
- **Detected by:** faculty comparison; Unable to Verify rates.
- **Related:** OQ-020, OQ-027.

### A-008 Only the per-paddle placement events belong to camera regions
- **Assumption:** The apical and sternal zones govern only `apical_paddle_placed` and
  `sternal_paddle_placed`.
- **Status:** active.
- **If wrong:** Other events (for example "paddles firmly on chest") need a region, which is one
  line in `engine.yaml`.
- **Related:** OQ-012.

### A-009 Zone visibility is the coverage of that zone's placement event
- **Assumption:** A zone counts as visible when its per-paddle placement event is covered.
- **Status:** active.
- **Related:** OQ-007.

### A-010 "Near the shock" uses the simultaneous window
- **Assumption:** A command is "near the shock" when its start is within
  `simultaneous_window_seconds` (0.5 s) of the shock time, boundary included.
- **Status:** active (placeholder value).
- **Related:** OQ-018, D-041.

### A-011 Speech-recognition confidence is only a proxy
- **Assumption:** The audio confidence comes from the speech model's probability. It is not a
  calibrated probability that the command was given, so the audio threshold is especially
  uncertain.
- **Status:** active.
- **If wrong:** Correct commands may be excluded, which gives Unable to Verify rather than Fail
  (D-010), or wrong ones kept.
- **Related:** OQ-019, OQ-037.

### A-012 One camera and one recording per assessment
- **Assumption:** Multi-camera fusion is a later extension.
- **Status:** active (D-032).
- **Related:** OQ-038.

### A-013 Event IDs are assigned before the rule engine
- **Assumption:** The pipeline merger or an input adapter gives every event a unique ID.
- **Status:** active (otherwise the timeline is rejected as `missing_event_id`).

### A-014 Under the removal fallback, the real shock time is unknown but before the removal
- **Assumption:** When no shock is confirmed on screen, the shock happened at some unknown time
  **before** the first paddle removal, never after it.
- **Why:** The paddles are removed after the shock is delivered.
- **Status:** **retired** (2026-10-19, D-115): the removal fallback it served is removed. Updated
  2026-10-13: the earlier version also assumed that a start command before the removal counts as
  "before the shock". D-053 rejected that, so commands before the
  removal are now timing-ambiguous (`command_before_removal`): they are not counted, and are not
  a mistake.
- **If wrong:** If paddles could be removed before the shock, the fallback itself (D-023) would
  be invalid. Every result using it is flagged `shock_time_from_removal`.
- **Related:** D-023, D-024, D-053, OQ-039.

### A-015 Annotation events are single moments
- **Assumption:** CVAT tags become point events (start = end), even for labels whose CVAT type
  is "any".
- **Status:** active.

### A-016 Only A7 needs other rules' results
- **Assumption:** Apart from A6 reusing R7, only A7 depends on other rules' results (A1–A5).
  Everything else depends only on events.
- **Status:** active; will be revisited as each rule is built.

### A-017 A time limit with a value but no approver is not used
- **Assumption:** If a clinical limit in `rules.yaml` has a value but no `approved_by`, the rule
  does not use it. Timing is not checked, and the result is flagged `timing_not_checked` and
  `limit_not_approved`.
- **Why:** D-005 says unapproved values stay empty, and the brief says clinical values are never
  invented. A value that is present but unapproved is treated as if it were empty, rather than
  silently used. No current limit is in this state (A8's 5 s is approved, D-016).
- **Status:** confirmed by D-061 (2026-10-14).
- **If wrong:** A provided value would be used, flagged instead. That is one line in
  `rules/checks.py` (`time_limit`).
- **Related:** D-005, D-061, D-062, OQ-042.

### A-018 No events at all is a missing event, not a count violation
- **Assumption:** The expected-count check (D-071) raises `count_violation` only when at least
  one confident event exists and the count is outside its range. Zero confident events is a
  missing event, decided by the coverage step (P-007, P-008) and the rules.
- **Why:**
  - Whether a missing step is a mistake depends on coverage: an event the camera could not
    see is not the learner's fault (D-004).
  - Low confidence is not absence (D-010).
  - A count anomaly for every missing step would mark every Fail for a skipped step as
    "timeline needs review", and turn every Unable to Verify into Incomplete.
  - "Too few but not zero" is still checked, for example `at_least: 2` with one found.
- **Status:** confirmed by D-072 (2026-10-14).
- **If wrong:** Remove the `not same` condition in `rules/prepare.py` (`_count_anomalies`).
- **Related:** D-071, D-072, OQ-046.

### A-019 The annotators' tagging convention for paddle placement
- **Assumption (from Arnikan, 2026-10-16):** a correct, fully visible procedure is tagged in this
  order: `first_paddle_taken` → `first_paddle_firmly_on_the_chest` → `second_paddle_taken` →
  `paddles_firmly_on_chest`. Two exceptions:
  - when a learner places both paddles at the same time (a mistake), annotators don't tag
    `first_paddle_firmly_on_the_chest`, because no paddle went first;
  - when only one paddle is visible as both are placed, `paddles_firmly_on_chest` isn't tagged.
- **Why it matters:** a missing first-placement tag is evidence in itself. With two
  near-simultaneous derived placements, it supports `possible_parallel_placement` (D-086).
- **Status:** active (stated by Arnikan from the annotation videos).
- **If wrong:** the T1 and T2 rules in `annotation/derive_paddle_placements.py` (`_check_tags`)
  change.
- **Related:** D-086, OQ-056.

### A-020 A frame where the zone is not visible is unknown, neither in nor out of the zone
- **Assumption (changed by Arnikan on 2026-10-16; the first version counted such a frame as
  "out"):** when the paddle's zone has no visible box on a frame, the frame is **unknown**. An
  example is the annotator marking the zone outside while the paddle covers it.
  - An unknown frame doesn't start a placement and doesn't end one.
  - If the paddle is in its zone on both sides of the gap, it is the same placement.
  - Out frames on both sides of a gap still add up towards an exit.
- **Why:** counting it as "out" would turn a zone occlusion longer than `exit_frames` into an
  invented re-placement.
- **How it is checked:** the validation report still gives each paddle's
  `frames_zone_not_visible`.
- **Status:** decided, D-090.
- **Related:** D-081, D-089, D-090.

### A-021 A paddle removal shows that the paddles were on the chest (R3/R4 inference)
- **Assumption (the proposal, kept by D-102):** a confirmed `paddles_removed_after_shock` means
  the paddles had been placed firmly and both buttons pressed, so it can support Pass – Inferred
  for R3 and R4, as the shock on the screen can.
- **Known limitation:** in the videos, the paddles are sometimes removed **without a successful
  shock**. R3/R4 may then be Pass – Inferred although no successful shock happened.
- **Why it is acceptable for now:** the overall result can never be Pass in that case. R5 is
  Fail `missing` when the screen was visible, or Unable to Verify when it wasn't.
- **Status:** **retired** (2026-10-19, D-115): R3 and R4 no longer infer from the removal, because
  a removal doesn't show that a shock was delivered. No inference rule from removal was found in
  the original documents; it came from the rule engine brief.
- **If wrong:** remove `paddles_removed_after_shock` from `inference_sources` in
  `configs/rules.yaml` (R3, R4). No code changes.
- **Detected by:** the supervisor's answer to OQ-060; comparing R3/R4 inferred passes with R5
  results in the interim runs.
- **Linked on results:** an inference from the removal is flagged `inferred_from_removal`, and its
  reason names A-021 (D-107).
- **Related:** D-102, D-107, D-057, P-016, OQ-060, OQ-061.

### A-022 A removal would have been seen if both placement zones were in view
- **Assumption:** when both placement zones are visible from the shock to the end of the
  recording, a paddle removal in that time would have been tagged. A missing removal is then a
  real absence (R6 `missing`).
- **Why:** the paddles leave the zones when they are removed, so the zones being in view is the
  best available coverage for a removal. No region is defined for the removal itself.
- **Status:** active.
- **If wrong:** R6 could fail `missing` when a removal happened but wasn't visible or wasn't
  tagged. Then R6 should give Unable to Verify instead (change `_removal_missing` in
  `rules/video_rules.py`).
- **Detected by:** reviewing R6 `missing` results in the interim runs against the videos.
- **Related:** D-104, D-092, P-034.

### A-023 `Gel applied` is tagged when the nozzle is on or near a zone
- **Assumption (from Arnikan, 2026-10-17):** `Gel applied` was tagged when the bottle's nozzle was
  clearly visible on or near a placement zone. Gel can be applied near the zone, not strictly
  inside it.
- **Why it matters:** 9d uses proximity to the zone, not overlap with it (D-111). A missing tag
  can also mean the nozzle wasn't clearly visible (A-026).
- **Status:** active (stated by Arnikan from the annotation videos).
- **If wrong:** the 9d settings, and the R1 proxy's reading of a tag as one application.
- **Related:** D-111, D-113, A-026.

### A-024 The `learner_hand` box covers only the hand holding the gel bottle
- **Assumption (from Arnikan, 2026-10-17):** the `learner_hand` box covers only the hand holding
  the gel bottle, and it is tracked during gel application in every video.
- **Why it matters:** the bottle period (the hand box's first to last frame in the gel phase) is
  when gel could have been applied, and a frame without a hand box inside it is hidden (D-111).
- **Status:** active.
- **If wrong:** a hand box of another hand would create false applications; a video without hand
  tracking gives unknown zones and the review issue `gel_hand_not_tracked`.
- **Detected by:** `gel_hand_not_tracked` in the audit; disagreements in `gel_validation.md`.
- **Related:** D-111.

### A-025 During gel application the hand is near the zone, sometimes overlapping, rarely further
- **Assumption (from Arnikan, 2026-10-17):** during gel application the hand box is usually near
  the zone box, sometimes overlapping it, and rarely a bit further away.
- **Why it matters:** `gel_hand_zone_max_gap` (placeholder 5% of the frame diagonal) must be
  generous enough for "a bit away", and overlap is not required (D-111).
- **Status:** active.
- **Detected by:** the distribution of the smallest gaps in `gel_validation.md`.
- **Related:** D-111, OQ-018.

### A-026 Zone visibility stands for "the gel could have been seen" (R1 proxy)
- **Assumption:** before the 9d gate, R1 treats a zone visible throughout the gel phase as meaning
  that a gel application there would have been tagged (D-113).
- **Known risk:** the learner's arm can hide the nozzle while the zone is visible, so a missing
  tag may be an application nobody could see. R1 could then wrongly fail `applied_once` or
  `missing`. The proxy also can't tell which zone a tag was on: two tags with both zones visible
  are taken as one per zone.
- **Status:** development only (until the 9d gate is approved).
- **If wrong:** use only the per-zone path (past the 9d gate), or give Unable to Verify instead.
- **Detected by:** the proxy check in progress.md (Increment 17) and the 9d validation report.
- **Related:** D-113, A-023.

### A-027 The team's working definition: `first_paddle_*` is the apical paddle, `second_paddle_*` the sternal paddle
- **Assumption (the team: Ananth, Sanjeevan, Arnikan, 2026-10-19):** `first_paddle_taken` and
  `first_paddle_firmly_on_the_chest` mean the **apical** paddle, and `second_paddle_taken` means the
  **sternal** paddle. This is the team's working definition of the labels. The names give identity
  only, never time order: wherever a rule or helper needs "first" or "second" in time, it computes
  it from the event times (D-118).
- **Background:** the labels were named when the annotated videos were understood to be
  apical-first, so order and identity coincide in the training labels. The video models are
  trained on these labels, so a learner who takes the sternal paddle first is expected to produce
  `second_paddle_taken` before `first_paddle_taken`.
- **The vocabulary is unchanged:** the names and the CVAT mapping stay as they are
  (`first_paddle_firmly_on_the_chest` → `first_paddle_placed`, D-047). This is a definition of what
  they mean, not a rename.
- **Remaining risk: untested on reversed-order recordings.** Order and identity never differed in
  the training data, so it is unknown whether the models learned the paddle's appearance or its
  order. Only a recording with the reversed order can test it. If the models learned the order, a
  reversed order would go unseen.
- **Consequences for the rules:** R8's one-zone inference compared the visible placement with
  `first_paddle_placed`, the apical placement under this definition, so it was circular; it is
  removed (D-116). Every other reader of these tags reads identity only: R1, R2, R3 and R8 take
  the order from `paddle_order`, and Steps 9c and 9d from the same times (D-118; the list is in
  progress.md, 2026-10-19).
- **Status:** active (team decision).
- **Detected by:** a recording with the sternal paddle first, run through the models.
- **Related:** D-013, D-014, D-047, D-051, D-086, D-116, D-118.
