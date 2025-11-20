const axios = require('axios');
const cheerio = require('cheerio');

exports.handler = async (event, context) => {
  // 1. Xử lý Logic Proxy (Để tải file về máy)
  if (event.httpMethod === 'GET') {
    try {
      const { url, type } = event.queryStringParameters;
      
      if (!url) return { statusCode: 400, body: 'Thiếu URL' };

      // Lấy thông tin file từ Facebook mà không tải hết về ngay
      const headResponse = await axios.head(url);
      const fileSize = parseInt(headResponse.headers['content-length'] || '0');
      
      // GIỚI HẠN CỦA NETLIFY FREE: Nếu file > 4.5MB thì không thể Proxy (sẽ bị lỗi Memory)
      // Giải pháp: Nếu file nặng, bắt buộc redirect (mở tab)
      if (fileSize > 4.5 * 1024 * 1024) {
        return {
          statusCode: 302,
          headers: { Location: url },
          body: ''
        };
      }

      // Nếu file nhẹ, tải về RAM server rồi gửi cho người dùng (Ép tải xuống)
      const response = await axios.get(url, { responseType: 'arraybuffer' });
      
      // Cấu hình tên file và định dạng
      const isAudio = type === 'audio';
      const ext = isAudio ? 'm4a' : 'mp4';
      const contentType = isAudio ? 'audio/mp4' : 'video/mp4'; // Mẹo: Audio thực chất vẫn là container mp4 nhưng đổi đuôi
      const filename = `fb_download_${Date.now()}.${ext}`;

      return {
        statusCode: 200,
        headers: {
          'Content-Type': contentType,
          'Content-Disposition': `attachment; filename="${filename}"`,
          'Content-Length': response.data.length.toString()
        },
        body: response.data.toString('base64'),
        isBase64Encoded: true,
      };

    } catch (error) {
      console.error(error);
      // Nếu lỗi Proxy, fallback về redirect
      return {
        statusCode: 302,
        headers: { Location: event.queryStringParameters.url },
        body: ''
      };
    }
  }

  // 2. Xử lý Logic Lấy Link Gốc (Giữ nguyên logic tốt từ trước)
  if (event.httpMethod === 'POST') {
    try {
      const { url } = JSON.parse(event.body);
      
      if (!url || !url.includes('facebook.com')) {
        return { statusCode: 400, body: JSON.stringify({ error: 'Link không hợp lệ' }) };
      }

      const headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
      };

      const response = await axios.get(url, { headers });
      const html = response.data;
      const $ = cheerio.load(html);

      // Ưu tiên lấy link HD -> SD
      let videoUrl = null;
      
      // Cách 1: Regex JSON (Thường chính xác nhất cho Reel)
      const matchHD = html.match(/"browser_native_hd_url":"([^"]+)"/);
      const matchSD = html.match(/"browser_native_sd_url":"([^"]+)"/);
      
      if (matchHD) videoUrl = matchHD[1].replace(/\\u0025/g, '%').replace(/\\/g, '');
      else if (matchSD) videoUrl = matchSD[1].replace(/\\u0025/g, '%').replace(/\\/g, '');

      // Cách 2: Meta tag (Dự phòng)
      if (!videoUrl) {
        videoUrl = $('meta[property="og:video"]').attr('content') || 
                   $('meta[property="og:video:secure_url"]').attr('content');
      }

      if (!videoUrl) {
        return { statusCode: 404, body: JSON.stringify({ error: 'Không lấy được link video (Riêng tư hoặc lỗi FB).' }) };
      }

      return {
        statusCode: 200,
        body: JSON.stringify({ downloadUrl: videoUrl }),
      };

    } catch (error) {
      return { statusCode: 500, body: JSON.stringify({ error: error.message }) };
    }
  }

  return { statusCode: 405, body: 'Method Not Allowed' };
};
