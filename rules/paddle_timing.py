"""The paddle-order facts, from times only (D-118). Dependency-free: imports nothing.

Used by the procedure context (``rules.context.paddle_order``, seconds, canonical events) and by
Step 9d (``annotation.derive_gel_applications.gel_phase``, frames, CVAT labels). Each caller maps its
own labels to the two paddles; under the team's working definition (A-027) ``first_paddle_*`` is the
apical paddle and ``second_paddle_*`` the sternal one, so the names give identity, never time order.
"""
from dataclasses import dataclass

APICAL, STERNAL = "apical", "sternal"
PADDLES = (APICAL, STERNAL)   # the order only breaks exact ties (apical)


def other(paddle):
    return STERNAL if paddle == APICAL else APICAL


@dataclass(frozen=True)
class PaddleTiming:
    """first_taken: the paddle taken first, or None when that can't be established.
    take_deduced: first_taken was deduced from its placement (its take is missing).
    earliest_taken / earliest_placed: the paddle with the earliest take / known firm placement, or None.
    earliest_certain: False when the other paddle's placement is unknown and could have been earlier.
    unknown_from: when not certain, the earliest time that unknown placement could be (its take, else 0).
    """
    first_taken: str | None
    take_deduced: bool
    earliest_taken: str | None
    earliest_placed: str | None
    earliest_certain: bool
    unknown_from: float | None


def _earliest(times):
    known = [p for p in PADDLES if times[p] is not None]
    return min(known, key=lambda p: times[p]) if known else None   # an exact tie counts as apical


def paddle_timing(taken, placed, window):
    """taken, placed: {"apical": time or None, "sternal": time or None}, in one unit (seconds or frames);
    window (same unit): a paddle placed more than this before the other was taken was taken first."""
    first, deduced = None, False
    missing = [p for p in PADDLES if taken[p] is None]
    if not missing:   # an exact tie counts as apical
        first = STERNAL if taken[STERNAL] < taken[APICAL] else APICAL
    elif len(missing) == 1:   # a paddle placed before the other was taken must have been taken first
        gap = missing[0]
        if placed[gap] is not None and placed[gap] < taken[other(gap)] - window:
            first, deduced = gap, True
    earliest = _earliest(placed)
    certain, unknown_from = True, None
    if earliest is not None and placed[other(earliest)] is None:
        other_taken = taken[other(earliest)]
        if other_taken is None or other_taken < placed[earliest]:   # it may have been placed earlier
            certain, unknown_from = False, (other_taken if other_taken is not None else 0)
    return PaddleTiming(first, deduced, _earliest(taken), earliest, certain, unknown_from)
