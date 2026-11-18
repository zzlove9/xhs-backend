export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: corsHeaders()
      });
    }

    if (url.pathname === '/api/xhs-card' && request.method === 'POST') {
      return handleCard(request);
    }

    if (url.pathname === '/api/xhs-images' && request.method === 'POST') {
      return handleImages(request);
    }

    return new Response(JSON.stringify({ ok: true, service: 'xhs-backend' }), {
      headers: { 'Content-Type': 'application/json', ...corsHeaders() }
    });
  }
};

const MOBILE_UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1';

function corsHeaders() {
  return {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  };
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: { 'Content-Type': 'application/json; charset=utf-8', ...corsHeaders() }
  });
}

function fixUrl(url) {
  if (!url) return '';
  url = url.replace(/\\u002F/g, '/');
  if (url.startsWith('//')) url = 'https:' + url;
  return url;
}

function extractNoteData(state) {
  try { return state.noteData.data.noteData; } catch(e) {}
  try { return state.noteData.normalNotePreloadData.note; } catch(e) {}
  return null;
}

async function handleCard(request) {
  let body;
  try { body = await request.json(); } catch(e) {
    return json({ ok: false, error: 'invalid json' }, 400);
  }

  const noteUrl = (body.url || '').trim();
  if (!noteUrl) return json({ ok: false, error: 'url is required' }, 400);

  try {
    const resp = await fetch(noteUrl, {
      headers: { 'User-Agent': MOBILE_UA },
      redirect: 'follow',
    });
    const html = await resp.text();

    const match = html.match(/window\.__INITIAL_STATE__\s*=\s*([\s\S]+?)<\/script>/);
    if (!match) return json({ ok: false, error: '无法提取 __INITIAL_STATE__' });

    let raw = match[1].trim().replace(/;\s*$/, '');
    raw = raw.replace(/undefined/g, 'null');
    const state = JSON.parse(raw);

    const note = extractNoteData(state);
    if (!note) return json({ ok: false, error: '未找到笔记数据' });

    const imageList = note.imageList || [];
    const images = imageList.map(img => {
      let u = img.urlDefault || img.url || '';
      if (typeof u === 'object') u = u.url || '';
      return fixUrl(u);
    }).filter(Boolean);

    const interact = note.interactInfo || {};
    const commentsRaw = (state.comment?.comments?.list) || [];
    const comments = commentsRaw.slice(0, 5).map(c => ({
      user: c.userInfo?.nickname || '',
      content: c.content || '',
      ipLocation: c.ipLocation || '',
    }));

    return json({
      ok: true,
      note: {
        title: note.title || '',
        author: note.user?.nickname || '',
        desc: note.desc || '',
        images,
        imageCount: images.length,
        likedCount: interact.likedCount || '0',
        commentCount: interact.commentCount || '0',
        collectedCount: interact.collectedCount || '0',
        comments,
        url: noteUrl,
      }
    });
  } catch(e) {
    return json({ ok: false, error: e.message }, 500);
  }
}

async function handleImages(request) {
  let body;
  try { body = await request.json(); } catch(e) {
    return json({ ok: false, error: 'invalid json' }, 400);
  }

  const urls = body.urls || [];
  const results = await Promise.all(urls.map(async (url) => {
    url = fixUrl(url);
    try {
      const r = await fetch(url, {
        headers: {
          'User-Agent': MOBILE_UA,
          'Referer': 'https://www.xiaohongshu.com/',
        }
      });
      const buf = await r.arrayBuffer();
      const mime = r.headers.get('content-type')?.split(';')[0] || 'image/jpeg';
      const b64 = btoa(String.fromCharCode(...new Uint8Array(buf)));
      return { url, base64: b64, mime };
    } catch(e) {
      return { url, base64: '', mime: '', error: e.message };
    }
  }));

  return json({ ok: true, images: results });
}
