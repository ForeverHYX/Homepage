# 性能预算与 Profile 方法

性能优化的边界是：视觉效果和功能完全保留，滚动期间不卸载内容，不通过激进缓存掩盖数据更新。

## 2026-07-17 参考结果

下表使用相同站点内容。Lighthouse 分数会受机器和网络波动影响，因此移动端/桌面端各跑三次并取中位数。

| 指标 | 重构前生产 | 重构后本地候选版本 | 重构后生产 |
| --- | ---: | ---: | ---: |
| Mobile Performance | 92–93 | 94 | 100 |
| Mobile CLS | 0.144 | 0 | 0 |
| Desktop Performance | 95 | 100 | 100 |
| Desktop CLS | 0.072 | 0 | 0 |
| 滚动长任务 | 0 | 0 | 0 |
| 最大捕获 timeline 事件 | 约 3.3 ms | 0.269 ms | — |

重构后本地三轮中位数的详细结果：

| 设备 | FCP | LCP | CLS | TBT | Accessibility | Best Practices | SEO |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Mobile | 1.7 s | 2.9 s | 0 | 0 ms | 98 | 100 | 100 |
| Desktop | 0.4 s | 0.6 s | 0 | 0 ms | 98 | 100 | 100 |

发布后生产三轮中位数：

| 设备 | Performance | FCP | LCP | CLS | TBT | Accessibility | Best Practices | SEO |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Mobile | 100 | 0.9 s | 1.8 s | 0 | 0 ms | 98 | 100 | 100 |
| Desktop | 100 | 0.3 s | 0.4 s | 0 | 0 ms | 98 | 100 | 100 |

同一次生产切换中，systemd cgroup `MemoryCurrent` 从 165,724,160 bytes 降至 68,726,784 bytes，下降约 58.5%。预热后的服务器回环中位数为：首页 1.58ms、Publications 1.05ms、Daily 3.35ms、Gallery 1.57ms、Search API 0.93ms。

服务层的 warm in-process payload 构建时间（用于比较 Python 端重复工作，不等同于公网 TTFB）：

| Payload | 重构前 | 重构后 |
| --- | ---: | ---: |
| Home | 约 0.64 ms | 约 0.10 ms |
| Publications | — | 约 0.008 ms |
| Gallery | 约 5.8 ms | 约 0.47 ms |
| Search | 约 2.67 ms | 约 0.43 ms |

最终生产发布后的三轮数据、资源内存和响应头应与发布记录一起保存。不要把单次 100 分当作性能保证；关注中位数、CLS、长任务和功能回归。

## 已采用的优化

### 浏览器

- 自托管原有字体，HTML 提前 preload 实际首屏字体，消除第三方连接和字体替换 CLS。
- variable font 只保留当前使用的 weight/optical-size 范围。
- CSS/JS parser-aware minify，并为 Nginx 预生成 gzip，减少传输和服务器压缩 CPU。
- 内容哈希 URL 允许安全的长期缓存；非指纹 URL 和 uploads 使用保守缓存。
- 图片声明 width/height 并异步解码；Gallery 列表使用持久缩略图，焦点页保持原图。
- 相册自动轮播使用一个 `requestAnimationFrame` scheduler，只调度可见且可滚动相册，页面隐藏时停止。
- 光场和玻璃效果保留；避免长期 `will-change`、重复 backdrop 层和无意义合成层。
- reduced-motion、移动端材质回退和输入设备差异保持可访问。

### Python 与文件系统

- Markdown、JSON、论文、新闻、Gallery payload 和搜索索引按完整输入签名复用。
- 缓存单飞避免冷请求并发重复解析，并限制在 256 项。
- Gallery 冷缩略图在响应后预热，重叠预热任务合并。
- 路径缓存 key 使用稳定绝对路径，避免每次命中都逐级 `resolve/lstat`。
- Nginx 直接服务静态/上传文件，动态 worker 不参与这些请求；指纹静态文件缓存 open metadata，而可原子替换的 uploads 明确关闭 open-file cache。
- 单 worker + preload 避免重复应用对象和内容缓存。

