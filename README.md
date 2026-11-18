# xhs-backend (Cloudflare Workers 版)

小红书笔记预览卡后端，基于 Cloudflare Workers。

## 接口
- `POST /api/xhs-card` — 抓取笔记结构化数据
- `POST /api/xhs-images` — 代理下载图片并转 base64

## 部署方式

### 方式 A： Cloudflare Dashboard 手动部署（无需安装任何东西）

1. 打开 https://dash.cloudflare.com
2. 左边菜单点 **Workers & Pages**
3. 点 **Create** → **Create Worker**
4. 右边编辑器里，将 `worker.js` 的内容全选覆盖进去
5. 点 **Deploy**
6. 拿到形如 `xhs-backend.xxx.workers.dev` 的地址

### 方式 B： wrangler CLI

```bash
npm install -g wrangler
wrangler login
wrangler deploy
```

## 验证

```bash
curl -X POST https://你的worker地址/api/xhs-card \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://www.xiaohongshu.com/explore/笔记ID"}'
```

返回 `ok: true` 就成功。
