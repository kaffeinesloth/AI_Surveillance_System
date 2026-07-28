# Shared AI Analysis Pipeline

The production backend uses one non-persistent frame-analysis engine for both
future input modes:

```text
BGR frame
→ YOLOv8 person detection + ByteTrack identity
→ person crop
→ InsightFace face detection + ArcFace embedding
→ in-memory gallery cosine matching
→ per-track recognition buffer
→ typed frame analysis
```

`FrameAnalysisEngine` never opens a database connection, saves a file, or
creates an alert. Later orchestration layers decide what happens to its result:

- Live webcam mode will persist selected logs, alerts, and snapshots.
- Uploaded-video mode will keep results temporary and non-persistent.

## Modules

| Module | Responsibility |
|---|---|
| `contracts.py` | Shared immutable inputs/results and adapter protocols |
| `person_tracker.py` | Lazy YOLOv8 + ByteTrack adapter |
| `face_recognizer.py` | Thread-safe in-memory gallery and InsightFace adapter |
| `recognition_buffer.py` | Independent recognition history for each `track_id` |
| `analysis_engine.py` | Shared frame pipeline and optional annotation |
| `embedding_manager.py` | Lazy InsightFace model and embedding extraction |

Construct a new `FrameAnalysisEngine` for each live or uploaded-video analysis
session so ByteTrack and recognition-buffer state cannot leak between sessions.
The heavy packages are imported or initialized only when real inference starts;
unit tests use lightweight test doubles.
