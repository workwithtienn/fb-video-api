export default function handler(req: any, res: any) {
  res.status(200).json({
    status: "ok",
    message: "Social Media Downloader API v3 - Hỗ trợ Facebook, YouTube, TikTok",
    docs: "/api/video?url=..."
  });
}
