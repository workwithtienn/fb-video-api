from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
import re
import uvicorn  # nếu chạy local

app = FastAPI(
    title="Social Media Downloader API",
    description="Tải video/audio từ Facebook, YouTube, TikTok",
    version="3.1 - Fixed FB Reels + Direct Download"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

def get_direct_url_and_info(url: str, audio_only: bool = False):
    base_opts = {
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 30,
        'retries': 10,
    }

    if audio_only:
        ydl_opts = {
            **base_opts,
            'format': 'bestaudio/best',
        }
    else:
        ydl_opts = {
            **base_opts,
            'format': '(bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best)[height>=720]/'
                      '(bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best)',  # ưu tiên HD, fallback SD
        }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            
            # Lấy format tốt nhất có url trực tiếp
            formats = info.get('formats', [info])
            best_format = None
            for f in reversed(formats):  # ưu tiên chất lượng cao trước
                if f.get('url') and f.get('vcodec') != 'none':  # có video và có url
                    best_format = f
                    break
            if not best_format:
                # fallback lấy url chính (thường là SD cho FB public)
                best_format = info

            direct_url = best_format.get('url') or info.get('url')
            if not direct_url:
                raise HTTPException(status_code=400, detail="Không tìm thấy link tải (có thể video private hoặc FB chặn)")

            title = info.get('title', 'Video') or 'Video'
            safe_title = re.sub(r'[^\w\-_\. ]', '_', title)[:150]

            return direct_url, safe_title, best_format.get('ext', 'mp4')
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Lỗi yt-dlp: {str(e)}")

@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "Social Media Downloader API v3.1 - Hỗ trợ FB, YT, TT",
        "usage_example": "https://fb-video-api-omega.vercel.app/?url=https://www.facebook.com/reel/123456"
    }

# Endpoint chung - dễ dùng nhất
@app.get("/")
async def download_or_api(url: str = Query(None, description="Link video"), audio: bool = Query(False, alias="audio")):
    if not url:
        return await root()
    
    direct_url, title, ext = get_direct_url_and_info(url, audio_only=audio)
    
    filename = f"{title}.{ 'm4a' if audio else 'mp4' }"

    async def stream_content():
        import aiohttp
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=600)) as session:
            async with session.get(direct_url) as resp:
                if resp.status != 200:
                    raise HTTPException(status_code=500, detail="Lỗi stream từ nguồn")
                async for chunk in resp.content.iter_chunked(1024 * 1024):
                    yield chunk

    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Type": "video/mp4" if not audio else "audio/m4a",
        "Accept-Ranges": "bytes",
    }

    return StreamingResponse(stream_content(), headers=headers, media_type="application/octet-stream")

# Giữ lại các endpoint cũ nếu bạn vẫn muốn dùng
@app.get("/download/video")
async def download_video_old(url: str = Query(..., description="Link video")):
    return await download_or_api(url=url, audio=False)

@app.get("/download/audio")
async def download_audio_old(url: str = Query(..., description="Link audio")):
    return await download_or_api(url=url, audio=True)

@app.get("/api/video")
async def api_video(url: str = Query(...)):
    direct_url, title, _ = get_direct_url_and_info(url, audio_only=False)
    return {"success": True, "title": title, "download_url": direct_url}

@app.get("/api/audio")
async def api_audio(url: str = Query(...)):
    direct_url, title, _ = get_direct_url_and_info(url, audio_only=True)
    return {"success": True, "title": title, "download_url": direct_url}

# Nếu chạy local
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
