# xhs-backend

小红书笔记预览卡后端，提供两个接口：
- `POST /api/xhs-card` — 抓取笔记结构化数据
- `POST /api/xhs-images` — 代理下载图片并转 base64

## 部署步骤（Ubuntu 服务器）

```bash
# 1. 克隆仓库
git clone https://github.com/zzlove9/xhs-backend.git /opt/xhs-backend
cd /opt/xhs-backend

# 2. 创建虚拟环境并安装依赖
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 3. 测试能否启动
.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8766

# 4. 安装为后台服务
sudo cp xhs-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now xhs-backend
sudo systemctl status xhs-backend

# 5. 开放端口
sudo ufw allow 8766
```

## nginx 反代（推荐）

```nginx
location /api/xhs {
    proxy_pass http://127.0.0.1:8766;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

## 验证

```bash
curl -X POST http://你的服务器IP:8766/api/xhs-card \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.xiaohongshu.com/explore/笔记ID"}'
```

返回 `ok: true` 就说明接口正常。
