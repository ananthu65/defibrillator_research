"""Audio rules (Increment 21 onward). Each rule is one small function built from the shared checks.

The input is Sanjeevan's command events (Whisper -> detect_commands, the shared Event schema, D-125);
nothing here imports audio/. A command event carries its Whisper segment, so it is compared as an
interval (checks.relation_between, D-125). A missing command can Fail only inside stated clear-audio
intervals (the audio region, D-122). Registered rules run only when approved in configs/rules.yaml.
"""
from itertools import combinations

from rules import checks
from rules.coverage import COVERED, LOW_CONFIDENCE_FLAG
from rules.outcome import failed, not_evaluable, passed, unable
from rules.registry import rule

SHOCK = "shock_delivered_on_screen"
OXYGEN_AWAY, STAND_CLEAR = "oxygen_away_command", "stand_clear_command"
FLAGS = ()   # rule-result flags raised here (the shared ones are in checks.FLAGS)


def _wrong_place(ctx, rule_id, code, event_name, window, reason, *, evidence, uses=(), timestamps=None):
    """D-128: a wrong-place Fail claims two things: the command was heard in a wrong place, AND it was not said
    in the right place. The second is an absence, so it needs the same evidence as `missing` over `window`, where
    a correctly placed occurrence would have had to be: stated clear audio (D-122) and no low-confidence command.
    Otherwise Unable to Verify: the correct occurrence may have been said but not heard."""
    found = ctx.missing(event_name, window)
    where = f"from {window[0]:g} s to {window[1]:g} s"
    if found.outcome == "fail":
        return failed(rule_id, code, f"{reason}; none in the right place, although the audio was clear {where} "
                      "(D-128)", evidence=evidence, uses=(*uses, found), timestamps=timestamps)
    why = ("a command may have been heard with low confidence" if LOW_CONFIDENCE_FLAG in found.flags else
           f"the audio was not clear {where} ({found.coverage.status}: {found.coverage.basis})")
    return unable(rule_id, f"{reason}, but a correctly placed one may have been said and not heard: {why} (D-128)",
                  evidence=evidence + found.low_confidence_event_ids, uses=(*uses, found), flags=(checks.CORRECT_UNSEEN,),
                  timestamps={**(timestamps or {}), "unseen_window_start": window[0], "unseen_window_end": window[1]})


def _timing_needs_clear_audio(ctx, result, names, window, what):
    """D-128 for a wrong-time Fail (A8, R7/A6 too_late): an unheard command inside `window` would change the time,
    so the Fail needs clear audio there (and no low-confidence command); otherwise Unable to Verify."""
    if result.kind != "fail":
        return result
    found = [ctx.missing(name, window) for name in names]
    if all(f.outcome == "fail" for f in found):
        return result
    where = f"from {window[0]:g} s to {window[1]:g} s"
    weak = next((f for f in found if LOW_CONFIDENCE_FLAG in f.flags), None)
    why = ("a command may have been heard with low confidence" if weak is not None else
           f"the audio was not clear {where} ({found[0].coverage.status}: {found[0].coverage.basis})")
    low = tuple(dict.fromkeys(i for f in found for i in f.low_confidence_event_ids))
    return unable(result.rule_id, f"{result.reason}; but {what} may have been said and not heard: {why} (D-128)",
                  evidence=result.evidence + low, uses=tuple(found), flags=(checks.CORRECT_UNSEEN,),
                  timestamps={**result.timestamps, "unseen_window_start": window[0], "unseen_window_end": window[1]})


# ---- A1, A3: a command given before the shock -------------------------------------------------------

@rule("A1", requires=(OXYGEN_AWAY, SHOCK), description="Free-flow oxygen away before the shock")
def oxygen_away(ctx, definition, results):
    """A1 (P-040): "oxygen away" said before the shock on the screen. See _before_shock."""
    return _before_shock(ctx, "A1", OXYGEN_AWAY, "oxygen away", "oxygen_away_before_shock_seconds")


@rule("A3", requires=(STAND_CLEAR, SHOCK), description="All stand clear before the shock")
def stand_clear(ctx, definition, results):
    """A3 (P-040): "all stand clear" said before the shock on the screen. See _before_shock."""
    return _before_shock(ctx, "A3", STAND_CLEAR, "stand clear", "stand_clear_before_shock_seconds")


