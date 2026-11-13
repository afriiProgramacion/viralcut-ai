# ViralCut AI

AI short-form video factory: upload a long video, get vertical clips.

## Architecture

- `backend/` — FastAPI (Python) + SQLite + FFmpeg + faster-whisper + OpenCV.
- `frontend/` — React + Vite + TypeScript + Tailwind + React Query.

## Requirements

- Python 3.11+ (tested on 3.14)
- Node.js 18+
- FFmpeg on PATH

## Backend setup

```powershell
cd backend
python -m pip install -r requirements.txt
copy .env.example .env
# edit .env with API keys (optional for transcription)
```

## Frontend setup

```powershell
cd frontend
npm install
```

## Run (Windows)

Backend:
```powershell
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend:
```powershell
cd frontend
npm run dev
```

Open http://localhost:5173

## Environment variables

See `backend/.env.example`.

- `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`: optional, required for semantic analysis & metadata.
- Transcription runs locally with faster-whisper (no key).
- Video processing uses FFmpeg locally.

## Features

- Upload MP4/MOV/WebM, drag & drop, progress.
- AI analysis pipeline with real progress stages.
- Transcription (faster-whisper), semantic moment detection, viral scoring.
- Automatic reframing to 9:16 with face detection (OpenCV Haar) + centered fallback.
- Dynamic subtitles (burned) with presets.
- Clip library, filtering/sorting.
- Clip editor: trim, title, subtitles, style, re-export, download, ZIP.
- Settings UI for providers/keys.
- Project history, deletion, reprocessing.

## Tests

Backend:
```powershell
cd backend
python -m pytest
```

Frontend build:
```powershell
cd frontend
npm run build
```
