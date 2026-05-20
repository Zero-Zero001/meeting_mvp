# AGENTS.md

本文件是 Codex/AI 开发者在本仓库工作的项目记忆。每次学习到关于项目的新信息，都要同步更新本文件。写任何代码前必须完整阅读 `memory-bank/2026-04-24-meeting-mvp-design.md` 和 `memory-bank/architecture.md`，每完成一个重要功能或里程碑后，必须更新 `memory-bank/architecture.md`。优先使用中文，保持结构清晰；不要写入任何密钥、token、私钥内容或用户隐私数据。

## 1. 仓库与文档现状

- 本地仓库根目录：`D:\meeting_mvp`。
- GitHub 远端：`https://github.com/Zero-Zero001/meeting_mvp.git`。
- 当前已建立工程目录边界：存在 `frontend/`、`backend/`、`deploy/`、`scripts/`、`tests/`、`.github/workflows/`。
- 前端工程已在 `frontend/` 初始化：Vite + React + TypeScript，使用 Tailwind CSS v4、shadcn/ui、lucide-react、Zustand、Vitest、Playwright 和 npm。
- 后端工程已在 `backend/` 初始化：Python 3.12 + FastAPI + uv，包名为 `meeting_mvp_backend`，当前 ASGI 入口为 `meeting_mvp_backend.main:app`，健康检查为 `GET /health`。
- 后端当前已有 `backend/pyproject.toml`、`backend/uv.lock`、`backend/.python-version`；根目录仍没有 `package.json` 或 `pyproject.toml`。
- Step 07 已建立后端数据库层：`meeting_mvp_backend.db` 包、Alembic 配置、初始 migration 和 PostgreSQL 集成测试。
- Step 05 已建立环境变量边界：唯一清单为 `memory-bank/environment-variables.md`；后端示例为 `backend/.env.example`；前端公开示例为 `frontend/.env.example`。
- Step 06 已建立部署骨架：`deploy/docker-compose.yml`、`deploy/Caddyfile`、`deploy/.env.example`、`backend/Dockerfile`、`frontend/Dockerfile` 和 `.dockerignore`。
- Step 06 本地静态检查、前后端既有验证和 Lighthouse `docker compose config --quiet` 均已通过；远端验收使用用户提供的 SSH 私钥完成，没有输出生产 `.env.production` 内容。
- Step 07 本地后端 Ruff/mypy/pytest、前端 lint/test/build/e2e、Lighthouse backend build、Alembic migration 和 PostgreSQL 集成测试均已通过。
- Step 08 已实现 F01 匿名用户初始化：前端生成并持久化 `client_id`，后端提供 `POST /api/anonymous-clients` 并 upsert `anonymous_client`；本地前后端验证和 Lighthouse PostgreSQL 匿名接口集成测试均已通过。
- Step 09 已实现 F02 后端内部额度与预算校验：新增 `meeting_mvp_backend.quota`，用 Redis 保存每日已用秒数、活跃会话和预算保险丝状态；本地后端/前端验证和 Lighthouse Redis 集成测试均已通过。
- Step 10 已实现 WebSocket 消息 schema：后端新增 `meeting_mvp_backend.ws_messages`，前端新增 `frontend/src/protocol/websocket-messages.ts` 并引入 Zod；本地前后端协议解析测试与完整本地验证均已通过。
- Step 11 已实现 F05 WebSocket 会话编排：后端新增 `meeting_mvp_backend.ws_sessions` 并注册 `/ws` endpoint，接入 PostgreSQL `meeting_session` 和 Redis `QuotaService` 完成 pending/active/stop/disconnect 生命周期；本地验证和 Lighthouse PostgreSQL+Redis WebSocket 集成测试均已通过。
- Step 12 已实现前端实时会议工作台骨架：首屏状态栏、捕获模式切换、匿名身份/额度/音频/ASR/翻译状态、四个可访问工作区和桌面/移动响应式布局均已落地；本地前端 lint/test/build/e2e 均已通过。
- Step 13 已实现前端会议音频捕获：新增 `frontend/src/lib/audio-capture.ts` 封装 `getDisplayMedia`，store 记录捕获状态、会议平台、授权尝试和 `MediaStream`，UI 处理授权成功/拒绝/无音轨/不支持/失败提示；本地前端 lint/test/build/e2e 均已通过。
- Step 14 已实现前端音频前处理与 binary 上传：新增 `frontend/src/lib/audio-frames.ts`、`frontend/src/lib/audio-processing.ts`、`frontend/src/lib/meeting-websocket.ts` 和 `frontend/public/audio-worklet/pcm16-processor.js`，将捕获到的 `MediaStream` 转为 16 kHz mono PCM16 100ms frame，仅上传超过 RMS 阈值的非静音 binary frame，并通过前端 WebSocket client 发送 `session_start`/`session_stop`；本地前端 lint/test/build/e2e 均已通过。
- Step 15 已实现本地 mock Provider 链路：后端新增 `meeting_mvp_backend.mock_providers` 固定脚本，并在首个有效 binary frame 激活会话后推送 `asr_interim`、`warning`、`translation_interim`、`segment_final`、`key_sentence_update` 和 `timeline_update`，同时写入 `transcript_segment`；前端 WebSocket client、Zustand store 和四区 UI 已消费实时文本；本地后端 Ruff/mypy/pytest 与前端 lint/test/build/e2e 均已通过。
- Step 16 已将 F06 英文实时转写生产主路径替换为 Qwen3-ASR-Flash-Realtime：后端 `meeting_mvp_backend.stt_providers` 接入 Qwen realtime ASR WebSocket，非 local 环境 WebSocket 会话会把首帧和后续非空 PCM16 binary frame 以 Base64 `input_audio_buffer.append` 持续转发给 Qwen，并发送 `asr_interim` 与 `asr_final`；local 环境继续保留 Step 15 mock Provider；前端 WebSocket client、Zustand store 和英文原文区已消费 `asr_final`，并支持 `session_resume` / `session_resumed` 浏览器断线恢复；本地后端 Ruff/mypy/pytest 与前端 lint/test/build/e2e 均已通过。
- Step 17 已实现 F07 中文 interim：后端新增 `meeting_mvp_backend.translation_providers`，非 local 且 `QWEN_INTERIM_ENABLED=true` 时对节流后的英文 `asr_interim` 异步调用 Qwen OpenAI-compatible `/chat/completions` 并推送 `translation_interim`；默认 1.5 秒最小间隔，空文本/重复文本跳过，请求中只保留最新待翻译文本；Qwen interim 失败只记录脱敏 warning，不阻塞英文 ASR 或后续 final；本地后端 Ruff/mypy/pytest、前端 lint/test/build/e2e 和 Lighthouse 后端容器真实 Qwen interim smoke 均已通过。
- Step 18 已实现 F08 中文 final：后端 `meeting_mvp_backend.translation_providers` 新增 Qwen final provider，非 local WebSocket 会话在英文 `asr_final` 后用 `QWEN_FINAL_MODEL` 调用 Qwen OpenAI-compatible `/chat/completions` 生成正式中文 final，成功写入 `transcript_segment(translation_status=completed)` 并发送 `segment_final`；请求携带最近 5 个成功双语 final 上下文，显式 `enable_thinking=false`、`max_tokens=512`；Qwen final 失败会保存英文 final、空中文 final、`translation_status=failed` 并发送 warning，不关闭 WebSocket；本地后端 Ruff/mypy/pytest、前端 lint/test/build/e2e 和 Lighthouse 后端容器真实 Qwen final smoke 均已通过。
- Step 19 已实现 F09 四区实时 UI 补强：前端四区只消费显式 WebSocket 消息，`asr_interim` / `translation_interim` 可替换，`segment_final` 幂等追加并移除匹配 `asr_final`，`key_sentence_update` / `timeline_update` 不从 final 派生；四区 callback 抛错不会破坏后续 WebSocket 消息分发；四个实时区已增加 `aria-live="polite"`；本地后端 Ruff/mypy/pytest 与前端 lint/test/build/e2e 均已通过。
- Step 20 已实现 F16 异常与降级提示：前端新增 `session-notices` 统一映射捕获失败、无音频、静音、WebSocket warning/error、关闭原因和预留导出失败提示；store 新增 `activeNotice`/`lastClosedReason`，错误时停止本地音频资源但保留已收到 final、归档入口和 session id；UI 使用 `role="status"`/`role="alert"` 展示可访问提示；后端在 Qwen interim 失败时发送 `warning(code="qwen_interim_translation_failed")`；本地后端 Ruff/mypy/pytest 与前端 lint/test/build/e2e 均已通过。
- Step 21 已实现 usage_event 埋点基础：新增 `meeting_mvp_backend.usage_events`，集中管理事件 allowlist、payload 安全校验、SQLAlchemy writer 和 best-effort 写入；匿名新用户写入 `client_created`，WebSocket 会话写入 `capture_started`、`quota_checked`、`session_started`、`audio_detected`、ASR/翻译/归档、Provider 错误、额度/预算拒绝和 `session_closed` 等后端可确定事件；本地后端 Ruff/mypy/pytest 与前端 lint/test/build/e2e 均已通过。
- Step 22 已实现 F10 基础双语归档页/API：后端新增 `meeting_mvp_backend.archive_tokens` 与 `meeting_mvp_backend.archives`，提供 `GET /api/archives/{session_id}?token=...`，复用 `meeting_session`、`transcript_segment` 和 `usage_event`，校验 archive token hash，按 `sequence` 返回双语 final 片段并记录 `archive_viewed`；前端新增 `frontend/src/api/archives.ts` 和 `frontend/src/archive/ArchivePage.tsx`，`App.tsx` 对 `/archive/:sessionId` 轻量分流；本地后端 Ruff/mypy/pytest 与前端 lint/test/build/e2e 均已通过。
- Step 23 已实现 F11 搜索与复制：后端 `usage_events` 新增 `archive_searched`、`segment_copied` 和 `STEP_23_USAGE_EVENT_TYPES`，`archives` / `main` 新增 `POST /api/archives/{session_id}/events?token=...`，复用 archive token 校验并只写安全元数据；前端归档页新增本地英文/中文/时间戳搜索、无结果状态、片段复制、复制失败提示和搜索/复制事件上报；本地后端 Ruff/mypy/pytest 与前端 lint/test/build/e2e 均已通过。
- Step 24 已实现 F12 Markdown / JSON 导出：后端新增 `meeting_mvp_backend.exports`，复用 archive token 授权生成 Markdown/JSON，上传腾讯 COS 私有对象，写入 `export_file`，返回短期下载地址，并记录 `export_created` / `export_failed` 安全事件；前端归档页新增 Markdown/JSON 导出按钮、空归档禁用、成功下载链接和导出失败提示；新增 `cos-python-sdk-v5` 后端依赖；本地后端 Ruff/mypy/pytest 与前端 lint/test/build/e2e 均已通过。
- Step 25 已实现后台 Final 补译队列：后端新增 `meeting_mvp_backend.translation_retries`，使用 Redis scheduled set 与 per-segment lock 调度 failed/retrying 片段，worker 复用 Qwen final provider 自动补译并更新 `transcript_segment.translation_status`；WebSocket final 首次失败后自动入队，FastAPI lifespan 在非 local 且 DB/Redis/Qwen final 配置完整时启动 worker；归档 API 返回 `translation_retry_attempts` / `translation_retry_exhausted`，前端归档页显示补译状态并自动 polling；本地后端 Ruff/mypy/pytest 与前端 lint/test/build/e2e 均已通过。
- Step 26 已实现 F17 当前重点句增强：后端新增 `meeting_mvp_backend.key_sentences` 用确定性规则识别行动项、决策、截止时间、风险、预算、负责人、确认、上线等重点句；Qwen final 成功后写入 `transcript_segment.is_key_sentence` 并命中时推送 `key_sentence_update`；归档 API 新增 `PATCH /api/archives/{session_id}/segments/{segment_id}/key-sentence?token=...` 支持人工标记/取消；`usage_event` 新增 `key_sentence_marked` 安全元数据事件；前端归档页新增“只看重点句”筛选和人工标记按钮；本地后端 Ruff/mypy/pytest 与前端 lint/test/build/e2e 均已通过。
- Step 27 已实现 F18 会议时间线增强：后端新增 `meeting_mvp_backend.timeline` 统一生成 `segment_final`、`key_sentence`、`export_created`、`exception` 节点；WebSocket final/重点句/warning/error 路径推送 `timeline_update`；归档 API 新增 `timeline_items` 派生字段；前端实时页和归档页新增时间线筛选、类型展示和关联片段跳转；本地后端 Ruff/mypy/pytest 与前端 lint/test/build/e2e 均已通过。
- Step 28 已实现 F14 使用量与成本看板：后端新增 `meeting_mvp_backend.usage_dashboard`，提供 `GET /api/admin/usage-dashboard?days=...`，使用 `DASHBOARD_ADMIN_TOKEN` bearer 鉴权，从 `meeting_session` 与 `usage_event` 安全元数据聚合会议数、有效会议、活跃匿名用户、ASR 分钟、Qwen 请求数、估算 token、导出、错误、漏斗、腾讯会议成功率和估算成本；前端新增 `/admin/usage-dashboard` 管理页，口令只保存在 React state，不写入本地存储或 URL；本地后端 Ruff/mypy/pytest 与前端 lint/test/build/e2e 均已通过。
- Step 29 已实现 F15 Provider 开关：后端新增 `QWEN_ASR_ENABLED` 与 `QWEN_FINAL_ENABLED`，并复用 `QWEN_INTERIM_ENABLED` 做条件配置校验；Qwen ASR 关闭时拒绝新实时会议且不创建 session/不占额度，interim 关闭时只跳过中文 interim，final 关闭时保存英文 final 为 failed 片段并入后台补译队列；`session_started` 新增安全 `provider_status`，前端 store 和状态栏展示 enabled/disabled/local_mock/unconfigured；OpenAI STT 仍仅保留配置校验不接入实时链路；本地后端 Ruff/mypy/pytest 与前端 lint/test/build/e2e 均已通过。
- Step 30 已开始但阻塞，尚未完成：已新增 `tests/compatibility/step-30-compatibility-results.json`、`tests/compatibility/step-30-compatibility-matrix.md` 和 `scripts/validate-step30-compatibility.ps1`，用于记录和校验真实会议平台兼容性矩阵；当前 `https://meeting.youroristore.com` 本地探测超时，无法确认真实 Qwen HTTPS/WSS 后端可用，因此没有录入任何真实平台结果，校验脚本按预期失败，不能标记 Step 30 通过；用户已在 2026-05-20 明确覆盖顺序门禁允许执行 Step 31。
- Step 31 已按用户明确覆盖 Step 30 顺序门禁后开始：新增 `.github/workflows/ci.yml`，配置 GitHub Actions 执行前端 lint/test/build/e2e、后端 Ruff/mypy/pytest 和 Docker Compose config 检查；CI 只做检查，不使用 secrets、SSH、自动部署、`docker compose up`、生产 migration 或真实 Provider/COS smoke；Step 30 仍保持 blocked，未标记通过。
- 前端只能使用 `VITE_*` 公开配置；不得把 Provider、数据库、Redis、COS 密钥加到前端代码或前端构建产物。
- 当前有效产品/技术文档集中在根目录和 `memory-bank/`：
  - `memory-bank/2026-04-24-meeting-mvp-design.md`
  - `memory-bank/tech-stack.md`
  - `meeting-prd.md`
  - `memory-bank/implementation-plan.md`
  - `memory-bank/set-up-env.md`
  - `memory-bank/environment-variables.md`