def _before_shock(ctx, rule_id, event_name, what, limit_name):
    """A1 and A3 (P-040; D-121, D-122, D-123, D-125). The rule owns the relation "command before the shock".

    With a shock time (the screen only, D-093):
    1. A command not certainly after the shock (before it, or within the cross-modal tolerance or its
       segment's overlap: a tie never breaks an order) -> Pass. Any one occurrence in the right place
       counts. The time limit before the shock is unset (timing_not_checked); an approved "no limit"
       passes fully (D-103).
    2. Commands only certainly after the shock -> Fail `after_shock`, only if the audio was clear from the start
       of the recording to the shock, where a correct one would have been (D-128); otherwise Unable to Verify.
    3. No command -> Fail `missing` only if the audio was clear throughout from the start to the shock
       (stated clear-audio intervals, D-122); otherwise Unable to Verify. Low confidence is never a Fail.
    Without a shock time (D-121):
    4. A command seen -> Not evaluable because of R5, naming it.
    5. No command while the audio was clear throughout the recording -> Fail `missing`, on the rule's
       own evidence; otherwise Not evaluable because of R5.
    """
    commands = ctx.named(event_name)
    shock = ctx.shock
    if not shock.present:
        return _without_shock(ctx, rule_id, event_name, what, commands, shock)
    screen = next(e for e in ctx.events if e.event_id == shock.event_id)
    valid = [c for c in commands if checks.relation_between(ctx, c, screen) != checks.AFTER]
    if valid:
        return _given(ctx, rule_id, valid[0], screen, shock, what, limit_name)
    if commands:
        late = commands[0]
        return _wrong_place(ctx, rule_id, "after_shock", event_name, (0.0, shock.time),
                            f"{what} said only at {late.start:g} s, after the shock on the screen at {shock.time:g} s",
                            evidence=(late.event_id, shock.event_id), uses=(shock,),
                            timestamps={event_name: late.start, SHOCK: shock.time})
    found = ctx.missing(event_name, (0.0, shock.time))
    where = f"before the shock ({shock.time:g} s)"
    if found.outcome == "fail":
        return failed(rule_id, "missing", f"{what} not said {where}, although the audio was clear throughout (D-122)",
                      evidence=(shock.event_id,), uses=(shock, found))
    reason = ("a command may have been heard with low confidence" if LOW_CONFIDENCE_FLAG in found.flags else
              f"the audio was not clear throughout ({found.coverage.status}: {found.coverage.basis})")
    return unable(rule_id, f"{what} not heard {where}, but {reason}", evidence=found.low_confidence_event_ids,
                  uses=(shock, found))


def _given(ctx, rule_id, command, screen, shock, what, limit_name):
    limit = ctx.config.limit(limit_name)
    if limit.value is not None and limit.approved:
        # the brief defines no failure code for it: refused loudly as engine_error (D-063), never guessed
        raise ValueError(f"{rule_id}: an approved time limit before the shock ({limit_name}) is not implemented; "
                         "only an approved 'no limit' is (D-103)")
    check = checks.time_limit(None, limit)
    when = ("before" if checks.relation_between(ctx, command, screen) == checks.BEFORE
            else "at (within the tolerance of)")
    return passed(rule_id, f"{what} said at {command.start:g} s, {when} the shock on the screen at {shock.time:g} s: "
                  f"{check.note}", (command.event_id, shock.event_id), uses=(shock, check),
                  timestamps={command.event_name: command.start, SHOCK: shock.time}, timing_checked=check.checked)


def _without_shock(ctx, rule_id, event_name, what, commands, shock):
    """D-121: "before the shock" can't be judged without a shock time; whether the command was said still is."""
    if commands:
        command = commands[0]
        return checks.partly_evaluable(rule_id, shock, "R5", f"{what} said at {command.start:g} s; whether before the "
                                       "shock can't be judged", evidence=(command.event_id,),
                                       timestamps={event_name: command.start})
    found = ctx.missing(event_name)
    if found.outcome == "fail":
        return failed(rule_id, "missing", f"{what} not said in the recording, although the audio was clear throughout "
                      "(D-122); no shock time is needed to judge this (D-121)", uses=(found,))
    return checks.partly_evaluable(rule_id, shock, "R5", f"{what} not heard, and the audio was not clear throughout "
                                   f"({found.coverage.status}), so whether it was said is unknown too", uses=(found,))


# ---- A2, A4: continue compressions, then stop --------------------------------------------------------

CONTINUE, STOP = "continue_compressions_command", "stop_compressions_command"


def _possibly(ctx, event_name):
    """Ambiguous commands left unresolved (P-011: near the shock, or no shock time) that could have been
    event_name. Their stage is unknown, so they are neither evidence nor absence (D-010, D-125)."""
    unresolved = {r.event_id for r in ctx.resolutions if r.resolved_to is None}
    return [e for e in ctx.events if e.event_id in unresolved
            and event_name in (ctx.config.vocabulary.resolution(e.source, e.event_name) or ())]


def _screen(ctx):
    return next(e for e in ctx.events if e.event_id == ctx.shock.event_id)


