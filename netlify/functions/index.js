import YTDlpWrap from 'yt-dlp-wrap';

const ytDlp = new YTDlpWrap();

export default async function handler(request) {
  const url = new URL(request.url).searchParams.get("url");
  const type = new URL(request.url).searchParams.get("type") || "video";

  if (!url) {
    return new Response(JSON.stringify({ error: "Thiếu url" }), {
      status: 400,
      headers: { "Content-Type": "application/json; charset=utf-8" }
    });
  }

  try {
    const infoJson = await ytDlp.execPromise([url, "-j"]);
    const info = JSON.parse(infoJson);
    const cleanTitle = (info.title || "media").replace(/[<>:"/\\|?*]/g, "_").substring(0, 100);

    // JSON API
    if (type === "json_video" || type === "json_audio") {
      const isAudio = type === "json_audio";
      const format = isAudio
        ? info.formats?.find(f => f.acodec !== "none" && f.vcodec === "none") || info
        : info.formats?.reverse().find(f => f.vcodec !== "none") || info;

      return new Response(JSON.stringify({
        success: true,
        title: info.title || "Unknown",
        download_url: format.url || null
      }), {
        headers: { "Content-Type": "application/json; charset=utf-8" }
      });
    }

    // Tải video/audio trực tiếp
    const isAudio = type === "audio";
    const format = isAudio
      ? info.formats?.find(f => f.acodec !== "none" && f.vcodec === "none") || info
      : info.formats?.reverse().find(f => f.vcodec !== "none") || info;

    if (!format.url) throw new Error("Không tìm thấy link");

    const filename = isAudio ? `${cleanTitle}.m4a` : `${cleanTitle}.mp4`;
    const contentType = isAudio ? "audio/m4a" : "video/mp4";

    const res = await fetch(format.url);
    if (!res.body) throw new Error("Không lấy được video");

    return new Response(res.body, {
      headers: {
        "Content-Type": contentType,
        "Content-Disposition": `attachment; filename="${filename}"; filename*=UTF-8''${encodeURIComponent(filename)}`,
        "Access-Control-Allow-Origin": "*",
        "Cache-Control": "public, max-age=31536000, immutable"
      }
    });

  } catch (err) {
    return new Response(JSON.stringify({ 
      success: false, 
      error: err.message || "Lỗi server" 
    }), {
      status: 500,
      headers: { "Content-Type": "application/json; charset=utf-8" }
    });
  }
}

export const config = { path: "/api/*" };
