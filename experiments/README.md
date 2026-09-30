# Experiment records

Each run has `config.json`, `metrics.json`, `run.json`, and `plots/`.
`results_summary.csv` contains one row per run and a JSON metrics column so
video, ASR, and charging metrics can coexist without changing column meanings.
Run names must be unique; use a new name for a repeat experiment.

Video training, video evaluation, Whisper benchmarks, and charging training
use `experiments.record.record_experiment`. This is a single-writer local
recorder: do not run simultaneous writers against one experiments directory.
On branches, combine per-run folders and run `python -m experiments.summarize`
to rebuild the summary rather than manually reconciling CSV rows.

Existing Phase 5 results were imported with their original config and
reproducibility metadata intact. Their old paths are historical. The current
path map is in `../docs/reorganization.md`; new training configs use new paths.
Only aggregate plots are copied here. Frame previews, checkpoints, recordings,
and detailed private outputs remain under ignored `data/`.