@rule("A2", requires=(CONTINUE, SHOCK), description="Continue compressions during preparation, before the shock")
def continue_compressions(ctx, definition, results):
    """A2 (P-041): "continue compressions" said in the preparation stage, before the shock (D-121 to D-125).

    A2 owns "continue before the shock" only (D-123): its place after stand clear is A7's, and before stop is
    A4's (D-027). A continue/resume phrase is resolved by its segment's position relative to the shock (P-011,
    D-125); one left unresolved could have been continue or start.
    With a shock time:
    1. A continue command not certainly after the shock -> Pass (any occurrence counts).
    2. Else an unresolved continue/resume command -> Unable to Verify: continue or start can't be told.
    3. Else continue commands only certainly after the shock -> Fail `wrong_stage`, only if the audio was clear
       from the start of the recording to the shock (D-128); otherwise Unable to Verify.
    4. No command -> Fail `missing` only if the audio was clear from the start to the shock (D-122);
       otherwise Unable to Verify. Low confidence is never a Fail.
    Without a shock time (D-121): a continue (or unresolved continue/resume) command seen -> Not evaluable
    because of R5, naming it; none while the audio was clear throughout -> Fail `missing`; otherwise Not
    evaluable because of R5.
    """
    commands, unsure, shock = ctx.named(CONTINUE), _possibly(ctx, CONTINUE), ctx.shock
    if not shock.present:
        seen = commands or unsure
        if seen:
            what = "continue said" if commands else "a continue/resume command (continue or start: no shock time)"
            return checks.partly_evaluable("A2", shock, "R5", f"{what} at {seen[0].start:g} s; whether before the "
                                           "shock can't be judged", evidence=(seen[0].event_id,),
                                           timestamps={seen[0].event_name: seen[0].start})
        return _missing_without_shock(ctx, "A2", CONTINUE, "continue compressions", shock)
    screen = _screen(ctx)
    valid = [c for c in commands if checks.relation_between(ctx, c, screen) != checks.AFTER]
    if valid:
        command = valid[0]
        return passed("A2", f"continue said at {command.start:g} s, before the shock on the screen at {shock.time:g} s",
                      (command.event_id, shock.event_id), uses=(shock,),
                      timestamps={CONTINUE: command.start, SHOCK: shock.time})
    if unsure:
        command = unsure[0]
        return unable("A2", f"a continue/resume command at {command.start:g} s overlaps the shock ({shock.time:g} s): "
                      "whether it was continue (before) or start (after) can't be told (D-125)",
                      evidence=(command.event_id,), uses=(shock,), timestamps={"command": command.start, SHOCK: shock.time})
    if commands:
        late = commands[0]
        return _wrong_place(ctx, "A2", "wrong_stage", CONTINUE, (0.0, shock.time),
                            f"continue said only at {late.start:g} s, after the shock on the screen at {shock.time:g} s",
                            evidence=(late.event_id, shock.event_id), uses=(shock,),
                            timestamps={CONTINUE: late.start, SHOCK: shock.time})
    return _missing_before_shock(ctx, "A2", CONTINUE, "continue compressions", shock)


@rule("A4", requires=(STOP, CONTINUE, SHOCK), description="Stop compressions after continue, before the shock")
def stop_compressions(ctx, definition, results):
    """A4 (P-041): "stop" said after "continue" and before the shock (D-027, D-121 to D-125).

    A4 owns "continue before stop" (D-027) and "stop before the shock" (D-123).
    With a shock time:
    1. No stop command not certainly after the shock: stops only after it -> Fail `after_shock` (only with clear
       audio from the first continue, or the recording start, to the shock, D-128); none ->
       Fail `missing` only if the audio was clear from the start to the shock, otherwise Unable to Verify.
    2. The order against continue, for a stop before the shock: a continue not certainly after the stop ->
       in order (in one segment: not ordered, flagged order_partially_checked); continues only certainly
       after every stop -> Fail `wrong_order`; no continue observed, or only unresolved continue/resume
       commands -> Not evaluable because of A2, naming the checked part.
    3. In order -> Pass; the stop-to-shock limit is unset (timing_not_checked); an approved "no limit"
       passes fully (D-103); an approved number is refused (engine_error): no failure code is defined.
    Without a shock time (D-121): the order against continue is still judged (`wrong_order` is A4's own
    evidence); otherwise a stop seen -> Not evaluable because of R5, naming it; none while the audio was
    clear throughout -> Fail `missing`; otherwise Not evaluable because of R5.
    """
    stops, continues, unsure, shock = ctx.named(STOP), ctx.named(CONTINUE), _possibly(ctx, CONTINUE), ctx.shock
    if not shock.present:
        if not stops:
            return _missing_without_shock(ctx, "A4", STOP, "stop compressions", shock)
        status, stop, other = _stop_order(ctx, stops, continues, unsure)
        if status == "wrong":
            return _wrong_order(ctx, stop, other, _recording_end(ctx))
        note = {"in_order": f", after continue ({other.start:g} s)" if other else "",
                "same_segment": f", in one segment with continue ({other.start:g} s): not ordered" if other else "",
                "unknown": "; its order against continue can't be judged either"}[status]
        return checks.partly_evaluable("A4", shock, "R5", f"stop said at {stop.start:g} s{note}; whether before the "
                                       "shock can't be judged", evidence=(stop.event_id,), timestamps={STOP: stop.start})
    screen = _screen(ctx)
    valid = [s for s in stops if checks.relation_between(ctx, s, screen) != checks.AFTER]
    if not valid:
        if stops:
            late = stops[0]
            early = [c for c in continues if checks.relation_between(ctx, c, screen) != checks.AFTER]
            start = min(checks.time_bounds(early[0])[0], shock.time) if early else 0.0   # a correct stop: after continue
            return _wrong_place(ctx, "A4", "after_shock", STOP, (start, shock.time),
                                f"stop said only at {late.start:g} s, after the shock on the screen at {shock.time:g} s",
                                evidence=(late.event_id, shock.event_id), uses=(shock,),
                                timestamps={STOP: late.start, SHOCK: shock.time})
        return _missing_before_shock(ctx, "A4", STOP, "stop compressions", shock)
    status, stop, other = _stop_order(ctx, valid, continues, unsure)
    if status == "wrong":
        return _wrong_order(ctx, stop, other, shock.time)
    if status == "unknown":
        why = (f"a continue/resume command at {other.start:g} s couldn't be resolved" if other is not None
               else "no continue command was observed")
        return not_evaluable("A4", "A2", f"not evaluable because of A2: {why}, so whether continue came before stop "
                             f"can't be judged; checked: stop said at {stop.start:g} s, before the shock on the screen "
                             f"at {shock.time:g} s", uses=(shock,), evidence=(stop.event_id, shock.event_id),
                             timestamps={STOP: stop.start, SHOCK: shock.time})
    limit = ctx.config.limit("stop_to_shock_seconds")
    if limit.value is not None and limit.approved:
        raise ValueError("A4: an approved stop-to-shock limit is not implemented; only an approved 'no limit' is (D-103)")
    check = checks.time_limit(None, limit)
    flags = (checks.ORDER_PARTIALLY_CHECKED,) if status == "same_segment" else ()
    order = (f"in one segment with continue ({other.start:g} s), so not ordered" if status == "same_segment"
             else f"after continue ({other.start:g} s)")
    return passed("A4", f"stop said at {stop.start:g} s, {order}, and before the shock on the screen at "
                  f"{shock.time:g} s: {check.note}", (stop.event_id, other.event_id, shock.event_id),
                  uses=(shock, check), flags=flags, timing_checked=check.checked,
                  timestamps={STOP: stop.start, CONTINUE: other.start, SHOCK: shock.time})


