import re
import json
import base64
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
    "Mobile/15E148 Safari/604.1"
)


class CardRequest(BaseModel):
    url: str


class ImagesRequest(BaseModel):
    urls: List[str]


def fix_url(url: str) -> str:
    url = url.replace("\\u002F", "/")
    if url.startswith("//"):
        url = "https:" + url
    return url


def extract_note_data(state: dict) -> dict:
    try:
        note = state["noteData"]["data"]["noteData"]
    except (KeyError, TypeError):
        try:
            note = state["noteData"]["normalNotePreloadData"]["note"]
        except (KeyError, TypeError):
            note = {}
    return note


@app.post("/api/xhs-card")
async def xhs_card(req: CardRequest):
    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": MOBILE_UA},
            follow_redirects=True,
            timeout=15,
        ) as client:
            resp = await client.get(req.url)
            html = resp.text

        match = re.search(
            r"window\.__INITIAL_STATE__\s*=\s*([\s\S]+?)\s*</script>",
            html,
        )
        if not match:
            return {"ok": False, "error": "无法提取 __INITIAL_STATE__"}

        raw = match.group(1).strip().rstrip(";")
        raw = re.sub(r"undefined", "null", raw)
        state = json.loads(raw)

        note = extract_note_data(state)
        if not note:
            return {"ok": False, "error": "未找到笔记数据"}

        image_list = note.get("imageList") or []
        images = []
        for img in image_list:
            url_info = img.get("urlDefault") or img.get("url") or ""
            if isinstance(url_info, dict):
                url_info = url_info.get("url", "")
            if url_info:
                images.append(fix_url(url_info))

        interact = note.get("interactInfo") or {}

        comments_raw = (
            state.get("comment", {}).get("comments", {}).get("list") or []
        )
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
                "url": req.url,
            },
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/xhs-images")
async def xhs_images(req: ImagesRequest):
    results = []
    async with httpx.AsyncClient(
        headers={
            "User-Agent": MOBILE_UA,
            "Referer": "https://www.xiaohongshu.com/",
        },
        follow_redirects=True,
        timeout=20,
    ) as client:
        for url in req.urls:
            try:
                url = fix_url(url)
                r = await client.get(url)
                mime = r.headers.get("content-type", "image/jpeg").split(";")[0]
                b64 = base64.b64encode(r.content).decode()
                results.append({"url": url, "base64": b64, "mime": mime})
            except Exception as e:
                results.append({
                    "url": url,
                    "base64": "",
                    "mime": "",
                    "error": str(e),
                })
    return {"ok": True, "images": results}
