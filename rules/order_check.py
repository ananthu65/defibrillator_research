"""The order check shared by A7 and S1 (plan section 4; D-123, D-125, D-128).

Given a rule's own "X before Y" relations and the observed occurrences of each step, find the minimum set of
misplaced steps: the fewest observed steps whose removal leaves the rest consistent. Any occurrence in the right
place counts; "X before Y" holds unless X is certainly after Y (checks.relation_between: segments compared as
intervals, a tie within the window satisfies either order). Steps seen only through low-confidence or unresolved
commands are free extra occurrences: they can only remove a misplacement, never cause one.
"""
from itertools import combinations

from rules import checks

MAX_STEPS = 16


class Solution:
    """The minimum solutions: misplaced = steps in every one; between = steps in some but not all (one mistake
    between them); chosen = the occurrences kept by the first solution."""

    def __init__(self, misplaced, between, chosen):
        self.misplaced, self.between, self.chosen = misplaced, between, chosen

    @property
    def all_dropped(self):
        return list(self.misplaced) + list(self.between)


def minimum_misplaced(ctx, ids, relations, real, unsure, rule_id):
    """Kept sets tried from the largest down (deterministic). Dropping a step observed for real costs 1; a step
    seen only through low-confidence or unresolved events drops for free. `ids` is in the procedure's step order,
    a topological order of the relations."""
    steps = [s for s in ids if real[s] or unsure.get(s)]
    if len(steps) > MAX_STEPS:
        raise ValueError(f"{rule_id}: {len(steps)} steps observed; the order search handles at most {MAX_STEPS}")
    free = sum(1 for s in steps if not real[s])
    occurrences = {s: sorted(real[s] + unsure.get(s, []), key=lambda e: (e.start, e.end)) for s in steps}
    preds = {s: [p for p, q in relations if q == s] for s in steps}
    best, solutions = None, []
    for size in range(len(steps), -1, -1):
        if best is not None and len(steps) - size - free > best:
            break   # every smaller kept set drops more observed steps than the best found
        for kept in combinations(steps, size):
            dropped = frozenset(s for s in steps if s not in kept and real[s])
            if best is not None and len(dropped) > best:
                continue
            chosen = place(ctx, kept, occurrences, preds)
            if chosen is None:
                continue
            if best is None or len(dropped) < best:
                best, solutions = len(dropped), [(dropped, chosen)]
            elif dropped not in [d for d, _ in solutions]:
                solutions.append((dropped, chosen))
    every = frozenset.intersection(*[d for d, _ in solutions])
    some = frozenset.union(*[d for d, _ in solutions]) - every
    return Solution([s for s in ids if s in every], [s for s in ids if s in some], solutions[0][1])


def place(ctx, kept, occurrences, preds):
    """A topological sweep: each kept step's earliest occurrence not certainly before any kept predecessor.
    Earliest is optimal: the constraints only push later steps later."""
    chosen = {}
    for step in kept:   # kept follows the procedure's step order, a topological order
        before = [chosen[p] for p in preds[step] if p in chosen]
        fits = [o for o in occurrences[step] if all(checks.relation_between(ctx, o, b) != checks.BEFORE for b in before)]
        if not fits:
            return None
        chosen[step] = fits[0]
    return chosen


def possibly(ctx, event_name):
    """Ambiguous commands left unresolved (P-011: near the shock, or no shock time) that could have been
    event_name. Their stage is unknown, so they are neither evidence nor absence (D-010, D-125)."""
    unresolved = {r.event_id for r in ctx.resolutions if r.resolved_to is None}
    return [e for e in ctx.events if e.event_id in unresolved
            and event_name in (ctx.config.vocabulary.resolution(e.source, e.event_name) or ())]


def unseen_occurrences(ctx, step):
    """Occurrences that could be this step but can't be used: low confidence, or unresolved (P-011)."""
    vocabulary = ctx.config.vocabulary
    low = [e for e in ctx.prepared.excluded if e.event_name in step.events
           or set(vocabulary.resolution(e.source, e.event_name) or ()) & set(step.events)]
    return low + [e for name in step.events for e in possibly(ctx, name)]


def same_segment_pairs(chosen, relations):
    return [(a, b) for a, b in relations if a in chosen and b in chosen and checks.same_segment(chosen[a], chosen[b])]


def listing(chosen):
    return ", ".join(f"{s} at {e.start:g} s" for s, e in chosen.items())


def describe(misplaced, between, real):
    parts = [f"{s} ({real[s][0].event_name} at {real[s][0].start:g} s) is out of order" for s in misplaced]
    if between:
        names = " and ".join(f"{s} ({real[s][0].event_name} at {real[s][0].start:g} s)" for s in between)
        parts.append(f"{names} are in the wrong order (one mistake)")
    return "; ".join(parts)


def evidence(steps, real, ids):
    return tuple(real[s][0].event_id for s in sorted(steps, key=ids.index))


def times(steps, real):
    return {s: real[s][0].start for s in steps}


def correct_window(step, relations, real, required, end):
    """D-128: where a correctly placed occurrence of `step` would have had to be: after the earliest occurrence of
    each observed required predecessor and before the latest occurrence of each observed required successor (any
    occurrence counts); the recording start, or `end`, where none."""
    preds = [p for p, q in relations if q == step and required(p)]
    succs = [q for p, q in relations if p == step and required(q)]
    start = max((checks.time_bounds(real[p][0])[0] for p in preds), default=0.0)
    stop = min((checks.time_bounds(real[q][-1])[1] for q in succs), default=end if end is not None else start)
    return (min(start, stop), max(start, stop))
