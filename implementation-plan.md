# Meeting MVP 实施计划

## 文档目标

本文面向 AI 开发者，基于 `docs/superpowers/specs/2026-04-24-meeting-mvp-design.md`、`tech-stack.md` 和 `meeting-prd.md` 拆解第一版开发工作。每一步都要求小而具体，先验证再继续，严禁在本文中写业务源码或代码片段。

## 依据文档

- `docs/superpowers/specs/2026-04-24-meeting-mvp-design.md`：产品范围、架构、Provider、数据模型、里程碑和验收标准。
- `tech-stack.md`：Vite + React + TypeScript、FastAPI、PostgreSQL、Redis、Tencent COS、Docker Compose、Caddy 等技术栈。
- `meeting-prd.md`：用户画像、WebSocket 消息、字段说明、F01 到 F18 功能清单、测试用例、埋点、成功指标和风险边界。

## 执行规则

- 严格按 M1-A、M1-B、M2、M3 的优先级推进；M1-A 未通过前，不做依赖真实用户的增强功能。
- 每一步完成后必须运行本步骤的验证测试，并记录实际结果。
- 所有 Provider 密钥只能放在后端环境变量或部署环境中，前端不得出现密钥。
- 正式档案只基于英文 final 和中文 final；interim 只用于实时预览。
- 第一版默认不保存原始会议音频。
- 不引入 Next.js SSR、Celery/RabbitMQ、自建 Whisper 生产链路、浏览器插件、桌面客户端、外部 BI SaaS。

## Codex 执行约束

- Codex 全程执行代码开发、文档更新、前端构建、后端纯单元测试和可自动化验证。
- Windows 本地不安装 Docker、PostgreSQL、Redis；本地只运行 Git、Node.js、npm、系统 Python、uv、Chrome/Edge 和不依赖真实数据库的测试。
- Windows 本地系统 Python 可以是 3.13.9，但后端项目必须通过 uv 创建并使用 Python 3.12 的项目级 `.venv`。
- 后端依赖和开发工具必须写入 `pyproject.toml` 并锁定到 `uv.lock`；`.python-version` 用于固定项目解释器为 Python 3.12；`.venv` 不提交 Git。
- 所有后端命令必须通过 `uv run ...` 执行，不使用全局 `pip install` 安装项目依赖或开发工具。
- Docker Compose、PostgreSQL、Redis、Alembic migration、数据库集成测试、Redis 集成测试和生产部署演练必须通过 SSH 在腾讯云 Lighthouse 或后续 CI 环境执行。
- 如果没有 Lighthouse SSH 访问、域名解析、Provider 凭证或 COS 信息，Codex 必须停在对应准备步骤，不得伪造云端验证结果。
- 密钥只进入服务器环境变量、CI secret 或安全配置，不写入 Git，不写入前端构建产物。

## 全局实现顺序

| 阶段 | 目标 | 完成标准 |
|---|---|---|
| M1-A 必须上线闭环 | 匿名使用、额度、音频捕获、WebSocket、Google STT、Qwen interim、OpenAI final、四区 UI、基础异常、final 归档。 | 测试用户能打开网页，捕获会议音频，看到英文和中文结果，并产生可追溯 final 片段。 |
| M1-B 上线后增强 | final 重试、轻量看板、Provider 开关、重点句增强、时间线增强。 | M1-A 跑通后，能降低运营风险并提升可观察性。 |
| M2 会后归档与导出 | 会后记录、搜索、复制、Markdown / JSON 导出、Tencent COS。 | 用户能带走完整双语会议记录。 |
| M3 成本与运营 | 成本估算、漏斗分析、兼容性报告、OpenAI STT 对比入口。 | 产品负责人能判断价值、质量和成本是否值得继续迭代。 |

## 分步指令

### Step 01：确认基线文档和仓库状态

目标：确保实施者基于最新 PRD 和技术栈开始开发。

具体指令：读取三份依据文档，确认当前分支、未提交变更、远端地址和根目录位置；记录 `meeting-prd.md` 中 F01 到 F18 的功能清单作为后续验收索引。

验证测试：运行 `git status --short --branch`、`git remote -v`，并搜索 `meeting-prd.md` 中 `F01` 到 `F18`。

预期结果：当前工作目录为项目根目录，远端指向 `Zero-Zero001/meeting_mvp`，F01 到 F18 均能在 PRD 中找到。

