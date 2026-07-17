# 内容维护

项目没有数据库。公开文字、Daily 快照、Gallery 配置和上传文件都是普通文件，便于编辑、迁移和备份。

## 个人信息

`content/about.md`：

```markdown
# About Me

![Avatar](/uploads/avatar.png)

## Role
Student / Researcher

## Connect
- [Email](mailto:name@example.com)
- [GitHub](https://github.com/example)

## Location
City, Country
```

头像放在 `uploads/avatar.png`。模板输出会为头像附加基于 mtime/size 的版本 token，替换后不需要手工改 URL。

## 首页章节

`content/content.md` 的一级标题成为首页 section，例如：

```markdown
# Introduction

Short biography.

# Education

- **University** | 2023 - Present
  *Degree and major*

# Awards

- **Award**, Organization, 2026
```

Education 支持专用时间线渲染。普通 Markdown 支持 fenced code、表格、链接和图片。页面内插入的 HTML 会按当前解析器行为展示，因此只允许受信任维护者编辑内容文件。

## 论文

论文记录也位于 `content/content.md`，使用 `:::publication` 块：

```markdown
:::publication
type: conference
title: Paper Title
venue: Full Conference Name
venue_short: CONF 2026
authors: A. Author, **Your Name**, B. Author
keywords: GPU | Architecture | Simulation
paper: https://example.com/paper.pdf
code: https://github.com/example/repo
:::
```

- `type` 常用 `conference` 或 `journal`。
- `keywords` 用 `|` 分隔，驱动 `/publications` filter。
- `paper`、`code` 可留空；空链接不会输出按钮。
- 标题会生成稳定 slug，用于站内搜索锚点。

修改后无需手工清缓存；下一个请求检测到文件签名变化会重新解析。

## News

`content/news.md`：

```markdown
- **2026-07**: A new paper was accepted.
- **2026-05**: Won an award.
```

首页展示最近 6 条，News 锚定 Popover 展示完整列表。公开 Gallery 相册元数据也会合并进 News；private/hidden 相册不会泄露到公开 feed。

## Gallery

目录结构：

```text
uploads/
└── Trip Name/
    ├── image-01.webp
    ├── image-02.webp
    └── meta.json
```

`meta.json`：

```json
{
  "title": "Trip Name",
  "description": "Short description",
  "date": "2026-07-17",
  "author": "Your Name"
}
```

`gallery_config.json` 控制可见性：

```json
{
  "folders": ["Public Album"],
  "visibility": {
    "Public Album": "public",
    "Private Album": "private"
  }
}
```

状态含义：

- `public`：所有访客可见，也会进入搜索和 News；相册原图与缩略图保留公开 `/uploads/...` URL。
- `private`：只有已登录上传管理员可见，原图和缩略图也需要会话，不只是隐藏列表。
- `hidden`：不保存到 visibility map，不在 Gallery 展示，普通 `/uploads/...` 地址默认同样不公开。

优先通过 `/upload` 创建目录、上传、编辑 metadata 和切换可见性。这样可以获得路径校验、原子写和缓存失效。直接编辑文件也支持，应用会在签名变化后刷新。

图片上传时会转成最长边不超过 1920px、质量 80 的 WebP（GIF 保留动画原文件）。Gallery 列表会生成最长边 1200px 的持久缩略图，焦点相册和灯箱仍使用原图。`uploads/_thumbs/` 是可重建缓存，不是备份的唯一来源。

## Resume、普通文件与分享链接

常用文件放在 `uploads/`，模板当前使用的名字可在 `app/templates/pages/resume.html` 查看。头像、Resume、文章附件和 public Gallery 属于显式公开站点资源；其他根文件、private/hidden 相册文件默认需要登录。文件名包含空格或中文时 URL 会编码，所有读取和管理 API 使用相同安全路径规则。

需要公开发送普通文件时，在 `/upload` 中点击 Copy link。后台会创建一个稳定、不可猜测的 `/share/<token>` URL：

- 收件人无需登录；
- 重复复制同一文件会得到同一链接；
- 后台重命名文件不会破坏链接；
- 删除文件会立即使链接失效；
- 不要把普通 `/uploads/...` 路径当作分享链接。

公开 uploads 缓存最多 1 小时，token 分享链接缓存 5 分钟，登录私有资源使用 `private, no-store`。需要立即切换的公开高关注资源应让模板通过 `upload_url()` 输出版本 token，或使用新文件名。

## Daily

默认位置：

```text
content/daily/
├── recommendations.json
├── feedback-config.json
├── favorites-archive.json
├── archive/
└── articles/
```

`app/daily.py` 会优先读取当前 recommendations，同时支持 archive 日期、关键词/type filter 和远端辅助数据的保守 TTL。常用环境覆盖：

| 变量 | 用途 |
| --- | --- |
| `HOMEPAGE_DAILY_CACHE_FILE` | 当前 recommendations 路径 |
| `HOMEPAGE_DAILY_ARCHIVE_DIR` | 历史快照目录 |
| `HOMEPAGE_DAILY_REMOTE_CACHE_SECONDS` | 主远端数据 TTL |
| `HOMEPAGE_DAILY_FEEDBACK_CONFIG_CACHE_SECONDS` | feedback 配置 TTL |
| `HOMEPAGE_DAILY_FAVORITES_CACHE_SECONDS` | favorites TTL |
| `HOMEPAGE_DAILY_RUN_READY_HOUR_UTC` | 当日结果可用时间边界 |

Daily 文章详情会在需要时写入 `content/daily/articles/`。若配置 `OPENAI_API_KEY`，可使用兼容 OpenAI API 生成内容；未配置时保留安全的本地回退。不要把私密 API key 写入 JSON 或提交到 Git。

## Git 与备份约定

`.gitignore` 默认排除大部分个性化 content、所有生产 uploads、Gallery 配置、`.env`、sessions 和 `.share-links.json`。仓库保存应用与必要示例/既有受跟踪内容，生产数据必须独立备份；恢复分享链接时必须同时恢复其映射文件。

内容发布前检查：

```bash
make check
curl -fsS http://127.0.0.1:8000/ >/dev/null
curl -fsS http://127.0.0.1:8000/api/search-index >/dev/null
```

然后在浏览器检查首页、Publications、News、Gallery 和 Daily。内容文件即数据源，不要为了“清缓存”删除构建产物或浏览器图片节点。
