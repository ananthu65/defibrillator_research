# Rule Engine Design Document

## Project

AI-based Defibrillation Assessment Pipeline

---

# 1. Objective

The purpose of the assessment pipeline is to automatically evaluate a student's defibrillation procedure using events detected by separate Audio Analysis and Video Analysis modules.

This module **does not perform speech recognition or object detection**.

Instead, it receives detected events and evaluates whether the student performed the procedure correctly according to the assessment rubric.

---

# 2. Overall Pipeline

```
               Audio Recording
                      │
                      ▼
            Audio Analysis Engine
                      │
             Audio Event Timeline
                      │

               Video Recording
                      │
                      ▼
            Video Analysis Engine
                      │
             Video Event Timeline

                      │
                      ▼
             Timeline Fusion Engine
                      │
                      ▼
            Clinical Logic Engine
                      │
                      ▼
            Rule Evaluation Engine
                      │
                      ▼
          Scoring & Feedback Engine
```

---

# 3. Responsibilities of Each Engine

## 3.1 Audio Analysis Engine

Responsibility:

- Detect spoken commands.
- Convert spoken commands into structured events.

Output example:

```python
[
    Event(
        event_name="all_stand_clear",
        timestamp=12.1,
        source="audio",
        confidence=0.96
    )
]
```

This engine is outside the scope of this module.

---

## 3.2 Video Analysis Engine

Responsibility:

- Detect physical actions.
- Convert actions into structured events.

Output example:

```python
[
    Event(
        event_name="shock_delivered",
        timestamp=13.8,
        source="video",
        confidence=0.94
    )
]
```

This engine is outside the scope of this module.

---

## 3.3 Timeline Fusion Engine

Input

- Audio events
- Video events

Responsibilities

- Merge both event lists.
- Sort events by timestamp.
- Produce one unified chronological timeline.

Output

```text
2.4 oxygen_away

4.8 continue_chest_compressions

7.3 pads_applied

11.5 all_stand_clear

13.8 shock_delivered
```

Version 1 intentionally performs **no clinical reasoning**.

---

## 3.4 Clinical Logic Engine

Purpose

Interpret the chronological timeline.

Version 1 Responsibilities

- Receive the sorted timeline.
- Return the same timeline unchanged.

Future Versions

This engine may infer additional clinical events.

Example:

```
pads_applied
+
all_stand_clear
+
shock_delivered

↓

patient_shocked
```

or

```
shock_delivered

↓

pads_must_have_been_placed
```

Clinical inference is intentionally postponed until the assessment rules are finalized.

---

## 3.5 Rule Evaluation Engine

Purpose

Evaluate whether the assessment criteria are satisfied.

The Rule Evaluation Engine performs three sequential checks.

### Step 1

Presence Check

Questions:

- Is the required event present?

Example

```
oxygen_away

Present?

YES
```

---

### Step 2

Order Check

Questions

Was the event performed in the correct order?

Example

Expected

```
oxygen_away

↓

continue_chest_compressions

↓

all_stand_clear
```

Observed

```
continue_chest_compressions

↓

oxygen_away
```

Result

FAIL

---

### Step 3

Rule Classification

Each criterion is assigned a result.

Current Version

- PASS
- FAIL

Future versions may include

- PARTIAL
- CRITICAL ERROR

---

## 3.6 Scoring & Feedback Engine

Responsibilities

- Collect the results from the Rule Evaluation Engine.
- Determine the overall assessment outcome.
- Generate feedback for the student.

### Overall Assessment

The assessment follows a binary outcome.

```
If every required criterion passes

↓

Overall Result

CORRECTLY DONE
```

```
If one or more required criteria fail

↓

Overall Result

WRONGLY DONE
```

This follows the current assessment policy, where a single mistake is sufficient for the overall procedure to be considered incorrect.

### Individual Rule Results

Although the final assessment is binary, each rule is still evaluated individually.

Example

```
A1    PASS

A2    PASS

A3    FAIL

R1    PASS

R2    PASS
```

These individual results are **not converted into partial scores**. Instead, they are used to identify where the student made mistakes and to generate meaningful feedback.

### Feedback Generation

Feedback is generated from the failed rules and the observed event sequence.

Examples

```
The student instructed "All Stand Clear" before removing free-flow oxygen.
```

```
Chest compressions were resumed before the shock sequence was completed.
```

```
The "All Stand Clear" command was not detected before shock delivery.
```

The goal of the feedback engine is to explain **why** the overall result was classified as **WRONGLY DONE**, allowing the student to understand and correct the specific mistakes.
---

# 4. Event Structure

Every engine communicates using Event objects.

Minimum Event Fields

| Field | Description |
|--------|-------------|
| event_name | Name of the detected event |
| timestamp | Time of occurrence |
| source | audio or video |
| confidence | Detection confidence |

Example

```python
Event(
    event_name="shock_delivered",
    timestamp=13.8,
    source="video",
    confidence=0.95
)
```

---

# 5. Version 1 Assumptions

To keep the first implementation simple, the following assumptions are made.

- Audio events are already detected.
- Video events are already detected.
- Event timestamps are correct.
- Event confidence values are available.
- Timing constraints are NOT evaluated.
- Confidence thresholds are NOT evaluated.
- Clinical inference is NOT performed.
- The assessment is based only on event presence and event order.

---

# 6. Initial Assessment Flow
# 6. Initial Assessment Flow

The assessment engine monitors the expected procedure sequence.

```
A1
↓
A2
↓
A3
↓
A4
↓
R1
↓
R2
↓
R3
↓
R4
↓
R5
↓
R6
↓
A6
```

For each criterion, the engine evaluates:

1. Is the required event present?
2. Is the event in the expected order?
3. Are all prerequisite events satisfied?

If all required criteria pass, the procedure is classified as **CORRECTLY DONE**.

If any required criterion fails, the procedure is classified as **WRONGLY DONE**.

Certain rules may depend on previous rules.

Example

```
R5

requires

R3
and
R4
```

These dependencies will be represented explicitly in the rule definitions rather than hardcoded into the evaluation engine.

---

# 7. Future Enhancements

The architecture is intentionally modular.

Future versions may include

- Timing validation
- Confidence threshold filtering
- Clinical event inference
- Alternative acceptable event sequences
- Multiple acceptable verbal commands
- Automatic weighting of critical errors
- Rich feedback generation
- Statistical performance reports

These features can be added without changing the overall pipeline architecture.