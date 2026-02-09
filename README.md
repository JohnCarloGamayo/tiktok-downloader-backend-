# TikTok Downloader – Backend

FastAPI server that downloads TikTok videos via **yt-dlp** and returns them as MP4 or MP3 files.

## Features

- **Video Preview**: Get video info (title, author, thumbnail, stats) before downloading
- **Multiple Formats**: HD no watermark, with watermark, or MP3 audio only
- **Latest yt-dlp**: Automatically updated for TikTok compatibility

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

| Method | Endpoint         | Params / Body                                    | Response             |
|--------|------------------|--------------------------------------------------|----------------------|
| GET    | `/`              | —                                                | Health check         |
| GET    | `/api/info`      | `?url=<tiktok_url>`                             | Video info JSON      |
| POST   | `/api/info`      | `{ "url": "<tiktok_url>" }`                     | Video info JSON      |
| GET    | `/api/download`  | `?url=<tiktok_url>&format=<format>`            | MP4/MP3 file         |
| POST   | `/api/download`  | `{ "url": "<url>", "format": "<format>" }`     | MP4/MP3 file         |

**Download Formats:**
- `hd_no_watermark` - HD video without watermark (default)
- `with_watermark` - Standard video with watermark
- `mp3` - Audio only (MP3)

## Deploy (Railway / Render)

1. Push the `backend/` folder to a repo.
2. Set **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
3. Ensure `ffmpeg` is available (most Python hosting images include it, or add an apt package).

**Production Deployment:** https://web-production-14dc.up.railway.app
