from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
import re

app = FastAPI(
    title="Social Media Downloader API",
    description="Tải video/audio từ Facebook, YouTube, TikTok",
    version="3.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

def get_direct_url(url: str, audio_only: bool = False):
    base_opts = {
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 30,
        'retries': 3,
    }
    
    if audio_only:
        ydl_opts = {
            **base_opts,
            'format': 'bestaudio/best',
        }
    else:
        ydl_opts = {
            **base_opts,
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            direct_url = info.get('url')
            title = info.get('title', 'Facebook Video')
            safe_title = re.sub(r'[^\w\-_\. ]', '_', title)[:100]
            return direct_url, safe_title
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"yt-dlp error: {str(e)}")

@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Social Media Downloader API - Hỗ trợ: Facebook, YouTube, TikTok",
        "docs": "/docs"
    }

@app.get("/download/video")
async def download_video(url: str = Query(..., description="Link video từ Facebook/YouTube/TikTok")):
    direct_url, title = get_direct_url(url, audio_only=False)
    return RedirectResponse(url=direct_url)

@app.get("/download/audio")
async def download_audio(url: str = Query(..., description="Link video từ Facebook/YouTube/TikTok")):
    direct_url, title = get_direct_url(url, audio_only=True)
    return RedirectResponse(url=direct_url)

@app.get("/api/video")
async def api_video(url: str = Query(...)):
    direct_url, title = get_direct_url(url, audio_only=False)
    return {
        "success": True,
        "title": title,
        "download_url": direct_url
    }

@app.get("/api/audio")
async def api_audio(url: str = Query(...)):
    direct_url, title = get_direct_url(url, audio_only=True)
    return {
        "success": True,
        "title": title,
        "download_url": direct_url
    }
