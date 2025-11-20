import type { VercelRequest, VercelResponse } from '@vercel/node';

export default function handler(req: VercelRequest, res: VercelResponse) {
  res.status(200).json({
    status: "ok",
    message: "Social Media Downloader API v3 - Hỗ trợ Facebook, YouTube, TikTok",
    docs: "/api/video?url=..."
  });
}
