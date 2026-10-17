"""Video rules (Increment 11 onward). Each rule is one small function built from the shared checks.

Registered rules run only when their status in configs/rules.yaml is `approved`; until then they
are reported as pending (D-043). Definitions and failure codes: docs/rule_engine/rules_status.md.
"""
from rules import checks
from rules.coverage import COVERED, LOW_CONFIDENCE_FLAG
from rules.outcome import assumed, failed, passed, unable
from rules.registry import rule

FIRST_TAKEN, FIRST_PLACED, SECOND_TAKEN = "first_paddle_taken", "first_paddle_placed", "second_paddle_taken"
BOTH_PLACED = "paddles_firmly_on_chest"
APICAL, STERNAL = "apical_paddle_placed", "sternal_paddle_placed"
PLACEMENTS = (APICAL, STERNAL)

# Rule-result flags raised here (listed in docs/rule_engine/anomalies.md and output_contract.md)
DERIVED = "derived_placement"              # the result rests on a placement derived from the boxes (D-081, D-088)
PARALLEL = "possible_parallel_placement"   # cause flag: one parallel placement fails R2 and R8 (D-091, D-098)
PLACEMENT_MISSING = "placement_missing"    # R8: a placement is missing while its zone was in view (D-058)
CONTRADICTORY = "contradictory"            # R8: the visible paddle placed clearly before the first placement
INFERRED_UNDECIDED = "inferred_fail_policy_undecided"   # R8: an inferred mistake while D-015 is undecided
FLAGS = (DERIVED, PARALLEL, PLACEMENT_MISSING, CONTRADICTORY, INFERRED_UNDECIDED)


def _evidence_flags(events):
    """Flags carried by the placement events a result rests on: derived, and the parallel cause flag."""
    flags = []
    for event in events:
        if event.metadata.get("derived_placement"):
            flags.append(DERIVED)
        if PARALLEL in event.metadata.get("flags", ()):
            flags.append(PARALLEL)
    return tuple(dict.fromkeys(flags))


def _parallel(ctx, rule_id):
    """D-091, D-098: derived placements flagged possible_parallel_placement (present only past the gate)."""
    events = [e for name in PLACEMENTS for e in ctx.named(name) if PARALLEL in e.metadata.get("flags", ())]
    if not events:
        return None
    return failed(rule_id, "simultaneous", "both paddles were placed at the same time (derived placements flagged "
                  "possible_parallel_placement, D-091); one parallel placement fails R2 and R8 (D-098)",
                  evidence=tuple(e.event_id for e in events), flags=_evidence_flags(events),
                  timestamps={e.event_name: e.start for e in events})


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
    parallel = _parallel(ctx, "R2")
    if parallel is not None:
        return parallel
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


# ---- R8 ---------------------------------------------------------------------------------------------

@rule("R8", requires=(APICAL, STERNAL, FIRST_PLACED, FIRST_TAKEN, SECOND_TAKEN, BOTH_PLACED),
      description="Apical paddle placed before the sternal paddle (D-013)")
def apical_before_sternal(ctx, definition, results):
    """R8 (P-015): which paddle was placed first, following diagram (f).

    1. Possible parallel placement (past the gate) -> Fail `simultaneous`, cause flag (D-091, D-098).
    2. Both placements observed -> direct comparison: apical first -> Pass; same time -> `simultaneous`;
       sternal first -> `wrong_order`.
    3. A zone counts as visible when it is covered over the placement phase (D-092, D-099). A paddle
       whose zone was visible but whose placement is missing -> Unable to Verify, `placement_missing`
       (D-058).
    4. One placement observed, the other zone not visible -> the one-zone inference against the first
       placement (D-013): the same time -> that paddle was first; clearly later -> the other was first;
       clearly earlier -> Unable to Verify, `contradictory`. Apical first -> Pass - Inferred; sternal
       first -> the inferred_fail_outcome setting (undecided: Unable to Verify, D-015).
    5. Not determinable (no placement and no zone visible, or no first placement) -> Unable to
       Verify, or "assumed apical first" when assume_first_taken_is_apical is on (D-014, D-060).
    """
    parallel = _parallel(ctx, "R8")
    if parallel is not None:
        return parallel
    apical, sternal = ctx.anchor("apical_placement"), ctx.anchor("sternal_placement")
    if apical.present and sternal.present:
        return _direct(ctx, apical, sternal)
    window = _placement_phase(ctx)
    visible = {name: ctx.coverage.status(name, window).status == COVERED for name in PLACEMENTS}
    anchors = {APICAL: apical, STERNAL: sternal}
    seen = [name for name in PLACEMENTS if anchors[name].present]
    for name in PLACEMENTS:
        if not anchors[name].present and visible[name]:   # D-058: in view, yet no placement
            found = ctx.missing(name, window)
            if LOW_CONFIDENCE_FLAG in found.flags:
                return unable("R8", f"{_paddle(name)} placement may have been seen with low confidence",
                              evidence=found.low_confidence_event_ids, uses=(found,))
            return unable("R8", f"the {_paddle(name)} zone was in view during the placement phase, but no "
                          f"{_paddle(name)} placement was observed, so the order cannot be established (R3 reports "
                          "the missing placement, D-058)", flags=(PLACEMENT_MISSING,),
                          evidence=tuple(anchors[n].event_id for n in seen), uses=tuple(anchors[n] for n in seen))
    first = ctx.anchor("first_placement")
    if len(seen) == 1 and first.present:
        return _one_zone(ctx, seen[0], anchors[seen[0]], first)
    return _not_determinable(ctx, first)