def _stop_order(ctx, stops, continues, unsure):
    """(status, stop, continue or unresolved command): in_order, same_segment, wrong or unknown (D-027, D-125)."""
    shared = None
    for stop in stops:
        for command in continues:
            if checks.same_segment(command, stop):
                shared = shared or (stop, command)
            elif checks.relation_between(ctx, command, stop) != checks.AFTER:
                return "in_order", stop, command
    if shared:
        return ("same_segment", *shared)
    for stop in stops:   # an unresolved command could have been the earlier continue
        for command in unsure:
            if checks.relation_between(ctx, command, stop) != checks.AFTER:
                return "unknown", stop, command
    if continues:
        return "wrong", stops[0], continues[0]
    return "unknown", stops[0], (unsure[0] if unsure else None)


def _wrong_order(ctx, stop, command, end):
    """Stop before every continue (D-027). D-128: a correct stop would have come after the continue and before
    the shock (or, without a shock time, the end of the recording), so the audio must be clear there."""
    first = checks.time_bounds(command)[0]
    window = (min(first, end), max(first, end)) if end is not None else (first, first)
    return _wrong_place(ctx, "A4", "wrong_order", STOP, window, f"stop said at {stop.start:g} s, before continue (said "
                        f"only at {command.start:g} s); stop comes after continue (D-027)",
                        evidence=(stop.event_id, command.event_id), timestamps={STOP: stop.start, CONTINUE: command.start})


def _missing_before_shock(ctx, rule_id, event_name, what, shock):
    found = ctx.missing(event_name, (0.0, shock.time))
    where = f"before the shock ({shock.time:g} s)"
    if found.outcome == "fail":
        return failed(rule_id, "missing", f"{what} not said {where}, although the audio was clear throughout (D-122)",
                      evidence=(shock.event_id,), uses=(shock, found))
    reason = ("a command may have been heard with low confidence" if LOW_CONFIDENCE_FLAG in found.flags else
              f"the audio was not clear throughout ({found.coverage.status}: {found.coverage.basis})")
    return unable(rule_id, f"{what} not heard {where}, but {reason}", evidence=found.low_confidence_event_ids,
                  uses=(shock, found))


def _missing_without_shock(ctx, rule_id, event_name, what, shock):
    found = ctx.missing(event_name)
    if found.outcome == "fail":
        return failed(rule_id, "missing", f"{what} not said in the recording, although the audio was clear throughout "
                      "(D-122); no shock time is needed to judge this (D-121)", uses=(found,))
    return checks.partly_evaluable(rule_id, shock, "R5", f"{what} not heard, and the audio was not clear throughout "
                                   f"({found.coverage.status}), so whether it was said is unknown too", uses=(found,))


# ---- A5: the shock command ----------------------------------------------------------------------------

SHOCK_COMMAND = "shock_command"


