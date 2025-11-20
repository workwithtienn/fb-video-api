import YTDlpWrap from 'yt-dlp-wrap';
import escape from 'escape-html';

const ytDlp = new YTDlpWrap();

export default async function handler(req: any, res: any) {
  const url = req.query.url as string;
  if (!url) return res.status(400).json({ error: 'Missing url' });

  try {
    const info = await ytDlp.execPromise([url, '-f', 'bestaudio/best', '--print', 'url']);
    const directUrl = info.trim();
    if (!directUrl) throw new Error('No audio URL');

    const meta = await ytDlp.execPromise([url, '--print', 'title']);
    let title = (meta.trim() || 'audio').replace(/[^\w\-_. ]/g, '_').substring(0, 100);
    title = escape(title) + '.m4a';

    const response = await fetch(directUrl);
    if (!response.ok || !response.body) throw new Error('Failed to fetch audio');

    res.setHeader('Content-Disposition', `attachment; filename="${title}"`);
    res.setHeader('Content-Type', 'audio/m4a');
    res.setHeader('Access-Control-Allow-Origin', '*');

    const reader = response.body.getReader();
    const stream = new ReadableStream({
      async start(controller) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          controller.enqueue(value);
        }
        controller.close();
      }
    });

    return new Response(stream, {
      headers: res.getHeaders()
    }).pipeTo(res.req.socket);
  } catch (e: any) {
    res.status(400).json({ error: e.message });
  }
}
