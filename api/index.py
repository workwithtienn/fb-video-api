from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
import re

app = FastAPI(
    title="Social Media Downloader API",
    description="Tải video/audio từ Facebook, YouTube, TikTok",
    version="3.2"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Location"],
)

def get_media_info(url: str, audio_only: bool = False):
    """Lấy thông tin media từ URL"""
    base_opts = {
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 15,
        'retries': 2,
        'no_check_certificate': True,
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
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Lấy URL trực tiếp
            direct_url = info.get('url')
            
            # Fallback: tìm trong formats
            if not direct_url and 'formats' in info:
                formats = [f for f in info['formats'] if f.get('url')]
                if formats:
                    direct_url = formats[-1]['url']
            
            # Fallback: requested_formats (cho video+audio merge)
            if not direct_url and 'requested_formats' in info:
                requested = info['requested_formats']
                if requested and len(requested) > 0:
                    direct_url = requested[0].get('url')
            
            if not direct_url:
                raise HTTPException(status_code=400, detail="Không tìm thấy URL download")
            
            # Làm sạch title
            title = info.get('title', 'video')
            safe_title = re.sub(r'[^\w\-_\. ]', '_', title)[:80]
            
            # Xác định extension
            ext = info.get('ext', 'mp4' if not audio_only else 'm4a')
            
            return {
                'url': direct_url,
                'title': safe_title,
                'ext': ext
            }
            
    except yt_dlp.utils.DownloadError as e:
        raise HTTPException(status_code=400, detail=f"Không thể tải: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi: {str(e)}")

@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Social Media Downloader API",
        "usage": {
            "download_video": "/download/video?url=YOUR_VIDEO_URL",
            "download_audio": "/download/audio?url=YOUR_VIDEO_URL",
            "get_info": "/api/video?url=YOUR_VIDEO_URL"
        },
        "docs": "/docs"
    }

@app.get("/download/video")
def download_video(url: str = Query(..., description="Link video")):
    """Tải video - redirect với download header"""
    media_info = get_media_info(url, audio_only=False)
    
    filename = f"{media_info['title']}.{media_info['ext']}"
    download_url = media_info['url']
    
    # Trả về HTML tự động trigger download
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Đang tải xuống...</title>
        <script>
            window.location.href = "{download_url}";
        </script>
    </head>
    <body>
        <h2>Đang chuyển hướng đến file tải xuống...</h2>
        <p>Nếu không tự động tải, <a href="{download_url}" download="{filename}">click vào đây</a></p>
    </body>
    </html>
    """
    
    return Response(
        content=html_content,
        media_type="text/html",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Refresh": f'0; url={download_url}'
        }
    )

@app.get("/download/audio")
def download_audio(url: str = Query(..., description="Link video")):
    """Tải audio - redirect với download header"""
    media_info = get_media_info(url, audio_only=True)
    
    filename = f"{media_info['title']}.{media_info['ext']}"
    download_url = media_info['url']
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Đang tải xuống...</title>
        <script>
            window.location.href = "{download_url}";
        </script>
    </head>
    <body>
        <h2>Đang chuyển hướng đến file tải xuống...</h2>
        <p>Nếu không tự động tải, <a href="{download_url}" download="{filename}">click vào đây</a></p>
    </body>
    </html>
    """
    
    return Response(
        content=html_content,
        media_type="text/html",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Refresh": f'0; url={download_url}'
        }
    )

@app.get("/api/video")
def api_video(url: str = Query(...)):
    """API trả về thông tin video"""
    try:
        media_info = get_media_info(url, audio_only=False)
        return {
            "success": True,
            "title": media_info['title'],
            "download_url": media_info['url'],
            "ext": media_info['ext']
        }
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"success": False, "error": e.detail}
        )

@app.get("/api/audio")
def api_audio(url: str = Query(...)):
    """API trả về thông tin audio"""
    try:
        media_info = get_media_info(url, audio_only=True)
        return {
            "success": True,
            "title": media_info['title'],
            "download_url": media_info['url'],
            "ext": media_info['ext']
        }
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"success": False, "error": e.detail}
        )

@app.get("/direct/video")
def direct_video(url: str = Query(...)):
    """Redirect trực tiếp đến video"""
    media_info = get_media_info(url, audio_only=False)
    return Response(
        status_code=302,
        headers={"Location": media_info['url']}
    )

@app.get("/direct/audio")
def direct_audio(url: str = Query(...)):
    """Redirect trực tiếp đến audio"""
    media_info = get_media_info(url, audio_only=True)
    return Response(
        status_code=302,
        headers={"Location": media_info['url']}
    )

@app.get("/health")
def health():
    return {"status": "healthy"}