@rule("A5", requires=(SHOCK_COMMAND, SHOCK), description="The verbal shock command, before or at the shock")
def shock_command(ctx, definition, results):
    """A5 (P-042): the verbal shock command. Its result never affects R5: the shock is judged visually (proposal).

    A5 owns only "shock command before or at the shock" (A5 -> R5, D-123). Its place among the shocking actions
    is unknown (OQ-075), and stop -> shock command is A7's. Whether A5 is required at all is open (OQ-075;
    the lecturer gave none), so it stays pending.
    1. With a shock time: a command not certainly after the shock satisfies A5 (any one occurrence): within the
       cross-modal tie it is "at" the shock -> Pass; before it -> Pass, but how long before is unset
       (shock_command_tolerance_seconds) -> timing_not_checked; an approved "no limit" passes fully (D-103); an
       approved number is refused (engine_error), since no failure code is defined for "too early".
    2. Commands only certainly after the shock -> Fail `after_shock`: an order mistake on A5's own relation, like
       A1 and A3, not a time-limit question; only with clear audio from the start to the shock (D-128).
    3. No command -> Fail `missing` only if the audio was clear throughout the recording (D-122); otherwise
       Unable to Verify. Low confidence is never a Fail.
    4. Without a shock time (D-121): a command seen -> Not evaluable because of R5, naming it; none while the
       audio was clear throughout -> Fail `missing`; otherwise Not evaluable because of R5.
    """
    commands, shock = ctx.named(SHOCK_COMMAND), ctx.shock
    if not shock.present:
        if commands:
            command = commands[0]
            return checks.partly_evaluable("A5", shock, "R5", f"shock command said at {command.start:g} s; whether "
                                           "before or at the shock can't be judged", evidence=(command.event_id,),
                                           timestamps={SHOCK_COMMAND: command.start})
        return _missing_without_shock(ctx, "A5", SHOCK_COMMAND, "the shock command", shock)
    if not commands:
        found = ctx.missing(SHOCK_COMMAND)
        if found.outcome == "fail":
            return failed("A5", "missing", "the shock command not said in the recording, although the audio was clear "
                          "throughout (D-122)", evidence=(shock.event_id,), uses=(shock, found))
        reason = ("a command may have been heard with low confidence" if LOW_CONFIDENCE_FLAG in found.flags else
                  f"the audio was not clear throughout ({found.coverage.status}: {found.coverage.basis})")
        return unable("A5", f"the shock command not heard, but {reason}", evidence=found.low_confidence_event_ids,
                      uses=(shock, found))
    screen = _screen(ctx)
    ties = [c for c in commands if checks.relation_between(ctx, c, screen) == checks.SIMULTANEOUS]
    before = [c for c in commands if checks.relation_between(ctx, c, screen) == checks.BEFORE]
    if ties:
        command = ties[0]
        return passed("A5", f"shock command said at {command.start:g} s, at (within the tolerance of) the shock on the "
                      f"screen at {shock.time:g} s", (command.event_id, shock.event_id), uses=(shock,),
                      timestamps={SHOCK_COMMAND: command.start, SHOCK: shock.time})
    if not before:
        late = commands[0]
        return _wrong_place(ctx, "A5", "after_shock", SHOCK_COMMAND, (0.0, shock.time),
                            f"shock command said only at {late.start:g} s, after the shock on the screen at "
                            f"{shock.time:g} s", evidence=(late.event_id, shock.event_id), uses=(shock,),
                            timestamps={SHOCK_COMMAND: late.start, SHOCK: shock.time})
    limit = ctx.config.limit("shock_command_tolerance_seconds")
    if limit.value is not None and limit.approved:
        raise ValueError("A5: an approved shock-command tolerance (how long before the shock) is not implemented; "
                         "only an approved 'no limit' is (D-103)")
    check = checks.time_limit(None, limit)
    command = before[-1]   # the one closest to the shock
    return passed("A5", f"shock command said at {command.start:g} s, before the shock on the screen at {shock.time:g} s; "
                  f"how long before: {check.note}", (command.event_id, shock.event_id), uses=(shock, check),
                  timestamps={SHOCK_COMMAND: command.start, SHOCK: shock.time}, timing_checked=check.checked)


# ---- R7/A6: restart compressions after the shock (one check, two IDs, D-044) -------------------------

START = "start_compressions_command"
MERGED_CAUSE = ("likely cause: the detector merges continue, resume and start into one command "
                "(resume_compressions_command), and a command carries its whole Whisper segment, not its word time "
                "(requested from Sanjeevan: a separate start command and word timestamps)")


@rule("R7", requires=(START, SHOCK), description="Compressions restarted promptly after the shock")
def restart_compressions(ctx, definition, results):
    """R7/A6 (P-043): the start/resume compressions command after the shock. Implemented once; A6 is same_as R7
    and reported under its own ID (D-044).

    R7 owns only "shock before the restart" (R5 -> R7, D-123); "removal before the restart" is S1's. The shock time
    comes only from the screen (D-093); no removal fallback (D-115). A resume phrase is resolved by its segment's
    position relative to the shock (P-011, D-125).
    With a shock time:
    1. A start command not certainly before the shock (after it, or a tie) -> Pass, timed from the shock with
       shock_to_compressions_seconds on the shortest and longest possible durations (D-125): unset -> timing not
       checked; approved and exceeded -> Fail `too_late` (only with clear audio from the shock to the restart,
       D-128); straddled -> Unable to Verify, `timing_uncertain`.
    2. Else an unresolved continue/resume command (near the shock) -> Unable to Verify, naming the likely cause.
    3. Else no restart: judged on the audio from the shock to the end of the recording (D-122). Clear -> Fail
       `before_shock` if start was said only certainly before the shock (D-053: ineligible starts), else Fail
       `missing`. Not clear, or low confidence -> Unable to Verify: the restart may have been said but not heard.
    Without a shock time (D-121): a start (or unresolved continue/resume) command seen -> Not evaluable because of
    R5, naming it; none while the audio was clear throughout -> Fail `missing`; otherwise Not evaluable because
    of R5.
    """
    starts, unsure, shock = ctx.named(START), _possibly(ctx, START), ctx.shock
    if not shock.present:
        seen = starts or unsure
        if seen:
            what = "start said" if starts else "a continue/resume command (continue or start: no shock time)"
            return checks.partly_evaluable("R7", shock, "R5", f"{what} at {seen[0].start:g} s; whether after the shock "
                                           "can't be judged", evidence=(seen[0].event_id,),
                                           timestamps={seen[0].event_name: seen[0].start})
        return _missing_without_shock(ctx, "R7", START, "the restart command", shock)
    screen, command = _screen(ctx), _restart(ctx)
    if command is not None:
        result = checks.timed_between("R7", screen, command, ctx.config.limit("shock_to_compressions_seconds"),
                                      code="too_late", what=f"restart said at {command.start:g} s, after the shock on "
                                      f"the screen at {shock.time:g} s", evidence=(command.event_id, shock.event_id),
                                      uses=(shock,))
        # D-128: an earlier restart, from the shock to this one, may have been said and not heard
        window = (shock.time, max(shock.time, checks.time_bounds(command)[0]))
        return _timing_needs_clear_audio(ctx, result, (START,), window, "an earlier restart")
    if unsure:
        command = unsure[0]
        return unable("R7", f"a continue/resume command at {command.start:g} s is within the cross-modal tolerance of "
                      f"the shock ({shock.time:g} s): whether it was the restart can't be told (D-125); {MERGED_CAUSE}",
                      evidence=(command.event_id,), uses=(shock,), timestamps={"command": command.start, SHOCK: shock.time})
    end = _recording_end(ctx)
    found = ctx.missing(START, (shock.time, end) if end is not None and end > shock.time else None)
    where = f"after the shock ({shock.time:g} s)"
    early = starts[0] if starts else None
    if found.outcome == "fail":   # the audio was clear from the shock to the end: no restart was said (D-122)
        if early is not None:
            return failed("R7", "before_shock", f"start said only at {early.start:g} s, before the shock on the "
                          f"screen at {shock.time:g} s, and none {where} although the audio was clear to the end of "
                          "the recording; a start before the shock is not the restart (D-025, D-053, D-122)",
                          evidence=(early.event_id, shock.event_id), uses=(shock, found),
                          timestamps={START: early.start, SHOCK: shock.time})
        return failed("R7", "missing", f"no restart command {where}, although the audio was clear to the end of the "
                      "recording (D-122)", evidence=(shock.event_id,), uses=(shock, found))
    reason = ("a command may have been heard with low confidence" if LOW_CONFIDENCE_FLAG in found.flags else
              f"the audio was not clear throughout ({found.coverage.status}: {found.coverage.basis})")
    if early is not None:
        return unable("R7", f"start said only at {early.start:g} s, before the shock on the screen at {shock.time:g} "
                      f"s; a restart may have been said {where} but not heard: {reason} (D-122)",
                      evidence=(early.event_id,) + found.low_confidence_event_ids, uses=(shock, found),
                      timestamps={START: early.start, SHOCK: shock.time})
    return unable("R7", f"no restart command heard {where}, but {reason}", evidence=found.low_confidence_event_ids,
                  uses=(shock, found))

