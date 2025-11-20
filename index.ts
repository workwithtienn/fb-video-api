import type { VercelRequest, VercelResponse } from '@vercel/node';

export default function (req: VercelRequest, res: VercelResponse) {
  res.json({
    status: "ok",
    message: "Social Media Downloader API v3 - Facebook, YouTube, TikTok",
    usage: {
      "Tải video trực tiếp": "/api/download?type=video&url=...",
      "Tải audio trực tiếp": "/api/download?type=audio&url=...",
      "JSON API video": "/api/download?type=json_video&url=...",
      "JSON API audio": "/api/download?type=json_audio&url=..."
    }
  });
}
