# Meeting MVP 技术栈推荐

## 1. 选型原则

第一版目标是简单但健壮：少服务、少运行时、清晰边界、可 Docker Compose 单机部署。腾讯云 Lighthouse 只负责编排、配额、存储、Provider 调用和 UI 推送，不在服务器上自建重型 ASR。

推荐采用静态前端 + FastAPI 后端 + PostgreSQL + Redis + Caddy 的单机架构。前端从设计初稿里的 Next.js 调整为 Vite + React，因为第一版不需要 SSR，Vite 静态产物更容易由 Caddy 服务，也更适合 0-500 RMB/月预算下的单机部署。

## 2. Frontend

推荐：

- Vite
- React
- TypeScript
- Tailwind CSS
- shadcn/ui
- lucide-react
- Zustand
- Vitest
- Playwright

用途：

- Vite 负责开发服务器和静态构建。
- React + TypeScript 负责实时会议工作台、会后归档页和轻量看板。
- Tailwind CSS + shadcn/ui 提供稳定的组件基础，适合做密集、清晰的效率工具 UI。
- lucide-react 用于工具栏、状态、导出、搜索等图标。
- Zustand 管理前端会话状态、WebSocket 状态、interim/final 展示状态和额度状态。
- Vitest 覆盖纯函数、状态 reducer、协议解析和格式化逻辑。
- Playwright 覆盖浏览器捕获入口、WebSocket mock、实时 UI 和导出流程 smoke test。

默认运行版本：

- Node.js 24 LTS
- npm

## 3. Browser Audio

推荐：

- `navigator.mediaDevices.getDisplayMedia`
- Web Audio API
- `AudioWorklet`
- WebSocket binary frames

音频路径：

```text
会议标签页/系统音频
-> getDisplayMedia
-> AudioContext
-> AudioWorklet
-> mono PCM16 frames
-> WebSocket binary upload
-> FastAPI
-> Google STT streaming
```

理由：

- Google STT streaming 更适合接收稳定的 PCM 音频帧。
- 浏览器侧转换成 mono PCM16 后，后端不需要 FFmpeg 做 WebM/Opus 转码。
- 减少 Lighthouse 单机 CPU 压力、降低延迟，并减少服务端故障点。

第一版不把 MediaRecorder + WebM + 服务端 FFmpeg 作为主路径。它可以保留为后续兼容性 fallback 研究项。

## 4. Backend

推荐：

- Python 3.12
- FastAPI
- Uvicorn
- Pydantic v2
- pydantic-settings
- SQLAlchemy 2 async
- Alembic
- psycopg
- redis-py asyncio
- httpx
- tenacity
- structlog
- pytest
- pytest-asyncio
- Ruff
- mypy

用途：

- FastAPI 提供 HTTP API、WebSocket endpoint 和健康检查。
- Uvicorn 作为 ASGI server。
- Pydantic v2 定义 API schema、WebSocket message schema 和内部 DTO。
- pydantic-settings 管理环境变量和部署配置。
- SQLAlchemy 2 async + psycopg 访问 PostgreSQL。
- Alembic 管理数据库迁移。
- redis-py asyncio 管理实时会话、配额、限流、预算保险丝和短期状态。
- httpx 调用 OpenAI-compatible HTTP provider。
- tenacity 处理 Qwen/OpenAI/COS 等外部 API 的有限重试。
- structlog 输出结构化日志，便于后续接入日志采集。
- pytest / pytest-asyncio 覆盖后端单元测试和异步会话测试。
- Ruff + mypy 保持 Python 代码质量。

包管理：

- uv
- `pyproject.toml`
- `uv.lock`

## 5. AI Providers

### English STT

主用：

- Google Cloud Speech-to-Text v2 streaming

用途：

- 英文 interim 实时转写。
- 英文 final 稳定片段。
- 第一版生产主路径。

备用/对比：

- OpenAI STT provider

用途：

- 保留 provider 接口。
- 可作为管理员实验入口或后续成本/质量对比。
- 第一阶段不要求完整替代 Google STT。

### Chinese Interim Translation

主用：

- Alibaba Cloud Model Studio Qwen Flash/Turbo
- OpenAI-compatible API 调用方式

用途：

- 对英文 interim 做低成本中文临时理解。
- 节流触发，不进入正式档案。
- 失败时不阻塞英文转写和 final 翻译。

### Chinese Final Translation

主用：

