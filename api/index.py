from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
import re
import httpx
from urllib.parse import urlparse, parse_qs

app = FastAPI(
    title="Social Media Downloader API",
    description="Tải video/audio từ Facebook, YouTube, TikTok",
    version="3.1"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Type", "Content-Length"],
)

def get_media_info(url: str, audio_only: bool = False):
    """Lấy thông tin media từ URL"""
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
        # Ưu tiên format có cả video+audio, fallback về best
        ydl_opts = {
            **base_opts,
            'format': 'best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
        }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Lấy URL trực tiếp
            direct_url = info.get('url')
            
            # Nếu không có URL, thử lấy từ formats
            if not direct_url and 'formats' in info:
                formats = info['formats']
                if formats:
                    # Lấy format cuối cùng (thường là best)
                    direct_url = formats[-1].get('url')
            
            if not direct_url:
                raise HTTPException(status_code=400, detail="Không thể lấy URL download")
            
            # Làm sạch title
            title = info.get('title', 'video')
            safe_title = re.sub(r'[^\w\-_\. ]', '_', title)[:100]
            
            # Xác định extension
            ext = info.get('ext', 'mp4' if not audio_only else 'm4a')
            
            return {
                'url': direct_url,
                'title': safe_title,
                'ext': ext
            }
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Lỗi xử lý: {str(e)}")

async def stream_file(url: str, filename: str):
    """Stream file từ URL với chunks"""
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
            async with client.stream('GET', url) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    yield chunk
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi tải file: {str(e)}")

@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Social Media Downloader API - Hỗ trợ: Facebook, YouTube, TikTok",
        "endpoints": {
            "video": "/download/video?url=<VIDEO_URL>",
            "audio": "/download/audio?url=<VIDEO_URL>",
            "api_video": "/api/video?url=<VIDEO_URL>",
            "api_audio": "/api/audio?url=<VIDEO_URL>"
        },
        "docs": "/docs"
    }

@app.get("/download/video")
async def download_video(url: str = Query(..., description="Link video từ Facebook/YouTube/TikTok")):
    """Tải video trực tiếp - tự động download"""
    media_info = get_media_info(url, audio_only=False)
    
    filename = f"{media_info['title']}.{media_info['ext']}"
    
    return StreamingResponse(
        stream_file(media_info['url'], filename),
        media_type="video/mp4",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache"
        }
    )

@app.get("/download/audio")
async def download_audio(url: str = Query(..., description="Link video từ Facebook/YouTube/TikTok")):
    """Tải audio trực tiếp - tự động download"""
    media_info = get_media_info(url, audio_only=True)
    
    filename = f"{media_info['title']}.{media_info['ext']}"
    
    return StreamingResponse(
        stream_file(media_info['url'], filename),
        media_type="audio/mp4",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache"
        }
    )

@app.get("/api/video")
async def api_video(url: str = Query(...)):
    """API trả về thông tin video"""
    media_info = get_media_info(url, audio_only=False)
    
    return {
        "success": True,
        "title": media_info['title'],
        "download_url": media_info['url'],
        "ext": media_info['ext']
    }

@app.get("/api/audio")
async def api_audio(url: str = Query(...)):
    """API trả về thông tin audio"""
    media_info = get_media_info(url, audio_only=True)
    
    return {
        "success": True,
        "title": media_info['title'],
        "download_url": media_info['url'],
        "ext": media_info['ext']
    }

# Health check endpoint
@app.get("/health")
def health():
    return {"status": "healthy", "service": "media-downloader"}