- `memory-bank/architecture.md` 与 `memory-bank/progress.md` 已记录 Step 01 到 Step 31 CI 检查的基线架构、工程目录边界、前端工程骨架、后端工程骨架、配置边界、部署骨架、数据库模型、匿名用户初始化、额度服务、WebSocket 消息 schema、WebSocket 会话编排、前端实时会议工作台骨架、前端会议音频捕获、前端音频前处理与 binary 上传、本地 mock Provider 链路、Qwen realtime ASR 英文实时转写、Qwen 中文 interim、Qwen 中文 final、四区实时 UI 补强、异常与降级提示、usage_event 埋点基础、基础双语归档页/API、搜索与复制、Markdown/JSON 导出、后台 Final 补译队列、当前重点句增强、会议时间线增强、使用量与成本看板、Provider 开关、兼容性矩阵资产、CI workflow 和执行进度，不再为空文件。
- PRD 已从 `memory-bank/meeting-prd.md` 重新定位到根目录 `meeting-prd.md`；后续引用 PRD 时使用根目录路径。
- 工作区曾出现根目录设计文档被删除、`memory-bank/` 新增的状态；不要擅自恢复或覆盖用户改动。

## 2. 产品定位

- 项目目标：开发一个网页会议效率工具，帮助中国职场用户在英语线上会议中实时理解英文发言，并形成完整可追溯的双语记录。
- 第一版重点：高质量优先，允许承担一定 API 成本；先把英语会议场景做准。
- 用户无需登录即可免费使用，通过匿名用户身份做额度控制。
- 默认额度：每个匿名用户每天 40 分钟，单场会议 30 分钟，同一匿名用户最多 1 个活跃会议。
- 第一批测试用户预期：10 到 50 人。
- 成本预算：0 到 500 RMB/月；全站月度预算保险丝初始建议 400 RMB。

## 3. 第一版范围与优先级

- M1-A 必须上线闭环：匿名使用、额度、音频捕获、WebSocket、Qwen realtime ASR、Qwen interim、Qwen final、四区 UI、基础异常、基础归档页。
- M1-B 上线后增强：final 重试、轻量看板、Provider 开关、当前重点句增强、会议时间线增强。
- M2 会后归档增强与导出：搜索、复制、Markdown / JSON 导出、腾讯 COS 存储。
- M3 成本与运营：成本估算、漏斗分析、兼容性报告、OpenAI STT 对比入口。

功能清单 F01-F18：

| 编号 | 功能 | 优先级 |
|---|---|---|
| F01 | 匿名用户初始化 | M1-A |
| F02 | 额度与预算校验 | M1-A |
| F03 | 会议音频捕获 | M1-A |
| F04 | 音频前处理 | M1-A |
| F05 | WebSocket 会话编排 | M1-A |
| F06 | 英文实时转写 | M1-A |
| F07 | 中文 interim | M1-A |
| F08 | 中文 final | M1-A |
| F09 | 四区实时 UI | M1-A |
| F10 | 会后基础双语归档 | M1-A |
| F11 | 搜索与复制 | M2 |
| F12 | Markdown / JSON 导出 | M2 |
| F13 | final 翻译重试 | M1-B |
| F14 | 使用量与成本看板 | M1-B |
| F15 | Provider 开关 | M1-B |
| F16 | 异常与降级提示 | M1-A |
| F17 | 当前重点句增强 | M1-B |
| F18 | 会议时间线增强 | M1-B |

## 4. 核心体验

- 实时会议页第一屏就是工作台，不做营销落地页。
- UI 至少包含四块：
  - 英文原文区
  - 中文翻译区
  - 当前重点句区
  - 会议时间线区
- 中文翻译目标不是逐词直译，而是语义准确、自然、适合中国职场用户快速阅读。
- 中文 interim 只做临时理解，不进入正式归档；中文 final 才写入正式记录。
- 会后纪要第一版偏“会议原文归档型”，重点是完整、可追溯。

## 5. 音频与会议平台

