# What the rule engine needs from upstream

For: Ananth (video postprocessing, pipeline) and Sanjeevan (audio command detection).
Owner: Arnikan (rule engine). Status: draft, 2026-10-10.

The rule engine reads one merged timeline of `schemas.event.Event` records (see
`docs/contracts.md`). It decides Pass/Fail itself, so upstream should report **only what was
observed**: no ordering, no gap-filling, no inference, no scores. Inference (for example which
paddle was placed first when only one zone is visible) happens in the rule engine.

## Names

Emit the **agreed canonical names** directly. The reference list is
`configs/rule_engine/vocabulary.yaml` (`events:` section). That file also maps a few legacy
labels as a safety layer, but new outputs should not rely on it. A name that is not in the list
is kept in the report and flagged as unknown, and no rule uses it. To add or rename a name,
agree it with Arnikan and add one line to `vocabulary.yaml`.

## General rules for every event

| Field | Requirement |
|---|---|
| `event_name` | A canonical name from the lists below |
| `start`, `end` | Seconds on the recording's common clock. A point event has `start == end`; a state (for example "zone visible") is an interval |
| `confidence` | 0–1; record what it means in `metadata.confidence_kind` |
| `source` | `video` or `audio` |
| `metadata` | Provenance (model, frame, etc.) |

- **Repeated events:** report every occurrence. The rule engine decides which one counts.
- **One recording:** all events must come from one recording, with one camera angle. Events with
  no camera angle (for example audio) are fine.
- **Event time:** the rule engine orders and times events by their **`start`** time.

## Upstream owns detection quality

These belong to video postprocessing and audio command detection, not the rule engine:

- **Merging duplicate detections:** one real action or command should be one event. For
  example, the same shock detected over several frames, or a command split across two
  transcript segments, should arrive as one event. The rule engine does **not** merge events. If
  it sees two shocks, it flags `multiple_shocks` and says whether they fall within
  `simultaneous_window_seconds` ("possibly the same shock detected twice").
- **Choosing confidence thresholds:** each model's owner selects and validates its threshold in
  pilot validation, and emits only events it considers confident.
- **Rule-engine safety check:** the rule engine keeps its own configurable confidence check
  (`configs/rule_engine/engine.yaml: confidence_thresholds`). A threshold of `0` disables it.
  To avoid applying two different thresholds to the same events, we need to agree which side
  applies them (open item 6).

## Timeline header (requested)

Please send a header with each timeline, alongside the events:

| Field | Meaning |
|---|---|
| `recording_id` | The recording / task ID (for example `P03_LL`) |
| `camera_angle` | The single camera angle the video events come from |
| `duration_seconds` | Length of the recording |
| `analyses_run` | Which analyses actually ran, for example `{video: true, audio: true}` |

**Why:** without `analyses_run`, a timeline with no audio events could mean "nobody gave a
command" (a learner mistake) or "audio analysis did not run" (no evidence). The rule engine
must not blame the learner for missing data, so today it has to treat both cases as unknown.
`duration_seconds` lets it tell "the event never happened" from "the recording was cut short".
The rule engine will use the header for coverage (Increment 4). The format is a proposal to
agree; it can be a small wrapper around the event list, so the `Event` schema does not change.

## From video postprocessing (Ananth)

### Action events

| Canonical name | Meaning | Used by | Priority |
|---|---|---|---|
| `gel_applied` | Gel applied (one event per application) | R1 | Required |
| `first_paddle_taken` | First frame where the first paddle is clearly visible | R2 | Required |
| `second_paddle_taken` | First frame where the second paddle is clearly visible | R2 | Required |
| `first_paddle_placed` | **First placement time**: the first time either paddle is placed firmly on the chest | R2, R8 | Required |
| `apical_paddle_placed` | **Per-paddle placement**: apical paddle placed in its zone | R8, R3 | Required |
| `sternal_paddle_placed` | **Per-paddle placement**: sternal paddle placed in its zone | R8, R3 | Required |
| `paddles_firmly_on_chest` | Both paddles stable in the approved zones | R3 | Required |
| `both_paddle_buttons_pressed` | Both discharge buttons pressed | R4 | Required |
| `shock_delivered_on_screen` | New shock indication on the approved screen (exactly one per recording expected) | R5, R3/R4 inference, shock time | Required |
| `paddles_removed_after_shock` | Paddles removed from the chest | R6, R3/R4 inference, shock-time fallback | Required |
| `apical_paddle_taken`, `sternal_paddle_taken` *(proposed names)* | **Per-paddle taken**: which paddle was taken | Future checks on R2/R8 | If feasible |

### Zone visibility

**Zone visibility** is required for R8. In some camera angles only one placement zone is
visible, and R8 then uses its one-zone inference. The rule engine must know which zones were
visible, and when.

| Canonical name *(proposed)* | Meaning |
|---|---|
| `apical_zone_visible` | Interval during which the apical placement zone is visible |
| `sternal_zone_visible` | Interval during which the sternal placement zone is visible |

- **No event for a zone** means the zone was not visible.
- **No zone information at all** means visibility is unknown, and R8 then reports Unable to
  Verify.

The format is a proposal to agree; it fits the current `Event` schema without changes.

Raw `object_visible:<class>` events are not used as rule evidence.

## From audio command detection (Sanjeevan)

Command names follow the A1–A6 wording in the supervisor's proposal. **All names and phrases are
provisional** until the medical-faculty supervisor confirms them.

| Canonical name | Command | Rule |
|---|---|---|
| `oxygen_away_command` | Free-flow oxygen away | A1 |
| `continue_compressions_command` | Continue chest compressions (before the shock) | A2 |
| `stand_clear_command` | All stand clear | A3 |
| `stop_compressions_command` | Stop chest compressions / hands off | A4, A8 |
| `shock_command` | DC shock / discharge | A5 |
| `start_compressions_command` | Start or resume chest compressions (after the shock) | R7/A6, A8 |

- **Unambiguous commands:** emit the action-specific name, one event per detected command.
- **Ambiguous phrases:** some phrases (for example "continue CPR") mean continue before the
  shock and restart after it. Audio detection cannot know the shock time, so these may keep the
  current label `resume_compressions_command`. The rule engine resolves it by position relative
  to the shock.
- **Current state:** `configs/pipeline.yaml` emits only `oxygen_away_command`,
  `stand_clear_command` and `resume_compressions_command`. Stop and shock are missing.
- **Audio coverage (nice to have; format to agree):** marking where audio was missing or
  unclear lets the rule engine say Unable to Verify instead of guessing. Without it, audio
  coverage is `unknown`.

## Open items to agree

1. **Per-paddle placement:** how video postprocessing will produce `apical_paddle_placed` and
   `sternal_paddle_placed`. CVAT has no per-paddle placement tags today.
2. **Zone visibility:** the format, and for annotation timelines, where it comes from
   (`events.jsonl` has no zone tracks).
3. **Per-paddle taken events:** whether they are feasible, and their final names.
4. **Command names:** the audio stop/shock commands and the final names after supervisor
   confirmation.
5. **Audio coverage:** the signal format.
6. **Confidence thresholds:** which side applies them (upstream, the rule engine, or both with
   the same values), so they are not applied twice with different values.
7. **Timeline header:** whether upstream can provide `recording_id`, `camera_angle`,
   `duration_seconds` and `analyses_run`, and in what format.
