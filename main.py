import os
import uuid
import logging
from pathlib import Path
from typing import Optional, Literal

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

# Common headers for TikTok
TIKTOK_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.tiktok.com/",
}

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="TikTok Downloader API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class VideoInfoRequest(BaseModel):
    url: str


class DownloadRequest(BaseModel):
    url: str
    format: Literal["hd_no_watermark", "with_watermark", "mp3"] = "hd_no_watermark"


class VideoInfo(BaseModel):
    title: str
    author: str
    author_url: Optional[str] = None
    thumbnail: Optional[str] = None
    duration: Optional[int] = None
    duration_string: Optional[str] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    description: Optional[str] = None
    upload_date: Optional[str] = None
    video_url: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def validate_tiktok_url(url: str) -> None:
    """Validate that the URL is a TikTok link."""
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    valid_domains = ["tiktok.com", "vm.tiktok.com", "vt.tiktok.com"]
    if not any(domain in url for domain in valid_domains):
        raise HTTPException(
            status_code=400, 
            detail="Invalid TikTok URL. Please provide a valid TikTok video link."
        )


def format_duration(seconds: Optional[int]) -> Optional[str]:
    """Convert seconds to MM:SS or HH:MM:SS format."""
    if seconds is None:
        return None
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    if hours > 0:
        return f"{hours}:{mins:02d}:{secs:02d}"
    return f"{mins}:{secs:02d}"


def get_video_info(video_url: str) -> dict:
    """Extract video information without downloading."""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "http_headers": TIKTOK_HEADERS,
        "nocheckcertificate": True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            if info is None:
                raise ValueError("Could not extract video information")
            return info
    except Exception as e:
        logger.error("Failed to get video info: %s", e)
        raise


def download_video(video_url: str, download_format: str) -> Path:
    """Download a TikTok video with the specified format."""
    job_id = uuid.uuid4().hex[:12]
    
    # Base options
    ydl_opts = {
        "quiet": False,
        "no_warnings": False,
        "http_headers": TIKTOK_HEADERS,
        "retries": 3,
        "fragment_retries": 3,
        "nocheckcertificate": True,
    }
    
    if download_format == "mp3":
        output_template = str(DOWNLOAD_DIR / f"{job_id}.%(ext)s")
        ydl_opts.update({
            "outtmpl": output_template,
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        })
        expected_ext = ".mp3"
    elif download_format == "with_watermark":
        output_template = str(DOWNLOAD_DIR / f"{job_id}.%(ext)s")
        ydl_opts.update({
            "outtmpl": output_template,
            "format": "best[ext=mp4]/best",
            "merge_output_format": "mp4",
            "postprocessors": [
                {
                    "key": "FFmpegVideoConvertor",
                    "preferedformat": "mp4",
                }
            ],
        })
        expected_ext = ".mp4"
    else:  # hd_no_watermark
        output_template = str(DOWNLOAD_DIR / f"{job_id}.%(ext)s")
        ydl_opts.update({
            "outtmpl": output_template,
            "format": "best[ext=mp4]/best",
            "merge_output_format": "mp4",
            "postprocessors": [
                {
                    "key": "FFmpegVideoConvertor",
                    "preferedformat": "mp4",
                }
            ],
        })
        expected_ext = ".mp4"
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info("Downloading [%s]: %s", download_format, video_url)
            info = ydl.extract_info(video_url, download=True)
            if info is None:
                raise ValueError("Could not extract video information")
            
            filename = ydl.prepare_filename(info)
            final_path = Path(filename).with_suffix(expected_ext)
            original_path = Path(filename)
            
            if final_path.exists():
                return final_path
            elif original_path.exists():
                return original_path
            else:
                for f in DOWNLOAD_DIR.iterdir():
                    if f.name.startswith(job_id):
                        logger.info("Found file: %s", f)
                        return f
            
            raise FileNotFoundError("Downloaded file not found")
    except Exception as e:
        logger.error("Download error: %s", e)
        raise


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/")
def root():
    return {"status": "ok", "message": "TikTok Downloader API v2.0"}


@app.post("/api/info")
def get_info_post(body: VideoInfoRequest):
    """Get video information (POST)."""
    return _handle_info(body.url)


@app.get("/api/info")
def get_info_get(url: str = Query(..., description="TikTok video URL")):
    """Get video information (GET)."""
    return _handle_info(url)


def _handle_info(video_url: str) -> VideoInfo:
    validate_tiktok_url(video_url)
    
    try:
        info = get_video_info(video_url)
    except Exception as exc:
        error_msg = str(exc)
        logger.error("Info extraction failed: %s", error_msg)
        
        if "Unable to extract" in error_msg:
            detail = "Could not extract video info. The video might be private, deleted, or unavailable."
        elif "HTTP Error 404" in error_msg:
            detail = "Video not found. Please check if the URL is correct."
        elif "HTTP Error 403" in error_msg:
            detail = "Access denied. The video might be private or region-locked."
        else:
            detail = f"Failed to get video info: {error_msg}"
        
        raise HTTPException(status_code=500, detail=detail)
    
    thumbnail = info.get("thumbnail")
    if not thumbnail:
        thumbnails = info.get("thumbnails", [])
        if thumbnails:
            thumbnail = thumbnails[-1].get("url") if thumbnails else None
    
    duration = info.get("duration")
    
    return VideoInfo(
        title=info.get("title", "TikTok Video"),
        author=info.get("uploader", info.get("creator", "Unknown")),
        author_url=info.get("uploader_url", info.get("channel_url")),
        thumbnail=thumbnail,
        duration=duration,
        duration_string=format_duration(duration),
        view_count=info.get("view_count"),
        like_count=info.get("like_count"),
        comment_count=info.get("comment_count"),
        description=info.get("description", ""),
        upload_date=info.get("upload_date"),
        video_url=video_url,
    )


@app.post("/api/download")
def download_post(body: DownloadRequest):
    """Download a TikTok video (POST)."""
    return _handle_download(body.url, body.format)


@app.get("/api/download")
def download_get(
    url: str = Query(..., description="TikTok video URL"),
    format: str = Query("hd_no_watermark", description="Download format")
):
    """Download a TikTok video (GET)."""
    return _handle_download(url, format)


def _handle_download(video_url: str, download_format: str) -> FileResponse:
    validate_tiktok_url(video_url)
    
    valid_formats = ["hd_no_watermark", "with_watermark", "mp3"]
    if download_format not in valid_formats:
        download_format = "hd_no_watermark"
    
    try:
        file_path = download_video(video_url, download_format)
    except Exception as exc:
        error_msg = str(exc)
        logger.error("Download failed: %s", error_msg)
        
        if "Unable to extract" in error_msg:
            detail = "Could not extract video. The video might be private, deleted, or unavailable."
        elif "HTTP Error 404" in error_msg:
            detail = "Video not found. Please check if the URL is correct."
        elif "HTTP Error 403" in error_msg:
            detail = "Access denied. The video might be private or region-locked."
        else:
            detail = f"Failed to download: {error_msg}"
        
        raise HTTPException(status_code=500, detail=detail)
    
    if download_format == "mp3":
        media_type = "audio/mpeg"
        filename = "tiktok_audio.mp3"
    else:
        media_type = "video/mp4"
        filename = "tiktok_video.mp4"
    
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
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