- 第一版重点支持 Windows Chrome / Edge。
- 第一版重点会议平台：Google Meet、Microsoft Teams Web、Zoom Web、腾讯会议网页版。
- 音频主路径：`getDisplayMedia` 捕获会议标签页或系统音频，Web Audio API / `AudioWorklet` 转 16 kHz mono PCM16，通过 WebSocket binary frame 上传。
- 第一版不把 MediaRecorder + WebM + 服务端 FFmpeg 转码作为主路径，避免增加 Lighthouse 单机 CPU、延迟和故障点。
- 腾讯会议网页版是重点平台；如果标签页音频失败，MVP 允许通过整个屏幕/系统音频完成验证，但必须记录为 `system_audio_only` 或 `system_audio_fallback`。
- 没有检测到有效音频前，不应正式消耗会议额度。

## 6. 技术栈

前端：

- Vite、React、TypeScript。
- Tailwind CSS、shadcn/ui、lucide-react。
- Zustand 管理会话状态、WebSocket 状态、interim/final 展示状态和额度状态。
- Vitest 覆盖纯函数、状态 reducer、协议解析和格式化逻辑。
- Playwright 覆盖捕获入口、WebSocket mock、实时 UI 和导出流程 smoke test。
- Node.js 24 LTS，npm。

后端：

- Python 3.12、FastAPI、Uvicorn。
- Pydantic v2、pydantic-settings。
- SQLAlchemy 2 async、Alembic、psycopg。
- redis-py asyncio。
- websockets 用于 Qwen realtime ASR 双向 WebSocket。
- httpx、tenacity、structlog。
- pytest、pytest-asyncio、Ruff、mypy。
- 使用 `uv` 管理 Python 版本、虚拟环境和依赖锁定。

存储与基础设施：

- PostgreSQL 16 保存匿名用户、会议、final 片段、usage event、导出文件和成本估算。
- Redis 7 保存活跃会话、匿名额度、限流、预算保险丝和短期 WebSocket 协调状态。
- 腾讯 COS 保存 Markdown / JSON 导出文件，后续可扩展 Word 导出。
- 第一版默认不保存原始会议音频，只保存 final 文本档案和导出文件。
- 会议归档和 COS 导出默认保留 30 天；COS 对象保持私有，由后端生成短期签名 URL。

## 7. AI Provider 策略

- 英文实时转写主路径：阿里云百炼 `qwen3-asr-flash-realtime` realtime WebSocket。
- 中文 interim 主路径：阿里云百炼 Qwen Flash/Turbo，使用 OpenAI-compatible API。
- 中文 final 主路径：阿里云百炼 Qwen `qwen3.6-max-preview`，默认携带最近 5 个 final 片段作为上下文。
- 环境变量必须包含并区分：
  - `QWEN_ASR_ENABLED`
  - `QWEN_INTERIM_MODEL`
  - `QWEN_INTERIM_ENABLED`
  - `QWEN_FINAL_ENABLED`
  - `QWEN_FINAL_MODEL=qwen3.6-max-preview`
- Step 29 后，Qwen ASR/interim/final 生产必填项按各自开关条件校验；Qwen ASR 关闭拒绝新实时会议，Qwen final 关闭会保存 failed 英文 final 并等待后续补译。
- Google STT 曾作为 Step 16 原候选，但北京地区腾讯云 Lighthouse 到 Google Speech API 的真实 gRPC/HTTP2 streaming 不可用，因此仅作为后续备用/对比候选，不再是第一版生产主路径。
- OpenAI 不作为第一版 M1-A 主路径；由于腾讯云 Lighthouse 当前无法访问官方 `api.openai.com:443`，OpenAI 仅保留为后续备用、质量对比或网络恢复后的扩展项。Step 29 仍未实现真实 OpenAI STT 音频转写链路或前端入口，只保留 `OPENAI_STT_ENABLED=true` 时的配置校验。
- Qwen interim 失败不应阻塞英文转写和 Qwen final；Qwen final 失败时片段进入可重试状态。

## 8. 部署与环境边界

- Windows 本地只做代码编辑、文档修改、Git 操作、前端依赖安装/测试/构建、后端纯单元测试和浏览器测试。
- Windows 本地不安装 Docker、PostgreSQL、Redis。
- Windows 系统 Python 可以是 3.13.9，但后端项目必须通过 `uv` 使用 Python 3.12 的项目级 `.venv`。
- 后端依赖和开发工具必须写入 `pyproject.toml` 并锁定到 `uv.lock`。
- `.python-version` 用于固定后端项目解释器为 Python 3.12，可提交；`.venv` 不提交。
- 所有后端命令使用 `uv run ...`，不要全局 `pip install` 项目依赖或开发工具。
- Docker Compose、PostgreSQL、Redis、Alembic migration、数据库集成测试、Redis 集成测试、生产部署演练都在腾讯云 Lighthouse 或后续 CI 环境执行。
- 真实 Qwen realtime ASR、Qwen 文本模型、COS smoke test 在 Lighthouse 云端后端容器执行；Windows 本地只跑 mock Provider 和不依赖真实密钥的测试。
- GitHub Actions 第一版只做检查，不自动部署到 Lighthouse。

已锁定实施决策：

- 工程目录固定为 `frontend/`、`backend/`、`deploy/`、`scripts/`、`tests/`。
- M1-A 包含基础归档页，用户通过 `session_id + archive_token` 查看已生成 final 片段；搜索、复制、导出放到 M2。
- 服务端只保存 `archive_token` hash，不保存明文 token。
- WebSocket 必须包含 `session_started` 响应，返回 `session_id`、`archive_token`、`archive_url` 和剩余额度。
- 浏览器上传音频固定为 16 kHz mono PCM16。
- 数据默认保留 30 天。
- COS 导出使用短期签名 URL。
- CI 第一版只检查，不自动部署。

云服务器当前已知信息：

- 服务器：腾讯云 Lighthouse Ubuntu 22.04 LTS 64 位 x86。
- 域名：`meeting.youroristore.com`。
- 服务器项目目录：`/opt/meeting_mvp`。
- Lighthouse SSH 私钥本地路径：`D:\lighthouse secretKey\lz_secretKey.pem`；只记录路径，不读取、不复制、不输出私钥内容。
- 已创建目录：`/opt/meeting_mvp/app`、`/opt/meeting_mvp/secrets`、`/opt/meeting_mvp/data/postgres`、`/opt/meeting_mvp/data/redis`、`/opt/meeting_mvp/backups`、`/opt/meeting_mvp/logs`。
- Docker 和 Docker Compose 已在 Lighthouse 上安装并验证过。
- 生产部署目标：Caddy 服务 Vite 静态前端，并通过 HTTPS/WSS 反向代理 `/api/*` 和 `/ws/*` 到 FastAPI。
- PostgreSQL 和 Redis 通过 Docker Compose 容器运行；5432 和 6379 不对公网开放。
- Step 06 Compose 骨架中 Caddy 是唯一公网入口，只映射 80/443；PostgreSQL 挂载 `/opt/meeting_mvp/data/postgres`，Redis 挂载 `/opt/meeting_mvp/data/redis`。
- Step 16 替换后，Compose 后端容器不再只读挂载 Google STT 服务账号 JSON；Qwen API key 只通过后端安全环境变量提供，不进入镜像或 Git。
- Step 17 远端真实 Qwen interim smoke 已在 Lighthouse 后端容器镜像内通过：使用 `deploy/.env.example` 完成 backend 镜像构建，容器运行时通过 `.env.production` 注入 Qwen 配置，脱敏 smoke 输出 `qwen-interim-smoke-passed`；临时 `/tmp/qwen_interim_smoke.py` 已删除。
- Step 18 远端真实 Qwen final smoke 已在 Lighthouse 后端容器镜像内通过：已同步 Step 18 文件到 `/opt/meeting_mvp/app`，使用 `.env.production` 完成 backend 镜像构建，并通过 `RUN_QWEN_FINAL_SMOKE=1` 在容器内运行 `tests/integration/test_qwen_final_translation_smoke.py`，最终结果为 `1 passed`；未输出 Qwen API key、完整生产 env 或任何密钥值。
- 远端配置检查命令为：`cd /opt/meeting_mvp/app && docker compose --env-file deploy/.env.example -f deploy/docker-compose.yml config --quiet`；Step 06 已执行通过，但未执行 `docker compose up -d`、`docker compose ps` 或 Alembic migration。
- Step 07 远端 migration 和 PostgreSQL 集成测试使用临时数据目录 `/opt/meeting_mvp/data/postgres_step07` 完成，验收后已清理临时容器、临时数据目录、远端临时脚本和测试缓存。
- Step 07 backend build 曾卡在 Lighthouse Docker build 的 `uv sync` 依赖下载阶段；`backend/Dockerfile` 已增加 `UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple` 与 `UV_HTTP_TIMEOUT=120`，后续 Compose backend build 已通过。
- Step 07/17 曾发现远端 `.env.production` 缺少 Compose 所需数据库/Redis/站点变量，尤其 `POSTGRES_USER` 会拦截 `docker compose --env-file .env.production ... build`；Step 18 前后已补齐到可用于 backend build 的状态，本次 `docker compose --env-file .env.production -f deploy/docker-compose.yml build backend` 通过。正式部署前仍需确认这些变量使用真实生产值，不能用 `deploy/.env.example` 占位值初始化正式数据目录。
- Step 08 远端匿名接口集成测试使用临时数据目录 `/opt/meeting_mvp/data/postgres_step08` 和临时 env 文件 `.env.step08` 完成；验收后已删除临时 PostgreSQL 容器、临时 env、临时数据目录和测试缓存。
- Step 09 远端 Redis 集成测试使用独立 Compose project `meeting_mvp_step09`、临时数据目录 `/opt/meeting_mvp/data/redis_step09`、临时 env 文件 `.env.step09` 和非真实 Google 凭据占位文件完成；验收后已删除临时 Redis 容器、临时网络、临时 backend 镜像、临时 env、占位凭据、临时 Redis 数据目录和测试缓存。
- 2026-05-09 真实 Google STT smoke 曾在 Lighthouse 使用 Google 官方公开 `brooklyn_bridge.raw` 英文样本尝试执行：样本下载成功，Google 凭证文件和必需环境变量存在性检查通过，未输出任何密钥或生产 env 内容。第一次网络检查时 `speech.googleapis.com:443` 在 host/container 中均不可达；用户第二次调整网络后，容器内简单 TCP/TLS 探针可达，但真实 Google STT gRPC streaming 仍报 `ServiceUnavailable: 503 failed to connect to all addresses; ... tcp handshaker shutdown`，未返回 interim/final。该结果已作为历史背景记录，Google STT 不再是 M1-A 生产主路径。
- 80/443 需要等 Caddy 和应用 Compose 部署后再验证。