- Alibaba Cloud Model Studio Qwen `qwen3.6-max-preview`
- OpenAI-compatible API 调用方式

用途：

- 对英文 final segment 做高质量中文正式翻译。
- 带最近 3 到 5 个 final segment 上下文。
- 结果进入正式会议档案。
- 环境变量使用 `QWEN_FINAL_MODEL=qwen3.6-max-preview`，与 `QWEN_INTERIM_MODEL` 分离。

可选/后续：

- OpenAI text model
- 仅在服务器网络可达或需要质量对比时启用。
- 当前腾讯云 Lighthouse 无法访问 OpenAI 官方 `api.openai.com:443`，不作为第一版生产主路径。

## 6. Storage

推荐：

- PostgreSQL 16
- Redis 7
- Tencent COS

PostgreSQL 存：

- anonymous client
- meeting session
- transcript segment
- usage event
- export file
- provider usage and cost estimate

Redis 存：

- active session state
- anonymous quota counters
- rate limit counters
- monthly budget fuse state
- short-lived WebSocket/session coordination data

Tencent COS 存：

- Markdown export
- JSON export
- later Word export

第一版默认不存原始会议音频，只存 final 文本档案和导出文件。

## 7. Deployment

推荐：

- Tencent Cloud Lighthouse
- Ubuntu 22.04 LTS 64-bit x86
- Docker
- Docker Compose
- Caddy
- PostgreSQL container
- Redis container
- FastAPI backend container
- static frontend files served by Caddy

部署结构：

```text
Caddy
  -> / 静态前端
  -> /api/* 反向代理 FastAPI
  -> /ws/* 反向代理 FastAPI WebSocket

FastAPI
  -> PostgreSQL
  -> Redis
  -> Google STT
  -> Qwen
  -> OpenAI optional
  -> Tencent COS
```

选择 Caddy 的原因：

- 自动 HTTPS 更简单。
- 同时服务静态前端和反向代理 API/WSS。
- 配置量比 Nginx 更少，适合第一版单机部署。

生产环境必须启用 HTTPS/WSS，因为浏览器音频捕获和 WebSocket 都需要安全上下文。

## 8. Tooling and CI

推荐：

- GitHub Actions
- npm scripts
- uv scripts
- Docker Compose config check

前端检查：

```bash
npm run lint
npm run test
npm run build
npm run test:e2e
```

后端检查：

```bash
uv run ruff check .
uv run mypy .
uv run pytest
uv run alembic upgrade head
```

部署检查：

```bash
docker compose config
docker compose up -d
docker compose ps
```

## 9. Not Recommended for V1

不推荐第一版使用：

- Next.js SSR：第一版不需要 SSR，增加运行时和部署复杂度。
- Celery/RabbitMQ：当前任务量不需要额外队列系统，Redis 和后台 async task 足够。
- 自建 Whisper/faster-whisper 生产链路：Lighthouse x86 单机没有稳定 GPU，实时质量和延迟风险高。
- 浏览器插件：体验好但权限、审核和兼容成本高，适合第二阶段。
- 桌面客户端/虚拟音频设备：捕获能力强，但安装和跨平台成本高，不适合第一版。
- 外部 BI/埋点 SaaS：先用自有 usage_event 和轻量看板控制成本与数据边界。
- 服务端 FFmpeg/WebM 转码主路径：会增加 CPU、延迟和故障点；仅作为后续 fallback 研究项。

## 10. References

- MDN `getDisplayMedia`: https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getDisplayMedia
- MDN Web Audio / AudioWorklet: https://developer.mozilla.org/docs/Web/API/Web_Audio_API/Using_AudioWorklet
- MDN WebSocket API: https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API
- Google STT streaming: https://cloud.google.com/speech-to-text/v2/docs/streaming-recognize
- Google STT audio encoding: https://cloud.google.com/speech-to-text/v2/docs/encoding
- Alibaba Cloud Model Studio Qwen OpenAI-compatible API: https://help.aliyun.com/zh/model-studio/qwen3-livetranslate-flash-api
- OpenAI text generation, optional provider: https://platform.openai.com/docs/guides/chat-completions
- Docker Compose docs: https://docs.docker.com/compose/
- Caddy Automatic HTTPS: https://caddyserver.com/docs/automatic-https
- SQLAlchemy asyncio: https://docs.sqlalchemy.org/20/orm/extensions/asyncio.html
- Pydantic Settings: https://docs.pydantic.dev/usage/settings/
