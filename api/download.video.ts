import type { VercelRequest, VercelResponse } from '@vercel/node';
import YTDlpWrap from 'yt-dlp-wrap';
import escape from 'escape-html';

const ytDlp = new YTDlpWrap();

export default async function handler(req: VercelRequest, res: VercelResponse) {
  const { url } = req.query;
  if (!url || typeof url !== 'string') return res.status(400).json({ error: 'Missing url parameter' });

  try {
    const info = await ytDlp.execPromise([url, '-j']);
    const metadata = JSON.parse(info);
    const title = (metadata.title || 'video').replace(/[^\w\-_. ]/g, '_').substring(0, 100) + '.mp4';

    const directUrl = metadata.url || metadata.formats?.reverse().find((f: any) => f.ext === 'mp4' && f.vcodec !== 'none')?.url;
    if (!directUrl) throw new Error('No direct URL found');

    res.setHeader('Content-Disposition', `attachment; filename="${escape(title)}"`);
    res.setHeader('Content-Type', 'video/mp4');
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Expose-Headers', 'Content-Disposition');

    const response = await fetch(directUrl);
    if (!response.body) throw new Error('No body');
    response.body.pipe(res);
  } catch (e: any) {
    res.status(400).json({ error: e.message || 'Failed to process video' });
  }
}