## 9. 密钥与安全

- 不要把任何密钥写入 Git、前端代码、前端构建产物或 `AGENTS.md`。
- Qwen API key 只应写入服务器安全环境变量文件，不得写入 Git、前端代码、前端构建产物或项目记忆文档；历史 Google STT 服务账号 JSON 不再是生产必需项。
- 生产环境变量文件在服务器上应位于 `/opt/meeting_mvp/app/.env.production`，权限 `600 ubuntu ubuntu`。
- 密钥文件只做脱敏校验；日志中不得打印 API key、SecretId、SecretKey、Google private key 或完整服务账号 JSON。
- `usage_event.payload` 不得保存密钥和原始音频。
- 匿名识别可以使用 `client_id` + IP hash + User-Agent hash，不保存明文 IP。

## 10. WebSocket 与数据模型

核心数据表：

- `anonymous_client`
- `meeting_session`
- `transcript_segment`
- `usage_event`
- `export_file`

Step 07 数据库模型已落地：

- `backend/src/meeting_mvp_backend/db/base.py`：SQLAlchemy `Base` 和命名约定。
- `backend/src/meeting_mvp_backend/db/models.py`：五张核心表、枚举、关系、索引和约束。
- `backend/src/meeting_mvp_backend/db/session.py`：async engine/sessionmaker 工具。
- `backend/alembic.ini` 与 `backend/migrations/`：Alembic 配置和初始 schema migration。
- `backend/tests/test_database_models.py`：本地无真实 DB 的 schema/model 测试。
- `backend/tests/integration/test_database_schema.py`：Lighthouse PostgreSQL 集成测试。

Step 07 表边界：

- `meeting_session` 支持 `pending_audio`、`archive_token_hash`、`retention_expires_at`；不保存明文 `archive_token`。
- `usage_event.payload` 使用 PostgreSQL `JSONB`；不得保存密钥、原始音频或隐私明文。
- `transcript_segment` 只保存英文 final、中文 final 和片段元数据；不保存 interim 或原始音频。

Step 08 匿名用户初始化已落地：

- 前端 `frontend/src/lib/anonymous-client.ts` 使用 `localStorage` 的 `meeting_mvp.client_id` 持久化匿名身份；为空时使用 `crypto.randomUUID()` 生成。
- 前端 `frontend/src/stores/session-store.ts` 已记录 `clientId`、匿名初始化状态、服务端同步状态、同步错误和默认今日剩余额度。
- 后端 `backend/src/meeting_mvp_backend/anonymous_clients.py` 负责匿名 client upsert 和 IP/User-Agent hash。
- 后端 `POST /api/anonymous-clients` 请求体为 `{"client_id": "<uuid>"}`，响应 `client_id`、`daily_free_seconds`、`remaining_seconds_today`、`is_new`。
- 后端只保存请求 IP 与 User-Agent 的 SHA-256 hash，不保存明文 IP 或明文 User-Agent；未配置 `DATABASE_URL` 时匿名初始化接口返回 503。
- 匿名初始化接口的 `remaining_seconds_today` 仍是 Step 08 基础值；Step 09 的 Redis 额度服务尚未接入公开接口或 WebSocket。

Step 09 额度与预算校验已落地：

- 后端 `backend/src/meeting_mvp_backend/quota.py` 负责内部额度服务，不新增公开 REST API，不新增 WebSocket 消息 schema。
- `QuotaPolicy` 负责纯逻辑判定；`RedisQuotaStore` 负责 Redis 状态读写；`QuotaService` 给后续会话编排提供 `check_start_allowed()`、`reserve_active_session()`、`release_active_session()`、`record_consumed_seconds()` 和 `check_session_duration()`；`create_quota_service_from_settings()` 从后端 `Settings.REDIS_URL` 创建 Redis-backed 额度服务。
- Redis key 边界：
  - `meeting_mvp:quota:{client_id}:{yyyyMMdd}:used_seconds`：Asia/Shanghai 自然日已用秒数，TTL 到下一个上海自然日零点。
  - `meeting_mvp:active_sessions:{client_id}`：sorted set，member 为 `session_id`，score 为过期 epoch；检查前清理过期会话。
  - `meeting_mvp:budget:{yyyyMM}:estimated_cost_cents`：全站当月预估成本，单位分。
  - `meeting_mvp:budget:{yyyyMM}:fuse_triggered`：预算保险丝显式开关，值为 `1` 时拒绝新会话。
- 拒绝优先级固定为：预算保险丝 > 活跃会话上限 > 每日额度耗尽 > 单场时长上限。
- Redis 不保存正式会议档案；PostgreSQL 仍是 final 文本、会议归档和导出记录来源。
- `backend/tests/test_quota.py` 覆盖本地纯逻辑与 fake store；`backend/tests/integration/test_quota_redis_integration.py` 覆盖 Lighthouse/CI 真实 Redis。
- Step 21 usage_event 埋点基础已完成；Step 22 基础双语归档页/API 已完成；Step 23 搜索与复制已完成；Step 24 Markdown/JSON 导出已完成；Step 25 后台 Final 补译队列已完成；Step 26 当前重点句增强已完成；Step 27 会议时间线增强已完成；Step 28 使用量与成本看板已完成；Step 29 Provider 开关已完成；Step 30 兼容性矩阵仍 blocked；Step 31 CI 检查已建立；Step 32 必须等用户明确允许后再开始。

Step 10 WebSocket 消息 schema 已落地：

- 后端 `backend/src/meeting_mvp_backend/ws_messages.py` 定义 Pydantic v2 JSON 消息 schema 与 `parse_client_message()`、`parse_server_message()`、`is_audio_chunk_frame()`；所有 JSON 消息使用顶层 `type` 字段，`audio_chunk` 只通过 binary frame 识别。
- 前端 `frontend/src/protocol/websocket-messages.ts` 使用 Zod 镜像同一套 wire schema，并导出 `parseClientMessage()`、`parseServerMessage()`、`isAudioChunkFrame()` 和推导类型。
- `session_start.audio_format` 固定为 16 kHz、1 channel、`pcm16`；Step 10 不新增 `/ws` endpoint，不接入 Redis、PostgreSQL、Provider 或 `QuotaService`。
- `backend/tests/test_ws_messages.py` 和 `frontend/src/protocol/websocket-messages.test.ts` 覆盖合法消息、缺失字段、未知消息类型、非固定音频格式和 binary frame 识别。

Step 11 WebSocket 会话编排已落地：

- 后端 `backend/src/meeting_mvp_backend/ws_sessions.py` 定义 `WebSocketSessionOrchestrator` 和 `SQLAlchemyMeetingSessionRepository`，负责 `session_start`、binary frame 临时激活、`heartbeat`、`session_stop`、断开清理、错误关闭和归档 token hash。
- 后端 `backend/src/meeting_mvp_backend/main.py` 已注册 `/ws` endpoint，并在 WebSocket 依赖中创建数据库仓储和 Redis-backed `QuotaService`；缺少 `DATABASE_URL` 或 `REDIS_URL` 时返回 `configuration_error`。
- `session_start` 成功后先写入 `meeting_session(status=pending_audio)`，首个非空 binary frame 后转为 `active`；Step 14 前端已实现音量阈值和静音帧过滤，因此静音 frame 不会上传，后端仍以首个非空 binary frame 作为会话激活信号。
- `session_stop` 会按 active 后 wall-clock 秒数结算额度、更新 `duration_seconds`/`quota_seconds_consumed`、释放 Redis active session，并发送 `quota_update` 与 `session_closed(reason="user_stopped")`。
- 浏览器断开或 WebSocket task 取消会走清理路径并释放 Redis active session；断开会话当前记录为 `meeting_session.status=error`。
- Step 11 不新增数据库 migration，不保存 raw audio，不保存 interim，不写 `transcript_segment`，不接入真实 Provider/STT/Qwen。
- `backend/tests/test_websocket_sessions.py` 覆盖本地 fake 仓储/额度服务下的会话生命周期；`backend/tests/integration/test_websocket_session_redis_integration.py` 覆盖 Lighthouse/CI 真实 PostgreSQL+Redis WebSocket 集成。

Step 12 前端实时会议工作台骨架已落地：

- 前端 `frontend/src/App.tsx` 已重构为第一屏会议工作台：顶部 `会议状态栏` 包含捕获模式、开始捕获、结束会议、匿名身份、服务端同步、今日剩余额度、音频状态、ASR 和翻译状态。
- 四个实时工作区以可访问区域名固定为 `英文原文区`、`中文翻译区`、`当前重点句区`、`会议时间线区`；桌面左右分栏，移动端纵向堆叠。
- 前端 `frontend/src/stores/session-store.ts` 新增 `setCaptureMode(mode)`，用于在开始捕获前切换 `tab_audio` / `system_audio`；`beginCapture()` / `endSession()` 仍是本地 UI 占位行为。
- Step 12 不实现 `getDisplayMedia`、真实音频捕获、AudioWorklet、WebSocket client、binary 上传、真实 ASR、Qwen 或 Provider 链路；其中 `getDisplayMedia` 和前端捕获授权已在 Step 13 落地，其余链路仍必须等后续步骤明确允许后再开始。
- `frontend/src/App.test.tsx`、`frontend/src/stores/session-store.test.ts` 和 `frontend/e2e/app.spec.ts` 覆盖状态栏、四区、捕获模式、按钮状态、匿名身份/额度/同步展示，以及桌面/移动无水平溢出。

