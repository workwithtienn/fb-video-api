from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
import re
import httpx
from typing import AsyncIterator

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

def get_media_info(url: str, audio_only: bool = False):
    """Lấy thông tin media từ URL"""
    base_opts = {
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 30,
        'retries': 5,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'Sec-Fetch-Mode': 'navigate',
        }
    }

    if audio_only:
        ydl_opts = {
            **base_opts,
            'format': 'bestaudio/best',
        }
    else:
        ydl_opts = {
            **base_opts,
            'format': 'best[ext=mp4]/best',
        }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            
            # Lấy URL tùy theo format
            if 'url' in info:
                direct_url = info['url']
            elif 'entries' in info and info['entries']:
                direct_url = info['entries'][0].get('url')
            elif 'formats' in info and info['formats']:
                # Lấy format tốt nhất
                best_format = info['formats'][-1]
                direct_url = best_format.get('url')
            else:
                direct_url = None
                
            title = info.get('title', 'media_file')
            safe_title = re.sub(r'[^\w\-_\. ]', '_', title)[:100]
            ext = info.get('ext', 'mp4' if not audio_only else 'm4a')
            
            return direct_url, safe_title, ext
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Không thể tải: {str(e)}")

async def stream_from_url(url: str) -> AsyncIterator[bytes]:
    """Stream nội dung từ URL"""
    async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes(chunk_size=1024 * 1024):  # 1MB chunks
                yield chunk

@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Social Media Downloader API - Hỗ trợ: Facebook, YouTube, TikTok",
        "endpoints": {
            "download_video": "/download/video?url=YOUR_URL",
            "download_audio": "/download/audio?url=YOUR_URL",
            "api_video": "/api/video?url=YOUR_URL",
            "api_audio": "/api/audio?url=YOUR_URL"
        },
        "docs": "/docs"
    }

@app.get("/download/video")
async def download_video(url: str = Query(..., description="Link video từ Facebook/YouTube/TikTok")):
    """Tải video trực tiếp - không chuyển hướng"""
    direct_url, title, ext = get_media_info(url, audio_only=False)
    
    if not direct_url:
        raise HTTPException(status_code=404, detail="Không tìm thấy URL video")
    
    filename = f"{title}.{ext}"
    
    return StreamingResponse(
        stream_from_url(direct_url),
        media_type="video/mp4",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )

@app.get("/download/audio")
async def download_audio(url: str = Query(..., description="Link video từ Facebook/YouTube/TikTok")):
    """Tải audio trực tiếp - không chuyển hướng"""
    direct_url, title, ext = get_media_info(url, audio_only=True)
    
    if not direct_url:
        raise HTTPException(status_code=404, detail="Không tìm thấy URL audio")
    
    filename = f"{title}.{ext}"
    
    return StreamingResponse(
        stream_from_url(direct_url),
        media_type="audio/mp4",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )

@app.get("/api/video")
async def api_video(url: str = Query(...)):
    """API trả về thông tin video"""
    direct_url, title, ext = get_media_info(url, audio_only=False)
    return {
        "success": True,
        "title": title,
        "download_url": direct_url,
        "extension": ext
    }

@app.get("/api/audio")
async def api_audio(url: str = Query(...)):
    """API trả về thông tin audio"""
    direct_url, title, ext = get_media_info(url, audio_only=True)
    return {
        "success": True,
        "title": title,
        "download_url": direct_url,
        "extension": ext
    }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "fb-video-api"}
