# 开发指南

## 环境

- Python 3.11+
- macOS 或 Linux
- 可选：Node.js 当前 LTS 与 Chrome/Chromium，用于 Lighthouse；脚本也会自动发现 agent-browser 自带的 Chrome for Testing
- 可选：Nginx，仅用于本地验证生产配置

```bash
make setup
make run
```

默认地址是 <http://127.0.0.1:8000>。可覆盖监听参数：

```bash
make run HOST=0.0.0.0 PORT=8080
```

本地开发使用 Uvicorn。不要在 macOS 上用生产 `--preload` Gunicorn 作为日常开发服务器：Objective-C runtime 的 fork 安全检查可能导致 worker 退出；这是平台行为，不是应用异常。

## 编辑后端

后端职责按以下顺序放置：

1. HTTP 参数、状态码、缓存头放在 `app/routers/`。
2. 跨来源的数据组合放在 `app/services/`。
3. 单一领域的解析或文件操作放在对应 `app/*.py`。
4. 共享文件派生值通过 `app/cache.py` 缓存，并使用唯一 namespace。
5. 模板只展示 payload，不在 Jinja 内扫描目录或解析 Markdown。

添加需要外部状态的缓存时，签名必须包含所有输入文件。缓存返回可变 dict/list 时，要在服务边界复制，避免请求间污染。

## 编辑 CSS

源码按级联顺序拆分：

| 文件 | 内容 |
| --- | --- |
| `00-foundations.css` | token、reset、排版基础 |
| `10-materials-home.css` | 首页玻璃材质、光场 |
| `20-content.css` | 主页布局与内容块 |
| `30-articles-daily-publications.css` | Daily、论文、文章 |
| `40-prose.css` | Markdown prose |
| `50-motion-navigation-admin.css` | 动效、导航、管理后台 |
| `60-controls-overlays.css` | 控件、弹层、灯箱 |
| `70-resume-gallery.css` | Resume 与 Gallery |
| `80-responsive-accessibility.css` | 响应式、reduced-motion、可访问性 |
| `90-theme-anniversary.css` | 主题与纪念日样式 |

不要直接编辑 `static/css/styles.css` 或 `styles.min.css`，它们由编号源码拼接生成：

```bash
make build
```

选择器顺序属于视觉行为的一部分。新增规则应放入职责最接近的模块，不要依赖构建器重排声明。

按钮统一使用 `00-foundations.css` 中的 `--button-*` 语义令牌：`.btn` 是 Neutral，`.btn-primary` 是论文会议徽标同款蓝色，Warning/Danger 只更换颜色，不另造形状或材质。文字操作使用胶囊圆角；等宽图标操作使用同一圆角得到圆形。表单和可点击区域使用 `--control-radius`，不要在页面模块内重新写一套按钮渐变、阴影或圆角。

## 编辑 JavaScript

- Header 的源码位于 `static/js/src/site-header/`，按 core、共享 anchored popover、navigation/search、theme、News popover 拆分。
- Header bundle 和所有 `.min.js` 都是生成文件。
- 其他组件与效果的可读 `.js` 是源码；构建器在原目录生成 `.min.js`。
- 页面模板只引用 `.min.js`，并通过 `asset_url()` 获取内容指纹。

修改后运行 `make build`。不要手工改 `.min.js` 或 `.gz`。

## 编辑字体

`static/fonts/src/fonts.css` 是字体声明源码。Source Sans 3 与 Source Serif 4 的完整 variable font 位于 `assets/fonts/vendor/`；构建器只保留站点实际使用的权重与 optical-size 范围。其他字体已经是固定子集。

构建会：

1. 生成裁剪后的 WOFF2；
2. 在字体 CSS 内加入字体文件内容哈希；
3. 让 HTML preload 与 CSS 请求使用同一 URL；
4. 生成确定性 gzip。

字体发生变化后必须跑完整 `make check`，并用 Lighthouse 确认 CLS 仍为 0。

## 生成文件

以下文件必须提交，但不能手工编辑：

- `static/css/styles.css`、`styles.min.css`
- `static/js/components/site-header.js`
- 所有 `static/js/**/*.min.js`
- 裁剪后的 variable fonts 与 `static/fonts/fonts.css`
- `static/asset-manifest.json`
- 所有受构建器管理的 `.gz`

CI 等价检查：

```bash
.venv/bin/python scripts/build_frontend.py --check
.venv/bin/ruff format --check app scripts tests
.venv/bin/ruff check app scripts tests
.venv/bin/python -m pytest -q
```

`--check` 会做一次确定性重建并比较字节；若失败，运行 `make build` 后审阅生成差异。

## 测试策略

测试覆盖：

- 页面/API payload 与 SEO 路由；
- 内容、新闻、Gallery、搜索缓存与外部编辑失效；
- 上传路径、并发写入、缩略图原子发布；
- 无默认凭据、密码空格、会话权限、服务端后台守卫与同源写请求；
- public/private/hidden 上传读取矩阵、持久 share token、重命名与删除失效；
- CSS/JS 视觉与性能约束；
- 资源清单、字体指纹、gzip 字节和构建新鲜度；
- Nginx/systemd 部署卫生。

修复 bug 时优先添加行为测试。对于性能优化，同时增加“不允许退回”的约束，例如禁止 `setInterval` 相册轮播、禁止滚动时卸载图片、禁止把未指纹资源标为 immutable。

## Profile 工作流

先启动本地服务，再另开终端：

```bash
make profile URL=http://127.0.0.1:8000
```

结果写到 `artifacts/lighthouse/<UTC timestamp>/`，目录默认不入 Git。每个设备跑三次并输出中位数。滚动和交互 trace 的浏览器步骤见 [PERFORMANCE.md](PERFORMANCE.md)。

## 提交前清单

```bash
make build
make check
git diff --check
git status --short
```

确认没有 `.env`、会话、生产上传或 Profile artifact 被纳入提交。