Step 13 前端会议音频捕获已落地：

- 前端 `frontend/src/lib/audio-capture.ts` 负责调用 `navigator.mediaDevices.getDisplayMedia({ audio: true, video: true })`，将授权拒绝映射为 `permission_denied`，将不支持/非安全上下文映射为 `not_supported`，将无 audio track 映射为 `no_audio_track` 并停止所有 tracks。
- 前端 `frontend/src/stores/session-store.ts` 新增 `SourcePlatform`、`captureStatus`、`captureErrorCode`、`captureErrorMessage`、`lastCaptureAttempt`、`mediaStream` 和 `setSourcePlatform()`；`beginCapture()` 为 async action，可注入 fake capture service，默认调用捕获封装；`endSession()` 会停止并清空当前 `MediaStream`。
- 前端 `frontend/src/App.tsx` 新增会议平台选择控件，开始捕获会触发浏览器授权；成功后显示 `已捕获音频`，拒绝授权显示重试入口，无 audio track 显示切换系统音频的降级提示，系统音频模式显示可能包含其他应用声音的风险提示。
- Step 13 只保留 `MediaStream` 引用，不读取、不保存、不上传原始音频；不实现 AudioWorklet、16 kHz mono PCM16 转换、音量电平/静音检测、WebSocket client、binary 上传、真实 ASR、Qwen 或 Provider 链路。
- `frontend/src/lib/audio-capture.test.ts`、`frontend/src/stores/session-store.test.ts`、`frontend/src/App.test.tsx` 和 `frontend/e2e/app.spec.ts` 覆盖捕获成功、授权拒绝、不支持、无 audio track 清理、结束会议停止 tracks、授权尝试记录、桌面/移动无水平溢出。
- Step 13 自动化测试使用 mock `getDisplayMedia`；真实 Windows Chrome/Edge + Google Meet/Teams/Zoom/腾讯会议 Web 兼容性矩阵仍需人工执行，不能把自动化测试等同于真实平台验收。

Step 14 前端音频前处理与 binary 上传已落地：

- 前端 `frontend/src/lib/audio-frames.ts` 定义固定上传格式 `{ sample_rate_hz: 16000, channels: 1, encoding: "pcm16" }`，并提供 mono 混合、16 kHz 重采样、RMS 音量计算、有效音频阈值判断、100ms 帧切分和 little-endian PCM16 编码；每帧固定 1600 samples / 3200 bytes。
- 前端 `frontend/public/audio-worklet/pcm16-processor.js` 是 AudioWorklet processor，只把实时输入通道样本通过 `postMessage` 传回主线程；不保存、不上传原始音频。
- 前端 `frontend/src/lib/audio-processing.ts` 负责创建 `AudioContext`、`MediaStreamAudioSourceNode` 和 `AudioWorkletNode`，把 worklet 样本转为 16 kHz mono PCM16，只对 RMS >= `0.015` 的有效音频触发 binary frame callback；静音帧不发送，30 秒无有效音频触发 `audio_silent_timeout`。
- 前端 `frontend/src/lib/meeting-websocket.ts` 负责推导 WebSocket URL，open 后发送 `session_start`，收到 `session_started` 后允许上传 PCM16 `ArrayBuffer`，结束时发送 `session_stop` 并关闭连接；复用既有 Step 10 WebSocket wire schema。
- 前端 `frontend/src/stores/session-store.ts` 新增 `audioProcessingStatus`、`audioLevel`、`hasEffectiveAudio`、`silenceWarning`、`webSocketStatus`、`sessionId`、`archiveUrl`、`audioPipelineErrorCode`；`beginCapture()` 串联匿名身份同步检查、Step 13 捕获、WebSocket 建会和 AudioWorklet 处理；`endSession()` 清理 processor、WebSocket 和 media tracks。
- 前端 `frontend/src/App.tsx` 在状态栏显示 WebSocket、音频处理、音量电平、有效音频、会话编号、归档入口和 30 秒无有效音频提示；四区工作台布局继续沿用 Step 12。
- `frontend/src/lib/audio-frames.test.ts`、`frontend/src/lib/audio-processing.test.ts`、`frontend/src/lib/meeting-websocket.test.ts`、`frontend/src/stores/session-store.test.ts`、`frontend/src/App.test.tsx` 和 `frontend/e2e/app.spec.ts` 覆盖 PCM16 帧、AudioWorklet 管线、WebSocket client、store/UI 状态和浏览器 mock 上传路径。
- Step 14 不实现 mock STT/Qwen Provider，不生成 interim/final 文本，不写归档，不接入真实 ASR 或 Qwen；真实会议平台兼容性矩阵和真实无声 30 秒场景仍需人工验收。

Step 15 本地 mock Provider 链路已落地：

- 后端 `backend/src/meeting_mvp_backend/mock_providers.py` 定义固定 mock Provider 脚本，包含英文 interim、中文 interim、双语 final、可恢复 provider warning、重点句和时间线元数据；输出稳定，不引入随机文本。
- 后端 `backend/src/meeting_mvp_backend/ws_sessions.py` 在首个有效 binary frame 激活会话后启动可取消 mock task，按固定短节奏发送 `asr_interim`、`warning`、`translation_interim`、`segment_final`、`key_sentence_update` 和 `timeline_update`。
- `MeetingSessionRepository` 协议已新增 `create_transcript_segment(...)`；`SQLAlchemyMeetingSessionRepository` 复用既有 `TranscriptSegment` 模型写入 final 双语片段，不新增 migration；interim、warning 和原始音频不入库。
- `session_stop`、浏览器断开或 WebSocket task 取消会取消 mock task，保留已写入片段，并继续沿用 Step 11 的 Redis active session 释放和额度结算逻辑。
- 前端 `frontend/src/lib/meeting-websocket.ts` 已新增 `onAsrInterim`、`onTranslationInterim`、`onSegmentFinal`、`onKeySentenceUpdate`、`onTimelineUpdate` 和 `onWarning` callbacks；不修改 Step 10 wire schema。
- 前端 `frontend/src/stores/session-store.ts` 已新增 `englishInterimText`、`translationInterimText`、`finalSegments`、`keySentenceText` 和 `timelineItems`；interim 可替换，final 只追加，新会话开始时清空上一场实时文本。
- 前端 `frontend/src/App.tsx` 四区已消费实时文本：英文区显示英文 interim/final，中文区显示中文 interim/final，当前重点句区显示最新重点句，会议时间线区显示 timeline items。
- `backend/tests/test_websocket_sessions.py` 覆盖 mock Provider 消息、final 入库、停止/断开取消和 warning 不阻塞 final；`frontend/src/lib/meeting-websocket.test.ts`、`frontend/src/stores/session-store.test.ts`、`frontend/src/App.test.tsx` 和 `frontend/e2e/app.spec.ts` 覆盖前端 callbacks、store、UI 和浏览器 mock 实时文本流。
- Step 15 只用于本地开发和自动化测试，不接入真实 Qwen，不新增 Provider 密钥变量，不保存原始音频，不新增会后归档 API/页面、搜索、复制、导出、COS 或完整 `usage_event` 链路。

Step 16 Qwen realtime ASR 英文实时转写已落地：

- 后端 `backend/src/meeting_mvp_backend/stt_providers.py` 定义 `StreamingSttProvider` 协议、`SttInterimEvent`、`SttFinalEvent` 和 `QwenRealtimeAsrProvider`，使用 `websockets` 连接 Qwen realtime ASR。
- Qwen realtime ASR 首包发送 `session.update`，配置 16 kHz、mono、`pcm`、可选语言；后续将浏览器 PCM16 binary frame Base64 后发送 `input_audio_buffer.append`。
- 配置新增 `ASR_PROVIDER=qwen_realtime`、`QWEN_ASR_MODEL=qwen3-asr-flash-realtime`、`QWEN_ASR_BASE_URL`、`QWEN_ASR_SAMPLE_RATE_HZ=16000`、`QWEN_ASR_AUDIO_FORMAT=pcm`、`QWEN_ASR_LANGUAGE`、`SESSION_RESUME_GRACE_SECONDS=30`；前端不新增任何 `VITE_QWEN_*`。
- WebSocket 服务端消息 schema 保留 `asr_final`，字段为 `sequence`、`start_ms`、`end_ms`、`text` 和 `confidence|null`；后端 Pydantic schema 与前端 Zod schema 已同步。
- WebSocket 协议新增 client `session_resume` 和 server `session_resumed`；浏览器断线后可在宽限期内用同一 `client_id + session_id + archive_token` 恢复同一业务 session。
- 后端 `backend/src/meeting_mvp_backend/ws_sessions.py` 在首个非空 binary frame 激活会话后启动 Qwen provider，并把首帧和后续非空 PCM16 binary frame 持续转发给 provider；Qwen interim 转为 `asr_interim`，Qwen final/completed 转为 `asr_final`。
- Qwen ASR 缺少时间戳时，后端用累计已发送音频字节数估算 `start_ms/end_ms`；由于前端过滤静音 frame，Qwen provider 会在音频短暂停顿后补发短静音尾帧以触发 server VAD final；`session_stop` 时先发送 `session.finish` 并等待 final/finished，再关闭 provider。
- Qwen ASR 异常会发送 `error(code="qwen_asr_error")`，关闭 provider，释放 Redis active session，并发送 `session_closed`。
- 浏览器断线恢复记录会先写入内存 registry，再清理旧 provider，避免前端快速重连时抢在 registry 写入之前导致 `session_resume_failed`。
- `APP_ENV=local` 继续保留 Step 15 mock Provider 行为；非 local 环境由 `backend/src/meeting_mvp_backend/main.py` 注入 Qwen realtime ASR provider factory。
- `asr_final` 不写数据库；正式 `transcript_segment` 仍只保存后续双语 final 链路产物，避免在中文 final 尚未生成时写入不完整片段。
- 前端 `frontend/src/lib/meeting-websocket.ts` 保留 `onAsrFinal` callback 并新增自动 resume 逻辑，`frontend/src/stores/session-store.ts` 保存 `archiveToken` 与 `englishFinalSegments`，`frontend/src/App.tsx` 英文原文区渲染 `asr_interim` 与 `asr_final`；中文区不伪造中文。
- 新增 `backend/tests/integration/test_qwen_realtime_asr_smoke.py` 作为真实 Qwen ASR gated smoke hook，仅在显式启用、真实 Qwen ASR 环境变量和测试音频 manifest 同时存在时运行；不得打印 API key、完整环境变量值或生产 `.env` 内容。
- 新增 `scripts/prepare-qwen-asr-smoke-audio.ps1`，下载公开 `brooklyn_bridge.raw` 并生成 30 秒、3 分钟、10 分钟 loop 样本和 smoke manifest；脚本不包含密钥。
- 真实 Qwen smoke 已使用 `D:\meeting_mvp_secrets\provider.env` 和公开样本 manifest 跑通：latency/resume 通过；完整 smoke 5 passed、1 skipped，30 秒/3 分钟/10 分钟连续流、术语、自动标点通过，中英混杂因 manifest 未配置样本跳过。
- Step 16 不调用 Qwen 文本翻译，不新增中文 interim/final 逻辑，不新增导出、COS、会后归档页/API 或完整 `usage_event` 链路。

