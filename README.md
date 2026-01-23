# foreverhyx 个人主页（轻量版）

## 功能
- 使用 Markdown 渲染主页内容（编辑 `content/index.md` 即可更新）
- 简易上传后台：本地磁盘存储

## 快速开始

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

访问：
- 主页：http://localhost:8000/
- 上传接口：`POST /api/upload`
- 文件列表：`GET /api/files`
- 文件访问：`/uploads/{filename}`

## 环境变量
- `HOMEPAGE_CONTENT_DIR`：Markdown 目录（默认 `./content`）
- `HOMEPAGE_UPLOAD_DIR`：上传目录（默认 `./uploads`）

## 目录结构
```
app/
  main.py
content/
  index.md
uploads/
requirements.txt
```

## 说明
这个版本是最小可运行版本，后续可逐步增加：登录鉴权、管理界面、图片压缩、CDN 等。
