# Area leads and boundaries

This is the current allocation, updated to the latest team plan. It can change
without changing code interfaces. All three contribute to annotation correction
and each leads benchmarks for two Whisper models; named leads coordinate reviews.

| Lead | Area | Input | Output | Owns |
| --- | --- | --- | --- | --- |
| Ananth | Video models | Frames/recordings | Timestamped video evidence | Detector comparisons, thresholds, persistence, smoothing, semantic postprocessing |
| Ananth | Pipeline | Recording + config | Merged timeline and assembled report | Branch execution, adapter selection, timestamps/offsets, orchestration and integration |
| Arnikan | Annotation | CVAT exports | Validated frozen dataset + annotation timelines | Guidelines, quality checks, extraction, participant splits, label definitions |
| Arnikan | Rule engine | Merged timeline | One decision per enabled rule, with evidence/reason | R1–R7/A1–A7, inference, missing-evidence behavior, approved timing rules |
| Sanjeevan | Audio models | Audio | Timestamped audio evidence | Whisper comparison, command observations/classifier, charging-sound classifier |
| Sanjeevan | Feedback | Rule results | Step-level explanations and improvement text | Templates and wording; no rule decisions |
| Sanjeevan | App | Recording or saved report | Displayed assessment report | Small upload/report UI; calls pipeline rather than duplicating logic |

Charging sound remains isolated in `audio/charging_sound/`, so Ananth or another
member can contribute or take ownership later without moving its public interface.
The newest allocation supersedes the earlier proposal assigning it to Ananth.

## What may cross a boundary

- Shared dataclasses from `schemas/` and the documented public functions.
- Config settings and saved experiment artifacts.
- Test fixtures containing events, rule results, and sample reports.

Models cannot decide Pass/Fail; the pipeline cannot implement clinical rules;
feedback cannot change a rule's result; the app cannot load a detector directly.
Rules have no dependency on `video/`, `audio/`, or `legacy/`.

## Working independently

- Arnikan uses `annotation.to_timeline` or the sample timeline to develop rules.
- Sanjeevan uses `tests/fixtures/sample_rule_results.json` and
  `sample_report.json` to build feedback and the UI before model training finishes.
- Ananth uses the same schemas/fixtures to test merging and integration, then
  swaps in trained adapters through configuration.

Keep the app limited to uploads, timeline, criteria, feedback and a downloadable
report. Research comparisons and agreement with faculty scores belong in
experiments and analysis, not a larger product UI.