Step 17 Qwen 中文 interim 已落地：

- 后端 `backend/src/meeting_mvp_backend/translation_providers.py` 定义 `InterimTranslationProvider` 协议、`InterimTranslationError` 和 `QwenInterimTranslationProvider`，负责调用 Qwen OpenAI-compatible `/chat/completions` 生成临时中文理解。
- Qwen interim 使用既有 `QWEN_API_KEY`、`QWEN_BASE_URL`、`QWEN_INTERIM_MODEL` 和 `QWEN_INTERIM_ENABLED`，本步不新增环境变量，不新增任何前端 `VITE_QWEN_*`。
- 后端 `backend/src/meeting_mvp_backend/ws_sessions.py` 在 `SttInterimEvent` 后立即发送英文 `asr_interim`，同时异步调度中文 interim；默认 1.5 秒节流，空文本/重复文本跳过，同一时间最多 1 个请求，请求中只保留最新待翻译文本。
- Qwen interim 失败只记录脱敏 `qwen_interim_translation_failed` warning，不发送 WebSocket `error`，不关闭会话，不阻塞英文 ASR 或后续 final。
- `session_stop`、浏览器断开、resume pause 和错误关闭会取消 pending translation task 并关闭 translation provider。
- `backend/src/meeting_mvp_backend/main.py` 仅在非 local 且 `QWEN_INTERIM_ENABLED=true` 时注入真实 Qwen interim provider；`APP_ENV=local` 继续使用 Step 15 mock Provider。
- 前端不需要修改 WebSocket schema；既有 `translation_interim` callback、Zustand `translationInterimText` 和中文翻译区继续消费临时中文。`frontend/src/App.test.tsx` 已新增 interim/final 样式区分断言。
- 新增 `backend/tests/integration/test_qwen_interim_translation_smoke.py` 作为真实 Qwen interim gated smoke hook；默认跳过，显式设置 `RUN_QWEN_INTERIM_SMOKE=1` 并提供真实 Qwen 文本配置时才访问真实服务。
- 中文 interim 不写 PostgreSQL、不生成 `segment_final`、不进入归档；Step 18 已补齐中文 final、最近 5 个 final 上下文和 `transcript_segment` 入库。

Step 18 Qwen 中文 final 已落地：

- 后端 `backend/src/meeting_mvp_backend/translation_providers.py` 新增 `FinalTranslationProvider` 协议、`FinalTranslationRequest`、`FinalTranslationContextSegment`、`FinalTranslationError` 和 `QwenFinalTranslationProvider`，负责调用 Qwen OpenAI-compatible `/chat/completions` 生成正式中文 final。
- Qwen final 复用 `QWEN_API_KEY`、`QWEN_BASE_URL` 和 `QWEN_FINAL_MODEL`，不新增环境变量；请求体显式 `enable_thinking=false`、`max_tokens=512`、`temperature=0.1`，默认超时 60 秒。
- 后端 `backend/src/meeting_mvp_backend/ws_sessions.py` 在 `SttFinalEvent` 后仍先发送英文 `asr_final`，再按 sequence 排队翻译；成功后写入 `transcript_segment(translation_status=completed)` 并发送既有 `segment_final`。
- 成功 final 会进入单 WebSocket 会话内存上下文窗口；后续 final 请求最多携带最近 5 个成功双语 final 片段，仅用于术语和指代一致性。
- Qwen final 失败不会关闭 WebSocket：后端写入英文 final、空中文 final、`translation_status=failed` 和 `asr_confidence`，发送 `warning(code="qwen_final_translation_failed")`；Step 25 已补齐后台自动补译队列。
- `session_stop`、浏览器断开、resume pause 和错误关闭会取消 pending final translation task、关闭 final provider，并将当前/排队未完成 final 片段按 failed 状态归档，避免丢失英文 final。
- 前端 `frontend/src/stores/session-store.ts` 只做必要去重：收到 `segment_final` 后按 `sequence` 移除匹配的 `englishFinalSegments`，避免英文区重复展示同一 final；Step 19 已进一步补强幂等和四区实时展示。
- 新增 `backend/tests/integration/test_qwen_final_translation_smoke.py` 作为真实 Qwen final gated smoke hook；默认跳过，显式设置 `RUN_QWEN_FINAL_SMOKE=1` 并提供真实 Qwen 文本配置时才访问真实服务。
- Step 18 不新增公开 REST API、不修改 WebSocket wire schema、不新增 database migration、不新增归档页/API、搜索、复制、导出、COS、完整 `usage_event`、重点句或时间线增强。

Step 19 四区实时 UI 补强已落地：

- 前端 `frontend/src/stores/session-store.ts` 明确四区实时状态边界：`asr_interim` / `translation_interim` 为可替换状态；`asr_final` 追加为临时英文 final；`segment_final` 按 `segment_id` 或 `sequence` 幂等追加为正式双语 final，并移除匹配 `asr_final`。
- 前端不从 `segment_final` 派生当前重点句或实时会议时间线；当前重点句只消费 `key_sentence_update`，会议时间线只消费 `timeline_update.items` 服务端快照；Step 26 已补齐服务端重点句推送和归档人工标记，Step 27 已补齐时间线节点、筛选和跳转。
- `frontend/src/lib/meeting-websocket.ts` 为四区实时 callbacks 增加隔离分发，某个区域更新抛错不会触发 WebSocket error，也不会阻塞后续实时消息。
- `frontend/src/App.tsx` 的英文原文区、中文翻译区、当前重点句区、会议时间线区均增加 `aria-live="polite"`。
- Step 19 不新增公开 REST API、不修改 WebSocket wire schema、不新增 database migration、不新增异常/降级提示、COS、搜索、复制、导出或完整 `usage_event` 链路。

Step 20 F16 异常与降级提示已落地：

- 前端新增 `frontend/src/lib/session-notices.ts`，统一把本地捕获失败、无音频轨道、30 秒静音、WebSocket `warning`、WebSocket `error`、`session_closed.reason` 和预留 `export_failed` 映射为中文 `SessionNotice`。
- 前端 `frontend/src/lib/meeting-websocket.ts` 新增 `MeetingWebSocketError`，服务端 `error` 会保留 `code` 和 server message；`warning` 仍作为可恢复消息分发，不触发失败控制流。
- 前端 `frontend/src/stores/session-store.ts` 新增 `activeNotice` 和 `lastClosedReason`；warning 不清空四区内容，不可继续 error 会停止本地音频处理和媒体流，但保留已收到 final、归档入口和 session id。
- 前端 `frontend/src/App.tsx` 在状态栏下方显示可访问提示区域，warning/info 使用 `role="status"`，不可继续 error 使用 `role="alert"`；提示不覆盖英文/中文 final 内容。
- 后端 `backend/src/meeting_mvp_backend/ws_sessions.py` 在 Qwen interim 翻译失败时发送 `warning(code="qwen_interim_translation_failed")`，不关闭 WebSocket，不阻塞英文 ASR 或 final；Qwen final warning、Qwen ASR error、额度/预算拒绝保持既有 schema。
- Step 20 不新增公开 REST API、不修改 WebSocket wire schema、不新增 database migration、不新增环境变量、不写 `usage_event`、不实现真实导出/COS/搜索/复制或成本看板。

Step 21 usage_event 埋点基础已落地：

- 新增 `backend/src/meeting_mvp_backend/usage_events.py`，定义 Step 21 事件 allowlist、`UsageEventRecord`、`UsageEventRecorder`、`SQLAlchemyUsageEventRecorder`、payload 安全校验和 best-effort 写入工具。
- `usage_event.payload` 安全校验会拒绝二进制音频、raw audio、PCM frame、API key、secret、token、password、private key、credential 等字段；事件 payload 只允许保存状态、长度、序号、时间点、错误 code/type、剩余额度、capture/source 类型等元数据。
- `backend/src/meeting_mvp_backend/anonymous_clients.py` 在新匿名用户创建成功后记录 `client_created`；payload 只包含 `daily_free_seconds`、`ip_hash_present`、`user_agent_hash_present`，不保存明文 IP、User-Agent 或 hash 值本身。
- `backend/src/meeting_mvp_backend/ws_sessions.py` 在后端可确定的会话节点写入 usage event：`capture_started`、`quota_checked`、`session_started`、`audio_detected`、`asr_interim_received`、`asr_final_received`、`translation_interim_requested`、`translation_final_completed`、`segment_archived`、`provider_error`、`quota_exhausted`、`budget_fuse_triggered`、`session_closed`。
- `capture_failed` 在 Step 21 只完成事件类型和安全写入能力，当前仍没有前端埋点 API；`archive_viewed` 的真实触发已由 Step 22 归档 API 补齐。
- Step 21 本身不新增公开 REST API、不修改 WebSocket wire schema、不新增 database migration、不新增环境变量、不实现会后归档 API/页面、搜索、复制、导出/COS 或成本看板。

