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
  - minimum gap between two gel applications: 1.0 s;
  - R8 placement-match window: 0.5 s;
  - header duration tolerance: 0.5 s.
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
- **Status:** active. Updated 2026-10-13: the earlier version also assumed that a start command
  before the removal counts as "before the shock". D-053 rejected that, so commands before the
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
