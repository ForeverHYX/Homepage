# Yixun Hong's Homepage

一个以文件为数据源、由 FastAPI 服务的个人学术主页。项目保留完整的 Liquid Glass 视觉、亮暗主题、站内搜索、Daily、Gallery、Resume 与上传管理功能，同时把前端构建、缓存和部署流程做成可复现的开箱即用工作流。

线上站点：[foreverhyx.top](https://foreverhyx.top)

## 快速开始

需要 Python 3.11 或更高版本。公开页面无需配置数据库，也无需配置管理员密码。

```bash
git clone git@github.com:ForeverHYX/Homepage.git
cd Homepage
make setup
make run
```

打开 <http://127.0.0.1:8000>。`make setup` 会创建 `.venv`、安装固定版本依赖、构建前端资源并运行环境诊断。

如需使用 `/upload` 管理后台：

```bash
cp .env.example .env
make password
```

把命令输出的 bcrypt 字符串写入 `.env` 的 `HOMEPAGE_UPLOAD_PASS_HASH`。项目没有默认密码；未配置哈希时登录会安全地失败。

## 常用命令

| 命令 | 用途 |
| --- | --- |
| `make setup` | 创建开发环境、安装依赖、构建并诊断 |
| `make run` | 用 Uvicorn 热重载启动本地服务 |
| `make build` | 重建 CSS、JS、字体子集、清单和 `.gz` |
| `make check` | 构建新鲜度、格式、静态检查和完整测试 |
| `make doctor` | 检查依赖、目录、清单、环境和构建状态 |
| `make password` | 交互式生成上传密码哈希 |
| `make profile URL=https://foreverhyx.top` | 移动端/桌面端各跑三次 Lighthouse |

## 功能

- Markdown 驱动的个人介绍、教育经历、论文、新闻与 Daily 页面
- 亮色/暗色主题、响应式悬浮导航、键盘友好的站内搜索
- 保留桌面端玻璃材质与动态光场；移动端使用视觉一致的轻量回退
- News 与后台编辑器使用就近锚定 Popover，统一复用功能卡材质并自动避让视口边缘
- Gallery 相册、焦点模式、懒加载预览、全尺寸灯箱和后台缩略图预热
- 受 bcrypt、HttpOnly Cookie、同源校验、限流和路径校验保护的上传管理
- 默认私有的普通上传与不可猜测、可持久使用的公开分享链接
- `robots.txt`、Sitemap、IndexNow key 和规范化 URL
- 无数据库：内容、相册元数据、Daily 数据均保存在可备份文件中

## 目录

```text
.
├── app/
│   ├── main.py                 # create_app() 与 ASGI 入口
│   ├── routers/                # 页面、认证、上传 HTTP 边界
│   ├── services/               # 首页、Gallery、搜索展示数据
│   ├── templates/              # Jinja 页面
│   ├── assets.py               # 静态/上传资源版本 URL
│   └── cache.py                # 有界、线程安全、按文件签名失效的缓存
├── content/                    # Markdown 与 Daily 文件数据
├── uploads/                    # 图片、PDF、相册元数据；生产数据不入库
├── static/
│   ├── css/src/                # 分层 CSS 源码
│   ├── js/src/site-header/     # 导航模块源码
│   ├── fonts/src/              # 字体样式源码
│   └── ...                     # 构建后的浏览器资源
├── assets/fonts/vendor/        # 可重复裁剪所需的完整字体源
├── scripts/                    # 构建、诊断、性能测试、密码工具
├── deploy/                     # Nginx 与 systemd 参考配置
├── docs/                       # 架构、开发、部署、性能、内容、运维
├── tests/                      # 功能、安全、并发与性能约束回归测试
├── Makefile
├── requirements.txt            # 生产运行依赖
└── requirements-dev.txt        # 开发/构建/测试依赖
```

## 构建与缓存模型

可读源码与浏览器产物明确分开：

- CSS 按编号维护在 `static/css/src/`，构建为单一 `styles.css` 和 `styles.min.css`。
- Header 按职责维护在 `static/js/src/site-header/`，构建为经典脚本，保持原加载方式和请求数。
- 其他页面脚本保留可读 `.js`，构建器生成对应 `.min.js`。
- Source Sans 3 和 Source Serif 4 从 `assets/fonts/vendor/` 裁剪到实际使用轴范围。
- `static/asset-manifest.json` 为每个运行资源生成 SHA-256 内容指纹 URL。
- 文本资源生成时间戳固定、跨平台一致的 `.gz`，由 Nginx `gzip_static` 直接返回。

Nginx 只对带 `?v=<内容哈希>` 的静态 URL 设置一年 immutable；无指纹静态 URL 仅缓存 5 分钟。`/uploads/` 先由 FastAPI 做公开/登录判断，再通过 `X-Accel-Redirect` 让 Nginx 直接发送文件字节：公开资源缓存 1 小时，私有资源 `no-store`，token 分享链接缓存 5 分钟。这里没有 `content-visibility: auto`、列表虚拟化或滚出视口卸载，因此页面滚动返回时不会出现内容消失后重新加载。

## 上传与分享边界

- 匿名访问 `/upload` 会在服务端直接跳转到 `/login`，管理 HTML 不会先发送到浏览器。
- 导航栏夜间模式右侧的个人中心圆标是后台入口：匿名访问先登录并回到 `/upload`，登录后直接进入；后台的 `Log out` 会同时销毁服务端会话与 Cookie。
- Public Gallery、头像、Resume、文章附件等站点资源保留原 `/uploads/...` URL。
- Private/Hidden Gallery 与普通文件的可猜测 `/uploads/...` 地址只允许登录会话读取。
- 后台的 Copy link 会创建稳定的 `/share/<随机 token>`；持有者无需登录即可打开，文件重命名后链接仍有效，删除文件会让链接失效。
- 生产环境关闭 `/docs`、`/redoc` 和 `/openapi.json`，本地开发默认保留。

## 配置

核心环境变量见 [.env.example](.env.example)：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `HOMEPAGE_UPLOAD_USER` | `admin` | 管理员用户名 |
| `HOMEPAGE_UPLOAD_PASS_HASH` | 空 | bcrypt 哈希；为空时禁止登录 |
| `HOMEPAGE_COOKIE_SECURE` | `true` | 生产 HTTPS Cookie |
| `HOMEPAGE_SESSION_TIMEOUT_SECONDS` | `86400` | 会话有效期 |
| `HOMEPAGE_SHARE_LINK_FILE` | `./.share-links.json` | 持久分享 token 存储 |
| `HOMEPAGE_CONTENT_DIR` | `./content` | 内容目录覆盖 |
| `HOMEPAGE_UPLOAD_DIR` | `./uploads` | 上传目录覆盖 |
| `HOMEPAGE_USE_X_ACCEL_REDIRECT` | `false` | 生产由 Nginx 发送受控上传字节 |
| `HOMEPAGE_ENABLE_API_DOCS` | `true` | 是否开放 FastAPI 交互文档 |

不要提交 `.env`、`.sessions.json`、`.share-links.json` 或生产 `uploads/`。密码中的首尾空格会被保留，不会被隐式裁剪。

## 质量与性能原则

- 视觉和功能回归优先：玻璃材质、阴影、动画和交互没有因性能优化被简化。
- 不采用会移除 DOM、清空图片 `src` 或让离屏内容重新挂载的激进优化。
- 图片保留稳定尺寸，异步解码；相册卡片使用持久缩略图，焦点模式保留原图。
- 文件内容缓存以纳秒 mtime 和大小为签名，内容改变自动失效，最大 256 项。
- Gallery 冷缩略图在响应后预热；重叠任务合并，避免并发重复编码。
- 搜索索引和 Gallery 展示数据复用缓存，但始终返回独立副本，避免请求间污染。
- 自托管字体消除第三方握手和字体替换导致的布局偏移。

性能基线、复测方法和当前数据见 [docs/PERFORMANCE.md](docs/PERFORMANCE.md)。

## 文档

- [架构与数据流](docs/ARCHITECTURE.md)
- [开发与前端构建](docs/DEVELOPMENT.md)
- [生产部署与回滚](docs/DEPLOYMENT.md)
- [性能预算与 Profile 方法](docs/PERFORMANCE.md)
- [内容、论文、Daily 与相册维护](docs/CONTENT.md)
- [监控、备份与故障处理](docs/OPERATIONS.md)

## 生产入口

生产参考拓扑是 Nginx → 单 worker Gunicorn/Uvicorn → FastAPI。静态文件由 Nginx 直接服务；上传请求经 FastAPI 授权后，以内部跳转交回 Nginx 发送字节。首次安装和无停机更新步骤见 [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)。部署前至少执行：

```bash
make check
.venv/bin/python scripts/doctor.py --production
```

macOS 本地开发请使用 `make run`。带 `--preload` 的 Gunicorn 生产配置面向 Linux；macOS 的 Objective-C runtime 在 fork 后可能主动终止进程。

## 字体许可

自托管字体均采用 SIL Open Font License 1.1。来源、子集范围和许可证文件位于 [`static/fonts/`](static/fonts/README.md)。