Step 22 基础双语归档页/API 已落地：

- 新增 `backend/src/meeting_mvp_backend/archive_tokens.py`，共享 `hash_archive_token()` 与 `build_archive_url()`；`ws_sessions.py` 改为从该模块导入并显式 re-export，保持既有 WebSocket 建会行为。
- 新增 `backend/src/meeting_mvp_backend/archives.py`，定义归档响应模型、repository protocol、SQLAlchemy repository、`ArchiveService` 和 `ArchiveAccessDenied`；复用现有表，不新增 migration。
- 新增 `GET /api/archives/{session_id}?token=...`：缺 token 返回 401，session 不存在、错误 token、归档过期统一 404，成功返回 session 元数据和按 `sequence` 升序的双语 final 片段。
- `end_reason` 优先读取最新 `usage_event.session_closed` payload reason，缺失时 fallback 到 `meeting_session.status`；成功查看归档记录 `archive_viewed`，payload 只含安全元数据。
- 前端新增 `frontend/src/api/archives.ts` 和 `frontend/src/archive/ArchivePage.tsx`；`frontend/src/App.tsx` 对 `/archive/:sessionId` 做轻量分流，不新增 React Router。
- Step 22 本身不实现搜索、复制、Markdown/JSON 导出、COS、成本看板或归档增强；搜索与复制已在 Step 23 补齐。

Step 23 搜索与复制已落地：

- `backend/src/meeting_mvp_backend/usage_events.py` 新增 `archive_searched`、`segment_copied` 和 `STEP_23_USAGE_EVENT_TYPES`；payload 安全校验拒绝搜索词、正文、token、archive URL、音频和密钥字段，只允许长度、命中数、sequence、translation status 等元数据。
- `backend/src/meeting_mvp_backend/archives.py` 新增 `ArchiveSearchEventRequest`、`ArchiveSegmentCopiedEventRequest` 和 `ArchiveService.record_archive_event()`；复制事件会验证 segment 属于当前归档，并由后端派生安全元数据。
- `backend/src/meeting_mvp_backend/main.py` 新增 `POST /api/archives/{session_id}/events?token=...`：缺 token 返回 401，session 不存在、错误 token、过期归档或非法 segment 统一 404，成功返回 204。
- `frontend/src/api/archives.ts` 新增 `ArchiveEvent`、`buildArchiveEventApiUrl()` 和 `recordArchiveEvent()`；事件 POST body 不包含 raw query、正文或 token 字段。
- `frontend/src/archive/ArchivePage.tsx` 新增归档页本地搜索、无结果状态、片段复制按钮、复制失败提示和搜索/复制事件上报；搜索范围覆盖英文 final、中文 final 和时间戳。
- Step 23 本身不实现 Markdown/JSON 导出、COS 上传、`export_file`、短期签名 URL、导出 UI；这些已在 Step 24 补齐。

Step 24 Markdown / JSON 导出已落地：

- 新增 `backend/src/meeting_mvp_backend/exports.py`，定义导出请求/响应模型、Markdown/JSON renderer、`ArchiveExportService`、COS storage 协议、Tencent COS 实现、`ExportFileRepository` 协议和 SQLAlchemy `export_file` 写入器。
- `backend/src/meeting_mvp_backend/main.py` 新增 `POST /api/archives/{session_id}/exports?token=...`：缺 token 返回 401，session 不存在、错误 token、过期归档统一 404，空归档返回 409，COS 配置/上传/签名/数据库写入临时不可用返回 503。
- 后端新增依赖 `cos-python-sdk-v5`，生产用于腾讯 COS 私有对象上传和短期下载地址生成；Windows 本地测试使用 fake storage，不依赖真实 COS 密钥。
- `backend/src/meeting_mvp_backend/usage_events.py` 新增 `export_created`、`export_failed` 和 `STEP_24_USAGE_EVENT_TYPES`；payload 安全校验拒绝 `download_url`、`signed_url`、`cos_url`、`object_key`、`cos_object_key`、token、正文、音频和密钥字段。
- `export_created` 只记录格式、片段数、文件字节数、翻译失败数和签名 URL TTL；`export_failed` 只记录格式、失败阶段、错误类型和安全统计。
- `frontend/src/api/archives.ts` 新增 `ArchiveExportResponse`、`ArchiveExportFormat`、`buildArchiveExportApiUrl()` 和 `createArchiveExport()`；导出 POST body 只包含格式，不包含 token、正文或下载地址。
- `frontend/src/archive/ArchivePage.tsx` 新增 Markdown/JSON 导出按钮、空归档禁用、导出成功下载链接和失败提示；导出失败不清空已加载归档、搜索或复制状态。
- Step 24 不实现 final 翻译重试、重试 API、后台补译、导出历史列表、COS 管理页、成本看板、重点句/时间线增强或 Step 25+ 功能。

Step 25 后台 Final 补译队列已落地：

- 新增 `backend/src/meeting_mvp_backend/translation_retries.py`，定义 `TranslationRetryJob`、Redis-backed queue、`TranslationRetryWorker`、`TranslationRetryProcessor`、SQLAlchemy repository、测试 fake、Redis key 常量、最大 3 次尝试和固定退避策略。
- Redis scheduled set key 为 `meeting_mvp:translation_retry:scheduled`，segment lock key 为 `meeting_mvp:translation_retry:lock:{segment_id}`；Redis job 只保存 `session_id`、`segment_id` 和 `due_at`，不保存正文、译文、token、URL、object key、密钥或隐私数据。
- `backend/src/meeting_mvp_backend/ws_sessions.py` 在 Qwen final 首次失败并写入 failed `transcript_segment` 后自动入队；入队失败只记录脱敏 warning，不阻断 WebSocket 主流程。
- `backend/src/meeting_mvp_backend/main.py` 在 FastAPI lifespan 中按条件启动 worker：需要 `DATABASE_URL`、`REDIS_URL`、非 local 环境且 Qwen final 配置完整；worker 启动时扫描未过期 session 下的 failed/retrying 片段并补加入队，关闭时 cancel task 并关闭 Redis queue。
- `TranslationRetryProcessor` 复用既有 `FinalTranslationProvider`，从数据库读取原英文 final 与目标片段前最近 5 条已完成双语上下文；状态流转为 `failed -> retrying -> completed`，失败时恢复 `failed` 并按退避重入队，达到最大次数后停止自动重试。
- `backend/src/meeting_mvp_backend/usage_events.py` 新增 `translation_final_retry_requested`、`translation_final_retry_failed` 和 `STEP_25_USAGE_EVENT_TYPES`；补译成功沿用 `translation_final_completed` 并标记 `retry=true`，所有 payload 只保存 attempt、长度、sequence、segment id、上下文数量、错误类型等安全元数据。
- `backend/src/meeting_mvp_backend/archives.py` 的 segment 响应新增 `translation_retry_attempts` 和 `translation_retry_exhausted`，从 `usage_event` 派生，不新增表字段。
- `frontend/src/api/archives.ts` 支持 retry metadata 默认值；`frontend/src/archive/ArchivePage.tsx` 显示“等待后台补译”“后台补译中”“补译失败”和“翻译完成”，并在存在未 exhausted failed/retrying 片段时 polling 重新拉取归档；polling 失败保留页面内容，不影响搜索、复制和导出。
- Step 25 不实现公开手动 retry API、重点句增强、时间线增强、新导出能力或数据库 migration；Step 26 已在后续补齐当前重点句增强，Step 27 已在后续补齐会议时间线增强，Step 28 已在后续补齐使用量与成本看板。

Step 26 当前重点句增强已落地：

- 新增 `backend/src/meeting_mvp_backend/key_sentences.py`，使用确定性关键词规则识别行动项、决策、截止时间、风险、预算、负责人、确认、上线和客户升级等重点句；不调用新模型，不新增环境变量。
- `backend/src/meeting_mvp_backend/ws_sessions.py` 在 Qwen final 成功后计算 `is_key_sentence`，写入 `transcript_segment.is_key_sentence`，命中时通过既有 `key_sentence_update` 推送当前重点句；final 失败路径不标记、不推送。
- `backend/src/meeting_mvp_backend/archives.py` 与 `backend/src/meeting_mvp_backend/main.py` 新增 `PATCH /api/archives/{session_id}/segments/{segment_id}/key-sentence?token=...`，复用 archive token 授权并支持归档人工标记/取消重点句。
- `backend/src/meeting_mvp_backend/usage_events.py` 新增 `key_sentence_marked` 和 `STEP_26_USAGE_EVENT_TYPES`；payload 只保存 segment id、sequence、标记状态、来源、翻译状态和文本长度，不保存正文、译文、token、URL、密钥或音频。
- `frontend/src/api/archives.ts` 新增重点句 PATCH client；`frontend/src/archive/ArchivePage.tsx` 新增“只看重点句”筛选和片段标记/取消重点句按钮，失败时显示可访问错误并保留归档内容。
- Step 26 不新增数据库 migration、新 Provider、新导出能力或时间线增强；Step 27 已在后续补齐会议时间线增强。

Step 27 会议时间线增强已落地：