def _restart(ctx):
    """The restart command, or None: the context's start anchor (D-025, D-125), shared by R7/A6 and A8 so they
    always judge the same command."""
    anchor = ctx.anchor("start_compressions")
    return next((e for e in ctx.named(START) if e.event_id == anchor.event_id), None) if anchor.present else None


def _recording_end(ctx):
    header = ctx.coverage.header
    ends = [e.end for e in ctx.prepared.events]
    return header.duration_seconds if header is not None and header.duration_seconds else (max(ends) if ends else None)


# ---- A8: the pre-shock pause ------------------------------------------------------------------------

END_EVENTS = {"start": "the restart", "shock": "the shock on the screen"}


@rule("A8", requires=(STOP, CONTINUE, START, SHOCK), description="Pre-shock pause within the approved limit")
def pre_shock_pause(ctx, definition, results):
    """A8 (P-044): the pause from stopping compressions to its end, within pre_shock_pause_seconds (5 s, approved).

    The end event is a config value, parameters.end_event (OQ-076): "start" (the restart, as approved; the
    default until the supervisor decides) or "shock" (the shock on the screen, never the removal, D-093);
    anything else is a configuration error (engine_error).
    - Pause start: the stop compressions command not certainly after the shock and not followed, before the
      shock, by a continue command (compressions resumed). A4 judges the stop itself.
    - Pause end: the restart is the context's start anchor (D-025, D-125), the same command R7/A6 judge.
    - Duration on the shortest and longest possible gap (D-125): both within the limit -> Pass; both over ->
      Fail `pre_shock_pause`, only with clear audio over the pause (D-128: an unheard earlier restart or later
      stop would shorten it); in between -> Unable to Verify (`timing_uncertain`).
    Missing references (D-121): no shock time (needed to find the restart, or as the end event) -> Not
    evaluable because of R5; no stop -> because of A4; no restart -> because of R7. A8 never fails for them.
    """
    end_event = definition.parameters.get("end_event", "start")
    if end_event not in END_EVENTS:
        # a configuration error: recorded as engine_error (D-063), never a result about the learner
        raise ValueError(f"A8 end_event must be one of {sorted(END_EVENTS)}, got {end_event!r} (OQ-076)")
    shock, limit, end_name = ctx.shock, ctx.config.limit("pre_shock_pause_seconds"), END_EVENTS[end_event]
    stops = ctx.named(STOP)
    if not shock.present:
        seen = f"; checked: stop said at {stops[0].start:g} s" if stops else ""
        return not_evaluable("A8", "R5", f"not evaluable because of R5: {shock.reason}; without the shock time "
                             f"{end_name} can't be identified (D-093){seen}", uses=(shock,),
                             evidence=(stops[0].event_id,) if stops else (),
                             timestamps={STOP: stops[0].start} if stops else None)
    screen = _screen(ctx)
    stop = _pause_start(ctx, stops, screen)
    end = screen if end_event == "shock" else _restart(ctx)
    if stop is None:
        also = "; the restart is missing too (R7)" if end is None else ""
        return not_evaluable("A8", "A4", f"not evaluable because of A4: {_why_no_stop(ctx, stops, screen)}, so the "
                             f"pause has no start{also}", uses=(shock,))
    if end is None:
        return not_evaluable("A8", "R7", f"not evaluable because of R7: {_why_no_restart(ctx)}, so the pause has no "
                             f"end; checked: stop said at {stop.start:g} s", uses=(shock,), evidence=(stop.event_id,),
                             timestamps={STOP: stop.start})
    result = checks.timed_between("A8", stop, end, limit, code="pre_shock_pause",
                                  what=f"pause from stop ({stop.start:g} s) to {end_name} ({end.start:g} s)",
                                  evidence=(stop.event_id, end.event_id), uses=(shock,))
    # D-128: an unheard earlier restart, or an unheard later stop, inside the pause would make it shorter
    window = (checks.time_bounds(stop)[0], max(checks.time_bounds(stop)[0], checks.time_bounds(end)[1]))
    names = (STOP, START) if end_event == "start" else (STOP,)
    return _timing_needs_clear_audio(ctx, result, names, window, "a command inside the pause")


def _pause_start(ctx, stops, screen):
    """The stop compressions were not resumed after: not certainly after the shock, and no continue command
    certainly after it and not after the shock. The earliest such stop starts the pause."""
    continues = ctx.named(CONTINUE)
    for stop in stops:
        if checks.relation_between(ctx, stop, screen) == checks.AFTER:
            continue
        if not any(checks.relation_between(ctx, c, stop) == checks.AFTER
                   and checks.relation_between(ctx, c, screen) != checks.AFTER for c in continues):
            return stop
    return None


def _why_no_stop(ctx, stops, screen):
    if not stops:
        return "no stop compressions command heard (A4 judges whether that is a mistake)"
    if all(checks.relation_between(ctx, s, screen) == checks.AFTER for s in stops):
        return f"stop said only after the shock ({stops[0].start:g} s)"
    return "every stop before the shock was followed by continue, so compressions resumed"


def _why_no_restart(ctx):
    if _possibly(ctx, START):
        return f"a continue/resume command near the shock is unresolved; {MERGED_CAUSE}"
    if ctx.named(START):
        return "start said only before the shock"
    return "no restart command heard after the shock"


# ---- A7: the order of the audio commands --------------------------------------------------------------

@rule("A7", requires=(OXYGEN_AWAY, STAND_CLEAR, CONTINUE, "charging_command", "gel_announcement_command", STOP,
                      SHOCK_COMMAND, START), description="The audio commands in the expected order")
def command_order(ctx, definition, results):
    """A7 (P-045): the audio-audio relations A7 owns in procedure_order.yaml (D-120, D-123), judged by the
    minimum set of misplaced commands (plan section 4). Relations owned by other rules (A2 -> A4 is A4's) are
    not judged again.

    - A step is observed by any occurrence of its events; any occurrence in the right place counts. "X before
      Y" holds unless X is certainly after Y (segments compared as intervals, a tie satisfies either order,
      D-125). Commands in one Whisper segment are not ordered (`order_partially_checked`).
    - The minimum set: the fewest observed steps whose removal leaves the rest consistent. A step in every
      minimum solution is misplaced; steps in some but not all are one ordering mistake between them; either
      way it is one `wrong_order` Fail. Missing steps are left out (their own rule reports them). Optional
      steps (charging, "applying gel") are checked for position only if said, never missing (D-127).
    - Unseen occurrences are left out and the result flagged `order_partially_checked`, never a clean Pass:
      a required step not heard while the audio was not clear throughout, a low-confidence command, or a
      continue/resume left unresolved (P-011). Such a command could be an occurrence in the right place, so a
      misplacement it could remove is not a Fail: Unable to Verify.
    - D-128: a Fail needs, for each command reported, clear audio (and no low-confidence command) over the
      window where a correctly placed occurrence would have had to be: from its latest observed required
      predecessor to its earliest observed required successor (A7's relations; the recording start or end
      where none). Otherwise a correct occurrence may have been said but not heard: Unable to Verify.
    - Fewer than two steps observed -> Unable to Verify.
    """
    order = ctx.config.procedure_order
    relations = [(r.before, r.after) for r in order.owned_by("A7")]
    ids = [s.id for s in order.steps if any(s.id in pair for pair in relations)]
    real = {s: [e for e in ctx.events if e.event_name in order.step(s).events] for s in ids}
    unsure = {s: _unseen_occurrences(ctx, order.step(s)) for s in ids}
    observed = [s for s in ids if real[s]]
    clear = ctx.coverage.region_status("audio", _whole(ctx)).status == COVERED
    unseen = [s for s in ids if not real[s] and (unsure[s] or (not clear and not order.step(s).optional))]
    partial = bool(unseen or any(unsure.values()))
    partial_flag = (checks.ORDER_PARTIALLY_CHECKED,) if partial else ()
    if len(observed) < 2:
        return unable("A7", f"fewer than two commands of the procedure order heard ({', '.join(observed) or 'none'}), "
                      "so their order can't be judged")   # nothing checked, so not "partially checked"
    certain = _minimum_misplaced(ctx, ids, relations, real, {})
    note = f"; not checked (unseen): {', '.join(unseen)}" if unseen else ""
    if not certain.all_dropped:
        same = _same_segment_pairs(certain.chosen, relations)
        segment = ("; in one segment, so not ordered: " + ", ".join(f"{a} and {b}" for a, b in same)) if same else ""
        return passed("A7", f"the commands heard are in the expected order ({_listing(certain.chosen)}){segment}{note}",
                      tuple(e.event_id for e in certain.chosen.values()),
                      flags=(checks.ORDER_PARTIALLY_CHECKED,) if partial or same else (),
                      timestamps={s: e.start for s, e in certain.chosen.items()})
    possible = _minimum_misplaced(ctx, ids, relations, real, unsure)
    if not possible.all_dropped:
        return unable("A7", f"{_describe(certain, real)}, but a low-confidence or unresolved command could be an "
                      f"occurrence in the right place{note}", evidence=_evidence(certain, real, ids),
                      timestamps=_times(certain, real), flags=(checks.ORDER_PARTIALLY_CHECKED,))
    unheard = [(step, window) for step in possible.all_dropped
               for window in [_correct_window(ctx, order, step, relations, real)]
               if any(ctx.missing(name, window).outcome != "fail" for name in order.step(step).events)]
    if unheard:
        where = "; ".join(f"{step} from {w[0]:g} s to {w[1]:g} s" for step, w in unheard)
        return unable("A7", f"{_describe(possible, real)}, but a correctly placed occurrence may have been said and not "
                      f"heard: the audio was not clear where it would have been ({where}) (D-128){note}",
                      evidence=_evidence(possible, real, ids), timestamps=_times(possible, real),
                      flags=(checks.ORDER_PARTIALLY_CHECKED, checks.CORRECT_UNSEEN))
    return failed("A7", "wrong_order", f"{_describe(possible, real)}{note}", evidence=_evidence(possible, real, ids),
                  timestamps=_times(possible, real), flags=partial_flag)


