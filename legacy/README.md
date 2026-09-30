# Archived assessment pipeline

The complete previous `assessment_pipeline/` is preserved here from main
commit `2c3508e921dfbd8f894cfb444c454afafd53ef8e` (Version 2 plus initial tests).
Its source files are unchanged. Old rule design documents are under `docs/`.
The earlier transcript-only rubric script and its saved JSON/CSV outputs are
under `audio_commands/`; these are historical results, not the new rule engine.

The active system must not import from this directory. Legacy imports still
refer to `assessment_pipeline`; to investigate the archived tests, install
their dependencies separately and run from this folder:

```powershell
..\.venv\Scripts\python.exe -m pytest assessment_pipeline/tests
```

Legacy tests are excluded from the new CI suite. The archived transcript
script retains its original path assumptions and is kept for reference.
Use the active `audio/` modules for new work.
