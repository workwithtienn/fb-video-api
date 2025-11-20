from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse, RedirectResponse
import re
import httpx
import urllib.parse

app = FastAPI(title="FB Video Downloader API")

async def get_video_urls(fb_url: str):
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        # Thêm headers giả lập mobile
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Fetch-Mode": "navigate",
        }
        
        # Dùng m.facebook.com để dễ parse hơn
        mobile_url = fb_url.replace("www.facebook.com", "m.facebook.com").replace("web.facebook.com", "m.facebook.com")
        if "fb.watch" in mobile_url:
            r = await client.get(fb_url, headers=headers)
            mobile_url = r.url.human_repr().replace("www.facebook.com", "m.facebook.com")

        resp = await client.get(mobile_url, headers=headers)
        html = resp.text

        # Tìm HD trước, không có thì SD
        hd_url = re.search(r'hd_src:"([^"]+)"', html)
        sd_url = re.search(r'sd_src:"([^"]+)"', html)

        video_url = None
        if hd_url:
            video_url = hd_url.group(1)
        elif sd_url:
            video_url = sd_url.group(1)

        # Decode URL (Facebook hay encode \u0025 thành %25 nhiều lớp)
        if video_url:
            video_url = urllib.parse.unquote(video_url)
            while "%" in video_url and "\\u" not in video_url:
                new_url = urllib.parse.unquote(video_url)
                if new_url == video_url:
                    break
                video_url = new_url

        title = re.search(r"<title>(.*?)</title>", html)
        title = title.group(1).replace(" | Facebook", "") if title else "Facebook Video"

        return video_url, title

@app.get("/")
async def root():
    return {"message": "FB Video Downloader API - Add ?url= or direct /your-fb-link"}

@app.get("/download")
async def download_page(url: str = None):
    if not url:
        return JSONResponse({"error": "Thêm ?url=https://... vào link nhé!"}, status_code=400)
    
    video_url, title = await get_video_urls(url)
    if not video_url:
        return JSONResponse({"success": false, "error": "Không tìm thấy video (có thể private quá mức hoặc Facebook chặn)"}, status_code=404)

    # Redirect thẳng để tải luôn (cách nhanh nhất + không tốn băng thông server)
    return RedirectResponse(url=video_url)

# Cách đẹp nhất: truy cập trực tiếp https://yourdomain.com/https://web.facebook.com/reel/123456
@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    # Nếu không bắt đầu bằng http → trả về hướng dẫn
    if not full_path.lower().startswith("http"):
        return JSONResponse({"success": false, "error": "Link phải bắt đầu bằng https://facebook.com hoặc fb.watch..."})

    decoded_url = urllib.parse.unquote(full_path)
    video_url, title = await get_video_urls(decoded_url)

    if not video_url:
        return JSONResponse({
            "success": False,
            "title": title,
            "message": "Video không public hoặc đã bị Facebook ẩn link trực tiếp"
        })

    # Trả về redirect tải luôn
    return RedirectResponse(url=video_url)
