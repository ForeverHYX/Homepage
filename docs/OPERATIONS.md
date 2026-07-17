# 运维手册

## 每日健康检查

```bash
systemctl is-active foreverhyx-homepage nginx
curl -fsS -o /dev/null -w 'home %{http_code} %{time_total}\n' \
  https://foreverhyx.top/
curl -fsS -o /dev/null -w 'search %{http_code} %{time_total}\n' \
  https://foreverhyx.top/api/search-index
curl -fsS -o /dev/null -w 'gallery %{http_code} %{time_total}\n' \
  https://foreverhyx.top/gallery
```

期望三个 GET 均为 200。根路径 HEAD 返回 405 是当前 FastAPI route 定义的正常结果，不要用 `curl -I /` 当健康检查。

## 日志

```bash
journalctl -u foreverhyx-homepage -n 100 --no-pager
journalctl -u foreverhyx-homepage --since '30 minutes ago' --no-pager
tail -n 100 /var/log/nginx/homepage_error.log
tail -n 100 /var/log/nginx/error.log
```

主页 access log 默认关闭以减少磁盘 IO。诊断流量问题时可临时开启并设置短期 logrotate，问题结束后恢复关闭。

常见信号：

- Gunicorn worker 反复启动：查看 Python traceback、依赖和 `.env` 路径。
- 429：Nginx 或 SlowAPI 限流生效，先识别来源，不要直接移除保护。
- 502：worker 未监听 `127.0.0.1:8000`，检查 service。
- 404 static：manifest 与部署目录不一致，重新部署同一提交的完整 `static/`。

## 资源监控

```bash
systemctl show foreverhyx-homepage \
  -p MainPID -p MemoryCurrent -p CPUUsageNSec -p TasksCurrent
ps -o pid,ppid,rss,%cpu,etime,cmd -C gunicorn
du -sh /root/newhomepage/{content,uploads,static,.venv}
df -h /root/newhomepage
```

一个 master 加一个 worker 是预期形态。持续增长的 uploads 是主要磁盘来源；`static` 很小，`uploads/_thumbs` 可重建。内存应在加载内容后趋于稳定，缓存有 256 项硬上限。

## 备份

至少备份：

- `.env`
- `content/`
- `uploads/`（包括原图；缩略图可选）
- `gallery_config.json`
- `.share-links.json`（必须与对应 uploads 同步，保留历史分享 URL）
- `.sessions.json`（可选，通常恢复时应丢弃）

```bash
install -d -m 0700 /root/homepage-backups
tar -C /root/newhomepage -czf \
  /root/homepage-backups/homepage-data-$(date -u +%Y%m%dT%H%M%SZ).tar.gz \
  .env .sessions.json .share-links.json content uploads gallery_config.json
chmod 0600 /root/homepage-backups/homepage-data-*.tar.gz
```

建议每日增量、每周完整备份，并把加密副本存到另一台机器。定期做恢复演练；“tar 成功”不代表备份可用。

检查归档：

```bash
tar -tzf /root/homepage-backups/<archive>.tar.gz | sed -n '1,40p'
gzip -t /root/homepage-backups/<archive>.tar.gz
```

## 恢复

1. 先备份当前损坏状态，便于取回最近文件。
2. 暂停管理写入，必要时停止 service。
3. 只恢复需要的数据目录，不覆盖应用代码和虚拟环境。
4. 不恢复旧 sessions，让所有管理员重新登录。
5. 修复所有者/权限，启动服务并验证 Gallery 与搜索。

```bash
systemctl stop foreverhyx-homepage
tar -C /root/newhomepage -xzf <archive> \
  content uploads gallery_config.json .share-links.json
systemctl start foreverhyx-homepage
curl -fsS https://foreverhyx.top/ >/dev/null
curl -fsS https://foreverhyx.top/api/search-index >/dev/null
```

恢复 `.env` 时设为 0600。恢复 uploads 后确认 Nginx 用户能遍历父目录和读取文件。

## 密码轮换与会话失效

```bash
cd /root/newhomepage
.venv/bin/python scripts/hash_password.py
```

更新 `.env` 中哈希后：

```bash
rm -f .sessions.json
systemctl restart foreverhyx-homepage
```

