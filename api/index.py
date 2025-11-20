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

def get_best_url(url: str, audio_only: bool = False):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'format': 'bestaudio' if audio_only else 'bestvideo[ext=mp4]+bestaudio/best[ext=mp4]/best',
        # Quan trọng: ép lấy format có url trực tiếp
        'format_sort': ['res:1080', 'ext:mp4', 'vcodec:^avc', 'acodec:^mp4a'] if not audio_only else [],
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
        # Fix lỗi Facebook trả url=None ở info cấp cao
        if 'url' not in info or not info['url']:
            # Lấy từ formats tốt nhất
            formats = info.get('formats', [])
            if not formats:
                formats = [info]
            best = max(formats, key=lambda x: x.get('height', 0) or 0)
            direct_url = best['url']
        else:
            direct_url = info['url']
            
        title = info.get('title', 'video')
        title = re.sub(r'[^\w\-_. ]', '_', title)[:120]
        ext = 'm4a' if audio_only else 'mp4'
        return direct_url, title, ext

@app.get("/download/video")
async def download_video(url: str = Query(...)):
    direct_url, title, ext = get_best_url(url, audio_only=False)
    
    def stream():
        with requests.get(direct_url, stream=True, timeout=30) as r:
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
    direct_url, title, ext = get_best_url(url, audio_only=True)
    
    def stream():
        with requests.get(direct_url, stream=True, timeout=30) as r:
            r.raise_for_status()
            for chunk in r.iter_content(chunk_size=1024*1024):
                yield chunk
                
    headers = {
        "Content-Disposition": f'attachment; filename="{title}.m4a"',
        "Content-Type": "audio/m4a",
    }
    return StreamingResponse(stream(), headers=headers)

# Bonus: trang chủ cho đẹp
@app.get("/")
async def root():
    return {"message": "FB/YT/TT Downloader - dùng /download/video?url=... hoặc /download/audio?url=..."}
