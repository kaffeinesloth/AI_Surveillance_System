# Face Security Backend

FastAPI backend for member registration, live webcam surveillance, persistent
live logs/alerts, and temporary uploaded-video analysis.

## Recommended Docker Run

From the repository root:

```powershell
docker compose up --build
```

This starts the FastAPI backend on `http://localhost:8000` and the Flutter web
client on `http://localhost:8080`. Runtime database, data, and model files are
stored in Docker volumes so a fresh clone does not need manual directory setup.

## Install

Run commands from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
```

macOS/Linux shell equivalent:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
```

For development and API tests:

```powershell
python -m pip install -r backend/requirements-dev.txt
```

## Configure

Configuration uses environment variables. See `backend/.env.example` for all
supported names and defaults. Relative configured paths are resolved from the
`backend/` directory.

The backend creates its required runtime directories during application
startup. By default:

```text
backend/database/app.db
backend/data/known_faces/
backend/data/embeddings/
backend/data/snapshots/
backend/data/test_videos/
backend/data/temp_uploads/
```

## Run

Use the single application entry point:

```powershell
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Health check:

```text
GET http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```

## Current API

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Backend health check |
| GET | `/health/readiness` | Check database schema, runtime storage, AI asset state, and active workers |
| POST | `/members/register` | Register a member using multipart `name` and `images` fields |
| GET | `/members` | List registered members |
| GET | `/members/{id}` | Get a member and saved face images |
| DELETE | `/members/{id}` | Delete a member and associated local files |
| POST | `/cameras` | Create a camera configuration |
| GET | `/cameras` | List active cameras |
| GET | `/cameras/{id}` | Get one camera configuration |
| PATCH | `/cameras/{id}` | Update or reactivate a camera |
| DELETE | `/cameras/{id}` | Soft-deactivate a camera |
| POST | `/cameras/{id}/test` | Test the source and return frame dimensions |
| GET | `/cameras/{id}/snapshot` | Return a non-persistent JPEG preview |
| POST | `/surveillance/start` | Start the live worker for one active camera |
| POST | `/surveillance/stop` | Stop the current live worker |
| GET | `/surveillance/status` | Get live state, FPS, and processed-frame count |
| GET | `/surveillance/latest` | Get the latest typed recognition results |
| GET | `/surveillance/frame` | Get the latest annotated JPEG frame |
| GET | `/logs` | List persistent live detection logs |
| GET | `/logs/latest` | Get the latest persistent live log |
| GET | `/alerts` | List persistent live alerts |
| GET | `/alerts/latest` | Get the latest persistent live alert |
| GET | `/alerts/{id}` | Get one alert |
| PATCH | `/alerts/{id}/read` | Mark an alert read or unread |
| GET | `/alerts/{id}/snapshot` | Return the saved alert JPEG |
| POST | `/video-analysis` | Submit a temporary uploaded-video job |
| GET | `/video-analysis/{job_id}/status` | Get progress and processing state |
| GET | `/video-analysis/{job_id}/results` | Get temporary partial/final events |
| GET | `/video-analysis/{job_id}/frame` | Get the latest annotated temporary frame |
| DELETE | `/video-analysis/{job_id}` | Cancel/delete a temporary job |

The member routes intentionally preserve the contract used by the Flutter
application. They must not be renamed to `/enroll/`.

Camera deletion is intentionally a soft deactivation. This hides the camera
from the default active list while preserving references from historical live
sessions. Use `GET /cameras?include_inactive=true` to include deactivated
cameras, and `PATCH /cameras/{id}` with `{"is_active": true}` to reactivate one.

Camera testing and snapshots open the configured source only long enough to
read a frame and always release it afterward. Snapshot previews are returned
directly as JPEG bytes and are not stored in SQLite or the snapshot directory.
Preview and test endpoints reject a camera while it is owned by live
surveillance.

## Live-surveillance lifecycle

Only one live camera worker runs at a time. Starting surveillance creates a
`surveillance_sessions` record, loads the current member gallery, opens the
configured camera, and processes frames with the shared AI engine. Stopping the
worker releases the camera and records its final status, frame count, FPS, and
end time.

The latest annotated frame and analysis result are held in memory for Flutter
polling.

## Persistent live events

Live surveillance writes meaningful state events rather than one database row
for every processed frame:

- A known member is logged when that track first becomes known or changes
  identity.
- A possible unknown person must remain unknown for the configured number of
  frames before it is logged and creates an alert.
- Repeated alerts for the same unknown track are limited by a configurable
  cooldown.
- Unknown restricted-zone lingering alerts are created after the configured
  dwell time, 5 seconds by default.
- Low-quality/no-face frames do not create false unknown logs.
- Confirmed unknown alerts save the annotated frame under
  `backend/data/snapshots/`.

These rules apply only to the live worker. Uploaded-video processing calls the
shared AI engine directly and does not create database logs, alerts, sessions,
or persistent snapshots.

## Temporary uploaded-video analysis

Uploaded videos are copied to `backend/data/temp_uploads/` while a background
job processes them. Flutter can poll job status, temporary events, and the
latest annotated frame. The uploaded file is deleted automatically when the
job completes, fails, or is cancelled.

Temporary results remain in server memory for a configurable TTL (30 minutes
by default) or until the delete endpoint is called. They are explicitly marked
with `"persistent": false`.

Live surveillance and uploaded-video analysis are mutually exclusive so the
demo does not run two heavy model pipelines concurrently. Uploaded-video
analysis never inserts rows into `surveillance_sessions`, `detection_logs`, or
`alerts`.

## Database persistence boundary

SQLite schema version 2 contains:

| Table | Purpose |
|---|---|
| `people` | Registered members |
| `face_embeddings` | Registered face-image and embedding references |
| `cameras` | Webcam or future stream-source configuration |
| `surveillance_sessions` | Persistent live-camera sessions only |
| `detection_logs` | Persistent events produced by live surveillance |
| `alerts` | Persistent live alerts and snapshot references |
| `zones` | Camera-specific restricted-area polygons |

Uploaded-video analysis is intentionally non-persistent. It has no job, video,
session, detection, or alert table. Uploaded files and analysis results stay
in temporary storage only.

## Shared AI engine

`backend/ai/analysis_engine.py` provides the shared, non-persistent frame
pipeline used by both processing modes. It combines YOLOv8 + ByteTrack
person tracks with InsightFace gallery matching and an independent recognition
buffer for each track.

The engine returns typed frame results and optionally draws an annotated frame.
It does not access SQLite, save snapshots, or decide whether results are
persistent. Those responsibilities belong to the live and uploaded-video
orchestrators.

## Test

Backend API and member-service tests do not load or download InsightFace:

```powershell
python -m unittest discover -s backend/tests -v
```

Additional checks:

```powershell
python -m compileall backend
cd app_flutter
flutter analyze
```

## AI model loading

Read-only member requests and health checks do not initialize face-detection or
embedding models. Registration initializes the required AI components lazily
only after basic request validation succeeds.

InsightFace `buffalo_l` is downloaded by InsightFace the first time a real
embedding extraction requires it. Unit tests use test doubles and do not
download this model.
