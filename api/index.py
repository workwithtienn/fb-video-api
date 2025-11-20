from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import re
import requests
from urllib.parse import quote

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

def get_direct_urls(original_url: str):
    # Bước 1: Chuyển sang mbasic để bypass login + dễ parse
    if "reel/" in original_url:
        reel_id = original_url.split("reel/")[1].split("?")[0]
        mbasic_url = f"https://mbasic.facebook.com/reel/{reel_id}"
    else:
        mbasic_url = original_url.replace("www.facebook.com", "mbasic.facebook.com").replace("web.facebook.com", "mbasic.facebook.com")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "sec-fetch-mode": "navigate",
    }

    try:
        r = requests.get(mbasic_url, headers=headers, timeout=30)
        r.raise_for_status()
        html = r.text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi tải trang: {str(e)}")

    # Parse HD trước
    hd_match = re.search(r'hd_src:"(https?://[^"]+)"', html)
    sd_match = re.search(r'sd_src:"(https?://[^"]+)"', html)

    direct_url = (hd_match or sd_match).group(1) if (hd_match or sd_match) else None
    if not direct_url:
        raise HTTPException(status_code=400, detail="Không tìm thấy link video (có thể private hoặc FB chặn tạm thời)")

    # Lấy title
    title_match = re.search(r"<title>(.*?)</title>", html, re.DOTALL)
    title = title_match.group(1).split(" | ")[0] if title_match else "Facebook_Video"
    title = re.sub(r'[^\w\-_. ]', '_', title)[:120]

    return direct_url, title

@app.get("/download/video")
async def download_video(url: str = Query(...)):
    direct_url, title = get_direct_urls(url)

    def stream():
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://mbasic.facebook.com/",
        }
        with requests.get(direct_url, stream=True, headers=headers, timeout=60) as r:
            r.raise_for_status()
            for chunk in r.iter_content(chunk_size=1024*1024):
                yield chunk

    headers = {
        "Content-Disposition": f'attachment; filename="{title}.mp4"',
        "Content-Type": "video/mp4",
    }
    return StreamingResponse(stream(), headers=headers, media_type="video/mp4")

@app.get("/download/audio")
async def download_audio(url: str = download_video):
    # Audio thì dùng video link luôn (Reels FB không có audio riêng, tải video rồi extract ở client nếu cần)
    # Hoặc anh muốn chỉ audio thì mình thêm ffmpeg sau, nhưng tạm để tải video như audio luôn (nhiều người vẫn dùng vậy)
    return await download_video(url=url)

@app.get("/")
async def root():
    return {"message": "Dùng /download/video?url=link_reel hoặc /download/audio?url=link_reel"}
