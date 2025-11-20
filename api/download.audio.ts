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
    const title = (metadata.title || 'audio').replace(/[^\w\-_. ]/g, '_').substring(0, 100) + '.m4a';

    const audioUrl = metadata.formats?.find((f: any) => f.acodec !== 'none' && f.vcodec === 'none')?.url || metadata.url;
    if (!audioUrl) throw new Error('No audio URL found');

    res.setHeader('Content-Disposition', `attachment; filename="${escape(title)}"`);
    res.setHeader('Content-Type', 'audio/m4a');
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Expose-Headers', 'Content-Disposition');

    const response = await fetch(audioUrl);
    if (!response.body) throw new Error('No body');
    response.body.pipe(res);
  } catch (e: any) {
    res.status(400).json({ error: e.message || 'Failed to process audio' });
  }
}
