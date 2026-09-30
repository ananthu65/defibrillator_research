# ARTS Defibrillation Assessment

Modular research workspace with separate ownership areas and configurable
model adapters. The previous assessment pipeline is archived in `legacy/`.

## Ownership and layout

| Folder | Owner | Purpose |
| --- | --- | --- |
| `configs/` | Shared | Model selection, experiment settings, pending rule definitions |
| `schemas/` | Shared | Event, transcript and rule-result handover formats |
| `annotation/` | Arnikan | CVAT audits, frames, grouped splits, validation and timeline conversion |
| `video/` | Ananth | Detectors, training, evaluation and detection postprocessing |
| `audio/` | Sanjeevan | Audio extraction, Whisper ASR, command observations and benchmarks |
| `audio/charging_sound/` | Sanjeevan | MFCC/random-forest training and event prediction; shared contributions |
| `pipeline/` | Ananth | Config-driven model registry, timeline merge and runner |
| `rules/` | Arnikan | New R1–R6 video and R7/A1–A7 audio rule implementations |
| `feedback/` | Sanjeevan | Feedback templates and rendering |
| `app/` | Sanjeevan | Small Streamlit recording upload and report viewer |
| `experiments/` | Shared | Per-run configs, metrics, aggregate plots and summary CSV |
| `tests/` | Shared | Unit and integration tests, synthetic timeline fixtures |
| `data/` | Local only | Recordings, datasets, checkpoints and run artifacts; only split text lists are tracked |
| `legacy/` | Archive | Previous pipeline, assumptions, tests and transcript-only rubric results |

## Quick start

Run from the repository root using Python 3.11 or newer. Activate the existing
`.venv` or create your own environment first.

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m pipeline.run --events tests/fixtures/sample_timeline.json
```

The last command writes `data/outputs/assessment.json`. It exercises the new
schema, timeline merge, rule handover and feedback flow without model downloads.
**All clinical rules currently return `unable_to_assess`**: their new definitions
and implementations are pending. Old timing assumptions are not reused.

## Model selection

Set adapter/checkpoint profiles in `configs/models.yaml`, select them in
`configs/pipeline.yaml`, and enable the
branches you need, then run:

```powershell
python -m pipeline.run --video data/video/example.mp4 --audio data/audio/example.wav
```

Detectors implement `detect(video) -> list[Event]`; speech models implement
`transcribe(audio) -> list[TranscriptSegment]`. YOLO and RT-DETR share the same
detector contract. Once profiles have compatible local checkpoints, switching
`video.model` selects the detector without changing pipeline code. Additional
profiles can reuse an adapter with different checkpoints/defaults. Faster R-CNN has an explicit
pending adapter. Whisper uses a local faster-whisper model directory.

Events have `event_name`, `start`, `end`, `source`, `confidence`, `evidence_type`
and `metadata`, plus camera angle, event ID and schema version. Rule results
include evidence IDs, timestamps and reasons. Times are seconds; audio/video
offsets are configurable. Agree recording synchronization before assessment.
Video object presence is not treated as correct paddle placement or proof of
a delivered shock. Agree semantic event mappings with the annotation and rules
owners. The detector adapter assumes constant-frame-rate video.

Install optional dependencies only for your area:

```powershell
python -m pip install -r requirements/video-training.txt
python -m pip install -r requirements/audio.txt
python -m pip install -r requirements/charging-sound.txt
python -m pip install -r requirements/app.txt
```

The video training requirements retain the existing CUDA 12.6 environment;
the core pipeline and tests do not require a GPU. The app starts with
`python -m streamlit run app/streamlit_app.py`.

## Existing work and experiments

- Annotation procedures: [annotation/guideline.md](annotation/guideline.md).
- YOLO training: [video/docs/phase5-local-training.md](video/docs/phase5-local-training.md).
- Charging-sound labeling and baseline: [audio/charging_sound/README.md](audio/charging_sound/README.md).
- Run format: [experiments/README.md](experiments/README.md).
- Old-to-new paths and implementation status: [docs/reorganization.md](docs/reorganization.md).
- Team responsibilities and boundaries: [docs/team.md](docs/team.md).
- Versioned handover formats: [docs/contracts.md](docs/contracts.md).
- Extension and PR workflow: [CONTRIBUTING.md](CONTRIBUTING.md).

The three completed Phase 5 experiments have been imported into `experiments/`.
Historical reports, configuration hashes and terminal transcripts are preserved.
Keep the P50_T quarantine and the existing participant-grouped split. Do not
use the official test set for model selection.

```powershell
python -m video.create_training_view
python -m video.train --config configs/video/yolov8n_preliminary.json
```

For another run, choose a new config `name`; completed runs cannot be overwritten.
The PowerShell launcher is now `video/run_training_logged.ps1`. Raw outputs and
weights stay under `data/`, while each new training/evaluation/benchmark run
writes its config and metrics to `experiments/<run>/` and updates the summary.
Whisper benchmark CSVs use `audio,reference` columns; run
`python -m audio.benchmark_whisper --manifest data/audio/benchmark.csv --name whisper_001`.

## Collaboration

Work on feature branches, get one other team member to review the PR, and
require passing GitHub Actions tests before merging. Do not push directly to
`main`. The workflow is in `.github/workflows/tests.yml`; repository branch
protection still needs to be configured in GitHub settings.

Keep recordings and model weights outside Git, using local `data/` or shared
Drive storage with paths in configs. Commit only text split lists from `data/`.
Charging-sound work is part of Sanjeevan's audio lead area under the latest
allocation; all members can contribute without changing module boundaries.
