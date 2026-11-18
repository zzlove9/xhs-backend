import json
import base64
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

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        urls = body.get("urls", [])

        try:
            import asyncio
            results = asyncio.run(self._fetch_all(urls))
            self._json({"ok": True, "images": results})
        except Exception as e:
            self._json({"ok": False, "error": str(e)}, 500)

    async def _fetch_all(self, urls):
        results = []
        async with httpx.AsyncClient(
            headers={
                "User-Agent": MOBILE_UA,
                "Referer": "https://www.xiaohongshu.com/",
            },
            follow_redirects=True,
            timeout=15,
        ) as client:
            for url in urls:
                try:
                    url = fix_url(url)
                    r = await client.get(url)
                    mime = r.headers.get("content-type", "image/jpeg").split(";")[0]
                    b64 = base64.b64encode(r.content).decode()
                    results.append({"url": url, "base64": b64, "mime": mime})
                except Exception as e:
                    results.append({"url": url, "base64": "", "mime": "", "error": str(e)})
        return results

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
