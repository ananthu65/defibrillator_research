"""Audio rules (Increment 21 onward). Each rule is one small function built from the shared checks.

The input is Sanjeevan's command events (Whisper -> detect_commands, the shared Event schema, D-125);
nothing here imports audio/. A command event carries its Whisper segment, so it is compared as an
interval (checks.relation_between, D-125). A missing command can Fail only inside stated clear-audio
intervals (the audio region, D-122). Registered rules run only when approved in configs/rules.yaml.
"""
from rules import checks
from rules.coverage import LOW_CONFIDENCE_FLAG
from rules.outcome import failed, not_evaluable, passed, unable
from rules.registry import rule

SHOCK = "shock_delivered_on_screen"
OXYGEN_AWAY, STAND_CLEAR = "oxygen_away_command", "stand_clear_command"
FLAGS = ()   # rule-result flags raised here (the shared ones are in checks.FLAGS)


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
    2. Commands only certainly after the shock -> Fail `after_shock`.
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
        return failed(rule_id, "after_shock", f"{what} said only at {late.start:g} s, after the shock on the screen at "
                      f"{shock.time:g} s", evidence=(late.event_id, shock.event_id), uses=(shock,),
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
    3. Else continue commands only certainly after the shock -> Fail `wrong_stage`.
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
        return failed("A2", "wrong_stage", f"continue said only at {late.start:g} s, after the shock on the screen at "
                      f"{shock.time:g} s", evidence=(late.event_id, shock.event_id), uses=(shock,),
                      timestamps={CONTINUE: late.start, SHOCK: shock.time})
    return _missing_before_shock(ctx, "A2", CONTINUE, "continue compressions", shock)


@rule("A4", requires=(STOP, CONTINUE, SHOCK), description="Stop compressions after continue, before the shock")
def stop_compressions(ctx, definition, results):
    """A4 (P-041): "stop" said after "continue" and before the shock (D-027, D-121 to D-125).

    A4 owns "continue before stop" (D-027) and "stop before the shock" (D-123).
    With a shock time:
    1. No stop command not certainly after the shock: stops only after it -> Fail `after_shock`; none ->
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
            return _wrong_order(stop, other)
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
            return failed("A4", "after_shock", f"stop said only at {late.start:g} s, after the shock on the screen at "
                          f"{shock.time:g} s", evidence=(late.event_id, shock.event_id), uses=(shock,),
                          timestamps={STOP: late.start, SHOCK: shock.time})
        return _missing_before_shock(ctx, "A4", STOP, "stop compressions", shock)
    status, stop, other = _stop_order(ctx, valid, continues, unsure)
    if status == "wrong":
        return _wrong_order(stop, other)
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


def _wrong_order(stop, command):
    return failed("A4", "wrong_order", f"stop said at {stop.start:g} s, before continue (said only at "
                  f"{command.start:g} s); stop comes after continue (D-027)", evidence=(stop.event_id, command.event_id),
                  timestamps={STOP: stop.start, CONTINUE: command.start})


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
       A1 and A3, not a time-limit question.
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
        return failed("A5", "after_shock", f"shock command said only at {late.start:g} s, after the shock on the screen "
                      f"at {shock.time:g} s", evidence=(late.event_id, shock.event_id), uses=(shock,),
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
