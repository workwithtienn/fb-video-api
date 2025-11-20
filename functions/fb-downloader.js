const axios = require('axios');
const cheerio = require('cheerio');

exports.handler = async (event, context) => {
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: 'Method Not Allowed' };
  }

  try {
    const { url, type } = JSON.parse(event.body);

    if (!url || !url.includes('facebook.com')) {
      return {
        statusCode: 400,
        body: JSON.stringify({ error: 'Link không hợp lệ. Vui lòng nhập link Facebook Reel.' }),
      };
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

    let videoUrl = $('meta[property="og:video"]').attr('content') || 
                   $('meta[property="og:video:secure_url"]').attr('content');

    if (!videoUrl) {
        const match = html.match(/"browser_native_hd_url":"([^"]+)"/) || 
                      html.match(/"browser_native_sd_url":"([^"]+)"/);
        if (match) {
            videoUrl = match[1].replace(/\\u0025/g, '%').replace(/\\/g, '');
        }
    }

    if (!videoUrl) {
      return {
        statusCode: 404,
        body: JSON.stringify({ error: 'Không tìm thấy media. Video có thể ở chế độ riêng tư.' }),
      };
    }

    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        downloadUrl: videoUrl, 
        type: type,
        message: 'Đã lấy link thành công!' 
      }),
    };

  } catch (error) {
    return {
      statusCode: 500,
      body: JSON.stringify({ error: 'Lỗi Server: ' + error.message }),
    };
  }
};