删除 sessions 会让所有现有登录失效。密码和环境由预载 master 读取，因此修改 `.env` 后必须 restart，不能只 reload。不要把明文密码放入命令参数、shell history、systemd unit 或 Git。

## 缓存与压缩核查

从 `static/asset-manifest.json` 取一个真实 URL：

```bash
curl --compressed -sS -D - -o /dev/null \
  'https://foreverhyx.top/static/css/styles.min.css?v=<hash>'
curl -sS -D - -o /dev/null \
  'https://foreverhyx.top/static/css/styles.min.css'
curl -sS -D - -o /dev/null \
  'https://foreverhyx.top/uploads/avatar.png'
```

| 类型 | 期望 |
| --- | --- |
| 指纹 `/static?v=hash` | 一年、immutable、文本可 gzip |
| 无指纹 `/static` | 300 秒、非 immutable |
| 公开 `/uploads` | 3600 秒 + 最多 3600 秒 stale-while-revalidate、非 immutable |
| 登录私有 `/uploads` | `private, no-store` |
| `/share/<token>` | 300 秒、`noindex`；文件主体由 Nginx 发送 |
| Search API | 60 秒 + stale-while-revalidate 300 秒 |
| 私有 Gallery | private, no-store |

若文本资源没有 `Content-Encoding: gzip`：

```bash
cd /root/newhomepage
ls -l static/css/styles.min.css.gz
nginx -T | rg 'gzip_static|location /static' || true
```

生产环境可能没有 `rg`，可改用 `grep`。生成文件缺失时应从已验证提交重新部署，不要在线手工压缩单个文件。

## 内容看起来陈旧

按顺序检查：

1. 实际文件是否已修改、时间和大小是否变化。
2. 请求是否命中浏览器 60 秒 API cache、公开 uploads 1 小时 cache 或分享链接 5 分钟 cache。
3. 应用是否已 reload 以读取新 `asset-manifest.json`。
4. Gallery visibility 是否为 public/private 的预期状态。
5. `/uploads/` 是否代理到 FastAPI，`/_homepage_uploads/` internal alias 是否仍指向 `/root/newhomepage/uploads/`。

Markdown、metadata 和搜索缓存不需要人工清理；签名变化会自动失效。如果是紧急替换可变上传，优先使用新文件名或通过 `upload_url()` 版本化，而不是把整个站点设为 no-cache。

## Gallery 缩略图

首次访问新相册时，响应可能先返回原图 URL，并在响应后生成缩略图。下一请求会检测新缩略图签名并切换；这不会卸载页面已有图片。

排查：

```bash
find /root/newhomepage/uploads/_thumbs -type f | head
find /root/newhomepage/uploads/_thumbs -type f ! -perm -004 -print
journalctl -u foreverhyx-homepage --since today | tail -n 100
```

源图删除时，应用也会清理对应缩略图。不要把 `_thumbs` 当作唯一图片副本。

## 滚动时内容消失或闪烁

当前实现不应发生这种行为。出现时先检查是否有人引入：

- `content-visibility: auto`
- IntersectionObserver 回调中删除卡片或图片 `src`
- Gallery 列表虚拟化
- 主题切换时替换整个页面树

用 Chrome Performance 录制“滚到底再返回”，同时在 Console 比较 Gallery 图片的 `src/currentSrc` 与 `complete/naturalWidth`。不要用延长缓存掩盖 DOM 被卸载的问题。

## 发布后检查

- 首页、Publications、Daily、Gallery、Resume 均为 200。
- 搜索返回论文/Daily/公开相册。
- 亮暗主题、News 锚定 Popover、移动菜单可用。
- Gallery 滚动返回后图片不消失，灯箱仍为原图。
- 匿名 `/upload` 为 303，个人中心图标进入 Login；登录后图标直达后台，Logout 后旧会话失效，private Gallery 不再可见。
- private/hidden 普通直链匿名为 404；Copy link 生成的 `/share/<token>` 匿名为 200。
- `/docs`、`/redoc`、`/openapi.json` 在生产均为 404。
- Console 无错误。
- Nginx 配置通过，service active。
- mobile/desktop Lighthouse 各三轮无明显回归。

完整发布步骤见 [DEPLOYMENT.md](DEPLOYMENT.md)，性能证据规范见 [PERFORMANCE.md](PERFORMANCE.md)。
