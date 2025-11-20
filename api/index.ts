import type { VercelRequest, VercelResponse } from '@vercel/node';
import ytdl from '@distube/ytdl-core';
import { pipeline } from 'stream/promises';

// Cấu hình CORS
const setCORS = (res: VercelResponse) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
};

// Làm sạch tên file
const sanitizeFilename = (title: string): string => {
  return title
    .replace(/[^\w\s\-]/g, '_')
    .replace(/\s+/g, '_')
    .substring(0, 100);
};

// Lấy thông tin video
const getVideoInfo = async (url: string) => {
  try {
    const info = await ytdl.getInfo(url);
    return {
      title: info.videoDetails.title,
      formats: info.formats,
      videoId: info.videoDetails.videoId,
    };
  } catch (error: any) {
    throw new Error(`Không thể lấy thông tin video: ${error.message}`);
  }
};

// Root endpoint
export default async function handler(req: VercelRequest, res: VercelResponse) {
  setCORS(res);

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  const { url, type = 'video' } = req.query;

  // Root path
  if (!url) {
    return res.status(200).json({
      status: 'ok',
      message: 'Social Media Downloader API - Node.js Version',
      version: '5.0',
      endpoints: {
        video: '/api/index?url=<link>&type=video',
        audio: '/api/index?url=<link>&type=audio',
        info: '/api/index?url=<link>&type=info',
      },
      supported: ['Facebook', 'YouTube', 'TikTok', 'Instagram', 'Twitter'],
      docs: 'https://github.com/distubejs/ytdl-core'
    });
  }

  try {
    const videoUrl = Array.isArray(url) ? url[0] : url;
    
    if (!videoUrl || typeof videoUrl !== 'string') {
      return res.status(400).json({ error: 'URL không hợp lệ' });
    }

    // Chỉ lấy thông tin
    if (type === 'info') {
      const info = await getVideoInfo(videoUrl);
      const format = ytdl.chooseFormat(info.formats, { quality: 'highest' });
      
      return res.status(200).json({
        success: true,
        title: info.title,
        videoId: info.videoId,
        url: format.url,
        quality: format.qualityLabel,
        container: format.container,
      });
    }

    // Xử lý download
    const info = await getVideoInfo(videoUrl);
    const safeTitle = sanitizeFilename(info.title);

    let format;
    let ext;
    let contentType;

    if (type === 'audio') {
      // Chọn format audio tốt nhất
      format = ytdl.chooseFormat(info.formats, { 
        quality: 'highestaudio',
        filter: 'audioonly' 
      });
      ext = 'm4a';
      contentType = 'audio/mp4';
    } else {
      // Chọn format video tốt nhất
      format = ytdl.chooseFormat(info.formats, { 
        quality: 'highest',
        filter: format => format.hasVideo && format.hasAudio
      });
      ext = 'mp4';
      contentType = 'video/mp4';
    }

    // Set headers cho download
    res.setHeader('Content-Type', contentType);
    res.setHeader('Content-Disposition', `attachment; filename="${safeTitle}.${ext}"`);
    
    if (format.contentLength) {
      res.setHeader('Content-Length', format.contentLength);
    }

    // Stream video trực tiếp
    const videoStream = ytdl(videoUrl, { format });
    
    // Pipe stream đến response
    await pipeline(videoStream, res);
    
  } catch (error: any) {
    console.error('Error:', error);
    
    if (!res.headersSent) {
      return res.status(500).json({
        error: 'Lỗi khi xử lý video',
        message: error.message,
        details: 'Vui lòng kiểm tra URL hoặc thử lại sau'
      });
    }
  }
}