class _Solution:
    """The minimum solutions: misplaced = steps in every one; between = steps in some but not all (one mistake
    between them); chosen = the occurrences kept by the first solution."""

    def __init__(self, misplaced, between, chosen):
        self.misplaced, self.between, self.chosen = misplaced, between, chosen

    @property
    def all_dropped(self):
        return list(self.misplaced) + list(self.between)


def _minimum_misplaced(ctx, ids, relations, real, unsure):
    """Kept sets tried from the largest down (deterministic; at most 15 steps). Dropping a step heard for real
    costs 1; a step seen only through low-confidence or unresolved commands drops for free."""
    steps = [s for s in ids if real[s] or unsure.get(s)]
    if len(steps) > 15:
        raise ValueError(f"A7: {len(steps)} steps observed; the order search handles at most 15")
    occurrences = {s: sorted(real[s] + unsure.get(s, []), key=lambda e: (e.start, e.end)) for s in steps}
    preds = {s: [p for p, q in relations if q == s] for s in steps}
    best, solutions = None, []
    for size in range(len(steps), -1, -1):
        for kept in combinations(steps, size):
            dropped = frozenset(s for s in steps if s not in kept and real[s])
            if best is not None and len(dropped) > best:
                continue
            chosen = _place(ctx, kept, occurrences, preds)
            if chosen is None:
                continue
            if best is None or len(dropped) < best:
                best, solutions = len(dropped), [(dropped, chosen)]
            elif dropped not in [d for d, _ in solutions]:
                solutions.append((dropped, chosen))
    every = frozenset.intersection(*[d for d, _ in solutions])
    some = frozenset.union(*[d for d, _ in solutions]) - every
    return _Solution([s for s in ids if s in every], [s for s in ids if s in some], solutions[0][1])


def _place(ctx, kept, occurrences, preds):
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


def _unseen_occurrences(ctx, step):
    """Occurrences that could be this step but can't be used: low confidence, or unresolved (P-011)."""
    vocabulary = ctx.config.vocabulary
    low = [e for e in ctx.prepared.excluded if e.event_name in step.events
           or set(vocabulary.resolution(e.source, e.event_name) or ()) & set(step.events)]
    return low + [e for name in step.events for e in _possibly(ctx, name)]


def _same_segment_pairs(chosen, relations):
    return [(a, b) for a, b in relations if a in chosen and b in chosen and checks.same_segment(chosen[a], chosen[b])]


def _listing(chosen):
    return ", ".join(f"{s} at {e.start:g} s" for s, e in chosen.items())


def _describe(solution, real):
    parts = [f"{s} ({real[s][0].event_name} at {real[s][0].start:g} s) is out of order" for s in solution.misplaced]
    if solution.between:
        names = " and ".join(f"{s} ({real[s][0].event_name} at {real[s][0].start:g} s)" for s in solution.between)
        parts.append(f"{names} are in the wrong order (one mistake)")
    return "; ".join(parts)


def _evidence(solution, real, ids):
    return tuple(real[s][0].event_id for s in sorted(solution.all_dropped, key=ids.index))


def _times(solution, real):
    return {s: real[s][0].start for s in solution.all_dropped}


def _correct_window(ctx, order, step, relations, real):
    """D-128: where a correctly placed occurrence of `step` would have had to be: after the earliest occurrence of
    each observed required predecessor and before the latest occurrence of each observed required successor (any
    occurrence counts); the recording start or end where none."""
    required = lambda other: real[other] and not order.step(other).optional
    preds = [p for p, q in relations if q == step and required(p)]
    succs = [q for p, q in relations if p == step and required(q)]
    start = max((checks.time_bounds(real[p][0])[0] for p in preds), default=0.0)
    end = min((checks.time_bounds(real[q][-1])[1] for q in succs), default=_recording_end(ctx) or start)
    return (min(start, end), max(start, end))


def _whole(ctx):
    end = _recording_end(ctx)
    return (0.0, end) if end else None
