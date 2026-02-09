# TikTok Downloader – Backend

FastAPI server that downloads TikTok videos via **yt-dlp** and returns them as MP4 files.

## Prerequisites

- Python 3.10+
- [ffmpeg](https://ffmpeg.org/download.html) installed and available on your `PATH`

## Setup

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

## Run

```bash
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.

## API

| Method | Endpoint         | Params / Body                | Response      |
|--------|------------------|------------------------------|---------------|
| GET    | `/api/download`  | `?url=<tiktok_url>`         | MP4 file      |
| POST   | `/api/download`  | `{ "url": "<tiktok_url>" }` | MP4 file      |
| GET    | `/`              | —                            | Health check  |

## Deploy (Railway / Render)

1. Push the `backend/` folder to a repo.
2. Set **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
3. Ensure `ffmpeg` is available (most Python hosting images include it, or add an apt package).
