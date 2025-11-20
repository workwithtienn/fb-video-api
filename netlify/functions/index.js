import YTDlpWrap from 'yt-dlp-wrap';

let ytDlp = null;

async function getYtDlp() {
  if (!ytDlp) {
    ytDlp = new YTDlpWrap();
    try {
      await YTDlpWrap.downloadFromGithub('./yt-dlp');
      ytDlp = new YTDlpWrap('./yt-dlp');
    } catch (e) {
      console.log('yt-dlp binary ready');
    }
  }
  return ytDlp;
}

export default async function handler(request) {
  const url = new URL(request.url).searchParams.get("url");
  const type = new URL(request.url).searchParams.get("type") || "video";

  if (!url) {
    return new Response("Thiếu url", { status: 400 });
  }

  try {
    const ytdlp = await getYtDlp();
    const infoJson = await ytdlp.execPromise([url, "-j"]);
    const info = JSON.parse(infoJson);

    const cleanTitle = (info.title || "video").replace(/[<>:"/\\|?*]/g, "_").substring(0, 100);

    if (type === "json_video" || type === "json_audio") {
      const isAudio = type === "json_audio";
      const format = isAudio
        ? info.formats?.find(f => f.acodec !== "none" && f.vcodec === "none") || info
        : info.formats?.reverse().find(f => f.vcodec !== "none") || info;

      return new Response(JSON.stringify({
        success: true,
        title: info.title,
        download_url: format.url || null
      }), {
        headers: { "Content-Type": "application/json" }
      });
    }

    const isAudio = type === "audio";
    const format = isAudio
      ? info.formats?.find(f => f.acodec !== "none" && f.vcodec === "none") || info
      : info.formats?.reverse().find(f => f.vcodec !== "none") || info;

    if (!format.url) throw new Error("Không tìm thấy link");

    const filename = isAudio ? `${cleanTitle}.m4a` : `${cleanTitle}.mp4`;
    const contentType = isAudio ? "audio/m4a" : "video/mp4";

    const res = await fetch(format.url);
    if (!res.body) throw new Error("Lỗi fetch video");

    return new Response(res.body, {
      headers: {
        "Content-Type": contentType,
        "Content-Disposition": `attachment; filename="${filename}"; filename*=UTF-8''${encodeURIComponent(filename)}`,
        "Access-Control-Allow-Origin": "*",
        "Cache-Control": "public, max-age=31536000"
      }
    });

  } catch (err) {
    return new Response("Lỗi: " + err.message, { status: 500 });
  }
}

export const config = { path: "/api/*" };