### Step 02：建立工程目录边界

目标：为前端、后端、部署和文档建立清晰边界。

具体指令：创建前端应用目录、后端应用目录、部署目录、脚本目录和测试目录；目录命名应能清楚表达职责，避免再创建嵌套的 `meeting_mvp` 子目录。

验证测试：运行目录列表检查，确认根目录下存在前端、后端、部署、脚本和测试相关目录。

预期结果：后续开发者能直接判断前端、后端、部署文件应放在哪里，且没有重复项目根目录。

### Step 03：初始化前端工程骨架

目标：建立 Vite + React + TypeScript 前端基础。

具体指令：在前端目录初始化 Vite React TypeScript 应用，接入 Tailwind CSS、shadcn/ui、lucide-react、Zustand、Vitest、Playwright，并配置基本 npm scripts。

验证测试：运行 `npm run lint`、`npm run test`、`npm run build`。

预期结果：前端能完成静态构建，单元测试和 lint 命令可执行，构建产物可被 Caddy 静态服务。

### Step 04：初始化后端工程骨架

目标：建立 Python 3.12 + FastAPI 后端基础。

具体指令：在后端目录初始化 uv 项目，创建 `pyproject.toml`、`uv.lock`、`.python-version`，并将项目解释器固定为 Python 3.12；加入 FastAPI、Uvicorn、Pydantic v2、pydantic-settings、SQLAlchemy async、Alembic、psycopg、redis asyncio、httpx、tenacity、structlog、pytest、pytest-asyncio、Ruff、mypy。

验证测试：先运行 `uv python install 3.12`、`uv python pin 3.12`、`uv sync`、`uv run python --version`，再运行 `uv run ruff check .`、`uv run mypy .`、`uv run pytest`。

预期结果：`uv run python --version` 输出 Python 3.12.x；后端检查命令全部从项目 `.venv` 执行；项目能启动最小健康检查服务。

### Step 05：定义环境变量和配置边界

目标：让所有部署配置可由环境变量控制。

具体指令：建立前端公开配置、后端服务配置、Provider 配置、数据库配置、Redis 配置、COS 配置和预算配置的环境变量清单；同时提供示例文件，但不得写入真实密钥。

验证测试：启动后端时缺少必填密钥应得到明确配置错误；使用示例配置启动本地 mock 模式应成功。

预期结果：开发、测试和生产环境可以用同一套配置名称切换，前端不会暴露 Provider 密钥。

### Step 06：建立 Docker Compose 与 Caddy 部署骨架

目标：形成云服务器单机部署基础。

具体指令：配置 PostgreSQL 16、Redis 7、FastAPI 后端、Caddy、前端静态产物的 Docker Compose 拓扑；Caddy 负责 HTTPS/WSS、静态前端、`/api/*` 和 `/ws/*` 代理。PostgreSQL 和 Redis 必须通过 Docker Compose 容器运行，不直接安装到 Lighthouse 宿主机；PostgreSQL 必须挂载持久化 volume 或 `/opt/meeting_mvp/data/postgres`，Redis 必须挂载持久化 volume 或 `/opt/meeting_mvp/data/redis`；5432 和 6379 只允许 Docker 内网服务访问，不映射到公网。

验证测试：通过 SSH 在 Lighthouse 或 CI 环境运行 `docker compose config`，再运行 `docker compose ps` 检查服务状态；检查 PostgreSQL 和 Redis 有持久化挂载；检查 Compose 文件没有把 5432 和 6379 暴露到公网网卡。

预期结果：Compose 配置合法，Caddy 能代理 API 和 WebSocket，PostgreSQL 与 Redis 服务名称可被后端解析；数据库和 Redis 重启容器后仍能保留必要状态；公网不能直接连接 PostgreSQL 或 Redis。

### Step 07：建立数据库迁移和数据模型

目标：落地 PRD 字段说明中的核心表。

具体指令：使用 Alembic 管理 `anonymous_client`、`meeting_session`、`transcript_segment`、`usage_event`、`export_file`，字段语义与 `meeting-prd.md` 保持一致。

验证测试：本地运行不依赖真实数据库的模型和 schema 单元测试；通过 SSH 在 Lighthouse 的 Docker Compose 环境运行 `uv run alembic upgrade head` 和数据库集成测试，确认五张表存在且关键字段可写入和读取。

