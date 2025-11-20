from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
import re
import requests

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

def get_direct_link(url: str, audio_only: bool = False):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'extract_flat': False,
        'format': 'bestaudio/best' if audio_only else 'bestvideo[ext=mp4]+bestaudio/best[ext=mp4]/best',
        'geo_bypass': True,
        # Trick 2025 để FB Reels public luôn lấy được link HD mà không cần cookie
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        },
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)

            # Lấy url trực tiếp tốt nhất
            if audio_only:
                formats = info.get('formats', [])
                best = max(formats, key=lambda f: f.get('abr', 0)) if formats else info
            else:
                best = info

            direct_url = best.get('url')
            if not direct_url:
                raise Exception("Không có link trực tiếp")

            title = info.get('title', 'video')
            title = re.sub(r'[^\w\-_. ]', '_', title)[:120]
            ext = 'm4a' if audio_only else 'mp4'

            return direct_url, title, ext
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Không lấy được link: {str(e)}")

@app.get("/download/video")
async def download_video(url: str = Query(...)):
    direct_url, title, ext = get_direct_link(url, audio_only=False)
    
    def stream():
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', 'Referer': 'https://facebook.com'}
        with requests.get(direct_url, stream=True, headers=headers, timeout=60) as r:
            r.raise_for_status()
            for chunk in r.iter_content(chunk_size=1024*1024):
                yield chunk

    headers = {
        "Content-Disposition": f'attachment; filename="{title}.mp4"',
        "Content-Type": "video/mp4",
    }
    return StreamingResponse(stream(), headers=headers)

@app.get("/download/audio")
async def download_audio(url: str = Query(...)):
    direct_url, title, ext = get_direct_link(url, audio_only=True)
    
    def stream():
        with requests.get(direct_url, stream=True, timeout=60) as r:
            r.raise_for_status()
            for chunk in r.iter_content(chunk_size=1024*1024):
                yield chunk

    headers = {
        "Content-Disposition": f'attachment; filename="{title}.m4a"',
        "Content-Type": "audio/m4a",
    }
    return StreamingResponse(stream(), headers=headers)

@app.get("/")
async def root():
    return {"message": "Dùng /download/video?url=... hoặc /download/audio?url=... (hỗ trợ FB Reels, YouTube, TikTok)"}
