# Event Schema
# Version 2 Specification

## Overview

The Event Schema defines the standard structure used throughout the assessment pipeline.

Both the Video Engine and Audio Engine generate events using this schema.

The Timeline Fusion Engine merges these events without modifying their meaning.

The Rule Evaluation Engine consumes these events to perform assessment.

Every event must follow the same structure.

---

# Event Structure

Each event contains:

```python
Event(
    event_name: str,
    timestamp: float,
    source: EventSource,
    confidence: float,
    evidence_type: EvidenceType,
    inferred_from: Optional[str],
    raw_data: dict
)
```

---

# Field Definitions

## event_name

Unique identifier describing the detected action.

Example

```text
gel_applied
```

---

## timestamp

Time (seconds) from the beginning of the recording.

Example

```text
12.54
```

---

## source

Origin of the event.

Possible values

- VIDEO
- AUDIO

---

## confidence

Detection confidence returned by the AI model.

Range

```text
0.0 – 1.0
```

The Rule Engine may use confidence when determining assessment outcomes.

---

## evidence_type

Specifies whether evidence was directly observed or inferred.

Possible values

- DIRECT
- INFERRED

---

## inferred_from

Records the inference rule or supporting events when evidence is inferred.

Direct observations should use:

```text
None
```

---

## raw_data

Stores optional detector-specific information.

Examples

- Bounding boxes
- Whisper transcript
- Detection scores
- Model metadata

The Rule Engine does not rely on this field for assessment.

---

# Video Events

Current Version 2 video events include:

| Event | Description |
|--------|-------------|
| gel_applied | Gel applied before defibrillation |
| take_first_paddle | First paddle picked up |
| take_second_paddle | Second paddle picked up |
| place_paddles | Paddles placed correctly |
| shock_button_pressed | Both discharge buttons pressed |
| shock_delivered | Shock delivered |
| remove_paddles | Paddles removed after shock |

---

# Audio Events

Current Version 2 audio events include:

| Event | Description |
|--------|-------------|
| oxygen_away | Oxygen moved away |
| continue_chest_compressions | Continue CPR command |
| all_stand_clear | Stand clear command |
| stop_chest_compressions | Stop CPR command |
| dc_shock_command | Deliver shock command |
| start_chest_compressions | Resume CPR command |

---

# Event Lifecycle

Every event follows the same lifecycle.

```
Detection
      │
      ▼

Event Creation
      │
      ▼

Timeline Fusion
      │
      ▼

Rule Evaluation
      │
      ▼

Feedback Generation
```

---

# Design Principles

All events should:

- represent a single observation
- contain one timestamp
- originate from one source
- remain immutable after creation
- support deterministic assessment

Assessment decisions are never made during event generation.

The event schema serves as the shared communication interface between every module in the assessment pipeline.