预期结果：PostgreSQL 能保存匿名用户、会议会话、final 片段、埋点事件和导出文件。

### Step 08：实现 F01 匿名用户初始化

目标：让免登录用户拥有稳定匿名身份。

具体指令：前端首次访问生成并保存 `client_id`；后端收到额度请求时创建或更新 `anonymous_client`，保存 IP hash、User-Agent hash、首次访问和最近访问时间。

验证测试：运行前端状态测试和后端匿名用户接口测试；手动清空浏览器本地存储后重新访问页面。

预期结果：首次访问会生成新 `client_id`，再次访问复用同一身份；服务端不保存明文 IP。

### Step 09：实现 F02 额度与预算校验

目标：控制每日 40 分钟、单场 30 分钟、同用户并发 1 场和全站预算保险丝。

具体指令：用 Redis 管理当日额度、活跃会话、单场上限和预算保险丝状态；服务端按 Asia/Shanghai 自然日刷新匿名额度。

验证测试：本地运行额度纯逻辑单元测试，覆盖额度充足、额度耗尽、并发冲突、单场上限、预算保险丝触发；通过 SSH 在 Lighthouse 运行 Redis 集成测试，确认真实 Redis 可写入、读取、过期和清理 active session。

预期结果：额度通过时允许开始会议；额度或预算不满足时拒绝新会话，并保留已有归档查看能力。

### Step 10：实现 WebSocket 消息 schema

目标：让前后端共享可测试的实时消息契约。

具体指令：定义 `session_start`、`audio_chunk`、`heartbeat`、`session_stop`、`quota_update`、`audio_status`、`asr_interim`、`translation_interim`、`segment_final`、`key_sentence_update`、`timeline_update`、`warning`、`error`、`session_closed` 的消息结构和校验规则。

验证测试：运行前后端协议解析测试，分别验证合法消息通过、缺失必填字段失败、未知消息类型失败、binary 音频帧被识别。

预期结果：协议变更能被测试捕获，前后端不会因消息字段歧义导致运行时错误。

### Step 11：实现 F05 WebSocket 会话编排

目标：建立、保持、关闭实时会议会话。

具体指令：后端 WebSocket endpoint 接收 `session_start`，完成额度校验和会话创建；接收 `heartbeat` 保活；接收 `session_stop` 时关闭 Provider、结算额度、清理 Redis active session。

验证测试：本地使用 mock Redis 或内存替身运行 WebSocket 行为测试；通过 SSH 在 Lighthouse 运行真实 Redis WebSocket 集成测试，覆盖正常开始、心跳保持、用户停止、浏览器断开、重复会话拒绝。

预期结果：会话生命周期可控；断开后不会永久占用并发；已归档片段不丢失。

### Step 12：实现前端实时会议工作台骨架

目标：第一屏就是可工作的会议工具页。

具体指令：构建顶部状态栏、英文原文区、中文翻译区、当前重点句区、会议时间线区；状态栏包含捕获入口、捕获模式、音频状态、剩余额度、Provider 状态和结束会议入口。

验证测试：运行组件测试和 Playwright smoke test，确认四个区域存在，状态栏控件可被定位，移动和桌面视口无文本重叠。

预期结果：用户打开页面后能直接开始会议，不出现营销页或无关介绍页。

### Step 13：实现 F03 会议音频捕获

目标：支持会议标签页音频优先，系统音频降级。

具体指令：前端使用浏览器屏幕共享能力引导用户选择会议标签页并共享音频；捕获失败或无音频时提示切换系统音频；记录平台、浏览器、捕获模式和授权结果。

验证测试：在 Windows Chrome 和 Edge 上分别测试 Google Meet、Teams Web、Zoom Web、腾讯会议网页版；对腾讯会议单独测试标签页音频和系统音频。

预期结果：至少能通过标签页或系统音频跑通有效会议；腾讯会议标签页失败时允许系统音频完成 MVP 验证，并记录为降级路径。

### Step 14：实现 F04 音频前处理

目标：浏览器侧输出 Google STT 友好的 mono PCM16 音频帧。

具体指令：前端用 Web Audio API 和 AudioWorklet 将捕获音频转换为单声道 PCM16，并通过 WebSocket binary frame 持续上传；静音时不应开始正式消耗额度。

