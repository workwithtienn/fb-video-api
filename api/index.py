from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

def get_best_direct_url(url: str, audio_only: bool = False):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'geo_bypass': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
        },
        # Ép lấy format tốt nhất có url trực tiếp (HD nếu có, fallback SD)
        'format': 'bestaudio/best' if audio_only else 'bestvideo[ext=mp4]+bestaudio/best[ext=mp4]/best',
        'format_sort': ['res:720', 'res:480', 'ext:mp4'],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)

            # Facebook Reels hay để url ở formats thay vì info['url']
            if 'formats' in info:
                formats = info['formats']
                # Ưu tiên HD có url
                best = max(formats, key=lambda f: f.get('height', 0) or 0)
            else:
                best = info

            direct_url = best.get('url')
            if not direct_url:
                # Fallback lấy từ info nếu formats không có
                direct_url = info.get('url')

            if not direct_url:
                raise Exception("Không tìm thấy link tải trực tiếp")

            title = info.get('title', 'Facebook_Video')
            title = re.sub(r'[^\w\-_. ]', '_', title)[:120]
            ext = 'm4a' if audio_only else 'mp4'

            return direct_url, f"{title}.{ext}"

        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Không lấy được link: {str(e)}")

@app.get("/download/video")
async def download_video(url: str = Query(...)):
    direct_url, filename = get_best_direct_url(url, audio_only=False)
    
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Location": direct_url,
    }
    return RedirectResponse(url=direct_url, headers=headers)

@app.get("/download/audio")
async def download_audio(url: str = Query(...)):
    direct_url, filename = get_best_direct_url(url, audio_only=True)
    
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Location": direct_url,
    }
    return RedirectResponse(url=direct_url, headers=headers)

@app.get("/")
async def root():
    return {"message": "FB Reels / YouTube / TikTok Downloader - dùng /download/video?url=... (click là tải luôn)"}
