# AGENTS.md

本文件是 Codex/AI 开发者在本仓库工作的项目记忆。每次学习到关于项目的新信息，都要同步更新本文件。写任何代码前必须完整阅读 `memory-bank/2026-04-24-meeting-mvp-design.md` 和 `memory-bank/architecture.md`，每完成一个重要功能或里程碑后，必须更新 `memory-bank/architecture.md`。优先使用中文，保持结构清晰；不要写入任何密钥、token、私钥内容或用户隐私数据。

## 1. 仓库与文档现状

- 本地仓库根目录：`D:\meeting_mvp`。
- GitHub 远端：`https://github.com/Zero-Zero001/meeting_mvp.git`。
- 当前已建立工程目录边界：存在 `frontend/`、`backend/`、`deploy/`、`scripts/`、`tests/`。
- 前端工程已在 `frontend/` 初始化：Vite + React + TypeScript，使用 Tailwind CSS v4、shadcn/ui、lucide-react、Zustand、Vitest、Playwright 和 npm。
- 后端工程已在 `backend/` 初始化：Python 3.12 + FastAPI + uv，包名为 `meeting_mvp_backend`，当前 ASGI 入口为 `meeting_mvp_backend.main:app`，健康检查为 `GET /health`。
- 后端当前已有 `backend/pyproject.toml`、`backend/uv.lock`、`backend/.python-version`；根目录仍没有 `package.json` 或 `pyproject.toml`。
- Step 05 已建立环境变量边界：唯一清单为 `memory-bank/environment-variables.md`；后端示例为 `backend/.env.example`；前端公开示例为 `frontend/.env.example`。
- 前端只能使用 `VITE_*` 公开配置；不得把 Provider、数据库、Redis、COS 密钥加到前端代码或前端构建产物。
- 当前有效产品/技术文档集中在 `memory-bank/`：
  - `memory-bank/2026-04-24-meeting-mvp-design.md`
  - `memory-bank/tech-stack.md`
  - `memory-bank/meeting-prd.md`
  - `memory-bank/implementation-plan.md`
  - `memory-bank/set-up-env.md`
  - `memory-bank/environment-variables.md`
- `memory-bank/architecture.md` 与 `memory-bank/progress.md` 已记录 Step 01 到 Step 05 的基线架构、工程目录边界、前端工程骨架、后端工程骨架、配置边界和执行进度，不再为空文件。
- 工作区曾出现根目录设计文档被删除、`memory-bank/` 新增的状态；不要擅自恢复或覆盖用户改动。

## 2. 产品定位

- 项目目标：开发一个网页会议效率工具，帮助中国职场用户在英语线上会议中实时理解英文发言，并形成完整可追溯的双语记录。
- 第一版重点：高质量优先，允许承担一定 API 成本；先把英语会议场景做准。
- 用户无需登录即可免费使用，通过匿名用户身份做额度控制。
- 默认额度：每个匿名用户每天 40 分钟，单场会议 30 分钟，同一匿名用户最多 1 个活跃会议。
- 第一批测试用户预期：10 到 50 人。
- 成本预算：0 到 500 RMB/月；全站月度预算保险丝初始建议 400 RMB。

## 3. 第一版范围与优先级

- M1-A 必须上线闭环：匿名使用、额度、音频捕获、WebSocket、Google STT、Qwen interim、Qwen final、四区 UI、基础异常、基础归档页。
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

- 英文实时转写主路径：Google Cloud Speech-to-Text v2 streaming。
- 中文 interim 主路径：阿里云百炼 Qwen Flash/Turbo，使用 OpenAI-compatible API。
- 中文 final 主路径：阿里云百炼 Qwen `qwen3.6-max-preview`，默认携带最近 5 个 final 片段作为上下文。
- 环境变量必须包含并区分：
  - `QWEN_INTERIM_MODEL`
  - `QWEN_FINAL_MODEL=qwen3.6-max-preview`
- OpenAI 不作为第一版 M1-A 主路径；由于腾讯云 Lighthouse 当前无法访问官方 `api.openai.com:443`，OpenAI 仅保留为后续备用、质量对比或网络恢复后的扩展项。
- Qwen interim 失败不应阻塞英文转写和 Qwen final；Qwen final 失败时片段进入可重试状态。

## 8. 部署与环境边界

- Windows 本地只做代码编辑、文档修改、Git 操作、前端依赖安装/测试/构建、后端纯单元测试和浏览器测试。
- Windows 本地不安装 Docker、PostgreSQL、Redis。
- Windows 系统 Python 可以是 3.13.9，但后端项目必须通过 `uv` 使用 Python 3.12 的项目级 `.venv`。
- 后端依赖和开发工具必须写入 `pyproject.toml` 并锁定到 `uv.lock`。
- `.python-version` 用于固定后端项目解释器为 Python 3.12，可提交；`.venv` 不提交。
- 所有后端命令使用 `uv run ...`，不要全局 `pip install` 项目依赖或开发工具。
- Docker Compose、PostgreSQL、Redis、Alembic migration、数据库集成测试、Redis 集成测试、生产部署演练都在腾讯云 Lighthouse 或后续 CI 环境执行。
- 真实 Google STT、Qwen、COS smoke test 在 Lighthouse 云端后端容器执行；Windows 本地只跑 mock Provider 和不依赖真实密钥的测试。
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
- 已创建目录：`/opt/meeting_mvp/app`、`/opt/meeting_mvp/secrets`、`/opt/meeting_mvp/data/postgres`、`/opt/meeting_mvp/data/redis`、`/opt/meeting_mvp/backups`、`/opt/meeting_mvp/logs`。
- Docker 和 Docker Compose 已在 Lighthouse 上安装并验证过。
- 生产部署目标：Caddy 服务 Vite 静态前端，并通过 HTTPS/WSS 反向代理 `/api/*` 和 `/ws/*` 到 FastAPI。
- PostgreSQL 和 Redis 通过 Docker Compose 容器运行；5432 和 6379 不对公网开放。
- 80/443 需要等 Caddy 和应用 Compose 部署后再验证。

## 9. 密钥与安全

- 不要把任何密钥写入 Git、前端代码、前端构建产物或 `AGENTS.md`。
- Google STT 服务账号 JSON 在服务器上应位于 `/opt/meeting_mvp/secrets/google-stt-sa.json`，权限 `600 ubuntu ubuntu`。
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

核心 WebSocket 请求消息：

- `session_start`
- `audio_chunk`
- `heartbeat`
- `session_stop`

核心 WebSocket 响应消息：

- `session_started`
- `quota_update`
- `audio_status`
- `asr_interim`
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
- 云端部署：`docker compose config`、`docker compose up -d`、`docker compose ps`。
- 本机若默认 npm cache 遇到 `EPERM` 权限错误，可临时设置 `$env:npm_config_cache='D:\meeting_mvp\.cache\npm'`；该目录已被根目录 `.gitignore` 忽略。

## 12. 开发约定

- 先按 `memory-bank/implementation-plan.md` 的步骤推进，不跳过每一步的验证测试和预期结果。
- 每次改动前先确认当前工作区状态，避免覆盖用户未提交更改。
- 不要擅自提交、推送或创建 PR，除非用户明确要求。
- 如果新增项目事实、环境事实、Provider 策略或部署边界，必须更新本文件。
- 若文档之间存在冲突，以最近的用户明确决策和 `memory-bank/` 当前文档为准，并在本文件记录冲突处理结论。