验证测试：运行音频处理单元测试，验证采样率、声道、音量电平、静音检测和 binary frame 发送节奏；手动测试会议无声 30 秒。

预期结果：后端持续收到稳定音频帧；无有效音频时前端提示检查共享音频，不消耗会议额度。

### Step 15：实现本地 mock Provider 链路

目标：在真实 Provider 凭证未配置时也能开发和测试主流程。

具体指令：提供 mock STT、mock Qwen、mock OpenAI final，用固定节奏输出英文 interim、英文 final、中文 interim、中文 final 和 Provider 错误。

验证测试：运行本地端到端测试，使用 mock Provider 从开始会议到归档生成完整双语片段。

预期结果：开发者无需真实 API 也能验证 UI、WebSocket、归档、异常和埋点链路。

### Step 16：实现 F06 英文实时转写

目标：接入 Google Speech-to-Text v2 streaming 主链路。

具体指令：后端创建 Google STT streaming 会话，转发 PCM16 音频帧，接收英文 interim 和英文 final；Google STT 失败时发送 `error` 并清理会话。

验证测试：使用真实 Google STT 凭证运行英文音频测试，确认 10 秒内出现英文 interim，停顿后产生英文 final。

预期结果：英文 interim 实时显示，英文 final 稳定追加，并能进入中文 final 流程。

### Step 17：实现 F07 中文 interim

目标：用 Qwen Flash/Turbo 生成低成本临时中文理解。

具体指令：后端仅对节流后的英文 interim 请求 Qwen；中文 interim 标记为临时状态，不写入正式归档；Qwen 失败不阻塞英文转写和中文 final。

验证测试：运行 Qwen 成功、节流、失败三类测试；前端检查中文 interim 样式与 final 明显区分。

预期结果：用户能看到临时中文理解；请求频率可控；失败时主链路继续运行。

### Step 18：实现 F08 中文 final

目标：用 OpenAI 文本模型生成正式中文翻译并归档。

具体指令：当英文 final 出现时，后端携带当前片段和最近 3 到 5 个 final 上下文请求 OpenAI；保存英文 final、中文 final、时间戳、序号和翻译状态。

验证测试：运行中文 final 单元测试和真实 Provider smoke test，检查语义准确、顺序稳定、上下文传递、失败状态。

预期结果：中文 final 表达自然，适合中国职场阅读；成功片段进入 `transcript_segment`。

### Step 19：实现 F09 四区实时 UI 更新

目标：让英文、中文、重点句、时间线四区独立更新。

具体指令：前端根据 WebSocket 消息分别更新英文原文区、中文翻译区、当前重点句区和会议时间线区；interim 可替换，final 只追加。

验证测试：运行前端状态测试和 Playwright 测试，模拟 `asr_interim`、`translation_interim`、`segment_final`、`key_sentence_update`、`timeline_update`。

预期结果：任一区域更新失败不阻塞其他区域；正式档案只依赖 final 片段。

### Step 20：实现 F16 异常与降级提示

目标：用户遇到问题时知道下一步怎么做。

具体指令：为捕获失败、无音频、额度不足、Provider 错误、WebSocket 断开、导出失败、预算保险丝触发提供明确提示；腾讯会议标签页音频失败时引导系统音频降级。

验证测试：运行异常场景测试，覆盖 PRD 的 TC-008、TC-009、TC-011、TC-015、TC-017、TC-022、TC-023。

预期结果：异常不会丢失已归档内容；可恢复问题用 `warning`，不可继续问题用 `error` 和 `session_closed`。

### Step 21：实现 usage_event 埋点基础

目标：为漏斗、质量和成本分析收集基础事件。

具体指令：后端写入 `client_created`、`quota_checked`、`capture_started`、`capture_failed`、`audio_detected`、`session_started`、`asr_interim_received`、`asr_final_received`、`translation_interim_requested`、`translation_final_completed`、`segment_archived`、`provider_error`、`quota_exhausted`、`budget_fuse_triggered`、`session_closed`。

验证测试：运行事件写入测试，确认每个事件包含 `client_id`、可选 `session_id`、`event_type`、`payload` 和 `created_at`，且不保存原始音频和密钥。

预期结果：首次使用漏斗和会议质量漏斗能从事件表计算。

### Step 22：实现 F10 会后双语归档

