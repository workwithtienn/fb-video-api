import type { VercelRequest, VercelResponse } from '@vercel/node';
import YTDlpWrap from 'yt-dlp-wrap';

const ytDlp = new YTDlpWrap();

export default async function handler(req: VercelRequest, res: VercelResponse) {
  const { url } = req.query;
  if (!url || typeof url !== 'string') return res.status(400).json({ success: false, error: 'Missing url' });

  try {
    const info = await ytDlp.execPromise([url, '-j']);
    const metadata = JSON.parse(info);
    const title = metadata.title || 'Unknown';
    const directUrl = metadata.url || metadata.formats?.reverse().find((f: any) => f.ext === 'mp4' && f.vcodec !== 'none')?.url;

    res.status(200).json({ success: true, title, download_url: directUrl || null });
  } catch (e: any) {
    res.status(400).json({ success: false, error: e.message });
  }
}