def _paddle(name):
    return name.split("_")[0]


def _placement_phase(ctx):
    """(start, end) of the placement phase in seconds, or None (whole recording) (D-099).

    From the first paddle taken (else the earliest placement) to paddles firmly on chest (else the
    second paddle taken, else the latest placement).
    """
    def first_time(name):
        events = ctx.named(name)
        return events[0].start if events else None
    placements = [a.time for a in (ctx.anchor("first_placement"), ctx.anchor("apical_placement"),
                                   ctx.anchor("sternal_placement")) if a.present]
    start = first_time(FIRST_TAKEN)
    start = start if start is not None else (min(placements) if placements else None)
    end = first_time(BOTH_PLACED)
    end = end if end is not None else first_time(SECOND_TAKEN)
    end = end if end is not None else (max(placements) if placements else None)
    if start is None or end is None or end < start:
        return None
    return (start, end)


def _direct(ctx, apical, sternal):
    events = [e for e in ctx.events if e.event_id in (apical.event_id, sternal.event_id)]
    flags = _evidence_flags(events)
    evidence = (apical.event_id, sternal.event_id)
    timestamps = {APICAL: apical.time, STERNAL: sternal.time}
    relation = checks.relation(apical.time, sternal.time, checks.simultaneous_window(ctx))
    if relation == checks.BEFORE:
        return passed("R8", f"apical paddle placed at {apical.time:g} s, before the sternal at {sternal.time:g} s",
                      evidence, uses=(apical, sternal), flags=flags, timestamps=timestamps)
    if relation == checks.SIMULTANEOUS:
        return failed("R8", "simultaneous", f"apical ({apical.time:g} s) and sternal ({sternal.time:g} s) paddles "
                      "placed at the same time", evidence=evidence, uses=(apical, sternal), flags=flags,
                      timestamps=timestamps)
    return failed("R8", "wrong_order", f"sternal paddle placed at {sternal.time:g} s, before the apical at "
                  f"{apical.time:g} s", evidence=evidence, uses=(apical, sternal), flags=flags, timestamps=timestamps)


def _one_zone(ctx, name, seen, first):
    """D-013: the visible paddle's placement against the first placement (placement_match_window_seconds)."""
    events = [e for e in ctx.events if e.event_id == seen.event_id]
    flags = _evidence_flags(events)
    window = ctx.config.engine.value("placement_match_window_seconds")
    relation = checks.relation(seen.time, first.time, window)
    evidence = (seen.event_id, first.event_id)
    timestamps = {name: seen.time, FIRST_PLACED: first.time}
    other = STERNAL if name == APICAL else APICAL
    if relation == checks.BEFORE:
        return unable("R8", f"the {_paddle(name)} paddle was placed at {seen.time:g} s, clearly before the first "
                      f"placement ({first.time:g} s): the evidence contradicts itself", evidence=evidence,
                      flags=(CONTRADICTORY, *flags), uses=(seen, first), timestamps=timestamps)
    first_paddle = name if relation == checks.SIMULTANEOUS else other
    how = (f"the {_paddle(name)} paddle (the only zone in view) was placed at the first placement time"
           if first_paddle == name else
           f"the {_paddle(name)} paddle (the only zone in view) was placed at {seen.time:g} s, clearly after the first "
           f"placement ({first.time:g} s), so the {_paddle(other)} paddle was first")
    if first_paddle == APICAL:
        return passed("R8", f"apical paddle first (inferred): {how}", evidence, inferred=True, uses=(seen, first),
                      flags=flags, timestamps=timestamps)
    setting = ctx.config.engine.settings["inferred_fail_outcome"]
    if setting.undecided:
        return unable("R8", f"sternal paddle first (inferred): {how}; whether an inferred mistake is a Fail is "
                      "undecided (D-015)", evidence=evidence, flags=(INFERRED_UNDECIDED, *flags), uses=(seen, first),
                      timestamps=timestamps)
    if setting.value == "fail":
        return failed("R8", "wrong_order", f"sternal paddle first (inferred): {how}", evidence=evidence,
                      uses=(seen, first), flags=flags, timestamps=timestamps)
    return unable("R8", f"sternal paddle first (inferred): {how}; inferred mistakes are not failed (D-015)",
                  evidence=evidence, uses=(seen, first), flags=flags, timestamps=timestamps)


def _not_determinable(ctx, first):
    why = ("no placement could be observed and no placement zone was in view" if first.present
           else "no first placement time")
    if ctx.config.engine.value("assume_first_taken_is_apical"):
        taken = ctx.named(FIRST_TAKEN)
        return assumed("R8", f"assumed apical first (the first paddle taken is taken to be apical): {why}; "
                       "to be checked by the evaluator (D-014, D-060)",
                       evidence=(taken[0].event_id,) if taken else ())
    return unable("R8", f"the order cannot be established: {why}", uses=(first,))
