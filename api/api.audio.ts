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
    const audioUrl = metadata.formats?.find((f: any) => f.acodec !== 'none' && f.vcodec === 'none')?.url || metadata.url;

    res.status(200).json({ success: true, title, download_url: audioUrl || null });
  } catch (e: any) {
    res.status(400).json({ success: false, error: e.message });
  }
}
