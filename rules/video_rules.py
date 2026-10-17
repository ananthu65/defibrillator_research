"""Video rules (Increment 11 onward). Each rule is one small function built from the shared checks.

Registered rules run only when their status in configs/rules.yaml is `approved`; until then they
are reported as pending (D-043). Definitions and failure codes: docs/rule_engine/rules_status.md.
"""
from rules import checks
from rules.coverage import COVERED, LOW_CONFIDENCE_FLAG
from rules.outcome import failed, passed, unable
from rules.registry import rule

FIRST_TAKEN, FIRST_PLACED, SECOND_TAKEN = "first_paddle_taken", "first_paddle_placed", "second_paddle_taken"
PLACEMENTS = ("apical_paddle_placed", "sternal_paddle_placed")
PARALLEL = "possible_parallel_placement"   # set by the exporter on derived placements (D-086)


@rule("R2", requires=(FIRST_TAKEN, FIRST_PLACED, SECOND_TAKEN, *PLACEMENTS),
      description="Second paddle taken only after the first is placed (D-051)")
def second_paddle_after_first_placed(ctx, definition, results):
    """R2 (P-032): first paddle taken -> first paddle placed firmly -> second paddle taken.

    1. Derived placements flagged possible_parallel_placement (they reach the engine only past the
       gate, D-088) -> Fail `simultaneous` (D-091).
    2. No second paddle taken -> Unable to Verify: the order can't be checked.
    3. First placement seen -> compare it with the second paddle taken: before -> Pass;
       within simultaneous_window_seconds -> Fail `simultaneous`; after -> Fail
       `taken_before_first_placed`.
    4. First placement not seen -> coverage of both placement zones over the window from first
       paddle taken to second paddle taken (D-092, D-095): both visible throughout -> Fail
       `first_placement_not_observed` (D-097): either the paddles were placed in parallel, or the
       second paddle was taken before the first was placed (A-019); otherwise Unable to Verify.
       Past the gate, derived parallel placements refine this to `simultaneous` (step 1).
    """
    parallel = [e for name in PLACEMENTS for e in ctx.named(name) if PARALLEL in e.metadata.get("flags", ())]
    if parallel:
        return failed("R2", "simultaneous", "both paddles were placed at the same time (derived placements flagged "
                      "possible_parallel_placement, D-091)", evidence=tuple(e.event_id for e in parallel),
                      timestamps={e.event_name: e.start for e in parallel})
    seconds = ctx.named(SECOND_TAKEN)
    if not seconds:
        found = ctx.missing(SECOND_TAKEN)
        return unable("R2", f"no confident {SECOND_TAKEN}, so the order cannot be checked (coverage "
                      f"{found.coverage.status})", evidence=found.low_confidence_event_ids, uses=(found,))
    second = seconds[0]
    placed = ctx.anchor("first_placement")
    if placed.present:
        return _order(ctx, placed, second)
    return _first_placement_missing(ctx, second)


def _order(ctx, placed, second):
    relation = checks.relation(placed.time, second.start, checks.simultaneous_window(ctx))
    evidence = (placed.event_id, second.event_id)
    timestamps = {FIRST_PLACED: placed.time, SECOND_TAKEN: second.start}
    if relation == checks.BEFORE:
        return passed("R2", f"first paddle placed at {placed.time:g} s, before the second paddle was taken at "
                      f"{second.start:g} s", evidence, uses=(placed,), timestamps=timestamps)
    if relation == checks.SIMULTANEOUS:
        return failed("R2", "simultaneous", f"second paddle taken at {second.start:g} s, at the same time as the "
                      f"first was placed ({placed.time:g} s)", evidence=evidence, uses=(placed,), timestamps=timestamps)
    return failed("R2", "taken_before_first_placed", f"second paddle taken at {second.start:g} s, before the first "
                  f"was placed at {placed.time:g} s", evidence=evidence, uses=(placed,), timestamps=timestamps)


def _first_placement_missing(ctx, second):
    weak = ctx.missing(FIRST_PLACED)
    if LOW_CONFIDENCE_FLAG in weak.flags:   # low confidence is not absence (D-010)
        return unable("R2", "the first placement may have been seen with low confidence",
                      evidence=weak.low_confidence_event_ids, uses=(weak,))
    taken = ctx.named(FIRST_TAKEN)
    if not taken or taken[0].start > second.start:
        return unable("R2", f"first placement not seen, and no {FIRST_TAKEN} before the second paddle was taken, "
                      "so there is no window in which it should have happened", evidence=(second.event_id,))
    window = (taken[0].start, second.start)
    zones = [ctx.missing(name, window) for name in PLACEMENTS]
    statuses = ", ".join(f"{z.event_name.split('_')[0]} zone {z.coverage.status}" for z in zones)
    where = f"between taking the first paddle ({window[0]:g} s) and the second ({window[1]:g} s)"
    if all(z.coverage.status == COVERED and z.outcome == "fail" for z in zones):
        return failed("R2", "first_placement_not_observed", f"no first placement observed {where}, although both "
                      "placement zones were visible throughout: either the paddles were placed in parallel, or the "
                      "second paddle was taken before the first was placed (A-019, D-097)",
                      evidence=(taken[0].event_id, second.event_id), uses=tuple(zones),
                      timestamps={FIRST_TAKEN: window[0], SECOND_TAKEN: window[1]})
    return unable("R2", f"first placement not seen {where}, but the placement zones were not visible throughout "
                  f"({statuses})", evidence=(taken[0].event_id, second.event_id), uses=tuple(zones))
