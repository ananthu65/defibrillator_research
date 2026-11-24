"""Procedure-level rules (Increment 27): S1, the order of the whole procedure (D-120, D-123, D-126, D-128).

S1 reads events, not rule results (D-123). Its relations come from configs/rule_engine/procedure_order.yaml (the
interim order, NOT clinically approved, OQ-062) and are derived per recording from the observed steps (OQ-078).
"""
from rules import checks, order_check
from rules.coverage import COVERED
from rules.outcome import failed, passed, unable
from rules.registry import rule

ZONES = ("apical_zone", "sternal_zone")
PADDLES = ("apical_paddle", "sternal_paddle")
# Events governed by no region: where each could have been seen (D-108, A-026; both zones for a placement-like
# event, since it could be in either). Events with a region (the zones, the screen, the audio) use it directly.
REGION_LESS = {"first_paddle_taken": PADDLES, "second_paddle_taken": PADDLES, "both_paddle_buttons_pressed": PADDLES,
               "first_paddle_placed": ZONES, "paddles_firmly_on_chest": ZONES, "paddles_removed_after_shock": ZONES,
               "gel_applied": ZONES, "apical_gel_applied": ("apical_zone",), "sternal_gel_applied": ("sternal_zone",)}
ORDER_EVENTS = ("oxygen_away_command", "stand_clear_command", "continue_compressions_command", "charging_command",
                "gel_applied", "apical_gel_applied", "sternal_gel_applied", "gel_announcement_command",
                "stop_compressions_command", "first_paddle_taken", "second_paddle_taken", "first_paddle_placed",
                "apical_paddle_placed", "sternal_paddle_placed", "paddles_firmly_on_chest", "shock_command",
                "both_paddle_buttons_pressed", "shock_delivered_on_screen", "paddles_removed_after_shock",
                "start_compressions_command")


@rule("S1", requires=ORDER_EVENTS, description="The whole procedure in the expected order")
def procedure_order(ctx, definition, results):
    """S1 (P-046): the order of the observed steps, on the relations no other rule owns.

    - **Relations, per recording (D-126 option B, OQ-078):** the transitive reduction of the order restricted
      to the observed steps, minus every relation another rule owns (R1, R2, R3, R4, R6, A1-A5, R7, A7's audio
      scope). A relation that bridges a missing or unseen step is then S1's unless another rule owns it.
    - **Method (plan section 4):** the minimum set of misplaced steps; any occurrence in the right place counts;
      a tie within the window (simultaneous_window_seconds in one modality, cross_modal_tolerance_seconds across)
      is not ordered; the gel phase is interchangeable; optional steps are checked only if present; A5 against the
      shocking actions stays unordered (OQ-075). Equal solutions are one mistake naming the steps.
    - **One rule per mistake (D-119, D-123):** a misplaced step that also breaks, in every occurrence, a relation
      another rule owns (for example the gel after the placement, R1's) is that rule's to report; S1 leaves it
      out and names the rule.
    - **D-128:** a misplaced step fails only if the window where its correct occurrence would have been was clear
      (audio) or in view (video); otherwise Unable to Verify, `correct_occurrence_unseen`.
    - Unseen steps (not observed, and not clearly absent: unclear audio, a region out of view, low confidence, an
      unresolved command) flag `order_partially_checked`, never a clean Pass. Missing steps (clearly absent) are
      left out silently: their own rule reports them.
    - Fewer than two observed steps in S1's relations -> Unable to Verify.
    """
    order = ctx.config.procedure_order
    default = order.default_owner
    closure = {(r.before, r.after): r for r in order.relations}
    real = {s.id: _occurrences(ctx, s) for s in order.steps}
    observed = [s.id for s in order.steps if real[s.id]]
    reduction = [(a, b) for (a, b) in closure if a in observed and b in observed
                 and not any((a, c) in closure and (c, b) in closure for c in observed)]
    mine = [(a, b) for (a, b) in reduction if closure[(a, b)].owner in (default, None)]
    ids = [s for s in observed if any(s in pair for pair in mine)]
    whole = _whole(ctx)
    unseen = [s.id for s in order.steps if not real[s.id] and not s.optional
              and not _clearly_absent(ctx, s, whole)[0]]
    unsure = {s: order_check.unseen_occurrences(ctx, order.step(s)) for s in ids}
    partial = bool(unseen or any(unsure.values()))
    note = f"; not checked (unseen): {', '.join(unseen)}" if unseen else ""
    if len(ids) < 2:
        return unable("S1", f"fewer than two observed steps in S1's own relations ({', '.join(ids) or 'none'}; "
                      f"observed: {', '.join(observed) or 'none'}), so the procedure order can't be judged{note}")
    certain = order_check.minimum_misplaced(ctx, ids, mine, real, {}, "S1")
    explained = {s: _owned_elsewhere(ctx, s, closure, default, observed, real) for s in certain.all_dropped}
    misplaced = [s for s in certain.misplaced if explained[s] is None]
    between = certain.between if all(explained[s] is None for s in certain.between) else []
    handed = {s: owner for s, owner in explained.items() if owner is not None}
    elsewhere = ("; reported by their own rule: " + ", ".join(f"{s} ({o})" for s, o in handed.items())) if handed else ""
    if not misplaced and not between:
        same = order_check.same_segment_pairs(certain.chosen, mine)
        segment = ("; in one segment, so not ordered: " + ", ".join(f"{a} and {b}" for a, b in same)) if same else ""
        kept = {s: e for s, e in certain.chosen.items()}
        return passed("S1", f"the observed steps are in the expected order on S1's relations "
                      f"({', '.join(f'{a}->{b}' for a, b in mine)}){elsewhere}{segment}{note}",
                      tuple(e.event_id for e in kept.values()),
                      flags=(checks.ORDER_PARTIALLY_CHECKED,) if partial or same else (),
                      timestamps={s: e.start for s, e in kept.items()})
    reported = misplaced + list(between)
    mistake = order_check.describe(misplaced, between, real)
    possible = order_check.minimum_misplaced(ctx, ids, mine, real, unsure, "S1")
    if not set(reported) <= set(possible.all_dropped):   # some reported step could be rescued
        return unable("S1", f"{mistake}, but a low-confidence or unresolved event could be an occurrence in the right "
                      f"place{note}", evidence=order_check.evidence(reported, real, ids),
                      timestamps=order_check.times(reported, real), flags=(checks.ORDER_PARTIALLY_CHECKED,))
    required = lambda other: real[other] and not order.step(other).optional
    unclear = []
    for step in reported:
        window = order_check.correct_window(step, reduction, real, required, _recording_end(ctx))
        if not _clearly_absent(ctx, order.step(step), window)[0]:
            unclear.append((step, window))
    evidence, times = order_check.evidence(reported, real, ids), order_check.times(reported, real)
    if unclear:
        where = "; ".join(f"{step} from {w[0]:g} s to {w[1]:g} s" for step, w in unclear)
        return unable("S1", f"{mistake}, but a correctly placed occurrence may have been missed: not clearly observed "
                      f"where it would have been ({where}) (D-128){elsewhere}{note}", evidence=evidence,
                      timestamps={**times, "unseen_window_start": unclear[0][1][0], "unseen_window_end": unclear[0][1][1]},
                      flags=(checks.ORDER_PARTIALLY_CHECKED, checks.CORRECT_UNSEEN))
    return failed("S1", "wrong_order", f"{mistake}{elsewhere}{note}", evidence=evidence, timestamps=times,
                  flags=(checks.ORDER_PARTIALLY_CHECKED,) if partial else ())


