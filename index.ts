export default function handler() {
  return new Response(JSON.stringify({
    status: "ok",
    message: "Facebook • YouTube • TikTok Downloader API",
    endpoints: {
      "Tải video (click là tải luôn)": "/api/download?type=video&url=...",
      "Tải audio (m4a)": "/api/download?type=audio&url=...",
      "JSON link video": "/api/download?type=json_video&url=...",
      "JSON link audio": "/api/download?type=json_audio&url=..."
    }
  }, null, 2), {
    headers: { "Content-Type": "application/json" }
  });
}
