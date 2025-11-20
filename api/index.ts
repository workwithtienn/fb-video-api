import YTDlpWrap from 'yt-dlp-wrap';

const ytDlp = new YTDlpWrap();

export default async function handler(req: Request) {
  const { searchParams } = new URL(req.url);
  const url = searchParams.get("url");
  const type = searchParams.get("type") || "video";   // video | audio | json_video | json_audio

  if (!url) {
    return new Response(JSON.stringify({ error: "Thiếu tham số url" }), {
      status: 400,
      headers: { "Content-Type": "application/json; charset=utf-8" }
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
    if (!videoRes.body) throw new Error("Không lấy được dữ liệu");

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
      error: err.message || "Lỗi xử lý video" 
    }), {
      status: 400,
      headers: { "Content-Type": "application/json; charset=utf-8" }
    });
  }
}

// Netlify cần export config
export const config = { path: "/api/*" };