## 明确不采用的优化

- `content-visibility: auto`
- DOM virtualization
- 滚出视口删除节点或清空 Gallery 卡片图片 `src`
- 页面返回视口时重新挂载组件
- 把可变 uploads 标为一年 immutable
- 为减少绘制而删除/弱化玻璃、光场、阴影或主题细节

这些策略可能让实验分数更漂亮，但会造成滚动时内容消失、重新解码、闪烁或视觉变化，不符合本项目目标。

## Lighthouse

启动站点后：

```bash
make profile URL=http://127.0.0.1:8000
make profile URL=https://foreverhyx.top
```

脚本用 Lighthouse 对 mobile/desktop 各跑三次，原始 JSON 与摘要存入 `artifacts/lighthouse/`。需要稳定对比时：

- 保持相同 Chrome/Lighthouse 版本；
- 关闭其他高负载程序；
- 本地测代码成本，线上测网络与真实缓存；
- 冷缓存与 warm cache 分开记录；
- 比较 median，而不是挑最好一轮。

脚本会自动发现系统 Chrome/Chromium、macOS Chrome 应用以及 agent-browser 的 Chrome for Testing；也可显式传入 `--chrome-path /path/to/chrome`。

建议预算：

| 指标 | 目标 | 回归阈值 |
| --- | ---: | ---: |
| CLS | 0 | > 0.02 必须排查 |
| TBT | < 100 ms | > 200 ms 不发布 |
| Long Task | 0 | 任一 > 50 ms 必须定位 |
| Mobile Performance median | ≥ 90 | < 90 不发布 |
| Desktop Performance median | ≥ 95 | < 95 不发布 |

## 滚动与交互 Trace

Lighthouse 不足以发现玻璃重绘或滚动回载问题。Chrome DevTools Performance 应覆盖：

1. 首页加载完成后开始录制；
2. 从顶部平滑滚到底部，再返回顶部；
3. 打开/关闭搜索、News modal 和移动菜单；
4. Gallery 滚出多个相册后返回，打开灯箱；
5. 停止录制并检查 Long Tasks、Layout、Paint 和图片 decode。

合格条件：

- 主线程没有超过 50 ms 的任务；
- 滚回后 Gallery 卡片图片的 `src/currentSrc` 未改变且仍 decoded；
- 没有连续 layout shift；
- 页面隐藏时相册 scheduler 停止；
- Console 无错误，Network 无重复字体或重复全图加载。

可使用 `agent-browser profiler start/stop` 或 Chrome Performance panel 保存 trace JSON，并与 Lighthouse artifact 放在同一发布记录目录。

## 服务端测量

端到端延迟：

```bash
for path in / /publications /daily /gallery /api/search-index; do
  curl -fsS -o /dev/null -w "$path %{http_code} %{time_total}\n" \
    "https://foreverhyx.top$path"
done
```

进程资源：

```bash
systemctl show foreverhyx-homepage -p MemoryCurrent -p CPUUsageNSec
ps -o pid,ppid,rss,%cpu,etime,cmd -C gunicorn
```

响应头：

```bash
curl --compressed -sS -D - -o /dev/null \
  'https://foreverhyx.top/static/css/styles.min.css?v=<hash>'
```

检查 `Content-Encoding: gzip`、`Vary: Accept-Encoding` 和正确的 Cache-Control。若 `.gz` 缺失，Nginx 会动态压缩，功能仍正常但浪费服务器 CPU。

## 改动后的最低验证集

```bash
make check
make profile URL=http://127.0.0.1:8000
```

随后手工/自动验证亮暗主题、桌面与移动导航、搜索、News modal、Daily filters、Gallery 滚动/灯箱、Resume、Login 和上传重定向。性能提升只有在这些行为全部不变时才成立。
