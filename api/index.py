from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
import re
import requests   # dùng requests đồng bộ cho ổn định trên Vercel

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

def get_video_info(url: str, audio_only: bool = False):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'bestaudio' if audio_only else 'bestvideo[ext=mp4]+bestaudio/best[ext=mp4]/best',
        'noplaylist': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            direct_url = info['url']
            title = info.get('title', 'video')
            title = re.sub(r'[^\w\-_. ]', '_', title)[:120]
            ext = 'm4a' if audio_only else 'mp4'
            return direct_url, title, ext
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Không lấy được link: {str(e)}")

# Endpoint chính - dùng cái này là tải luôn
@app.get("/")
async def main(url: str = Query(None), audio: str = "false"):
    if not url:
        return {"status": "ok", "message": "Thả link vào ?url=... nhé anh iu"}

    audio_only = audio.lower() in ("true", "1", "yes")

    try:
        direct_url, title, ext = get_video_info(url, audio_only)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"error": e.detail})

    # Stream bằng requests (ổn định nhất trên Vercel)
    def iterfile():
        with requests.get(direct_url, stream=True, timeout=30) as r:
            r.raise_for_status()
            for chunk in r.iter_content(chunk_size=1024*1024):
                if chunk:
                    yield chunk

    filename = f"{title}.{ext}"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Type": "video/mp4" if not audio_only else "audio/m4a",
    }

    return StreamingResponse(iterfile(), headers=headers, media_type="application/octet-stream")

# Giữ lại các endpoint cũ cho tương thích
@app.get("/download/video")
async def old_video(url: str = Query(...)):
    return await main(url=url, audio="false")

@app.get("/download/audio")
async def old_audio(url: str = Query(...)):
    return await main(url=url, audio="true")

@app.get("/api/video")
async def api_video(url: str = Query(...)):
    direct_url, title, _ = get_video_info(url, False)
    return {"success": True, "title": title, "url": direct_url}

@app.get("/api/audio")
async def api_audio(url: str = Query(...)):
    direct_url, title, _ = get_video_info(url, True)
    return {"success": True, "title": title, "url": direct_url}
