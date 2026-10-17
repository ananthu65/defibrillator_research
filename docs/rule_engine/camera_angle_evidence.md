# Camera angle evidence for the rule engine

**Status: interim.** This is based on the smoke-run export of 38 corrected backups (one
annotator's set, D-084). P14_LS is excluded as unreliable (OQ-055), so **37 videos are counted:
12 LL, 12 LS, 13 T**. To be rerun on the final export (OQ-054). Prepared 2026-10-17 for the
decision on the final camera angle (OQ-038).

**The key point.** The shock time is taken only from the shock seen on the defibrillator screen,
and never inferred (D-093). **A view that doesn't show the screen therefore leaves every
shock-dependent rule unverifiable:** R6, R7/A6, A1–A4, A7, A8, and R3's direct check. In this
data, the shock is seen on the screen in **0 of 12 LL**, **10 of 12 LS** and **9 of 13 T**
videos.

## What each view shows

### Placement zones (from the exporter's zone tracks)

| View | Apical zone | Sternal zone |
|---|---|---|
| LL (12) | visible throughout: 12 | no track: 12 |
| LS (12) | visible throughout: 12 | visible throughout: 12 |
| T (13) | throughout: 3, **partly: 10** | throughout: 12, partly: 1 |

A zone visible for only part of a T video is judged per time window (D-092). Whether it was in
view at the moment that matters is decided by the rule that asks.

### The defibrillator screen

The interim export was made before screen visibility was added to the exporter (D-094), so it
has no screen intervals. The evidence comes from two sources:

| View | Shock seen on screen (interim, tag `shock_delivered_on_screen`) | Screen tracked in the video (Phase 1 inventory, 144 older backups) | Shock symbol tracked (Phase 1) |
|---|---|---|---|
| LL | **0 of 12** | 3 of 48 | 0 of 48 |
| LS | **10 of 12** | 48 of 48 | 38 of 48 |
| T | **9 of 13** | 19 of 48 | 9 of 48 |

The screen is reliably in view only from LS. T shows the shock in most interim videos, but the
screen is tracked in fewer than half of the older T videos. LL essentially never shows it.

### Tags (videos with at least one; interim)

| Tag | LL (12) | LS (12) | T (13) |
|---|---|---|---|
| Gel applied | 10 (twice or more: 1) | 12 (twice or more: 9) | 11 (twice or more: 3) |
| first_paddle_taken | 11 | 12 | 13 |
| first_paddle_firmly_on_the_chest | 12 | 11 | 13 |
| second_paddle_taken | **7** | 12 | 13 |
| paddles_firmly_on_chest | **5** | 12 | 13 |
| both_paddle_buttons_pressed | **2** | 10 | 11 |
| shock_delivered_on_screen | **0** | 10 | 9 |
| paddles_removed_after_shock | 12 | 12 | 13 |

Each angle is a separate video in this project. This report compares what each view **can**
show, to inform the choice of angle; rule results are never compared or cross-checked across
angles (D-096).

The counts can't separate "the learner didn't do it" from "the camera didn't see it". For
example, a single gel tag may be a learner who applied gel once, or a second application out of
view. The pattern across views (LS sees two applications most often) points to visibility.

One LL video carries an object label as a tag (`apical_placement_zone`). The engine flags it as
an unknown label, and it belongs on Ananth's fix list.

## Which rules each view can check

These assume the final system (video and audio), the decided setting `shock_time_fallback:
none`, and annotation-like evidence.
- **Direct:** the evidence is visible in (nearly) all videos.
- **Partly:** only in some videos, only by inference, or only some failure codes.
- **Unverifiable:** never from this view.

| Rule | Needs | LL | LS | T |
|---|---|---|---|---|
| R1 Gel applied twice | gel tags | partly (two applications seen in 1 of 12) | **direct** | partly (3 of 13) |
| R2 Second paddle after first placed | first taken, first placement, second taken; both zones for `first_placement_not_observed` | partly (second taken in 7 of 12; the sternal zone is never in view, so `first_placement_not_observed` can't be confirmed) | **direct** | direct when the placement is tagged; `first_placement_not_observed` only where both zones are in view throughout the window (apical partly visible in 10 of 13) |
| R8 Apical before sternal | per-paddle placements (derived, after the gate) and the zones | partly (one-zone inference only) | **direct** (both zones throughout) | partly (apical zone partly visible) |
| R3 Paddles firmly on chest before the shock | placement and the shock time; or inference from the shock on screen or removal | partly: Pass – Inferred from removal only; `placed_after_shock` can't be checked | **direct** | partly (shock seen in 9 of 13) |
| R4 Both buttons pressed | button press, placement; or inference | partly (pressed in 2 of 12; otherwise inferred from removal) | **direct** | **direct** |
| R5 Shock confirmed on screen | the screen | **unverifiable** | **direct** | partly |
| R6 Paddles removed after the shock | removal and the shock time | **unverifiable** (no shock time) | **direct** | partly |
| A5 Shock command | audio | from audio in any view (a timing tolerance, if approved, needs the shock time) | as LL | as LL |
| A1, A3 (before the shock), A2 (stage), A4 | audio and the shock time | **unverifiable** | **direct** | partly |
| R7/A6 Restart promptly, A8 pre-shock pause | audio and the shock time (the restart is the first start after the shock) | **unverifiable** | **direct** | partly |
| A7 Command sequence | A1–A5 results | **unverifiable** | **direct** | partly |

Annotation timelines contain no audio, so every audio rule is Unable to Verify on annotation
data in any view. The table describes the final system.

## Reading

- **LS** is the only view where every rule can be checked directly in most videos. It shows
  both placement zones throughout and the screen.
- **T** shows the screen in most interim videos, but not reliably (screen tracked in 19 of 48
  older videos). Its apical zone is often only partly in view.
- **LL** shows the apical zone throughout but never the sternal zone and almost never the
  screen. With no shock-time fallback, about half the rules become unverifiable from LL.

To be rerun on the final export, with the screen intervals the exporter now produces (D-094).
