from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
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

def get_facebook_video_url(url: str, audio_only: bool = False):
    # Trick bypass Facebook 2025 - thêm header + cookie giả nhẹ + format mạnh
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'cookiefile': None,  # không cần file cookie thật
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        },
        'format': 'bestvideo[ext=mp4]+bestaudio/best' if not audio_only else 'bestaudio',
        # Force lấy format có url trực tiếp, ưu tiên HD, fallback SD (SD lúc nào cũng có)
        'format_sort': ['res:720', 'res:480', 'res', 'ext:mp4'],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            # Facebook hay trả url ở formats chứ không ở info['url']
            formats = info.get('formats', [info])
            best_format = None
            
            # Ưu tiên HD có url
            for f in sorted(formats, key=lambda x: x.get('height') or 0, reverse=True):
                if f.get('url') and 'fragment' not in f.get('protocol', ''):  # tránh dash fragment
                    best_format = f
                    break
            
            # Nếu không có HD thì lấy cái đầu tiên có url (SD - lúc nào cũng có)
            if not best_format:
                for f in formats:
                    if f.get('url'):
                        best_format = f
                        break

            if not best_format or not best_format.get('url'):
                raise Exception("Không tìm thấy link tải")

            direct_url = best_format['url']
            title = info.get('title', 'Facebook_Video')
            title = re.sub(r'[^\w\-_. ]', '_', title)[:100]
            ext = 'm4a' if audio_only else 'mp4'

            return direct_url, title, ext

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi: {str(e)}")

@app.get("/")
async def root():
    return {"message": "Dùng /download/video?url=... hoặc /download/audio?url=..."}

@app.get("/download/video")
async def download_video(url: str = Query(...)):
    direct_url, title, ext = get_facebook_video_url(url, audio_only=False)
    
    def stream():
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.facebook.com/',
            'Origin': 'https://www.facebook.com'
        }
        with requests.get(direct_url, stream=True, headers=headers, timeout=30) as r:
            r.raise_for_status()
            for chunk in r.iter_content(chunk_size=1024*1024):
                if chunk:
                    yield chunk

    headers = {
        "Content-Disposition": f'attachment; filename="{title}.mp4"',
        "Content-Type": "video/mp4",
        "Cache-Control": "no-cache",
    }
    return StreamingResponse(stream(), headers=headers, media_type="video/mp4")

@app.get("/download/audio")
async def download_audio(url: str = Query(...)):
    direct_url, title, ext = get_facebook_video_url(url, audio_only=True)
    
    def stream():
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.facebook.com/'
        }
        with requests.get(direct_url, stream=True, headers=headers, timeout=30) as r:
            r.raise_for_status()
            for chunk in r.iter_content(chunk_size=1024*1024):
                if chunk:
                    yield chunk

    headers = {
        "Content-Disposition": f'attachment; filename="{title}.m4a"',
        "Content-Type": "audio/m4a",
    }
    return StreamingResponse(stream(), headers=headers, media_type="audio/m4a")
