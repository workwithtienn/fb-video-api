import YTDlpWrap from 'yt-dlp-wrap';

const ytDlp = new YTDlpWrap();

export default async function handler(req: any, res: any) {
  const url = req.query.url as string;
  if (!url) {
    return res.status(400).json({ success: false, error: "Thiếu tham số url" });
  }

  try {
    const titleOutput = await ytDlp.execPromise([url, '--print', 'title']);
    const title = titleOutput.trim() || "Video";

    const videoUrlOutput = await ytDlp.execPromise([
      url,
      '-f',
      'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
      '--print',
      'url'
    ]);
    const download_url = videoUrlOutput.trim();

    res.status(200).json({
      success: true,
      title: title,
      download_url: download_url || null
    });
  } catch (error: any) {
    res.status(400).json({
      success: false,
      error: error.message || "Không lấy được link video"
    });
  }
}
