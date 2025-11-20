import YTDlpWrap from 'yt-dlp-wrap';

const ytDlp = new YTDlpWrap();

export default async function handler(req: any, res: any) {
  const url = req.query.url as string;
  const type = (req.query.type as string) || 'video';

  if (!url) {
    return res.status(400).json({ error: 'Thiếu tham số url' });
  }

  try {
    const infoJson = await ytDlp.execPromise([url, '-j']);
    const info = JSON.parse(infoJson);
    const title = (info.title || 'video')
      .replace(/[<>:"/\\|?*]/g, '_')
      .substring(0, 100);

    // JSON API
    if (type === 'json_video' || type === 'json_audio') {
      const isAudio = type === 'json_audio';
      const format = isAudio 
        ? info.formats?.find((f: any) => f.acodec !== 'none' && f.vcodec === 'none') || info
        : info.formats?.reverse().find((f: any) => f.vcodec !== 'none') || info;

      return res.json({
        success: true,
        title: info.title || 'Unknown',
        download_url: format.url || null
      });
    }

    // Tải trực tiếp video/audio
    const isAudio = type === 'audio';
    const format = isAudio
      ? info.formats?.find((f: any) => f.acodec !== 'none' && f.vcodec === 'none') || info
      : info.formats?.reverse().find((f: any) => f.vcodec !== 'none') || info;

    if (!format.url) throw new Error('Không tìm thấy link trực tiếp');

    const filename = isAudio ? `${title}.m4a` : `${title}.mp4`;
    const contentType = isAudio ? 'audio/m4a' : 'video/mp4';

    res.setHeader('Content-Disposition', `attachment; filename="${filename}"; filename*=UTF-8''${encodeURIComponent(filename)}`);
    res.setHeader('Content-Type', contentType);
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Expose-Headers', 'Content-Disposition');
    res.setHeader('Cache-Control', 'public, max-age=31536000, immutable');

    const response = await fetch(format.url);
    if (!response.body) throw new Error('Không có dữ liệu');

    response.body.pipe(res);
  } catch (err: any) {
    console.error(err);
    res.status(400).json({ 
      success: false, 
      error: err.message || 'Lỗi xử lý video' 
    });
  }
}

export const config = {
  api: {
    responseLimit: false,
  },
};