def _occurrences(ctx, step):
    """A step's observed occurrences; a derived step comes from the paddle order (event times, D-118)."""
    order = ctx.paddle_order
    if step.derived == "earliest_take":
        return [order.earliest_taken] if order.earliest_taken is not None else []
    if step.derived == "later_take":
        takes = [e for e in order.taken.values() if e is not None]
        if len(takes) < 2 or order.earliest_taken is None:
            return []
        return [e for e in takes if e.event_id != order.earliest_taken.event_id][:1]
    if step.derived == "earliest_placement":
        return [order.earliest_placement] if order.earliest_placement is not None else []
    return [e for e in ctx.events if e.event_name in step.events]


def _clearly_absent(ctx, step, window):
    """(True, outcomes) when none of the step's events could have been missed over the window: its region in view
    (or the audio clear) throughout and no low-confidence detection (D-122, D-128)."""
    outcomes = []
    for name in step.events:
        regions = REGION_LESS.get(name)
        if regions:
            outcomes += [ctx.coverage.region_missing(region, name, window) for region in regions]
        else:
            outcomes.append(ctx.missing(name, window))
    return all(o.coverage.status == COVERED and o.outcome == "fail" for o in outcomes), outcomes


def _owned_elsewhere(ctx, step, closure, default, observed, real):
    """The rule that owns a relation this step breaks in every occurrence, against an observed step; else None.
    That rule reports the misplacement (one rule per mistake, D-119, D-123)."""
    for (a, b), relation in closure.items():
        if relation.owner in (default, None) or step not in (a, b):
            continue
        if (b if a == step else a) not in observed:
            continue
        if not any(checks.relation_between(ctx, x, y) != checks.AFTER for x in real[a] for y in real[b]):
            return relation.owner
    return None


def _recording_end(ctx):
    header = ctx.coverage.header
    ends = [e.end for e in ctx.prepared.events]
    return header.duration_seconds if header is not None and header.duration_seconds else (max(ends) if ends else None)


def _whole(ctx):
    end = _recording_end(ctx)
    return (0.0, end) if end else None