目标：让用户会后按时间顺序回看 final 片段。

具体指令：构建会后归档页和查询 API，按 `sequence` 或时间戳返回英文 final、中文 final、时间戳、翻译状态、重点句标记和结束原因。

验证测试：运行归档 API 测试和前端归档页测试，覆盖正常结束、额度结束、Provider 错误结束和 WebSocket 断开。

预期结果：无论会话如何结束，已归档 final 片段都能查看，异常结束原因清晰可见。

### Step 23：实现 F11 搜索与复制

目标：让会后记录可进入用户工作流。

具体指令：归档页支持按英文、中文、时间戳搜索片段；片段复制时包含时间、英文原文和中文翻译；记录搜索和复制事件。

验证测试：运行搜索测试、复制测试和价值漏斗事件测试。

预期结果：用户能快速定位片段并复制到工作文档；`archive_searched` 和 `segment_copied` 可被统计。

### Step 24：实现 F12 Markdown / JSON 导出

目标：生成可带走的双语会议文件。

具体指令：后端按 final 片段顺序生成 Markdown 和 JSON 导出文件，上传腾讯 COS，写入 `export_file`，返回下载或访问地址。

验证测试：运行导出测试，覆盖 Markdown、JSON、空归档拒绝、COS 上传失败、导出事件记录。

预期结果：导出文件包含 session 信息和双语 final 片段；COS 失败时提示重试并记录 `export_failed`。

### Step 25：实现 F13 final 翻译重试

目标：补齐 OpenAI final 失败片段。

具体指令：为 `translation_status=failed` 的片段提供手动重试或后台补译；重试成功后更新中文 final 和状态，失败时保留原因和次数。

验证测试：运行重试测试，覆盖首次失败、重试成功、重复失败、归档顺序不变。

预期结果：失败片段不会破坏归档；补译成功后前端自动显示正式中文 final。

### Step 26：实现 F17 当前重点句增强

目标：提升实时阅读时的关键信息抓取能力。

具体指令：M1-A 先展示最新 final 作为当前重点句；M1-B 支持模型或规则提取重点句，并允许人工标记重点片段。

验证测试：运行重点句更新测试，验证最新 final、自动提取、人工标记、归档保留 `is_key_sentence`。

预期结果：当前重点句通过 `key_sentence_update` 推送，归档页能筛选或识别重点片段。

### Step 27：实现 F18 会议时间线增强

目标：让用户按时间快速定位会议过程。

具体指令：M1-A 时间线展示 final 片段；M1-B 增加重点句节点、导出节点、异常节点、筛选和跳转到关联 segment。

验证测试：运行时间线测试，模拟 final、重点句、导出、异常四类节点。

预期结果：时间线节点包含时间点、类型、摘要和关联 segment ID，前端点击节点能定位对应片段。

### Step 28：实现 F14 使用量与成本看板

目标：判断产品价值和成本是否可控。

具体指令：基于 `usage_event` 和 Provider 用量记录，展示每日会议数、STT 分钟数、Qwen 请求和 token、OpenAI 请求和 token、日成本、月成本、错误率、延迟、腾讯会议成功率。

验证测试：运行看板聚合测试，使用固定事件样本计算激活指标、核心使用指标、质量指标、留存指标和成本指标。

预期结果：产品负责人能看到成本是否接近 400 RMB 保险丝阈值，以及用户卡在哪个漏斗步骤。

### Step 29：实现 F15 Provider 开关

目标：支持 Provider 降级、关闭和实验入口。

具体指令：后端用配置控制 Google STT、OpenAI STT、Qwen interim、OpenAI final 的启停；前端只展示服务状态和可执行提示，不暴露密钥。

验证测试：运行 Provider 开关测试，覆盖关闭 Qwen、关闭 OpenAI final、启用 OpenAI STT 对比入口、配置缺失。

预期结果：单个 Provider 关闭时，系统能按 PRD 定义降级；关闭 Qwen 不影响英文转写和中文 final。

### Step 30：完成兼容性测试矩阵

目标：明确四个会议平台在 Chrome 和 Edge 的捕获结果。

具体指令：按 PRD 兼容性矩阵测试 Google Meet、Teams Web、Zoom Web、腾讯会议网页版；分别记录浏览器、版本、平台、捕获模式、授权结果、音频检测、首条英文 interim 延迟、final 片段数量、失败码。

