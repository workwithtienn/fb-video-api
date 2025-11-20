import YTDlpWrap from 'yt-dlp-wrap';

const ytDlp = new YTDlpWrap();

export default async function handler(req: Request) {
  const url = new URL(req.url).searchParams.get("url");
  const type = new URL(req.url).searchParams.get("type") || "video";

  if (!url) {
    return new Response(JSON.stringify({ error: "Thiếu url" }), {
      status: 400,
      headers: { "Content-Type": "application/json" }
    });
  }

  try {
    const infoJson = await ytDlp.execPromise([url, "-j"]);
    const info = JSON.parse(infoJson);

    const cleanTitle = (info.title || "media")
      .replace(/[<>:"/\\|?*]/g, "_")
      .substring(0, 100);

    // JSON API
    if (type === "json_video" || type === "json_audio") {
      const isAudio = type === "json_audio";
      const format = isAudio
        ? info.formats?.find((f: any) => f.acodec !== "none" && f.vcodec === "none") || info
        : info.formats?.reverse().find((f: any) => f.vcodec !== "none") || info;

      return Response.json({
        success: true,
        title: info.title || "Unknown",
        download_url: format.url || null
      });
    }

    // Tải trực tiếp video/audio
    const isAudio = type === "audio";
    const format = isAudio
      ? info.formats?.find((f: any) => f.acodec !== "none" && f.vcodec === "none") || info
      : info.formats?.reverse().find((f: any) => f.vcodec !== "none") || info;

    if (!format.url) throw new Error("Không tìm thấy link trực tiếp");

    const filename = isAudio ? `${cleanTitle}.m4a` : `${cleanTitle}.mp4`;
    const contentType = isAudio ? "audio/m4a" : "video/mp4";

    const videoRes = await fetch(format.url);
    if (!videoRes.body) throw new Error("Không lấy được dữ liệu video");

    return new Response(videoRes.body, {
      headers: {
        "Content-Type": contentType,
        "Content-Disposition": `attachment; filename="${filename}"; filename*=UTF-8''${encodeURIComponent(filename)}`,
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Expose-Headers": "Content-Disposition",
        "Cache-Control": "public, max-age=31536000, immutable"
      }
    });

  } catch (err: any) {
    return new Response(JSON.stringify({ 
      success: false, 
      error: err.message || "Lỗi xử lý" 
    }), {
      status: 400,
      headers: { "Content-Type": "application/json" }
    });
  }
}

export const config = {
  runtime: 'nodejs22', // hoặc bỏ dòng này nếu Vercel tự nhận
};