- 新增 `backend/src/meeting_mvp_backend/timeline.py`，统一定义 `segment_final`、`key_sentence`、`export_created`、`exception` 四类时间线节点和安全异常 code 文案映射；不新增模型调用、环境变量或数据库 migration。
- `backend/src/meeting_mvp_backend/ws_sessions.py` 在 final 成功、重点句命中、warning/error 发生时通过既有 `timeline_update` 推送服务端权威时间线；local mock provider 也复用同一生成路径。
- `backend/src/meeting_mvp_backend/archives.py` 的 `GET /api/archives/{session_id}?token=...` 响应新增 `timeline_items`，从 `transcript_segment`、`ExportFile` 和安全 `usage_event` 元数据派生 final、重点句、导出和异常节点。
- 导出节点不暴露 COS object key、下载 URL、token 或正文；异常节点只使用错误 code 映射摘要，不透传 provider 原始异常正文。
- `frontend/src/api/archives.ts` 支持 `timeline_items` schema 并对旧响应默认 `[]`；`frontend/src/App.tsx` 和 `frontend/src/archive/ArchivePage.tsx` 分别增加实时/归档时间线筛选、类型展示和关联 segment 跳转。
- Step 27 不新增使用量与成本看板、成本聚合 API、运营漏斗页面或新指标 UI；Step 28 已在后续补齐使用量与成本看板。

Step 28 使用量与成本看板已落地：

- 新增 `backend/src/meeting_mvp_backend/usage_dashboard.py`，从既有 `meeting_session` 与安全 `usage_event` 元数据聚合每日会议数、有效会议数、活跃匿名用户、ASR 分钟、Qwen interim/final 请求数、估算 token、导出、错误、预算保险丝、漏斗、腾讯会议成功率和估算成本；不新增数据库表或 migration。
- `backend/src/meeting_mvp_backend/main.py` 新增 `GET /api/admin/usage-dashboard?days=...`，`days` 限制 1..90；必须使用 `Authorization: Bearer <DASHBOARD_ADMIN_TOKEN>`，未配置返回 503，缺失/错误返回 401，不支持 query token。
- `backend/src/meeting_mvp_backend/config.py`、`backend/.env.example`、`deploy/.env.example` 与 `memory-bank/environment-variables.md` 新增后端私有看板口令和成本估算配置；`DASHBOARD_ADMIN_TOKEN` 不得进入前端、URL、本地存储、日志、usage event 或项目记忆文档。
- `frontend/src/api/usage-dashboard.ts` 新增看板 API client，只在 Authorization header 发送口令；`frontend/src/admin/UsageDashboardPage.tsx` 新增 `/admin/usage-dashboard` 管理页，口令只保存在 React state，展示 7/30/90 天指标、趋势、漏斗、错误质量和成本预算。
- 看板响应只返回安全聚合数据，不返回英文/中文正文、archive token、archive URL、COS object key、下载 URL、密钥、IP/User-Agent 明文或音频。
- Step 28 不新增 Provider 开关、Provider 配置页面、真实 Provider 对比入口或外部模型调用；Step 29 已在后续补齐 Provider 开关。

Step 29 Provider 开关已落地：

- `backend/src/meeting_mvp_backend/config.py` 新增 `QWEN_ASR_ENABLED`、`QWEN_FINAL_ENABLED`，并复用 `QWEN_INTERIM_ENABLED`；生产必填项按 Qwen ASR/interim/final 开关分别校验，OpenAI STT 仍只在 `OPENAI_STT_ENABLED=true` 时做配置校验。
- `backend/src/meeting_mvp_backend/ws_messages.py` 和 `frontend/src/protocol/websocket-messages.ts` 的 `session_started` 新增安全 `provider_status`，只允许 `enabled`、`disabled`、`local_mock`、`unconfigured`，不得暴露 endpoint、模型名、密钥或账号细节。
- `backend/src/meeting_mvp_backend/ws_sessions.py` 在非 local 且 `QWEN_ASR_ENABLED=false` 时拒绝新会议，不创建 session、不占额度；`QWEN_INTERIM_ENABLED=false` 时跳过中文 interim；`QWEN_FINAL_ENABLED=false` 时保存 failed 英文 final 并入后台补译队列。
- `backend/src/meeting_mvp_backend/main.py` 仅在对应 Qwen 开启时注入真实 ASR/final provider；后台补译 worker 仅在 `QWEN_FINAL_ENABLED=true` 且配置完整时启动。
- `frontend/src/stores/session-store.ts` 保存 provider 状态；`frontend/src/App.tsx` 在实时状态栏展示 ASR/翻译的 disabled/unconfigured/local_mock 提示；`frontend/src/lib/session-notices.ts` 映射 `qwen_asr_disabled`、`qwen_interim_translation_disabled`、`qwen_final_translation_disabled`。
- Step 29 不实现真实 OpenAI STT 音频链路、不新增前端 OpenAI 入口、不新增数据库 migration、不运行真实 Provider smoke；Step 30 已开始但 blocked，Step 31 已建立 CI 检查。

Step 31 CI 检查已落地：

- `.github/workflows/ci.yml` 定义 `frontend`、`backend`、`compose-config` 三个 GitHub Actions jobs。
- `frontend` job 使用 Node.js 24、`npm ci`、Playwright Chromium，运行 `npm run lint`、`npm run test`、`npm run build`、`npm run test:e2e`。
- `backend` job 使用 `backend/.python-version`、uv 和 `backend/uv.lock`，运行 `uv sync --locked`、`uv run ruff check .`、`uv run mypy .`、`uv run pytest`。
- `compose-config` job 使用 `deploy/.env.example` 运行 `docker compose --env-file deploy/.env.example -f deploy/docker-compose.yml config --quiet`，只校验配置，不启动容器。
- CI workflow 顶层权限为 `contents: read`，不配置 secrets，不使用 SSH/scp/rsync，不自动部署，不运行 production migration 或真实 Qwen/COS/Provider smoke。
- GitHub Actions 首轮 push CI 已通过：`codex/step31-ci-checks` 分支 run `26148035200` 中 `Docker Compose config`、`Backend`、`Frontend` jobs 均为 success。
- Step 31 不修改运行时 API、WebSocket schema、数据库 schema、环境变量清单、前端公开配置或业务代码；Step 32 必须等待用户明确允许后再开始。

核心 WebSocket 请求消息：

- `session_start`
- `session_resume`
- `audio_chunk`
- `heartbeat`
- `session_stop`

核心 WebSocket 响应消息：

- `session_started`
- `session_resumed`
- `quota_update`
- `audio_status`
- `asr_interim`
- `asr_final`
- `translation_interim`
- `segment_final`
- `key_sentence_update`
- `timeline_update`
- `warning`
- `error`
- `session_closed`

## 11. 验收、指标与测试

MVP 需要同时判断“有人用了”和“是否值得继续做”。指标包括：

- 激活指标：首次访问到创建会议、首次有效音频捕获、首场有效会议。
- 核心使用指标：有效会议完成率、平均有效会议时长、final 片段生成率、导出率。
- 质量指标：英文 final 可读性、中文 final 满意度、中文 final 延迟、Provider 错误率、腾讯会议可用率。
- 留存指标：次日/7 日复用、同一用户第二场会议比例。
- 成本指标：每有效会议成本、每分钟成本、预算保险丝触发次数。

漏斗分析：

- 漏斗 1：首次使用，定位用户卡在打开、授权、捕获、建会、看到首条结果的哪一步。
- 漏斗 2：会议质量，定位音频、STT、interim、final、归档链路是否稳定。
- 漏斗 3：价值验证，定位用户是否查看归档、搜索、复制、导出、复用。

常用验证命令：

- 前端：`npm run lint`、`npm run test`、`npm run build`、`npm run test:e2e`。
- 后端：在 `backend/` 内执行 `uv run python --version`、`uv run ruff check .`、`uv run mypy .`、`uv run pytest`；数据库步骤完成后再执行 `uv run alembic upgrade head`。
- 后端本地默认 `uv run pytest` 会排除 `integration` 标记；真实 PostgreSQL/Redis/Qwen 集成测试需在 Lighthouse/CI 中执行 `uv run pytest -o addopts= -m integration`，也可按步骤单独运行 `tests/integration/test_database_schema.py`、`tests/integration/test_anonymous_clients_integration.py`、`tests/integration/test_quota_redis_integration.py`、`tests/integration/test_qwen_realtime_asr_smoke.py`、`tests/integration/test_qwen_interim_translation_smoke.py` 或 `tests/integration/test_qwen_final_translation_smoke.py`；Qwen ASR smoke 需要 `RUN_QWEN_ASR_SMOKE=1`、真实 Qwen ASR 环境变量和测试音频 manifest，Qwen interim smoke 需要 `RUN_QWEN_INTERIM_SMOKE=1` 和真实 Qwen 文本模型环境变量，Qwen final smoke 需要 `RUN_QWEN_FINAL_SMOKE=1` 和真实 Qwen 文本模型环境变量。
- 云端部署：`docker compose config`、`docker compose up -d`、`docker compose ps`。
- 本机若默认 npm cache 遇到 `EPERM` 权限错误，可临时设置 `$env:npm_config_cache='D:\meeting_mvp\.cache\npm'`；该目录已被根目录 `.gitignore` 忽略。

## 12. 开发约定

- 先按 `memory-bank/implementation-plan.md` 的步骤推进，不跳过每一步的验证测试和预期结果。
- 每次改动前先确认当前工作区状态，避免覆盖用户未提交更改。
- 不要擅自提交、推送或创建 PR，除非用户明确要求。
- 如果新增项目事实、环境事实、Provider 策略或部署边界，必须更新本文件。
- Step 30 已获用户允许并开始建立兼容性矩阵资产，但因真实 HTTPS/WSS + Qwen ASR 测试目标不可用而阻塞；用户已在 2026-05-20 明确覆盖 Step 30 顺序门禁允许执行 Step 31，但不得记录 Step 30 通过。
- Step 31 已建立 CI 检查；CI 通过不代表 Step 30 兼容性矩阵通过，也不代表 Step 32 生产部署演练通过。在用户明确允许前，不得开始 Step 32。
- 若文档之间存在冲突，以最近的用户明确决策和 `memory-bank/` 当前文档为准，并在本文件记录冲突处理结论。
