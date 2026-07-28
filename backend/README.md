# Face Security Backend

FastAPI backend for the face recognition security system.

See the root `README.md` for full Windows/macOS setup, model download, and
Flutter run instructions.

## Run

```powershell
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

The first implemented feature is image-based member registration:

- `POST /members/register`
- `GET /members`
- `GET /members/{id}`
- `DELETE /members/{id}`

Images are saved under `backend/data/known_faces/`. SQLite data is stored in
`backend/database/app.db`.
