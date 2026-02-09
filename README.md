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

## Deploy to Render

### Option 1: Using Blueprint (Recommended)

1. The `render.yaml` file is already configured in this repo
2. Go to https://dashboard.render.com/blueprints
3. Click **New Blueprint** → Connect `JohnCarloGamayo/tiktok-downloader-backend-`
4. Branch: `main`, Blueprint Path: `render.yaml`
5. Click **Apply** and wait for deployment

### Option 2: Manual Setup

1. Create New Web Service on Render
2. Connect your GitHub repo
3. **Build Command**: `pip install -r requirements.txt`
4. **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. **Environment**: Python 3
6. Deploy

### After Deployment

- Copy your backend URL (e.g., `https://tiktok-backend-xxxxx.onrender.com`)
- Update frontend environment variable `VITE_API_BASE_URL` with this URL
- Render provides built-in ffmpeg support
