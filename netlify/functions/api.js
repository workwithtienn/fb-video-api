import { getVideo } from 'facebook-reel-downloader';
import { tiktokdl } from 'tiktok-scraper-without-watermark';
import ytdl from 'ytdl-core';

export default async function handler(request) {
  const url = new URL(request.url).searchParams.get('url');
  const type = new URL(request.url).searchParams.get('type') || 'video'; // video hoặc audio

  if (!url) return new Response('Thiếu url', { status: 400 });

  try {
    let videoUrl, title = 'video';

    if (url.includes('facebook.com') || url.includes('fb.com')) {
      const data = await getVideo(url);
      videoUrl = data.hd || data.sd;
      title = 'Facebook_Reel';
    } else if (url.includes('tiktok.com')) {
      const data = await tiktokdl(url);
      videoUrl = data.video;
      title = 'TikTok';
    } else if (ytdl.getURLVideoID(url)) {
      title = 'YouTube';
      videoUrl = url; // ytdl sẽ stream trực tiếp
    } else {
      return new Response('Link không hỗ trợ', { status: 400 });
    }

    if (type === 'audio' && !url.includes('tiktok.com')) {
      return new Response('Audio chỉ hỗ trợ TikTok tạm thời', { status: 400 });
    }

    // YouTube hoặc TikTok/FB video
    if (url.includes('youtube.com') || url.includes('youtu.be')) {
      const stream = ytdl(videoUrl, { quality: type === 'audio' ? 'highestaudio' : 'highestvideo' });
      const contentType = type === 'audio' ? 'audio/mp4' : 'video/mp4';
      return new Response(stream, {
        headers: {
          'Content-Type': contentType,
          'Content-Disposition': `attachment; filename="${title}_${Date.now()}.${type === 'audio' ? 'm4a' : 'mp4'}"`,
          'Access-Control-Allow-Origin': '*'
        }
      });
    }

    // Facebook & TikTok
    const res = await fetch(videoUrl);
    const ext = type === 'audio' ? 'm4a' : 'mp4';
    const contentType = type === 'audio' ? 'audio/m4a' : 'video/mp4';

    return new Response(res.body, {
      headers: {
        'Content-Type': contentType,
        'Content-Disposition': `attachment; filename="${title}_${Date.now()}.${ext}"`,
        'Access-Control-Allow-Origin': '*'
      }
    });

  } catch (err) {
    return new Response('Lỗi: ' + err.message, { status: 500 });
  }
}

export const config = { path: "/api" };
