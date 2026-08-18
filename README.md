# AI Face Recognition Security System

Flutter + FastAPI application for registering known people and analyzing
persons from a laptop webcam or an uploaded video.

## Processing modes

| Mode | Input | Results | Persistence |
|---|---|---|---|
| Live surveillance | Laptop webcam/configured camera | Annotated frames, recognition status, logs and alerts | Sessions, meaningful detection events, confirmed unknown alerts, and alert snapshots are saved |
| Uploaded video | MP4, AVI, MOV, MKV or WebM | Progress, annotated frames, and temporary events | Nothing is written to surveillance history; the upload is deleted after processing |

Only one mode can run at a time so the demonstration does not run two heavy AI
pipelines concurrently.

## Project structure

```text
backend/                FastAPI, SQLite, YOLO/ByteTrack and InsightFace
app_flutter/            Flutter desktop/mobile client
scripts/                startup, smoke-test and verification helpers
beta_testing_files_02/  teammate presentation pipeline; not production code
docs/                   report and assignment documents
```

## Quick Start For Teammates

The recommended fresh-clone path is Docker because it installs the backend,
builds the Flutter web app, creates runtime volumes, and serves the app from
one command.

```powershell
git clone <repository-url>
cd AI_Surveillance_System
docker compose up --build
```

Open:

```text
http://localhost:8080
```

The backend API is available at:

```text
http://localhost:8000/health
http://localhost:8000/health/readiness
http://localhost:8000/docs
```

The first real registration or analysis request can be slow because InsightFace
and YOLO model assets may download into the Docker model volume.

## Prerequisites

- Python 3.12
- Flutter SDK
- Git
- Docker Desktop, for the recommended Docker setup
- Windows desktop: Visual Studio Desktop development tools
- macOS desktop: Xcode

## Local Install

From the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
cd app_flutter
flutter pub get
cd ..
```

macOS/Linux shell equivalent:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
cd app_flutter
flutter pub get
cd ..
```

InsightFace `buffalo_l` and the configured YOLO model load lazily. Their model
assets may download on the first real registration or analysis request. By
default, InsightFace is stored under `backend/models/insightface/` and YOLO is
stored at `backend/models/yolo/yolov8n.pt`:

```powershell
python -c "from backend.ai.embedding_manager import InsightFaceEmbeddingManager; InsightFaceEmbeddingManager()._get_app(); print('InsightFace ready')"
```

## Run

Open two PowerShell terminals at the project root.

Terminal 1:

```powershell
.\scripts\start_backend.ps1
```

Terminal 2:

```powershell
.\scripts\start_flutter.ps1
```

Manual equivalents:

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
cd app_flutter
flutter run -d windows --dart-define=BACKEND_URL=http://127.0.0.1:8000
```

Useful backend diagnostics:

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/health/readiness
http://127.0.0.1:8000/docs
```

The readiness endpoint verifies the SQLite schema and writable runtime
directories without loading or downloading AI models.

## Run With Docker

Install Docker Desktop, start it, then run from the project root:

```powershell
docker compose up --build
```

Then open:

```text
http://localhost:8080
```

The backend is also exposed directly at:

```text
http://localhost:8000/health
http://localhost:8000/docs
```

Docker Compose builds two services:

| Service | Purpose | Host port |
|---|---|---|
| `backend` | FastAPI API, SQLite, AI pipeline and uploaded-video analysis | `8000` |
| `frontend` | Flutter web app served by Nginx, with `/api` proxied to backend | `8080` |

Docker runtime settings are committed in
[`docker/backend.env`](docker/backend.env). The Compose file reads that file, so
teammates do not need to create a local `.env` before the first run. Important
defaults include unknown confirmation after 5 frames and restricted-zone
lingering after 5 seconds.

SQLite data, uploaded runtime files, and downloaded AI models are kept in Docker
volumes named `backend_database`, `backend_data`, and `backend_models`, so they
survive container restarts.

First real AI usage may take time because InsightFace and YOLO assets can be
downloaded inside the `backend_models` volume. Live webcam access from Docker is
host-dependent; uploaded-video analysis works without camera passthrough. If
webcam access is required and Docker cannot see the device, run the backend
locally with the manual command above.

Useful Docker commands:

```powershell
docker compose ps
docker compose logs -f backend
docker compose logs -f frontend
docker compose down
```

After pulling new code, rebuild containers:

```powershell
git pull
docker compose up --build
```

To reset all saved Docker data, including the SQLite database and downloaded
models:

```powershell
docker compose down -v
```

## First-time use

1. Start the backend and Flutter application.
2. Register known people from clear, single-face images.
3. Open **Surveillance**.
4. For webcam monitoring, select **Live webcam**. If the camera list is empty,
   click **Add laptop webcam**, then click **Start**.
5. For file analysis, select **Upload video** and choose a supported video.
6. Open **Persistent Logs & Alerts** to review live-webcam history. Uploaded
   video results intentionally never appear there.

## Persistence boundary

SQLite stores members, embeddings, camera configurations, live sessions,
detection logs, alerts, and zones. Runtime files are written below
`backend/data/` and the database defaults to `backend/database/app.db`.

Uploaded-video jobs have no database table. Their input, latest annotated frame,
progress and events are temporary. Completed results expire from memory after
the configured TTL (30 minutes by default).

## Configuration

Copy values from [backend/.env.example](backend/.env.example) into environment
variables as needed. Important options include:

- `BACKEND_HOST`, `BACKEND_PORT`, `CORS_ORIGINS`
- AI thresholds and model paths
- live unknown-confirmation and alert-cooldown settings
- uploaded-video maximum size, result TTL and maximum event count

The Flutter backend URL can be changed with:

```powershell
flutter run -d windows --dart-define=BACKEND_URL=http://HOST:PORT
```

## Verification

Run the complete automated checks:

```powershell
.\scripts\verify_project.ps1
```

With the backend already running, perform a non-mutating endpoint smoke test:

```powershell
python scripts\smoke_test.py
```

The smoke test reads health, readiness, member, camera, surveillance-status,
log, and alert endpoints. It never starts a camera, submits a video, or changes
database records.

## Troubleshooting

- **Backend is offline:** open `/health/readiness` and confirm its status is
  `ready`.
- **Laptop camera cannot open:** close applications currently using the webcam,
  confirm the camera source is `0`, and try again.
- **Live start returns HTTP 409:** cancel or wait for uploaded-video analysis.
- **Video upload returns HTTP 409:** stop live surveillance first.
- **First analysis is slow:** the AI assets may still be downloading or
  initializing.
- **No unknown alert appears immediately:** an unknown track must remain
  unknown for the configured confirmation-frame count.
