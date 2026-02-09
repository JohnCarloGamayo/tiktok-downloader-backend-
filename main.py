import os
import uuid
import shutil
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import yt_dlp

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DOWNLOAD_DIR = Path(__file__).resolve().parent / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tiktok-dl")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="TikTok Downloader API", version="1.0.0")

# CORS – allow the React dev server and common deploy origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],            # tighten for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class DownloadRequest(BaseModel):
    url: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def download_tiktok(video_url: str) -> Path:
    """Download a TikTok video using yt-dlp and return the file path."""
    job_id = uuid.uuid4().hex[:12]
    output_template = str(DOWNLOAD_DIR / f"{job_id}.%(ext)s")

    ydl_opts = {
        "outtmpl": output_template,
        # Try multiple format fallbacks
        "format": "best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "quiet": False,
        "no_warnings": False,
        "verbose": True,
        # Important for TikTok
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://www.tiktok.com/",
        },
        # Retry on errors
        "retries": 3,
        "fragment_retries": 3,
        # Don't check certificates (sometimes needed)
        "nocheckcertificate": True,
        # Extract flat to avoid playlist issues
        "extract_flat": False,
        # Post-process: ensure mp4 container via ffmpeg if needed
        "postprocessors": [
            {
                "key": "FFmpegVideoConvertor",
                "preferedformat": "mp4",
            }
        ],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info("Attempting to download: %s", video_url)
            info = ydl.extract_info(video_url, download=True)
            if info is None:
                raise ValueError("Could not extract video information")
            
            # yt-dlp may change the extension after postprocessing
            filename = ydl.prepare_filename(info)
            # Ensure we point to the actual mp4 file
            final_path = Path(filename).with_suffix(".mp4")
            
            # Also check the original filename
            original_path = Path(filename)
            
            if final_path.exists():
                return final_path
            elif original_path.exists():
                return original_path
            else:
                # Fallback: look for any file that matches the job_id
                for f in DOWNLOAD_DIR.iterdir():
                    if f.name.startswith(job_id):
                        logger.info("Found file: %s", f)
                        return f
                        
            raise FileNotFoundError("Downloaded file not found")
    except Exception as e:
        logger.error("yt-dlp error: %s", e)
        raise


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/")
def root():
    return {"status": "ok", "message": "TikTok Downloader API is running"}


@app.post("/api/download")
def download_post(body: DownloadRequest):
    """Download a TikTok video (POST with JSON body)."""
    return _handle_download(body.url)


@app.get("/api/download")
def download_get(url: str = Query(..., description="TikTok video URL")):
    """Download a TikTok video (GET with query parameter)."""
    return _handle_download(url)


def _handle_download(video_url: str) -> FileResponse:
    # Accept various TikTok URL formats including vm.tiktok.com short links
    if not video_url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    valid_domains = ["tiktok.com", "vm.tiktok.com", "vt.tiktok.com"]
    if not any(domain in video_url for domain in valid_domains):
        raise HTTPException(status_code=400, detail="Invalid TikTok URL. Please provide a valid TikTok video link.")

    try:
        file_path = download_tiktok(video_url)
    except Exception as exc:
        error_msg = str(exc)
        logger.error("Download failed: %s", error_msg)
        
        # Provide more helpful error messages
        if "Unable to extract" in error_msg:
            detail = "Could not extract video. The video might be private, deleted, or TikTok is blocking the request. Please try again later."
        elif "HTTP Error 404" in error_msg:
            detail = "Video not found. Please check if the URL is correct."
        elif "HTTP Error 403" in error_msg:
            detail = "Access denied. The video might be private or region-locked."
        else:
            detail = f"Failed to download video: {error_msg}"
        
        raise HTTPException(status_code=500, detail=detail)

    return FileResponse(
        path=str(file_path),
        media_type="video/mp4",
        filename="tiktok_video.mp4",
        headers={"Content-Disposition": 'attachment; filename="tiktok_video.mp4"'},
    )


# ---------------------------------------------------------------------------
# Cleanup old files on startup (optional)
# ---------------------------------------------------------------------------
@app.on_event("startup")
def cleanup_downloads():
    """Remove leftover files from previous runs."""
    for f in DOWNLOAD_DIR.iterdir():
        try:
            f.unlink()
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Run with: uvicorn main:app --reload
# ---------------------------------------------------------------------------
