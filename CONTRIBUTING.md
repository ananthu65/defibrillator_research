# Working as a three-person research team

See [team boundaries](docs/team.md) and [handover contracts](docs/contracts.md)
before changing a shared interface. Folder ownership is a lead responsibility,
not a restriction on who may contribute.

1. Branch from the team's integration branch using `feature/<area>-<change>`.
2. Keep implementation changes in the owning folder. Models must not score
   criteria, rules must not load models, and the app must not duplicate rules.
3. Develop against `tests/fixtures/` and run `python -m unittest discover -s tests -v`.
   Install `requirements/charging-sound.txt` to include the synthetic classifier
   integration test. The GitHub workflow runs that test too.
4. Add a contract fixture and tests for new events/rules or an adapter's output.
   Record experiment config, metrics and dataset/split version when comparing models.
5. Open a PR with the change, verification and known limitations. One other
   member reviews it; shared schema changes involve the affected area leads.
6. Merge only after tests and review pass. Do not push directly to `main`.

The repository owner must enable GitHub branch protection with one required
approval and the `unit` status check. GitHub usernames were not supplied, so
no guessed CODEOWNERS handles or remote repository settings were created.

## Adding a model

Implement `Detector.detect(video) -> list[Event]` or
`SpeechModel.transcribe(audio) -> list[TranscriptSegment]` in your area. Charging
models implement `detect(audio) -> list[Event]`. Add its import path and default
options to `configs/models.yaml`, then select its key in `configs/pipeline.yaml`.
The registry and orchestration code do not need to change. Import heavy
dependencies inside the adapter so other developers can work without them.
These Python implementation paths are trusted repository configuration.

Model variants can be separate catalog entries pointing at the same adapter
with different weights/options. There is no fixed number of models in the code.
Compatible pre-downloaded checkpoints must exist before enabling a model.

## Adding or changing a rule

Implement a function in `rules/video_rules.py`, `rules/audio_rules.py`, or a
new module: `(timeline, rule_config) -> RuleResult`. Add its ID, implementation
path, parameters and definition source to `configs/rules.yaml`. Set its status
to `approved` only when the team has an agreed rule definition; otherwise the
engine returns `unable_to_assess`. `enabled: false` excludes an experimental
rule. Rule IDs and count are configuration-driven.

Use event IDs for evidence and named timestamps for timing decisions. The
engine rejects references to events outside the supplied timeline. Inference
must retain evidence and a reason; missing evidence must not become a pass.
The generic engine does not know clinical thresholds. Test changes using
annotation-derived timelines before model-generated timelines.

## Evolving the research

Add optional schema fields compatibly, document their units and add fixtures.
For a breaking change, introduce a new schema version and an explicit migration;
do not reinterpret old experiment files. Freeze split versions before comparing
models. Copy configs and use distinct run names for each experiment. Keep the
test set outside training and model selection. Rebuild the comparison CSV with
`python -m experiments.summarize` after combining experiment folders from PRs;
the per-run files are the source of truth.
