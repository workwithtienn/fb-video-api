from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
import re
import httpx
from typing import AsyncGenerator

app = FastAPI(
    title="Social Media Downloader API",
    description="Tải video/audio từ Facebook, YouTube, TikTok với streaming trực tiếp",
    version="4.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Length", "Content-Type"],
)

def get_video_info(url: str, audio_only: bool = False):
    """Lấy thông tin video từ URL"""
    base_opts = {
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 30,
        'retries': 5,
        'nocheckcertificate': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }

    if audio_only:
        ydl_opts = {
            **base_opts,
            'format': 'bestaudio/best',
        }
    else:
        ydl_opts = {
            **base_opts,
            'format': 'best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if not info:
                raise HTTPException(status_code=404, detail="Không thể lấy thông tin video")
            
            # Lấy URL tải trực tiếp
            direct_url = info.get('url')
            if not direct_url:
                # Thử lấy từ formats
                formats = info.get('formats', [])
                if formats:
                    direct_url = formats[-1].get('url')
            
            if not direct_url:
                raise HTTPException(status_code=404, detail="Không tìm thấy URL tải video")
            
            title = info.get('title', 'Video')
            safe_title = re.sub(r'[^\w\-_\. ]', '_', title)[:100]
            filesize = info.get('filesize') or info.get('filesize_approx')
            ext = info.get('ext', 'mp4')
            
            return {
                'url': direct_url,
                'title': safe_title,
                'filesize': filesize,
                'ext': ext
            }
    except yt_dlp.utils.DownloadError as e:
        raise HTTPException(status_code=400, detail=f"Lỗi tải video: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống: {str(e)}")

async def stream_from_url(url: str, chunk_size: int = 1024 * 1024) -> AsyncGenerator[bytes, None]:
    """Stream video từ URL nguồn"""
    async with httpx.AsyncClient(
        timeout=300.0,
        follow_redirects=True,
        verify=False
    ) as client:
        async with client.stream('GET', url) as response:
            if response.status_code >= 400:
                raise HTTPException(status_code=response.status_code, detail="Không thể tải video từ nguồn")
            
            async for chunk in response.aiter_bytes(chunk_size):
                yield chunk

@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Social Media Downloader API v4.0 - Tải trực tiếp video/audio",
        "endpoints": {
            "download_video": "/download/video?url=<link>",
            "download_audio": "/download/audio?url=<link>",
            "api_info": "/api/info?url=<link>",
        },
        "docs": "/docs",
        "supported": ["Facebook", "YouTube", "TikTok", "Instagram", "Twitter"]
    }

@app.get("/download/video")
async def download_video(url: str = Query(..., description="Link video từ Facebook/YouTube/TikTok")):
    """Tải video trực tiếp - không cần redirect"""
    info = get_video_info(url, audio_only=False)
    
    headers = {
        'Content-Disposition': f'attachment; filename="{info["title"]}.{info["ext"]}"',
        'Content-Type': f'video/{info["ext"]}',
    }
    
    if info.get('filesize'):
        headers['Content-Length'] = str(info['filesize'])
    
    return StreamingResponse(
        stream_from_url(info['url']),
        headers=headers,
        media_type=f'video/{info["ext"]}'
    )

@app.get("/download/audio")
async def download_audio(url: str = Query(..., description="Link video từ Facebook/YouTube/TikTok")):
    """Tải audio trực tiếp"""
    info = get_video_info(url, audio_only=True)
    
    ext = info.get('ext', 'm4a')
    if ext == 'mp4':
        ext = 'm4a'
    
    headers = {
        'Content-Disposition': f'attachment; filename="{info["title"]}.{ext}"',
        'Content-Type': f'audio/{ext}',
    }
    
    if info.get('filesize'):
        headers['Content-Length'] = str(info['filesize'])
    
    return StreamingResponse(
        stream_from_url(info['url']),
        headers=headers,
        media_type=f'audio/{ext}'
    )

@app.get("/api/info")
async def api_info(url: str = Query(..., description="Lấy thông tin video")):
    """Lấy thông tin video không tải"""
    info = get_video_info(url, audio_only=False)
    
    return {
        "success": True,
        "title": info['title'],
        "download_url": info['url'],
        "filesize": info.get('filesize'),
        "ext": info['ext']
    }

@app.get("/api/video")
async def api_video(url: str = Query(...)):
    """API tương thích cũ - trả về thông tin"""
    return await api_info(url)

@app.get("/api/audio")
async def api_audio(url: str = Query(...)):
    """API audio - trả về thông tin"""
    info = get_video_info(url, audio_only=True)
    
    return {
        "success": True,
        "title": info['title'],
        "download_url": info['url'],
        "filesize": info.get('filesize'),
        "ext": info.get('ext', 'm4a')
    }

@app.get("/{url:path}")
async def fallback_download(url: str):
    """Route fallback cho URL trực tiếp"""
    # Xử lý trường hợp người dùng gọi /https://facebook.com/...
    if url.startswith(('http://', 'https://')):
        full_url = url
    else:
        raise HTTPException(status_code=404, detail="URL không hợp lệ")
    
    info = get_video_info(full_url, audio_only=False)
    
    return {
        "success": True,
        "title": info['title'],
        "download_url": info['url'],
        "message": "Sử dụng endpoint /download/video để tải trực tiếp"
    }