验证测试：人工执行兼容性测试并录入结果；腾讯会议必须分别测试标签页音频和系统音频。

预期结果：每个平台都有明确结论；腾讯会议可归类为 `tab_audio_supported`、`system_audio_only` 或 `unsupported`。

### Step 31：建立 CI 检查

目标：防止后续提交破坏基础质量。

具体指令：配置 GitHub Actions 执行前端 lint、前端测试、前端构建、后端 Ruff、后端 mypy、后端 pytest、Docker Compose 配置检查。

验证测试：推送分支或本地触发 CI 等价命令，确认所有检查能运行并失败即阻塞合并。

预期结果：主分支不会合入无法构建、类型错误、测试失败或 Compose 配置非法的变更。

### Step 32：完成生产部署演练

目标：在腾讯云 Lighthouse 上验证单机部署可行。

具体指令：部署 Docker Compose、PostgreSQL、Redis、FastAPI、Caddy 和前端静态产物；后端容器使用 `uv.lock` 锁定依赖并运行 Python 3.12，避免本地系统 Python 3.13.9 与生产环境依赖漂移；配置 HTTPS/WSS、Provider 凭证、COS、预算保险丝和健康检查。部署前创建 PostgreSQL 备份目录，部署后执行一次 PostgreSQL 备份和恢复演练；Redis 只保存短期状态，不能作为正式会议档案来源。

验证测试：通过 SSH 在 Lighthouse 运行部署检查，访问 HTTPS 页面，测试 `/api` 健康检查、`/ws` WebSocket、PostgreSQL migration、Redis 连接、Provider smoke test、COS 导出；执行一次 PostgreSQL 备份文件生成检查和恢复演练检查；确认 5432、6379 不对公网开放。

预期结果：生产环境可通过 HTTPS 打开工具页，WebSocket 使用 WSS，核心链路能跑通至少一场有效会议；PostgreSQL 有可用备份，恢复流程可验证，Redis 状态丢失不会影响已归档 final 片段。

### Step 33：执行上线验收

目标：确认 MVP 可以给 10 到 50 名测试用户试用。

具体指令：按 `meeting-prd.md` 的 TC-001 到 TC-026 执行验收，重点检查 M1-A 闭环、腾讯会议降级、额度、异常、归档、导出、埋点和预算保险丝。

验证测试：逐项记录 TC-001 到 TC-026 的通过或失败结果，并补充浏览器、平台、Provider、错误码和截图证据。

预期结果：M1-A 必须全部通过；M1-B、M2、M3 未完成项不能阻塞 M1-A 小范围上线，但必须在发布说明中标注状态。

## 覆盖关系

| PRD 功能 | 覆盖步骤 |
|---|---|
| F01 匿名用户初始化 | Step 08 |
| F02 额度与预算校验 | Step 09 |
| F03 会议音频捕获 | Step 13、Step 30 |
| F04 音频前处理 | Step 14 |
| F05 WebSocket 会话编排 | Step 10、Step 11 |
| F06 英文实时转写 | Step 16 |
| F07 中文 interim | Step 17 |
| F08 中文 final | Step 18 |
| F09 四区实时 UI | Step 12、Step 19 |
| F10 会后双语归档 | Step 22 |
| F11 搜索与复制 | Step 23 |
| F12 Markdown / JSON 导出 | Step 24 |
| F13 final 翻译重试 | Step 25 |
| F14 使用量与成本看板 | Step 21、Step 28 |
| F15 Provider 开关 | Step 29 |
| F16 异常与降级提示 | Step 20 |
| F17 当前重点句增强 | Step 26 |
| F18 会议时间线增强 | Step 27 |

## 最终验收清单

- M1-A：匿名初始化、额度、捕获、音频处理、WebSocket、Google STT、Qwen interim、OpenAI final、四区 UI、基础归档、异常提示全部通过。
- M1-B：final 重试、看板、Provider 开关、重点句增强、时间线增强有独立测试。
- M2：归档、搜索、复制、Markdown / JSON 导出和 COS 上传通过。
- M3：漏斗、成本、兼容性和 Provider 状态可观察。
- 安全：前端无 Provider 密钥，不保存原始会议音频，不保存明文 IP。
- 成本：每日 40 分钟、单场 30 分钟、并发 1 场、400 RMB 预算保险丝可验证。
