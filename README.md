# AI Face Recognition Security System

Flutter + FastAPI project for registering known people from face images. The
current working feature is image-based registration:

```text
name + face images
-> backend validates images
-> detects one face per image
-> saves cropped face images
-> extracts InsightFace embeddings
-> stores person/image/embedding records in SQLite
-> Flutter shows registered people
```

## Project Structure

```text
.
+-- backend/              # FastAPI, SQLite, AI registration pipeline
+-- app_flutter/          # Flutter desktop/mobile UI
+-- beta_testing_files/   # experimental notebooks/scripts only
+-- docs/                 # project guideline/report files
```

## What Is Implemented

- Register a person with multiple face images.
- Reject unreadable images, no-face images, and multiple-face images.
- Save cropped face images to `backend/data/known_faces/`.
- Save InsightFace `.npy` embeddings to `backend/data/embeddings/`.
- Store people and embedding paths in `backend/database/app.db`.
- Show registered people in Flutter.
- Delete registered people and their saved files.

Not implemented yet:

- live webcam recognition
- known/unknown matching
- alerts/logs connected to the backend

## Prerequisites

Install these before running the project:

- Python 3.12 recommended
- Flutter SDK
- Git
- Windows: Visual Studio with Desktop development tools for Windows if running
  the Flutter Windows app
- macOS: Xcode if running the Flutter macOS app

Check tools:

```bash
python --version
flutter doctor
git --version
```

## Clone

```bash
git clone <your-repo-url>
cd "Internship Project_v01"
```

If your folder has a different name, use that folder instead.

## Backend Setup

Run all backend commands from the project root, not from inside `backend/`.

### Windows PowerShell

```powershell
cd "D:\HomePage_D\Internship Project_v01"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then activate again.

### macOS Terminal

```bash
cd "/path/to/Internship Project_v01"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
```

## Download / Initialize InsightFace Model

The project uses InsightFace `buffalo_l`. The model is downloaded automatically
the first time this command runs:

### Windows PowerShell

```powershell
python -c "from backend.ai.embedding_manager import InsightFaceEmbeddingManager; InsightFaceEmbeddingManager()._get_app(); print('InsightFace buffalo_l ready')"
```

### macOS Terminal

```bash
python -c "from backend.ai.embedding_manager import InsightFaceEmbeddingManager; InsightFaceEmbeddingManager()._get_app(); print('InsightFace buffalo_l ready')"
```

Expected model location:

```text
backend/models/insightface/models/buffalo_l/
```

This folder is large and is ignored by Git.

## Run Backend

Keep this terminal open while using Flutter.

### Windows PowerShell

```powershell
cd "D:\HomePage_D\Internship Project_v01"
.\.venv\Scripts\Activate.ps1
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

### macOS Terminal

```bash
cd "/path/to/Internship Project_v01"
source .venv/bin/activate
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Health check:

```text
http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```

## Flutter Setup

Open a second terminal.

### Windows

```powershell
cd "D:\HomePage_D\Internship Project_v01\app_flutter"
flutter pub get
flutter run -d windows
```

### macOS

```bash
cd "/path/to/Internship Project_v01/app_flutter"
flutter pub get
flutter run -d macos
```

The Flutter app expects the backend at:

```text
http://127.0.0.1:8000
```

You can override it at build/run time:

```bash
flutter run -d windows --dart-define=BACKEND_URL=http://127.0.0.1:8000
```

On macOS:

```bash
flutter run -d macos --dart-define=BACKEND_URL=http://127.0.0.1:8000
```

## How To Use Current App

1. Start the backend.
2. Start Flutter.
3. Open the Register tab.
4. Enter a person name.
5. Choose face images.
6. Click Register.
7. Check accepted/rejected image feedback.
8. Confirm the person appears in Registered people or the Members tab.

Good registration images:

- one person per image
- clear face
- not blurry
- enough lighting
- face not too small

## Local Files Created At Runtime

These are generated locally and should not be committed:

```text
backend/database/app.db
backend/data/known_faces/
backend/data/embeddings/
backend/data/snapshots/
backend/models/
```

They are ignored in `.gitignore`.

## API Endpoints Currently Available

```text
GET    /health
POST   /members/register
GET    /members
GET    /members/{id}
DELETE /members/{id}
```

## Troubleshooting

### Flutter says backend is Offline

Make sure backend is running:

```text
http://127.0.0.1:8000/health
```

If this does not return `{"status":"ok"}`, restart the backend.

### Registration succeeds but Members tab looks stale

Open the Members tab or click the refresh button. The Register tab also has a
registered-people section that refreshes after successful registration.

### Model download fails

Run the model initialization command again. It downloads from the official
InsightFace release URL through the `insightface` package.

If a partial model folder exists, delete:

```text
backend/models/insightface/models/buffalo_l/
```

Then rerun the initialization command.

### Python package install fails on macOS

Make sure you are using a normal Python 3.12 environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r backend/requirements.txt
```

### Flutter desktop target is missing

Run:

```bash
flutter doctor
```

Then enable the platform if needed:

```bash
flutter config --enable-windows-desktop
flutter config --enable-macos-desktop
```

Use only the command for your OS.

## Developer Checks

Backend:

```bash
python -m compileall backend
```

Flutter:

```bash
cd app_flutter
flutter analyze
```
