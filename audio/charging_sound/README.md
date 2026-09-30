# Charging sound — Sanjeevan (audio lead), shared contributions

This is an untrained baseline: one-second windows every 0.5 seconds, 13 MFCC
means plus 13 standard deviations, and a balanced random forest. At least
three consecutive positive windows make one event (configurable). It emits
the shared `charging_sound` event; no clinical rule is inferred from that event.

1. Review each complete WAV recording and label every charging interval in
   Audacity. Export TSV rows `start<TAB>end<TAB>charging`; an empty file means
   a fully reviewed negative recording. Convert MP3s to WAV before use.
2. Create a local CSV with columns `participant_id,audio,labels`. Audio and
   label paths are relative to the CSV. Use participant IDs from the frozen
   `data/splits/phase3/*_sets.txt` lists. Windows with at least 50% positive
   interval coverage are labeled positive; incomplete trailing windows are omitted.
3. Install `python -m pip install -r requirements/charging-sound.txt`.
4. Run:

```powershell
python -m audio.charging_sound.train --manifest data/audio/charging/manifest.csv --name charging_rf_001
```

Only train participants fit the model. Validation participants supply event
precision, recall, false-alarm count and matched-event mean start-time error
(one-to-one greedy matching, IoU >= 0.1). Test audio and labels are not read.
All camera recordings of one participant must have the same split.

The model is saved under `data/weights/audio/` and run metadata under
`experiments/<name>/`. Enable `charging_sound` in `configs/pipeline.yaml` to
use it. Load only your own trusted joblib models. There is no trained classifier
or real-data performance claim yet. YAMNet is a later alternative, not implemented.
