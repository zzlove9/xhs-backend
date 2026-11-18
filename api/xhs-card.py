import re
import json
import httpx
from http.server import BaseHTTPRequestHandler

MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
    "Mobile/15E148 Safari/604.1"
)

def fix_url(url: str) -> str:
    url = url.replace("\\u002F", "/")
    if url.startswith("//"):
        url = "https:" + url
    return url

def extract_note_data(state: dict) -> dict:
    try:
        return state["noteData"]["data"]["noteData"]
    except (KeyError, TypeError):
        pass
    try:
        return state["noteData"]["normalNotePreloadData"]["note"]
    except (KeyError, TypeError):
        return {}

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        url = body.get("url", "").strip()

        if not url:
            self._json({"ok": False, "error": "url is required"}, 400)
            return

        try:
            import asyncio
            result = asyncio.run(self._fetch(url))
            self._json(result)
        except Exception as e:
            self._json({"ok": False, "error": str(e)}, 500)

    async def _fetch(self, url):
        async with httpx.AsyncClient(
            headers={"User-Agent": MOBILE_UA},
            follow_redirects=True,
            timeout=12,
        ) as client:
            resp = await client.get(url)
            html = resp.text

        match = re.search(
            r"window\.__INITIAL_STATE__\s*=\s*([\s\S]+?)\s*</script>", html
        )
        if not match:
            return {"ok": False, "error": "\u65e0\u6cd5\u63d0\u53d6 __INITIAL_STATE__"}

        raw = match.group(1).strip().rstrip(";")
        raw = re.sub(r"undefined", "null", raw)
        state = json.loads(raw)

        note = extract_note_data(state)
        if not note:
            return {"ok": False, "error": "\u672a\u627e\u5230\u7b14\u8bb0\u6570\u636e"}

        image_list = note.get("imageList") or []
        images = []
        for img in image_list:
            u = img.get("urlDefault") or img.get("url") or ""
            if isinstance(u, dict):
                u = u.get("url", "")
            if u:
                images.append(fix_url(u))

        interact = note.get("interactInfo") or {}
        comments_raw = state.get("comment", {}).get("comments", {}).get("list") or []
        comments = []
        for c in comments_raw[:5]:
            comments.append({
                "user": c.get("userInfo", {}).get("nickname", ""),
                "content": c.get("content", ""),
                "ipLocation": c.get("ipLocation", ""),
            })

        return {
            "ok": True,
            "note": {
                "title": note.get("title", ""),
                "author": note.get("user", {}).get("nickname", ""),
                "desc": note.get("desc", ""),
                "images": images,
                "imageCount": len(images),
                "likedCount": interact.get("likedCount", "0"),
                "commentCount": interact.get("commentCount", "0"),
                "collectedCount": interact.get("collectedCount", "0"),
                "comments": comments,
                "url": url,
            },
        }

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass
