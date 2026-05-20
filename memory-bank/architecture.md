# Meeting MVP 架构记录

## 2026-05-04 Step 01 基线架构洞察

### 当前仓库状态

- 仓库根目录为 `D:\meeting_mvp`。
- Git 远端为 `https://github.com/Zero-Zero001/meeting_mvp.git`。
- 当前应用工程目录边界已建立；根目录下已有 `frontend/`、`backend/`、`deploy/`、`scripts/`、`tests/`；前端工程骨架已初始化，后端工程骨架尚未初始化。
- 当前有效产品、技术、部署和实施依据集中在根目录 `meeting-prd.md` 与 `memory-bank/`。
- PRD 和验收索引已重新定位到项目根目录 `meeting-prd.md`，便于作为顶层产品依据引用。
- Step 01 完成基线确认和文档记录；Step 02 已建立工程目录边界；Step 03 已初始化前端工程骨架，未进入 Step 04。

### 目标架构概览

Meeting MVP 第一版采用前后端分离和单机 Docker Compose 部署：

- 前端：Vite + React + TypeScript，静态产物由 Caddy 服务。
- 实时音频：浏览器通过 `getDisplayMedia` 捕获会议标签页或系统音频，使用 Web Audio API / `AudioWorklet` 转为 16 kHz mono PCM16，并通过 WebSocket binary frame 上传。
- 后端：Python 3.12 + FastAPI 负责编排 WebSocket 会话、额度、Provider 调用、归档、导出和埋点。
- 英文 STT：Google Cloud Speech-to-Text v2 streaming 为 M1-A 主路径。
- 中文翻译：Qwen Flash/Turbo 负责中文 interim，Qwen `qwen3.6-max-preview` 负责中文 final。
- 存储：PostgreSQL 16 保存正式数据，Redis 7 保存短期会话和额度状态，Tencent COS 保存导出文件。
- 入口：Caddy 提供 HTTPS/WSS，服务静态前端，并反向代理 `/api/*` 和 `/ws/*` 到 FastAPI。

### 文件与目录作用

| 路径 | 当前作用 |
|---|---|
| `AGENTS.md` | Codex/AI 开发者项目记忆，记录仓库规则、产品边界、技术栈、Provider 策略、部署边界和安全要求。 |
| `README.md` | 仓库基础说明文件，当前不作为主要产品或技术设计来源。 |
| `.gitignore` | Git 忽略规则，后续应确保 `.venv`、依赖缓存、构建产物和密钥文件不被提交。 |
| `docs/` | 可放补充设计、执行计划或对外说明；当前有效产品和技术设计仍以 `memory-bank/` 为准。 |
| `frontend/` | 已初始化的 Vite + React + TypeScript 前端工程目录，后续承载实时会议工作台、归档页、前端状态管理、音频捕获和前端测试。 |
| `frontend/README.md` | 前端目录占位和边界说明；当前不代表前端工程已初始化。 |
| `backend/` | 后端工程边界目录；后续 Step 04 初始化 Python 3.12 + FastAPI + uv 工程，承载 API、WebSocket、Provider、数据库、Redis、归档和导出逻辑。 |
| `backend/README.md` | 后端目录占位和边界说明；当前不代表后端工程已初始化。 |
| `deploy/` | 部署配置边界目录；后续 Step 06 放置 Docker Compose、Caddy 和云端部署配置。 |
| `deploy/README.md` | 部署目录占位和安全边界说明；禁止放置真实密钥或生产 `.env`。 |
| `scripts/` | 辅助脚本边界目录；后续放置本地验证、部署辅助、数据维护或一次性运维脚本。 |
| `scripts/README.md` | 脚本目录占位和安全边界说明；脚本不得写入或打印密钥。 |
| `tests/` | 跨端测试、验收资产和集成测试说明边界目录；前后端单元测试优先随各自工程组织。 |
| `tests/README.md` | 测试目录占位和边界说明；真实外部服务测试应在 Lighthouse 或 CI 环境执行。 |
| `memory-bank/` | 当前项目事实、设计和执行依据的核心目录。 |
| `memory-bank/2026-04-24-meeting-mvp-design.md` | 正式设计文档，定义产品定位、范围、核心链路、Provider、WebSocket、数据模型、部署和验收标准。 |
| `memory-bank/tech-stack.md` | 技术栈推荐，明确前端、音频、后端、Provider、存储、部署、工具链和 V1 不推荐方案。 |
| `meeting-prd.md` | PRD 和验收索引，包含用户画像、功能清单 F01-F18、字段说明、测试用例 TC-001 到 TC-026、埋点和风险。 |
| `memory-bank/implementation-plan.md` | 分步实施计划，规定从 Step 01 到 Step 33 的执行顺序、验证命令和预期结果。 |
| `memory-bank/set-up-env.md` | 开发与部署环境准备手册，定义 Windows 本地、Lighthouse 云端、Provider 凭证、COS、环境变量和验证边界。 |
| `memory-bank/progress.md` | 开发进度记录；从 Step 01 起记录已完成工作、验证结果和后续注意事项。 |
| `memory-bank/architecture.md` | 架构记录；从 Step 01 起沉淀当前架构洞察、目录职责和后续里程碑后的架构变化。 |

### 后续架构约束

- 下一步只能在用户明确允许后执行 Step 04：初始化 `backend/` 工程；当前不得创建 `backend/pyproject.toml`、`backend/uv.lock` 或项目级 `.venv`。
- 前端不得暴露任何 Provider 密钥。
- 第一版默认不保存原始会议音频，只保存 final 文本档案和导出文件。
- 服务端只保存 `archive_token` hash，不保存明文 token。
- Windows 本地不安装 Docker、PostgreSQL、Redis；相关验证在腾讯云 Lighthouse 或后续 CI 环境执行。

## 2026-05-04 Step 03 前端工程骨架

### 当前架构状态

- `frontend/` 已从目录占位升级为 Vite + React + TypeScript 前端工程。
- 前端当前只实现最小可验证会议工作台骨架，用于验证依赖链路、状态管理、构建和测试；正式音频捕获、WebSocket 协议、四区实时数据流和归档页仍在后续步骤实现。
- `backend/` 仍保持 Step 02 的边界目录状态，尚未初始化 Python/FastAPI/uv 工程；当前不存在 `backend/pyproject.toml` 和 `backend/uv.lock`。
- 仓库根目录仍不作为 Node 或 Python 工程根；当前不存在根目录 `package.json` 和根目录 `pyproject.toml`。
- 前端构建产物位于 `frontend/dist/`，该目录由 `.gitignore` 忽略，后续部署时由 Caddy 服务静态文件。
- 前端代码不得包含 Google STT、Qwen、COS 或任何后端生产密钥；Provider 调用仍应通过后续 FastAPI 后端编排。

### 前端文件作用

| 路径 | 当前作用 |
|---|---|
| `frontend/README.md` | 前端工程说明，记录当前技术栈、边界、常用 npm 命令和本机 npm cache 权限绕过方式。 |
| `frontend/.gitignore` | 前端本地忽略规则，排除 `node_modules`、`dist`、`test-results`、`playwright-report` 等依赖、构建和测试产物。 |
| `frontend/package.json` | 前端 npm 工程清单，声明 Vite/React/Tailwind/shadcn/lucide/Zustand/Vitest/Playwright 依赖，并提供 `dev`、`lint`、`test`、`build`、`test:e2e`、`preview` scripts。 |
| `frontend/package-lock.json` | npm 依赖锁文件，用于固定前端依赖解析结果。 |
| `frontend/index.html` | Vite HTML 入口，设置 `zh-CN` 页面语言、favicon 和 React 挂载点 `#root`。 |
| `frontend/vite.config.ts` | Vite 配置，接入 React 插件、Tailwind CSS v4 Vite 插件、`@` 路径别名和 Vitest `jsdom` 测试环境。 |
| `frontend/tsconfig.json` | TypeScript 根配置，串联 app/node 子配置并声明 `@/* -> ./src/*` 路径映射。 |
| `frontend/tsconfig.app.json` | 浏览器应用 TypeScript 配置，覆盖 `src/` 应用代码并从生产构建中排除测试文件。 |
| `frontend/tsconfig.node.json` | Node 侧 TypeScript 配置，覆盖 `vite.config.ts` 等配置文件类型检查。 |
| `frontend/eslint.config.js` | 前端 ESLint 扁平配置，启用 TypeScript、React Hooks、React Refresh 规则，并对 shadcn/ui 组件导出模式做局部豁免。 |
| `frontend/components.json` | shadcn/ui 项目配置，定义 Tailwind v4 CSS 入口、neutral base color、lucide 图标库和组件路径别名。 |
| `frontend/playwright.config.ts` | Playwright 配置，当前只配置 Chromium，并通过 `npm run preview` 启动 Vite 预览服务做 smoke test。 |
| `frontend/e2e/app.spec.ts` | Playwright smoke test，验证前端首屏会议工作台能在浏览器中加载并显示关键入口。 |
| `frontend/src/main.tsx` | React 应用挂载入口，引入全局 CSS 并渲染 `App`。 |
| `frontend/src/App.tsx` | 当前最小会议工作台页面，展示英文原文区、中文翻译区、当前重点句区、会议时间线区，以及捕获状态和基础操作按钮。 |
| `frontend/src/App.test.tsx` | React Testing Library 测试，验证工作台骨架渲染和开始捕获按钮的状态变化。 |
| `frontend/src/index.css` | Tailwind CSS v4 与 shadcn/ui 全局样式入口，包含主题变量、基础颜色、字体和 body/html 基础样式。 |
| `frontend/src/components/ui/button.tsx` | shadcn/ui Button 组件，作为后续 UI 控件的基础按钮实现。 |
| `frontend/src/lib/utils.ts` | 通用 `cn` 工具函数，合并 clsx 与 tailwind-merge 的 className 处理。 |
| `frontend/src/stores/session-store.ts` | 最小 Zustand 会话状态 store，当前管理捕获模式、捕获状态和今日剩余额度。 |
| `frontend/src/stores/session-store.test.ts` | Zustand store 单元测试，覆盖开始捕获、结束会议和捕获模式状态更新。 |
| `frontend/src/test/setup.ts` | Vitest 测试初始化文件，引入 `@testing-library/jest-dom/vitest` 断言扩展。 |
| `frontend/public/favicon.svg` | 当前浏览器 favicon 静态资源。 |
| `frontend/public/icons.svg` | 当前公共 SVG 图标资源占位，来自脚手架/组件初始化阶段，后续可按实际品牌和图标策略调整。 |

### Step 03 验证结论

- `npm run lint`、`npm run test`、`npm run build`、`npx playwright install chromium`、`npm run test:e2e` 已通过。
- 防越界检查确认未创建 `backend/pyproject.toml`、`backend/uv.lock`、根目录 `package.json`、根目录 `pyproject.toml`。
- Step 04 尚未开始；后端初始化、数据库、Redis、Provider mock、API/WebSocket 结构均应等待用户明确允许后再执行。

## 2026-05-05 Step 04 后端工程骨架

### 当前架构状态

- `backend/` 已从目录占位升级为 Python 3.12 + FastAPI + uv 后端工程。
- 后端当前只实现最小健康检查服务，用于验证 Python 版本、依赖锁定、ASGI 应用入口、质量工具和本地轻量测试链路。
- 后端包名为 `meeting_mvp_backend`，ASGI 入口为 `meeting_mvp_backend.main:app`。
- `pyproject.toml` 限定 Python `>=3.12,<3.13`，`.python-version` 固定为 `3.12`，`uv.lock` 固定后端依赖解析结果。
- `backend/.venv` 由 `uv sync` 本地生成并被根目录 `.gitignore` 忽略，不进入 Git。
- Step 04 未建立环境变量清单、配置类、示例 env 文件、Alembic migration、Docker Compose、数据库连接、Redis 连接或 Provider mock；这些仍属于后续步骤。
- 仓库根目录仍不作为 Node 或 Python 工程根；当前仍不存在根目录 `package.json` 和根目录 `pyproject.toml`。

### 后端文件作用

| 路径 | 当前作用 |
|---|---|
| `backend/README.md` | 后端工程说明，记录当前边界、常用 uv 命令和最小健康检查入口。 |
| `backend/.python-version` | uv 项目级 Python 版本锁，固定后端使用 Python 3.12。 |
| `backend/pyproject.toml` | 后端项目清单，声明运行依赖、开发依赖、构建配置、Ruff、mypy 和 pytest 配置。 |
| `backend/uv.lock` | uv 依赖锁文件，用于固定后端依赖解析结果。 |
| `backend/src/meeting_mvp_backend/__init__.py` | 后端 Python 包入口，导出当前 FastAPI `app`。 |
| `backend/src/meeting_mvp_backend/main.py` | 当前 ASGI 应用入口，创建 FastAPI app 并提供 `GET /health` 健康检查。 |
| `backend/tests/test_health.py` | 本地轻量测试，使用 `httpx.ASGITransport` 验证 `/health` 响应。 |
| `.gitignore` | 继续作为全仓库忽略规则；Step 04 补充忽略 `.mypy_cache/` 与 `.ruff_cache/`，避免后端质量工具缓存进入 Git。 |

### Step 04 验证结论

- `uv run python --version` 输出 `Python 3.12.11`。
- `uv run ruff check .`、`uv run mypy .`、`uv run pytest` 已通过。
- Uvicorn 本地启动后，`GET http://127.0.0.1:8000/health` 返回 HTTP `200` 和 `{"status":"ok"}`。
- 防越界检查确认未创建根目录 `package.json`、根目录 `pyproject.toml`、`.env`、`.env.example`、Docker Compose 或 Alembic migration。
- Step 05 尚未开始；环境变量清单、配置加载、密钥脱敏和 mock 模式启动边界应等待用户明确允许后再执行。

## 2026-05-05 Step 05 配置边界

### 当前架构状态

- 项目已建立统一环境变量清单：`memory-bank/environment-variables.md`。
- 后端配置由 `pydantic-settings` 统一加载，`APP_ENV=local` 支持 Windows 本地 mock 模式，`staging` / `production` 会强制校验必填配置。
- 后端启动时通过 FastAPI lifespan 加载配置，并用 `structlog` 输出配置项名称和 `set` / `unset` 状态，不输出任何配置值。
- 前端配置边界固定为 Vite `VITE_*` 公开变量；Provider、数据库、Redis、COS 密钥不得进入前端代码或构建产物。
- 示例配置拆分为 `backend/.env.example` 和 `frontend/.env.example`；真实 `.env`、`.env.*` 仍由 `.gitignore` 忽略。
- Step 05 未创建 Docker Compose、Alembic migration、真实数据库/Redis 集成、Provider 客户端或真实密钥文件；这些仍属于后续步骤。

### 配置文件作用

| 路径 | 当前作用 |
|---|---|
| `memory-bank/environment-variables.md` | Step 05 建立的唯一环境变量清单，区分后端私有变量和前端 `VITE_*` 公开变量。 |
| `backend/.env.example` | 后端 local mock 示例配置，覆盖后端配置清单，使用空值或 placeholder，不包含真实密钥。 |
| `backend/src/meeting_mvp_backend/config.py` | 后端配置模型、环境文件解析、生产必填配置校验、OpenAI STT 条件校验和脱敏状态输出。 |
| `backend/src/meeting_mvp_backend/main.py` | FastAPI 应用入口；Step 05 增加 lifespan，在启动时加载配置并输出脱敏配置状态。 |
| `backend/tests/test_config.py` | 后端配置测试，覆盖 local 示例配置、production 缺失配置、OpenAI STT 条件必填和脱敏状态。 |
| `frontend/.env.example` | 前端公开配置示例，只包含 `VITE_APP_ENV`、`VITE_PUBLIC_BASE_URL`、`VITE_API_BASE_URL`、`VITE_WS_BASE_URL`。 |
| `frontend/src/config/public-config.ts` | 前端公开配置读取模块，只映射允许进入浏览器的 `VITE_*` 变量。 |
| `frontend/src/config/public-config.test.ts` | 前端配置边界测试，确认 public config 不包含私有 Provider、数据库、Redis、COS 变量名。 |
| `frontend/src/vite-env.d.ts` | Vite 环境变量类型声明，限制当前前端可读公开配置名。 |
| `.gitignore` | 继续忽略真实 `.env` 与 `.env.*`；Step 05 增加 `!**/.env.example`，允许提交嵌套示例配置。 |
| `backend/README.md` | 后端 README 增加配置边界、mock 示例启动命令和配置相关文件入口。 |

### Step 05 验证结论

- `uv run python --version`、`uv run ruff check .`、`uv run mypy .`、`uv run pytest` 已通过。
- 使用 `MEETING_MVP_ENV_FILE=backend/.env.example` 启动本地后端 mock 模式后，`GET /health` 返回 HTTP `200` 和 `{"status":"ok"}`。
- `APP_ENV=production` 且缺少必填配置时，`load_settings()` 抛出 `SettingsError` 并列出缺失变量名，不输出密钥值。
- `npm run lint`、`npm run test`、`npm run build`、`npm run test:e2e` 已通过。
- 防越界检查确认未创建 Docker Compose、Alembic migration、真实 `.env`、根目录 Node/Python 工程文件。

## 2026-05-05 Step 06 Docker Compose 与 Caddy 部署骨架

### 当前架构状态

- `deploy/` 已从占位目录升级为单机 Docker Compose 部署骨架目录。
- 部署拓扑包含 `postgres`、`redis`、`backend`、`caddy` 四个服务；前端静态产物在 Caddy 镜像构建阶段由 `frontend/Dockerfile` 生成并复制到 `/srv`。
- Caddy 是唯一公网入口，只映射 `80` 和 `443`，负责 HTTPS/WSS、静态前端、`/api/*` 和 `/ws/*` 反向代理。
- PostgreSQL 16 和 Redis 7 通过 Compose 容器运行，不安装到 Lighthouse 宿主机；两者均不发布 `5432` 或 `6379` 到宿主机公网。
- PostgreSQL 数据绑定挂载到 `/opt/meeting_mvp/data/postgres`；Redis 数据绑定挂载到 `/opt/meeting_mvp/data/redis`。
- 后端容器基于 Python 3.12 与 `uv.lock` 构建，运行 `meeting_mvp_backend.main:app`，并通过 Compose 环境变量接收数据库、Redis、Provider、COS、额度和归档配置；Step 16 替换后生产 ASR 改用 Qwen realtime，Compose 不再挂载 Google STT 服务账号 JSON。
- Step 06 只建立部署骨架和配置合法性边界；已在 Lighthouse 上完成 `docker compose config --quiet` 验收，但尚未启动生产容器，尚未执行 Alembic migration，尚未进入 Step 07 数据模型。
- Windows 本地仍不安装 Docker；本地只做静态部署检查和前后端现有测试。
- Lighthouse 远端验收使用用户提供的 SSH 私钥完成；本轮没有输出生产 `.env.production` 内容。

### 部署文件作用

| 路径 | 当前作用 |
|---|---|
| `.dockerignore` | Docker build context 忽略规则，排除 Git、本地缓存、真实 `.env`、虚拟环境、`node_modules`、构建产物和常见密钥文件形态。 |
| `backend/Dockerfile` | 后端容器构建文件；使用 Python 3.12 / uv 镜像，按 `uv.lock` 安装生产依赖，暴露 8000 并启动 Uvicorn。 |
| `frontend/Dockerfile` | 前端/Caddy 容器构建文件；先用 Node 24 执行 `npm ci` 和 `npm run build`，再把 `dist/` 与 `deploy/Caddyfile` 复制进 Caddy 镜像。 |
| `deploy/docker-compose.yml` | 单机部署拓扑；定义 PostgreSQL、Redis、后端、Caddy 服务、健康检查、数据挂载、端口映射和容器网络。 |
| `deploy/Caddyfile` | Caddy 路由配置；以 Vite 静态产物作为根目录，代理 `/api/*` 与 `/ws/*` 到 `backend:8000`。 |
| `deploy/.env.example` | Docker Compose 示例环境变量；只包含 placeholder，用于安全地运行 `docker compose config`，不包含真实密钥。 |
| `deploy/README.md` | 部署目录说明；记录 Step 06 验证命令、端口边界、持久化路径和禁止放置真实密钥的规则。 |

### 网络与数据边界

- 公网入口：仅 `caddy` 服务通过宿主机 `80` 和 `443` 暴露。
- 后端入口：`backend` 不映射宿主机端口，只由 Caddy 通过 Compose 网络访问 `backend:8000`。
- 数据库入口：`postgres` 仅由 Compose 网络内服务访问 `postgres:5432`，不对公网发布端口。
- Redis 入口：`redis` 仅由 Compose 网络内服务访问 `redis:6379`，不对公网发布端口。
- 正式档案仍以未来 PostgreSQL 数据模型为准；Redis 只保存短期状态，不能作为正式会议归档来源。
- 生产真实配置仍应放在服务器安全环境文件中；`deploy/.env.example` 只用于示例和安全配置检查。
- Provider 密钥不进入镜像和 Git；Step 16 替换后 Qwen API key 只通过后端环境变量提供，前端和 Compose 镜像均不包含密钥值。

### Step 06 验证结论

- 本地静态部署检查已确认 Compose 不发布 `5432` / `6379`，只发布 `80` / `443`，并包含 PostgreSQL 与 Redis 持久化挂载路径。
- 后端 `uv run python --version`、`uv run ruff check .`、`uv run mypy .`、`uv run pytest` 已通过。
- 前端 `npm run lint`、`npm run test`、`npm run build`、`npm run test:e2e` 已通过。
- Lighthouse `docker compose --env-file deploy/.env.example -f deploy/docker-compose.yml config --quiet` 已在 `/opt/meeting_mvp/app` 执行通过。
- 远端边界检查已确认只发布 `80` / `443`，不发布 `5432` / `6379`，保留 PostgreSQL 与 Redis 的 `/opt/meeting_mvp/data/*` 挂载路径；Step 16 替换后不再需要后端只读 Google STT 凭据挂载。

## 2026-05-05 Step 07 数据库迁移和数据模型

### 当前架构状态

- 后端已新增 `meeting_mvp_backend.db` 数据层包，使用 SQLAlchemy 2 typed ORM 表达 PostgreSQL 正式档案模型。
- Alembic 已成为后端 schema 变更入口；当前唯一迁移版本为 `20260505_0001_initial_schema`。
- PostgreSQL 正式数据边界已落地为五张核心表：匿名用户、会议会话、final 片段、使用事件和导出文件。
- Redis 未参与 Step 07；后续仍只用于活跃会话、额度、限流、预算保险丝和短期 WebSocket 协调状态。
- `meeting_session` 的初始状态支持 `pending_audio`，用于“检测到有效音频前不正式消耗额度”的后续会话编排。
- 会后归档访问边界已体现在数据模型中：只保存 `archive_token_hash`，不保存明文 `archive_token`。
- 第一版不保存原始音频的边界已体现在 schema 和测试中；Step 07 未新增任何 raw audio/blob/bytes 字段。
- 后端容器构建现在包含 Alembic 和测试文件，Lighthouse 可以通过一次性 backend 容器执行 migration 和数据库集成测试。

### 数据模型文件作用

| 路径 | 当前作用 |
|---|---|
| `backend/src/meeting_mvp_backend/db/__init__.py` | 数据层包入口，标记 `db` 为后端数据库相关模块集合。 |
| `backend/src/meeting_mvp_backend/db/base.py` | SQLAlchemy Declarative `Base` 和统一命名约定，保证索引、外键、唯一约束和主键命名稳定。 |
| `backend/src/meeting_mvp_backend/db/models.py` | 五张核心 ORM 表、枚举、关系、索引和约束定义；是后续仓储层、API、WebSocket 会话编排和归档查询的模型基础。 |
| `backend/src/meeting_mvp_backend/db/session.py` | async SQLAlchemy engine/sessionmaker 创建工具；后续业务代码和集成测试通过 `DATABASE_URL` 创建数据库会话。 |
| `backend/tests/test_database_models.py` | 本地无真实数据库的模型/schema 测试，验证核心表、关键字段、枚举值、JSONB payload、UUID 主键和安全字段边界。 |
| `backend/tests/integration/test_database_schema.py` | Lighthouse PostgreSQL 集成测试，执行真实表反射和五张表关键字段写入/读取。 |

### Alembic 文件作用

| 路径 | 当前作用 |
|---|---|
| `backend/alembic.ini` | Alembic 命令入口配置；本地 `uv run alembic history` 可读取迁移链，真实连接串由 `DATABASE_URL` 注入。 |
| `backend/migrations/env.py` | Alembic runtime 环境；加载后端 `Settings`，读取 `DATABASE_URL`，使用 async engine 执行在线 migration。 |
| `backend/migrations/script.py.mako` | Alembic 新迁移文件模板，保持类型标注和项目格式。 |
| `backend/migrations/versions/20260505_0001_initial_schema.py` | 初始 schema migration；创建五张核心表、PostgreSQL enum、外键、索引和唯一约束。 |

### 表与持久化边界

- `anonymous_client`：保存免登录匿名用户身份、首次/最近访问时间、每日已用分钟、IP hash 和 User-Agent hash；不保存明文 IP。
- `meeting_session`：保存会议会话、平台、捕获模式、会话状态、有效时长、额度消耗、`archive_token_hash` 和 30 天保留期。
- `transcript_segment`：保存按 `session_id + sequence` 唯一排序的英文 final、中文 final、时间戳、重点句和翻译状态；不保存 interim 或原始音频。
- `usage_event`：保存埋点事件和 JSONB payload；payload 仍必须避免密钥、原始音频和隐私明文。
- `export_file`：保存 Markdown/JSON 导出对象 key、短期 URL 字段和导出保留期；COS 对象仍保持私有。

### 部署与验证洞察

- `backend/Dockerfile` 已复制 `alembic.ini`、`migrations/` 和 `tests/`，因此 backend 镜像可直接执行 `uv run alembic upgrade head` 和数据库集成测试。
- Lighthouse Docker build 曾卡在 `uv sync` 依赖下载阶段；加入 `UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple` 与 `UV_HTTP_TIMEOUT=120` 后，Compose backend build 通过。
- Step 07 远端验收使用临时 PostgreSQL 数据目录 `/opt/meeting_mvp/data/postgres_step07`，没有使用 `deploy/.env.example` 的占位密码初始化正式数据目录。
- Step 07 远端验收后已清理临时 PostgreSQL 容器、临时数据目录、临时脚本和远端测试 `.venv`/缓存。
- 当前未启动 Caddy、Redis 或常驻 backend 服务；未进入 Step 08。

### Step 07 验证结论

- 本地 `uv run python --version` 输出 `Python 3.12.11`。
- 本地 `uv run alembic history` 显示 `<base> -> 20260505_0001 (head)`。
- 本地 `uv run ruff check .`、`uv run mypy .`、`uv run pytest` 已通过；pytest 结果为 11 passed、1 integration deselected。
- 前端 `npm run lint`、`npm run test`、`npm run build`、`npm run test:e2e` 已通过。
- Lighthouse `docker compose --env-file .env.production -f deploy/docker-compose.yml build --progress plain backend` 已通过。
- Lighthouse `docker compose --env-file .env.production -f deploy/docker-compose.yml run --rm --no-deps backend uv run alembic upgrade head` 已通过。
- Lighthouse `docker compose --env-file .env.production -f deploy/docker-compose.yml run --rm --no-deps backend uv run --group dev pytest -o addopts= -m integration` 已通过，1 个真实 PostgreSQL 集成测试通过。

## 2026-05-06 Step 08 F01 匿名用户初始化

### 当前架构状态

- F01 匿名用户初始化已形成前后端闭环：浏览器负责生成并持久化稳定 `client_id`，后端负责把该匿名身份 upsert 到 PostgreSQL `anonymous_client` 表。
- 前端本地身份不依赖后端成功返回；如果服务端暂不可用，用户仍能获得本地 `client_id`，工作台显示“稍后重试”的服务端同步状态。
- 后端匿名初始化接口固定为 `POST /api/anonymous-clients`，请求体只接收 UUID 格式的 `client_id`。
- 后端只保存请求 IP 与 User-Agent 的 SHA-256 hash，不保存明文 IP 或明文 User-Agent；响应体也不包含这些请求身份信息。
- `remaining_seconds_today` 当前由 PostgreSQL `anonymous_client.daily_minutes_used` 和 `DAILY_FREE_SECONDS` 计算，仍是 Step 08 的基础值；真实会议消耗、Redis 限流和预算保险丝留给 Step 09。
- 未新增数据库 migration；Step 08 复用 Step 07 已创建的 `anonymous_client` 表。
- FastAPI lifespan 会在配置了 `DATABASE_URL` 时创建 async engine 和 session factory；未配置数据库时匿名初始化接口返回 HTTP 503，`GET /health` 仍可用于本地轻量健康检查。
- Lighthouse 验证继续采用临时 PostgreSQL 数据目录和一次性 backend 容器，未启动 Redis、Caddy 或常驻 backend 服务。

### 后端新增与修改文件作用

| 路径 | 当前作用 |
|---|---|
| `backend/src/meeting_mvp_backend/anonymous_clients.py` | 匿名用户初始化业务服务；负责请求身份 hash、查询或创建 `AnonymousClient`、更新 `last_seen_at` 和 `user_agent_hash`，并返回初始化结果。 |
| `backend/src/meeting_mvp_backend/main.py` | FastAPI 应用入口；Step 08 增加数据库 session factory 初始化、匿名 client 请求/响应模型、匿名服务依赖和 `POST /api/anonymous-clients` 路由。 |
| `backend/tests/test_anonymous_clients_api.py` | 本地 API 单元测试；通过依赖覆盖验证新 client 响应、非法 UUID 422、无 `DATABASE_URL` 返回 503、响应不暴露明文请求身份。 |
| `backend/tests/integration/test_anonymous_clients_integration.py` | Lighthouse PostgreSQL 集成测试；在真实数据库上验证匿名接口首次创建、重复请求更新、hash 字段不保存明文 IP/User-Agent。 |

### 前端新增与修改文件作用

| 路径 | 当前作用 |
|---|---|
| `frontend/src/lib/anonymous-client.ts` | 浏览器匿名身份本地存储工具；从 `localStorage` 读取 `meeting_mvp.client_id`，为空时使用 `crypto.randomUUID()` 生成并写回。 |
| `frontend/src/api/anonymous-clients.ts` | 匿名 client API 客户端；调用 `POST /api/anonymous-clients`，把后端 `client_id`、`daily_free_seconds`、`remaining_seconds_today`、`is_new` 映射为前端状态。 |
| `frontend/src/stores/session-store.ts` | Zustand 会话状态；Step 08 增加匿名身份状态、服务端同步状态、错误信息和 `initializeAnonymousClient()` action。 |
| `frontend/src/App.tsx` | 实时会议工作台首屏；加载时初始化匿名身份，并在状态区展示匿名身份短 ID、今日剩余额度和服务端同步状态。 |
| `frontend/src/lib/anonymous-client.test.ts` | 本地匿名身份工具测试；覆盖首次生成、再次复用、清空存储后生成新 ID 和存储不可用错误。 |
| `frontend/src/stores/anonymous-client-store.test.ts` | Zustand 匿名身份状态测试；覆盖初始化并同步额度、服务端同步失败保留本地 ID、存储不可用进入错误状态。 |

### 接口与数据边界

- 请求：`POST /api/anonymous-clients`，JSON body 为 `{"client_id": "<uuid>"}`。
- 成功响应：`client_id`、`daily_free_seconds`、`remaining_seconds_today`、`is_new`。
- 错误响应：非法 UUID 由 FastAPI/Pydantic 返回 422；未配置 `DATABASE_URL` 返回 503。
- 数据库写入：新匿名用户写入 `client_id`、`first_seen_at`、`last_seen_at`、`created_ip_hash`、`user_agent_hash`；重复初始化只更新最近访问时间和最近 User-Agent hash。
- 安全边界：不保存明文 IP，不保存明文 User-Agent，不读取或输出 Lighthouse SSH 私钥内容，不新增任何前端私有环境变量。

### Step 08 验证结论

- 本地 TDD RED 已覆盖后端匿名接口和前端匿名身份状态，缺少实现时均按预期失败。
- 后端 `uv run python --version`、`uv run ruff check .`、`uv run mypy .`、`uv run pytest` 已通过；pytest 结果为 15 passed、2 integration deselected。
- 前端 `npm run lint`、`npm run test`、`npm run build`、`npm run test:e2e` 已通过；单元测试结果为 5 个测试文件、13 个测试通过。
- Lighthouse 临时 PostgreSQL 环境下 Alembic migration 与 `tests/integration/test_anonymous_clients_integration.py` 已通过，验证真实数据库 upsert 和 hash 边界。
- 远端 Step 08 临时 `.env.step08`、临时数据目录和临时 PostgreSQL 容器已清理。
- Step 09 尚未开始。

## 2026-05-06 Step 09 F02 额度与预算校验

### 当前架构状态

- F02 已落地为后端内部额度服务，不对外暴露新的 REST API，不定义新的 WebSocket 消息 schema；Step 10 尚未开始。
- 额度判定分为纯策略层和 Redis 状态层：纯策略可本地单测，Redis 层只保存短期额度、活跃会话和预算保险丝状态。
- PostgreSQL 仍是正式会议档案来源；Redis 不保存 final 文本、归档 token、导出文件或任何正式会议记录。
- 额度服务以 `client_id` 为匿名用户边界，后续 `session_start` 可复用同一服务完成开始前校验、活跃会话登记、释放和会议消耗累计。
- 拒绝优先级固定为：预算保险丝 > 活跃会话上限 > 每日额度耗尽 > 单场时长上限。
- Asia/Shanghai 自然日是每日额度 key 的日期边界；`used_seconds` key 的 TTL 到下一个上海自然日零点。
- 预算保险丝读取 Redis 中的当月预估成本或显式开关；真实成本写入仍留给后续 usage/cost 步骤。

### 额度模块文件作用

| 路径 | 当前作用 |
|---|---|
| `backend/src/meeting_mvp_backend/quota.py` | Step 09 核心额度模块；定义 `QuotaDecision`、`QuotaDenialReason`、`QuotaSettings`、`QuotaSnapshot`、`QuotaPolicy`、`RedisQuotaStore`、`QuotaService` 和 `create_quota_service_from_settings()`，并集中生成 Redis key 与 Asia/Shanghai TTL。 |
| `backend/tests/test_quota.py` | 本地额度单元测试；覆盖额度充足、每日额度耗尽、同用户并发冲突、单场时长上限、预算保险丝优先级、成本阈值触发、消费秒数封顶和上海自然日 key/TTL。 |
| `backend/tests/integration/test_quota_redis_integration.py` | Lighthouse/CI Redis 集成测试；连接真实 Redis，验证过期活跃会话清理、活跃会话并发限制、消费秒数写入和预算保险丝读取。 |

### Redis key 与状态边界

| Redis key | 数据结构 | 当前用途 |
|---|---|---|
| `meeting_mvp:quota:{client_id}:{yyyyMMdd}:used_seconds` | string integer | 保存匿名用户在 Asia/Shanghai 当日已消耗秒数，写入时封顶到 `DAILY_FREE_SECONDS`，TTL 到下一个上海自然日零点。 |
| `meeting_mvp:active_sessions:{client_id}` | sorted set | 保存匿名用户活跃会话，member 是 `session_id`，score 是过期 epoch；每次校验前删除已过期 member。 |
| `meeting_mvp:budget:{yyyyMM}:estimated_cost_cents` | string integer | 保存当月全站预估成本，单位分；达到 `BUDGET_FUSE_RMB * 100` 时拒绝新会话。 |
| `meeting_mvp:budget:{yyyyMM}:fuse_triggered` | string flag | 显式预算保险丝，值为 `1` 时无条件拒绝新会话。 |

### 服务方法边界

- `check_start_allowed(client_id)`：读取 Redis 快照，返回是否允许开始、今日剩余秒数和拒绝原因。
- `reserve_active_session(client_id, session_id)`：登记活跃会话，达到同用户并发上限时拒绝。
- `release_active_session(client_id, session_id)`：从活跃会话 sorted set 删除会话。
- `record_consumed_seconds(client_id, session_id, seconds)`：累计当日消耗秒数，最多写到 `DAILY_FREE_SECONDS`，不写正式归档。
- `check_session_duration(elapsed_seconds)`：本地纯逻辑判定单场 30 分钟上限。

### Step 09 验证结论

- TDD RED 已确认缺少 `meeting_mvp_backend.quota` 时 `backend/tests/test_quota.py` 失败。
- 后端 `uv run python --version`、`uv run ruff check .`、`uv run mypy .`、`uv run pytest tests/test_quota.py`、`uv run pytest` 已通过；额度单测结果为 10 passed，默认 pytest 结果为 25 passed、3 integration deselected。
- 前端 `npm run lint`、`npm run test`、`npm run build`、`npm run test:e2e` 已通过。
- Lighthouse 使用独立 Compose project `meeting_mvp_step09` 构建 backend 镜像，只启动临时 Redis 和一次性 backend 测试容器；`tests/integration/test_quota_redis_integration.py` 已通过。
- 远端 Step 09 临时 `.env.step09`、占位凭据、临时 Redis 容器、临时 backend 镜像和 `/opt/meeting_mvp/data/redis_step09` 已清理。
- Step 10 尚未开始；额度服务尚未接入 WebSocket `session_start`。

## 2026-05-06 Step 10 WebSocket 消息 Schema

### 架构状态

- Step 10 建立了前后端共享的 WebSocket wire protocol 契约层，但没有启动运行时会话链路：未新增 `/ws` endpoint，未实现 session lifecycle，未接入 Redis、PostgreSQL、Provider 或 `QuotaService`。
- WebSocket JSON 消息统一使用顶层 `type` 字段做判别，字段名继续使用 snake_case，保持与后端 API、PRD 和数据库命名风格一致。
- `audio_chunk` 不属于 JSON discriminated union，而是 WebSocket binary frame；浏览器上传音频格式固定为 16 kHz、mono、PCM16。
- 前后端 schema 暂时镜像维护，不引入跨语言 codegen；后端 Pydantic 是服务端校验权威，前端 Zod 用于运行时协议校验和 TypeScript 类型推导。

### 文件作用

| 文件 | 作用 |
|---|---|
| `backend/src/meeting_mvp_backend/ws_messages.py` | 后端 WebSocket 协议模型。用 Pydantic v2 定义 client/server JSON 消息的 discriminated union，导出 `parse_client_message()`、`parse_server_message()` 和 `is_audio_chunk_frame()`；禁止额外字段，固定 `session_start.audio_format`。 |
| `backend/tests/test_ws_messages.py` | 后端协议契约测试。覆盖合法消息、缺失必填字段、未知 `type`、非固定音频格式，以及 binary PCM16 音频帧识别。 |
| `frontend/src/protocol/websocket-messages.ts` | 前端 WebSocket 协议模块。用 Zod 镜像后端 wire schema，导出 schema、推导类型、`parseClientMessage()`、`parseServerMessage()` 和 `isAudioChunkFrame()`，供后续真实 WebSocket client 复用。 |
| `frontend/src/protocol/websocket-messages.test.ts` | 前端协议契约测试。覆盖与后端一致的消息解析失败/成功场景，以及 `ArrayBuffer`、typed array、`Blob` binary frame 识别。 |
| `frontend/package.json` | 增加前端运行时依赖 `zod`。 |
| `frontend/package-lock.json` | 锁定 `zod` 依赖版本，保证前端协议校验依赖可重复安装。 |

### 协议边界

- Client JSON request：
  - `session_start`：必填 `client_id`、`capture_mode`、`source_platform`、`audio_format`。
  - `heartbeat`：必填 `session_id`。
  - `session_stop`：必填 `session_id`。
- Server JSON response：
  - `session_started`：必填 `session_id`、`archive_token`、`archive_url`、`remaining_seconds_today`。
  - `quota_update`：必填 `remaining_seconds_today`。
  - `audio_status`：必填 `has_audio`，`level` 可选且范围为 0 到 1。
  - `asr_interim`、`translation_interim`、`key_sentence_update`：必填 `text`。
  - `segment_final`：必填 `segment_id`、`sequence`、`start_ms`、`end_ms`、`english_text_final`、`chinese_text_final`。
  - `timeline_update.items`：最小节点结构为 `id`、`item_type`、`timestamp_ms`、`text`，`segment_id` 可选。
  - `warning`、`error`：必填 `code`，`message` 可选。
  - `session_closed`：必填 `reason`。
- Step 10 不定义公开 REST API，不持久化会议数据，不保存 interim 或原始音频；正式会话编排、额度扣减、Provider streaming、归档写入留给 Step 11 及后续步骤。

### 验证结论

- 后端本地协议测试、Ruff、mypy 和完整 pytest 已通过；默认 pytest 结果为 34 passed、3 integration deselected。
- 前端 lint、Vitest、build 和 Playwright e2e 已通过；Vitest 结果为 6 个测试文件、22 个测试通过，Playwright 结果为 1 个 Chromium smoke test 通过。
- `git diff --check` 已通过，仅有 Windows LF/CRLF 工作区提示；当前工作区只包含 Step 10 代码、依赖锁文件和记忆文档改动。

## 2026-05-07 Step 11 WebSocket 会话编排

### 架构状态

- F05 已落地为后端 `/ws` WebSocket endpoint 和会话编排层；前端 UI、真实音频捕获、Provider/STT/Qwen、final 归档写入仍未开始。
- 会话创建顺序固定为：解析 `session_start` -> 校验匿名 client 已存在 -> Redis 额度/并发/预算校验并登记 active session -> PostgreSQL 写入 `meeting_session(status=pending_audio)` -> 返回 `session_started`。
- `session_started` 返回明文 `archive_token` 和 `archive_url`；PostgreSQL 只保存 `archive_token_hash`，继续不保存明文 token。
- Step 11 的有效音频判定是临时最小实现：首个非空 WebSocket binary frame 将会话从 `pending_audio` 转为 `active`，设置 `started_at` 并发送 `audio_status(has_audio=true)`；真实音量、静音检测和 binary frame 节奏仍属于 Step 14。
- `session_stop` 按 active 后 wall-clock 秒数结算额度，写回 `duration_seconds` 和 `quota_seconds_consumed`，释放 Redis active session，并向前端发送 `quota_update` 和 `session_closed`。
- 浏览器断开、WebSocket task 取消、非法消息和 session mismatch 都会触发清理路径，避免 Redis active session 永久占用并发。
- Step 11 不新增数据库 migration，不保存 raw audio，不保存 interim，不写 `transcript_segment`，不启动或关闭真实 Provider session。

### 文件作用

| 文件 | 作用 |
|---|---|
| `backend/src/meeting_mvp_backend/ws_sessions.py` | Step 11 核心会话编排模块。定义 `WebSocketSessionOrchestrator`、`SQLAlchemyMeetingSessionRepository`、`hash_archive_token()` 和 `build_archive_url()`；负责 session_start、binary audio frame 临时激活、heartbeat、session_stop、断开清理、错误关闭和 Redis 额度释放。 |
| `backend/src/meeting_mvp_backend/main.py` | FastAPI ASGI 入口。Step 11 新增 `/ws` endpoint 和 `get_websocket_session_orchestrator()`，把 app settings、数据库 session factory、SQLAlchemy 仓储和 Redis-backed `QuotaService` 接入 WebSocket 编排。 |
| `backend/tests/test_websocket_sessions.py` | 本地 WebSocket 会话编排单元测试。使用 fake 仓储和 fake quota service 覆盖 pending 会话创建、音频激活、heartbeat、停止结算、浏览器断开、重复会话拒绝、未初始化 client、非法消息和 session mismatch。 |
| `backend/tests/integration/test_websocket_session_redis_integration.py` | Lighthouse/CI 真实 PostgreSQL + Redis 集成测试。执行 migration 后验证 `/ws` 正常开始/停止、重复 active session 拒绝，以及直接注入 ASGI disconnect 时 Redis active session 可释放。 |
| `backend/src/meeting_mvp_backend/ws_messages.py` | Step 10 协议 schema 被 Step 11 编排层复用；本步未修改该文件，但 `/ws` endpoint 通过它解析 client JSON 消息并生成 server JSON 消息。 |
| `backend/src/meeting_mvp_backend/quota.py` | Step 09 额度服务被 Step 11 接入 `session_start` 和 `session_stop`；本步未修改该文件。 |
| `backend/src/meeting_mvp_backend/db/models.py` | Step 07 数据模型被 Step 11 复用，尤其是 `MeetingSession`、`MeetingSessionStatus`、`CaptureMode` 和 `SourcePlatform`；本步未新增 migration。 |

### 协议与状态边界

- `session_start` 成功后会话先处于 `pending_audio`；此时 Redis active session 已登记，但不消耗每日额度。
- 首个非空 binary frame 后会话进入 `active`；只有 active 后的时长会在 `session_stop` 或断开清理时写入 quota。
- `heartbeat` 只校验 session_id 并保持连接；Step 11 不新增 heartbeat 响应消息。
- `session_stop` 正常关闭 reason 固定为 `user_stopped`。
- 额度、预算、并发拒绝使用 `QuotaDenialReason.value` 作为 `error.code` 和 `session_closed.reason`。
- 未初始化匿名 client 的错误码为 `client_not_initialized`；非法消息为 `invalid_message`；session 不匹配为 `session_mismatch`；配置缺失为 `configuration_error`。
- `archive_url` 生成规则：优先使用后端 `PUBLIC_BASE_URL` 拼接 `/archive/{session_id}?token={archive_token}`；未配置时返回相对路径。

### 验证结论

- 本地后端 `uv run python --version`、Ruff、mypy、默认 pytest 已通过；默认 pytest 结果为 41 passed、5 integration deselected。
- 前端 lint、Vitest、build 和 Playwright e2e 已通过；Vitest 结果为 6 个测试文件、22 个测试通过，Playwright 结果为 1 个 Chromium smoke test 通过。
- Lighthouse 使用独立 `meeting_mvp_step11` Compose project 完成 backend build、PostgreSQL/Redis healthy、Alembic migration 和真实 WebSocket 集成测试；集成测试结果为 2 passed。
- Step 11 临时远端资源已清理；Step 12 尚未开始。

## 2026-05-07 Step 12 前端实时会议工作台骨架

### 架构状态

- Step 12 将前端首屏从早期占位页升级为可继续接入实时链路的会议工作台骨架；第一屏仍是工具页，不做营销页。
- UI 顶层结构固定为 `会议状态栏` + 四个可访问工作区：`英文原文区`、`中文翻译区`、`当前重点句区`、`会议时间线区`。
- 状态栏集中承载会议前操作和关键运行态：捕获模式、开始捕获、结束会议、匿名身份、服务端同步、今日剩余额度、音频状态、ASR 状态和翻译状态。
- 桌面端布局为主内容左侧双区 + 右侧辅助双区；移动端纵向堆叠，Playwright 覆盖桌面与移动视口并检查无水平溢出。
- `开始捕获` 在本步仍只调用 Zustand `beginCapture()` 占位 action；不会请求浏览器捕获权限，不会调用 `getDisplayMedia`，不会创建 `AudioWorklet`，不会建立 WebSocket 或上传 binary 音频帧。
- ASR、翻译和音频状态在本步均为本地 UI 状态文案，不代表真实 Google STT、Qwen、Provider session 或后端 `/ws` 连接。
- 本步不修改后端 REST API、WebSocket wire schema、数据库 schema、环境变量清单、部署拓扑或 Provider 配置；Step 13 尚未开始。

### 文件作用

| 文件 | 作用 |
|---|---|
| `frontend/src/App.tsx` | Step 12 核心工作台页面。负责状态栏、捕获模式切换、开始/结束占位按钮、匿名身份/额度/同步展示，以及四个实时会议工作区的响应式布局和可访问名称。 |
| `frontend/src/stores/session-store.ts` | Zustand 会话状态。Step 12 新增 `setCaptureMode(mode)`，允许开始捕获前在 `tab_audio` 与 `system_audio` 间切换；继续保留 `beginCapture()` / `endSession()` 的本地状态占位行为。 |
| `frontend/src/App.test.tsx` | React Testing Library UI 契约测试。覆盖工作台标题、`会议状态栏` landmark、四区 region、捕获模式按钮、开始/结束按钮状态、匿名身份短 ID、今日剩余额度和服务端同步状态。 |
| `frontend/src/stores/session-store.test.ts` | Zustand store 单元测试。新增覆盖 `setCaptureMode()` 在不启动捕获时切换模式，防止后续真实捕获接入前破坏 UI 预选模式。 |
| `frontend/e2e/app.spec.ts` | Playwright 浏览器 smoke test。覆盖桌面和移动视口下状态栏、四个工作区、关键按钮和无水平溢出，验证生产构建产物的首屏可用性。 |

### UI 状态边界

- `captureMode` 仍沿用 Step 03/10 的 `tab_audio` / `system_audio` 枚举，当前只影响 UI 选中态和未来 `beginCapture(captureMode)` 的入参。
- `status` 仍只有 `idle` / `capturing`，当前 `capturing` 表示用户点击了占位入口，不代表已经捕获到有效音频。
- `anonymousClientStatus`、`serverSyncStatus`、`clientId` 和 `remainingSecondsToday` 继续复用 Step 08 的匿名身份初始化状态；Step 12 只改变展示密度和位置。
- 当前重点句和会议时间线是结构占位；真实 `key_sentence_update`、`timeline_update`、`asr_interim`、`translation_interim`、`segment_final` 的消费和渲染仍属于后续步骤。

### 验证结论

- Step 12 已先跑失败测试确认缺口，再实现 UI/store 改动。
- 前端目标单测通过：`npm run test -- src/stores/session-store.test.ts src/App.test.tsx`，结果为 2 个测试文件、7 个测试通过。
- 前端完整验证通过：`npm run lint`、`npm run test`、`npm run build`、`npm run test:e2e`。
- 完整 Vitest 结果为 6 个测试文件、25 个测试通过；Playwright 结果为 2 个 Chromium 测试通过。
- `git diff --check` 已通过，仅输出 Windows LF/CRLF 工作区提示，无空白错误。
- 本步无需 Lighthouse、PostgreSQL、Redis、Docker 或 Provider 集成测试；Step 13 未开始。

## 2026-05-07 Step 13 前端会议音频捕获

### 架构状态

- Step 13 将前端捕获入口从 UI 占位升级为浏览器 `getDisplayMedia` 调用；仍只处理会议标签页/系统音频授权和 `MediaStream` 生命周期。
- 捕获模式仍沿用 `tab_audio` / `system_audio`；网页不能强制浏览器 picker 选中某个标签页或系统音频源，只能通过 UI 文案引导用户选择并勾选共享音频。
- 捕获成功的最小判定是 `MediaStream.getAudioTracks().length > 0`；没有 audio track 时立即停止所有 tracks 并提示切换系统音频。
- Zustand store 保存当前 `MediaStream` 引用，用于 Step 13 的结束会议清理；不会读取音频样本，不会保存原始音频，不会上传音频。
- `lastCaptureAttempt` 是前端本地记录，包含 source platform、capture mode、browser name、authorization result、failure code 和 attemptedAt；正式 usage event 写入仍属于后续步骤。
- Step 13 不修改后端 REST API、WebSocket wire schema、数据库 schema、环境变量清单、部署拓扑或 Provider 配置。
- Step 13 不实现 AudioWorklet、16 kHz mono PCM16 转换、音量电平/静音检测、WebSocket client、binary 上传、Google STT、Qwen 或 Provider session；这些边界从 Step 14 或后续步骤开始。

### 文件作用

| 文件 | 作用 |
|---|---|
| `frontend/src/lib/audio-capture.ts` | Step 13 的浏览器音频捕获封装。负责调用 `getDisplayMedia({ audio: true, video: true })`、判断是否存在 audio track、归一化授权/不支持/无音轨/未知失败错误，并提供 `stopMediaStream()` 清理所有 tracks。 |
| `frontend/src/stores/session-store.ts` | Zustand 会话状态。Step 13 新增 `SourcePlatform`、`captureStatus`、`captureErrorCode`、`captureErrorMessage`、`lastCaptureAttempt`、`mediaStream`、`setSourcePlatform()` 和 async `beginCapture()`；`endSession()` 负责停止并清空当前 `MediaStream`。 |
| `frontend/src/App.tsx` | 前端会议工作台 UI。Step 13 新增会议平台选择、真实捕获授权入口、授权中/已捕获/拒绝/无音轨/不支持/失败状态展示、系统音频风险提示和无音轨降级提示；四区响应式布局继续沿用 Step 12。 |
| `frontend/src/lib/audio-capture.test.ts` | 捕获封装单元测试。覆盖成功返回音频流、拒绝授权、不支持 API/非安全上下文、成功但无 audio track 时停止 tracks。 |
| `frontend/src/stores/session-store.test.ts` | store 单元测试。覆盖 async 捕获成功、捕获模式切换、拒绝授权记录、`lastCaptureAttempt` 字段、`endSession()` 停止 tracks 和状态复位。 |
| `frontend/src/App.test.tsx` | React Testing Library UI 契约测试。覆盖状态栏平台选择、捕获成功按钮状态、拒绝授权重试入口、无音轨系统音频降级提示，以及 Step 12 四区语义。 |
| `frontend/e2e/app.spec.ts` | Playwright 浏览器测试。通过 mock `navigator.mediaDevices.getDisplayMedia` 覆盖捕获成功、拒绝授权、无 audio track、桌面/移动视口四区可见和无水平溢出。 |

### UI 与状态边界

- `captureStatus` 可取 `idle`、`requesting`、`ready`、`denied`、`no_audio`、`unsupported`、`failed`。
- `captureErrorCode` 可取 `permission_denied`、`no_audio_track`、`not_supported`、`capture_failed` 或 `null`。
- `status='capturing'` 在 Step 13 表示浏览器已授权并返回带 audio track 的 `MediaStream`；仍不代表已经完成音频前处理、有效音量检测、后端建会或额度消耗。
- `sourcePlatform` 是用户选择的平台标签：`google_meet`、`teams_web`、`zoom_web`、`tencent_meeting_web` 或 `unknown`；本步只在前端本地记录，不写数据库。
- `beginCapture()` 支持测试注入 capture service；生产路径默认调用 `requestDisplayMediaCapture()`。
- `endSession()` 只负责停止本地 tracks 和复位前端捕获状态；不发送 `session_stop`，不释放后端 Redis active session，因为 Step 13 尚未接入 WebSocket client。

### 验证结论

- Step 13 已先跑失败测试确认缺口，再实现捕获封装、store 和 UI 改动。
- 前端目标单测通过：`npm run test -- src/lib/audio-capture.test.ts src/stores/session-store.test.ts src/App.test.tsx`，结果为 3 个测试文件、15 个测试通过。
- 前端完整验证通过：`npm run lint`、`npm run test`、`npm run build`、`npm run test:e2e`。
- 完整 Vitest 结果为 7 个测试文件、33 个测试通过；Playwright 结果为 5 个 Chromium 测试通过。
- `git diff --check` 已通过，仅输出 Windows LF/CRLF 工作区提示，无空白错误。
- 静态边界扫描未发现 Step 13 新增 AudioWorklet、WebSocket client、MediaStream audio graph 或 PCM16 转换代码；命中的 `pcm16` 仅来自 Step 10 既有协议 schema/test。
- 本步自动化测试使用 mock `getDisplayMedia`，真实 Windows Chrome/Edge + Google Meet/Teams/Zoom/腾讯会议 Web 兼容性矩阵仍需人工验收；Step 14 未开始。

## 2026-05-09 Step 14 前端音频前处理与 binary 上传

### 架构状态
- Step 14 将前端捕获链路从“只保留 `MediaStream` 引用”升级为完整的本地上传前管线：`getDisplayMedia` 成功后先建立 WebSocket session，再通过 Web Audio API / `AudioWorklet` 处理实时音频。
- 前端上传格式固定为 16 kHz、mono、PCM16、100ms 一帧；每帧 1600 samples / 3200 bytes。
- 静音判定在前端完成，默认 RMS 阈值为 `0.015`；低于阈值的静音帧不会通过 WebSocket binary frame 发送。
- 30 秒无有效音频只触发前端 `silenceWarning` 和 `audio_silent_timeout`，不发送静音 binary frame。
- WebSocket JSON 继续复用 Step 10 既有 schema：`session_start`、`session_stop`、`session_started`、`quota_update`、`audio_status`、`error`、`session_closed`；本步不修改 wire schema。
- Step 14 不实现 STT/Qwen/mock Provider，不生成 interim/final 文本，不写 `transcript_segment`，不实现归档页数据流。
- Step 14 不修改后端 REST API、后端 `/ws` 编排、数据库 schema、环境变量清单或部署配置。

### 文件作用

| 文件 | 作用 |
|---|---|
| `frontend/src/lib/audio-frames.ts` | 音频帧纯函数模块。定义固定 `AUDIO_FORMAT`，实现多声道混合为 mono、线性重采样到 16 kHz、RMS 音量计算、有效音频阈值判断、PCM16 little-endian 编码和 100ms 帧生成。该模块无浏览器副作用，便于 Vitest 覆盖边界行为。 |
| `frontend/public/audio-worklet/pcm16-processor.js` | 浏览器 AudioWorklet processor。运行在 AudioWorkletGlobalScope 中，接收实时输入音频，把各通道样本与输入 sample rate 通过 `postMessage` 传回主线程；不保存、不上传原始音频。 |
| `frontend/src/lib/audio-processing.ts` | 前端实时音频处理管线。创建 `AudioContext`、`MediaStreamAudioSourceNode` 和 `AudioWorkletNode`，把 worklet 样本送入 `audio-frames` 处理器；只对有效音频调用 binary frame callback，管理 30 秒静音 warning，并在 `stop()` 时清理 node/context/timer。 |
| `frontend/src/lib/meeting-websocket.ts` | 前端会议 WebSocket client。解析 `VITE_WS_BASE_URL` 或从当前页面推导 `/ws`，open 后发送 `session_start`，收到 `session_started` 后允许发送 PCM16 `ArrayBuffer`，结束时发送 `session_stop` 并关闭连接；只消费本步需要的既有服务端消息。 |
| `frontend/src/stores/session-store.ts` | 会话状态中枢。Step 14 新增 WebSocket 状态、音频处理状态、音量电平、有效音频、静音 warning、session id、archive url 和 pipeline error code；`beginCapture()` 串联身份同步检查、浏览器捕获、WebSocket 建会和音频处理启动，`endSession()` 完整清理 processor/WebSocket/tracks。 |
| `frontend/src/App.tsx` | 会议工作台 UI。状态栏新增 WebSocket、音频处理、音量电平、有效音频、会话编号和归档入口；开始按钮根据身份同步、授权、连接和处理状态禁用；四区布局继续保持 Step 12 的工具型工作台结构。 |
| `frontend/src/lib/audio-frames.test.ts` | 纯函数单元测试。覆盖固定格式、mono 混合、16 kHz 重采样、PCM16 clamp/编码、RMS level、阈值判断和 100ms 帧生成。 |
| `frontend/src/lib/audio-processing.test.ts` | 音频处理单元测试。覆盖有效帧触发 binary callback、静音帧不发送、跨 worklet message 累积 100ms 帧、30 秒静音 warning 和 stop 清理 audio graph。 |
| `frontend/src/lib/meeting-websocket.test.ts` | WebSocket client 单元测试。覆盖 URL 推导、`session_start` 发送、`session_started` 后发送 binary frame、`session_stop` 和错误关闭。 |
| `frontend/src/stores/session-store.test.ts` | store 集成式单元测试。通过 fake capture service、fake WebSocket client 和 fake audio processor 覆盖 Step 14 状态流、identity gate、WebSocket 失败清理、静音 warning 和结束会议清理。 |
| `frontend/src/App.test.tsx` | React UI 测试。覆盖新增状态栏控件、开始捕获后的 WebSocket/音频处理状态、音量电平、有效音频、静音提示，以及 Step 13 授权失败/无音轨提示。 |
| `frontend/e2e/app.spec.ts` | Playwright 测试。通过 mock `getDisplayMedia`、`fetch`、`WebSocket`、`AudioContext`、`AudioWorkletNode` 覆盖有效音频 binary 上传、静音不上传、授权失败、无音轨降级、桌面/移动无水平溢出。 |

### 状态与边界
- 新增 `AudioProcessingStatus = idle | starting | running | silent | unsupported | failed`，表示本地 AudioWorklet/PCM16 管线状态。
- 新增 `WebSocketStatus = idle | connecting | started | closing | closed | error`，表示前端 WebSocket client 生命周期。
- 新增 `AudioPipelineErrorCode = identity_not_ready | websocket_failed | audio_processing_unsupported | audio_processing_failed | audio_silent_timeout`，只描述前端音频上传前链路错误。
- `beginCapture()` 现在要求匿名身份已同步；否则不会请求浏览器捕获，也不会建立 WebSocket。
- `session_started` 后才启动音频处理；有效 PCM16 frame 只在 WebSocket session 已建立后发送。
- `endSession()` 会停止 audio processor、发送 `session_stop`、关闭 WebSocket，并停止 `MediaStream.getTracks()`。
- 静音 frame 不发送，后端 Step 11 的“首个非空 binary frame 激活会话”仍可避免静音导致额度开始消耗。

### 验证结论
- Step 14 已先跑 RED 测试确认缺口，再实现到 GREEN。
- `npm run lint`、`npm run test`、`npm run build`、`npm run test:e2e` 均已通过。
- 完整 Vitest 结果为 10 个测试文件、55 个测试通过；Playwright 结果为 6 个 Chromium 测试通过。
- `git diff --check` 已通过，仅输出 Windows LF/CRLF 工作区提示，无空白错误。
- 真实 Windows Chrome/Edge + Google Meet/Teams/Zoom/腾讯会议 Web 音频兼容性和真实无声 30 秒场景仍需人工验收；Step 15 未开始。

## 2026-05-09 Step 15 本地 mock Provider 链路

### 架构状态
- Step 15 把 Step 14 的有效 PCM16 binary 上传接到本地后端 mock 文本链路：首个有效 binary frame 仍负责把 `meeting_session` 从 `pending_audio` 激活为 `active`，随后启动 mock Provider task。
- mock Provider task 使用固定脚本，依次推送英文 interim、可恢复 provider warning、中文 interim、final 双语片段、重点句和时间线更新。
- 后端不修改 WebSocket wire schema；继续使用 Step 10 已定义的 `asr_interim`、`translation_interim`、`segment_final`、`key_sentence_update`、`timeline_update`、`warning` 等服务端消息。
- final 片段通过 `MeetingSessionRepository.create_transcript_segment(...)` 写入既有 `transcript_segment` 表，不新增 migration；sequence 从 1 递增，interim、warning 和原始音频不入库。
- mock task 绑定在 `WebSocketSessionState` 上，`session_stop`、浏览器断开和 task 取消都会取消 mock task；已写入的 final 片段保留，Redis active session 释放和额度结算仍沿用 Step 11 逻辑。
- 前端 WebSocket client 只新增 callbacks，不新增公开环境变量；`VITE_*` 边界保持不变。
- Zustand store 新增实时文本状态，四区 UI 从占位状态升级为消费 mock 实时数据：英文区、中文区、重点句区和时间线区都会随服务端消息更新。
- 本步不是 Step 16：当时没有接入真实 ASR provider，没有调用真实 Qwen，没有新增 Provider 密钥变量，没有新增会后归档查询 API/页面、搜索、复制、导出、COS 或完整 `usage_event` 链路。

### 文件作用

| 文件 | 作用 |
|---|---|
| `backend/src/meeting_mvp_backend/mock_providers.py` | Step 15 的本地 mock Provider 脚本模块。定义固定英文 interim、中文 interim、双语 final、可恢复 warning、重点句和时间线元数据，供 WebSocket 编排层按稳定顺序推送。 |
| `backend/src/meeting_mvp_backend/ws_sessions.py` | 后端 WebSocket 会话编排层。Step 15 扩展 repository 协议与 SQLAlchemy 实现，新增 `transcript_segment` 写入；会话激活后启动可取消 mock task，并发送实时文本、重点句、时间线和 warning 消息。 |
| `backend/tests/test_websocket_sessions.py` | 后端本地 WebSocket 行为测试。Fake repository 新增 `transcript_segments` 存储，覆盖有效 binary frame 后收到 mock 实时消息、final 双语片段入库、停止/断开取消 mock task 且保留已写片段，以及 warning 不阻塞 final。 |
| `frontend/src/lib/meeting-websocket.ts` | 前端 WebSocket client。Step 15 新增 `onAsrInterim`、`onTranslationInterim`、`onSegmentFinal`、`onKeySentenceUpdate`、`onTimelineUpdate`、`onWarning` callbacks，把既有服务端消息暴露给 store。 |
| `frontend/src/stores/session-store.ts` | Zustand 会话状态中枢。Step 15 新增 `englishInterimText`、`translationInterimText`、`finalSegments`、`keySentenceText` 和 `timelineItems`；负责替换 interim、追加 final、更新重点句和时间线，并在新会话开始时清空旧实时文本。 |
| `frontend/src/App.tsx` | 会议工作台 UI。Step 15 将四区内容从占位文案升级为实时渲染：英文区显示英文 interim/final，中文区显示中文 interim/final，重点句区显示最新重点句，时间线区显示服务端 timeline items。 |
| `frontend/src/lib/meeting-websocket.test.ts` | WebSocket client 单元测试。覆盖新增服务端消息到 callbacks 的分发，包括 ASR interim、翻译 interim、final segment、重点句、时间线和 warning。 |
| `frontend/src/stores/session-store.test.ts` | store 集成式单元测试。通过 fake WebSocket client 验证 interim 替换、final 追加、重点句更新和时间线更新。 |
| `frontend/src/App.test.tsx` | React UI 测试。直接设置 store 实时文本状态，验证英文原文区、中文翻译区、当前重点句区和会议时间线区渲染 mock Provider 内容。 |
| `frontend/e2e/app.spec.ts` | Playwright 浏览器测试。FakeWebSocket 在收到 binary frame 后推送 mock 服务端消息，验证真实页面四区更新且桌面/移动视口仍无水平溢出。 |

### 状态与边界
- `englishInterimText` 和 `translationInterimText` 表示当前临时理解文本，可被后续 interim 替换；本步保留它们用于实时提示，不写数据库。
- `finalSegments` 只追加 `segment_final` 消息，作为当前会话前端展示的正式双语片段列表；正式持久化来源仍是后端 `transcript_segment`。
- `keySentenceText` 保存最新重点句；`timelineItems` 使用服务端 `timeline_update.items` 替换当前时间线列表。
- `onWarning` callback 已在 WebSocket client 层暴露；当前 store 不持久化 warning 文本，provider warning 主要由测试验证其不会阻塞 final 链路。
- mock Provider 输出是固定脚本，只用于本地开发和自动化测试；不读取真实音频内容，不保存原始音频，不依赖 Google/Qwen/COS 密钥。

### 验证结论
- Step 15 已先跑 RED 测试确认缺口，再实现后端 mock Provider、final 入库和前端实时文本消费到 GREEN。
- 后端完整验证通过：`uv run python --version`、`uv run ruff check .`、`uv run mypy .`、`uv run pytest`；结果为 Python 3.12.11、Ruff 通过、mypy 25 个源文件无问题、pytest 43 passed 且 5 integration deselected。
- 前端完整验证通过：`npm run lint`、`npm run test`、`npm run build`、`npm run test:e2e`；结果为 lint 通过、Vitest 10 个测试文件 58 个测试通过、build 通过、Playwright 6 个 Chromium 测试通过。
- `git diff --check` 已通过，仅输出 Windows LF/CRLF 工作区提示，无空白错误。
- Step 15 完成时 Step 16 尚未开始；当前最新 Step 16 状态见下方 Qwen realtime ASR 替换记录，会后归档页面/API 仍等待后续明确步骤。

## 2026-05-10 Step 16 Qwen realtime ASR 替换

### 架构状态
- Step 16 的英文实时 ASR 生产主路径已从 Google Speech-to-Text v2 streaming 替换为阿里云百炼 `qwen3-asr-flash-realtime`。
- Google STT 相关运行依赖、生产环境变量和 Compose 凭据挂载已移除；`google-cloud-speech` 不再是后端运行依赖，`websockets` 成为 Qwen realtime ASR 的显式依赖。
- WebSocket 服务端协议保留 `asr_interim` 与 `asr_final`。`asr_final` 字段仍为 `sequence`、`start_ms`、`end_ms`、`text`、`confidence|null`，且仍不写入 `transcript_segment`。
- 后端 WebSocket 编排支持 `session_resume` / `session_resumed`：浏览器断线后，在 `SESSION_RESUME_GRACE_SECONDS=30` 内可用同一 `client_id + session_id + archive_token` 恢复同一业务 session；本步只恢复浏览器到后端 `/ws`，不补传断线期间音频，不做 Qwen Provider 自动重连补偿。
- Qwen ASR provider 连接 `QWEN_ASR_BASE_URL + ?model=QWEN_ASR_MODEL`，使用 `Authorization: Bearer <QWEN_API_KEY>` 和 `OpenAI-Beta: realtime=v1`，首包发送 `session.update` 配置 16 kHz mono PCM，后续将 PCM16 frame Base64 后发送 `input_audio_buffer.append`。
- 因 Step 14 前端会过滤静音 frame，Qwen provider 在音频输入短暂停顿后会补发一小段 16 kHz mono PCM 静音尾帧，帮助 Qwen server VAD 产生 `completed` / final 事件；`session_stop` 时也会先发送 `session.finish` 并等待 final/finished，再关闭 provider。
- Qwen interim 映射为 `asr_interim`；Qwen completed/final 映射为 `asr_final`。Qwen 缺少时间戳时，后端用已发送 PCM16 字节数估算累计音频时长，保证 `start_ms/end_ms` 单调递增。
- Qwen ASR 异常会转为 `error(code="qwen_asr_error")`，随后关闭 provider、释放 Redis active session、结算/标记会话并发送 `session_closed`。
- 浏览器断开恢复记录会先写入内存 registry，再清理旧 provider，避免前端快速重连时抢在 registry 写入之前导致 `session_resume_failed`。
- Step 16 不新增数据库 migration，不保存原始音频，不保存 interim，不把 `asr_final` 写入数据库，不新增前端 `VITE_QWEN_*` 或 provider 密钥变量。
- Step 17 未开始：本步没有调用 Qwen 文本翻译，没有新增中文 interim/final 逻辑，没有新增导出、COS、会后归档页或完整 `usage_event` 链路。

### 文件作用

| 文件 | 作用 |
|---|---|
| `backend/src/meeting_mvp_backend/stt_providers.py` | STT provider 抽象与 Qwen realtime ASR 实现。负责构造 realtime WebSocket URL/header，发送 `session.update`，Base64 转发 PCM16 audio append，补发短静音尾帧触发 VAD final，解析 Qwen interim/final/error/finished 事件，并输出 `SttInterimEvent` 与 `SttFinalEvent`。 |
| `backend/src/meeting_mvp_backend/config.py` | 后端配置模型。新增 `ASR_PROVIDER`、`QWEN_ASR_MODEL`、`QWEN_ASR_BASE_URL`、`QWEN_ASR_SAMPLE_RATE_HZ`、`QWEN_ASR_AUDIO_FORMAT`、`QWEN_ASR_LANGUAGE` 和 `SESSION_RESUME_GRACE_SECONDS`，移除 Google STT 生产必填项。 |
| `backend/src/meeting_mvp_backend/ws_messages.py` | 后端 WebSocket wire schema。保留 `AsrFinalMessage`，新增 `SessionResumeMessage` 与 `SessionResumedMessage`，并把恢复协议纳入 client/server union。 |
| `backend/src/meeting_mvp_backend/ws_sessions.py` | 后端 WebSocket 会话编排层。负责 Qwen provider 生命周期、binary frame 持续转发、`asr_interim`/`asr_final` 推送、`qwen_asr_error` 错误关闭、stop/disconnect provider 清理，以及内存级短期 session resume registry。 |
| `backend/src/meeting_mvp_backend/main.py` | FastAPI ASGI 入口与依赖组装。非 local WebSocket orchestrator 注入 Qwen realtime ASR provider factory；local 仍保留 Step 15 mock Provider。 |
| `backend/pyproject.toml` | 后端项目依赖清单。移除 `google-cloud-speech`，新增 `websockets>=16.0`。 |
| `backend/uv.lock` | 后端 uv 锁文件。锁定 Qwen realtime ASR 所需的 `websockets` 依赖解析结果，移除 Google STT 传递依赖。 |
| `backend/.env.example` | 后端示例环境变量。新增 Qwen ASR 与 session resume 配置，去掉 Google STT 服务账号/recognizer 配置。 |
| `deploy/.env.example` | 部署示例环境变量。新增 Qwen ASR 与 session resume 配置，生产示例不再要求 Google STT。 |
| `deploy/docker-compose.yml` | 生产 Compose 拓扑。后端环境变量改为 Qwen ASR 配置，移除 Google 服务账号 JSON 只读挂载。 |
| `backend/tests/test_qwen_realtime_asr_provider.py` | Qwen realtime ASR provider 单元测试。使用 fake websocket client 验证 URL/header、首包配置、audio append、interim/final 解析、时间估算、异常传播和关闭清理。 |
| `backend/tests/test_ws_messages.py` | 后端 WebSocket schema 测试。覆盖 `asr_final`、`session_resume`、`session_resumed` 的合法解析和非法字段拒绝。 |
| `backend/tests/test_config.py` | 后端配置测试。覆盖 `.env.example` 加载、脱敏状态、生产必填和 OpenAI STT 可选边界。 |
| `backend/tests/test_websocket_sessions.py` | 后端 WebSocket 会话行为测试。覆盖 binary frame 转发给 STT provider、`asr_interim`/`asr_final` 推送、`qwen_asr_error` 关闭、stop/disconnect provider 清理、断线恢复同一 session，以及 Qwen 路径不写 `transcript_segment`。 |
| `backend/tests/integration/test_qwen_realtime_asr_smoke.py` | 真实 Qwen realtime ASR gated smoke hook。仅在显式启用、提供真实 Qwen ASR 环境变量和测试音频 manifest 时运行，覆盖 `/ws` 建连、首个 interim/final 延迟、30 秒/3 分钟/10 分钟连续流、术语、自动标点、中英混杂和断线恢复。 |
| `scripts/prepare-qwen-asr-smoke-audio.ps1` | 测试音频准备脚本。下载公开 `brooklyn_bridge.raw`，生成 30 秒、3 分钟、10 分钟 loop 样本和 smoke manifest；不包含任何密钥。 |
| `frontend/src/protocol/websocket-messages.ts` | 前端 Zod WebSocket wire schema。镜像 `asr_final`、`session_resume`、`session_resumed`，用于类型推导和运行时解析。 |
| `frontend/src/lib/meeting-websocket.ts` | 前端 WebSocket client。保留 `onAsrFinal`，新增断线后自动发送 `session_resume` 的恢复逻辑；恢复后继续用同一 client 对象发送 audio frame。 |
| `frontend/src/stores/session-store.ts` | Zustand 会话状态中枢。保存 `archiveToken`，新会话清空旧英文 final，收到 `asr_final` 后追加到 `englishFinalSegments`。 |
| `frontend/src/App.tsx` | 会议工作台 UI。英文原文区展示 `asr_interim` 与 `asr_final`；中文区仍只由 `translation_interim` 与 `segment_final` 驱动。 |
| `frontend/src/protocol/websocket-messages.test.ts` | 前端协议测试。覆盖 `asr_final`、`session_resume`、`session_resumed` 的解析与额外字段拒绝。 |
| `frontend/src/lib/meeting-websocket.test.ts` | 前端 WebSocket client 测试。覆盖 `asr_final` callback、断线后发送 `session_resume`、恢复成功后继续发送音频。 |
| `frontend/src/stores/session-store.test.ts` | store 集成式单元测试。覆盖 `archiveToken` 持久化/清理、`asr_final` 追加，以及新会话清空旧英文 final 状态。 |
| `frontend/src/App.test.tsx` | React UI 测试。覆盖英文原文区渲染 `asr_final`，并确认中文区仍只由翻译消息驱动。 |
| `frontend/e2e/app.spec.ts` | Playwright 浏览器测试。FakeWebSocket 推送 `asr_final`，验证真实页面英文区展示英文 final 且既有捕获/上传 smoke 仍通过。 |

### 状态与边界
- `StreamingSttProvider.send_audio(frame)` 仍是 WebSocket binary frame 到 ASR provider 的唯一入口；本步只传递前端已过滤的非空 PCM16 frame。
- `SttFinalEvent.sequence` 从 1 开始递增；时间轴优先使用 provider 可得信息，当前 Qwen 缺少时间戳时用累计已发送音频字节数估算，避免倒退区间。
- `confidence` 当前 Qwen ASR 路径按 `null` 处理，协议保留字段以兼容后续 provider。
- `QwenRealtimeAsrProvider.close()` 会发送 `session.finish` 并关闭 realtime WebSocket；WebSocket stop/disconnect/error 路径都会调用清理。
- `APP_ENV=local` 不创建真实 Qwen ASR provider，因此本地无真实 Qwen 凭证时仍使用 Step 15 mock Provider 测试链路。
- 真实 Qwen realtime ASR smoke 不应在 Windows 本地默认运行；需要 Lighthouse/CI 提供真实凭证和测试音频，并且测试日志不得输出 API key、完整环境变量或生产 `.env` 内容。
- Google STT 的 2026-05-09 真实 smoke 历史结论保留：样本和凭证存在性检查通过，但 Lighthouse 到 Google Speech API 的真实 gRPC/HTTP2 streaming 报 `ServiceUnavailable` / `tcp handshaker shutdown`，因此 Google STT 不再作为 M1-A 生产主路径。

### 验证结论
- Step 16 替换已先跑 RED 测试确认缺口，再实现 Qwen realtime ASR provider、`session_resume` 协议、WebSocket 编排和前端恢复到 GREEN。
- 已通过的目标验证：后端 Step 16 目标集 `uv run pytest tests/test_qwen_realtime_asr_provider.py tests/test_ws_messages.py tests/test_config.py tests/test_websocket_sessions.py -q` 为 37 passed；前端协议/WebSocket/store 目标集为 29 passed；真实 Qwen smoke 使用 `D:\meeting_mvp_secrets\provider.env` 和公开样本 manifest 跑通，结果为 5 passed、1 skipped，中英混杂用例因 manifest 未配置样本跳过。
- 完整本地验证结果记录在 `memory-bank/progress.md` 的最新 Step 16 替换进度中。
- Step 17 尚未开始；Qwen interim/final 文本翻译、中文 final 入库、会后归档页/API、导出和 COS 仍等待后续明确步骤。

## 2026-05-13 Step 17 中文 interim

### 架构状态
- Step 17 已接入中文 interim 生产链路：非 local 环境下，后端对节流后的英文 `asr_interim` 异步请求 Qwen Flash/Turbo，并通过既有 `translation_interim` WebSocket 消息推送给前端。
- WebSocket wire schema 未变化；`translation_interim` 仍只有 `type` 和 `text`，前后端沿用 Step 10/15 已建立的协议和消费链路。
- 中文 interim 只用于实时临时理解，不写 PostgreSQL，不生成正式 `segment_final`，不进入归档；正式中文 final 仍等待 Step 18。
- Qwen interim 请求走 OpenAI-compatible `/chat/completions`，复用 `QWEN_API_KEY`、`QWEN_BASE_URL` 和 `QWEN_INTERIM_MODEL`；本步未新增环境变量，也未新增前端 `VITE_QWEN_*`。
- WebSocket 编排层新增独立 translation task：英文 interim 先立即发给浏览器，再异步翻译；翻译失败只记录脱敏 warning，不发送 WebSocket `error`，不关闭会话，也不影响英文 ASR 或后续 final。
- 默认节流策略固定为 1.5 秒最小间隔；空文本跳过、重复文本跳过、同一时间最多一个翻译请求，请求期间只保留最新待翻译 interim。
- `session_stop`、浏览器断开、resume pause 和错误关闭都会取消 pending translation task 并关闭 translation provider，避免后台请求泄漏。
- `APP_ENV=local` 继续使用 Step 15 mock Provider，确保本地无真实 Qwen 凭证时仍能看到 mock 中文 interim/final；非 local 且 `QWEN_INTERIM_ENABLED=true` 时才注入真实 Qwen interim provider。
- Lighthouse 真实 Qwen interim smoke 已在后端容器镜像内通过；当时远端 `.env.production` 仍缺少 Compose 所需数据库变量名，Step 18 前后已补齐到可完成 backend build 的状态，正式部署前仍需确认变量均为真实生产值。

### 文件作用

| 文件 | 作用 |
|---|---|
| `backend/src/meeting_mvp_backend/translation_providers.py` | 中文 interim translation provider 模块。定义 `InterimTranslationProvider` 协议、可恢复 `InterimTranslationError` 和 `QwenInterimTranslationProvider`；负责构造 Qwen OpenAI-compatible chat completions 请求、固定 interim prompt、解析 assistant content，并把 HTTP/JSON/空响应/缺失配置包装为脱敏错误。 |
| `backend/src/meeting_mvp_backend/ws_sessions.py` | 后端 WebSocket 会话编排层。Step 17 在 STT interim 分支中调度中文 interim 翻译 task，维护 pending/latest/last request 状态和 1.5 秒节流，发送 `translation_interim`，并在 stop/disconnect/resume/error 路径取消和关闭 translation provider。 |
| `backend/src/meeting_mvp_backend/main.py` | FastAPI ASGI 入口与依赖组装。非 local 且 `QWEN_INTERIM_ENABLED=true` 时向 `WebSocketSessionOrchestrator` 注入 Qwen interim translation provider factory；local 模式保持 mock provider 路径。 |
| `backend/tests/test_translation_providers.py` | Qwen interim provider 单元测试。使用 `httpx.MockTransport` 覆盖 OpenAI-compatible 请求 URL/header/body、成功解析、缺失配置只报变量名、HTTP 错误、空内容和非法 JSON。 |
| `backend/tests/test_websocket_sessions.py` | 后端 WebSocket 行为测试。新增 fake interim translation provider，覆盖 `asr_interim` 后发送 `translation_interim`、请求中只保留最新文本、重复文本跳过、provider 失败不阻塞 `asr_final`、停止时取消 in-flight 翻译、且不写 `transcript_segment`。 |
| `backend/tests/integration/test_qwen_interim_translation_smoke.py` | 真实 Qwen interim gated smoke hook。只有显式设置 `RUN_QWEN_INTERIM_SMOKE=1` 且提供真实 Qwen 文本环境变量时运行；断言返回非空中文文本，不打印密钥或模型响应正文。 |
| `frontend/src/App.test.tsx` | 前端 UI 回归测试。新增中文 interim 与 final 同屏时的样式区分断言，确认 interim 使用 muted 文本，final 使用正式文本样式。 |

### 状态与边界
- `translation_interim` 是可替换的临时状态；前端 `translationInterimText` 继续只保存当前临时理解文本。
- `segment_final`、`TranscriptSegment` 和 `TranslationStatus` 未因 Step 17 变化；中文 final 入库仍必须等 Step 18。
- 真实 Qwen interim provider 不进入前端构建产物；前端仍只读取 `VITE_*` 公开配置。
- Provider prompt 不扩写、不补充原文没有的信息，适合实时理解但不作为正式会议档案。
- 失败隔离边界固定：Qwen interim 失败不会阻塞英文 ASR，也不会阻塞后续 Step 18 的中文 final 设计。

### 验证结论
- Step 17 已先跑 RED 测试确认后端缺口，再实现 Qwen interim provider、WebSocket 调度/节流/失败隔离到 GREEN。
- 本地完整验证已通过：后端 Ruff、mypy、pytest；前端 lint、Vitest、build、Playwright E2E；`git diff --check` 仅有 Windows LF/CRLF 提示，无空白错误。
- Lighthouse backend 镜像构建通过，容器内真实 Qwen interim smoke 输出 `qwen-interim-smoke-passed`。
- 截至 Step 17 完成时，Step 18 尚未开始；中文 final、最近 5 个 final 上下文和正式双语归档已在后续 Step 18 补齐。

## 2026-05-13 Step 18 中文 final

### 架构状态
- Step 18 已接入中文 final 生产链路：非 local 环境下，后端在 `SttFinalEvent` 后立即发送英文 `asr_final`，再异步请求 Qwen final 翻译，成功后写入 `transcript_segment` 并推送既有 `segment_final`。
- WebSocket wire schema 未变化；前后端继续复用 Step 10/15/16 已建立的 `asr_final` 与 `segment_final` 消息。
- Qwen final 请求走 OpenAI-compatible `/chat/completions`，复用 `QWEN_API_KEY`、`QWEN_BASE_URL` 和 `QWEN_FINAL_MODEL`；本步未新增环境变量，也未新增前端 `VITE_QWEN_*`。
- final prompt 面向正式会议归档：中文表达准确自然，保留人名、产品名、公司名、数字、日期、金额和业务术语，不总结、不扩写，只输出当前片段中文译文。
- final 请求显式关闭 thinking：`enable_thinking=false`，并限制 `max_tokens=512`、`temperature=0.1`；默认请求超时为 60 秒，避免 `qwen3.6-max-preview` 在会议翻译低推理场景下因思考输出导致延迟过高。
- WebSocket 编排层维护最近 5 个已成功双语 final 片段作为内存上下文窗口；上下文只用于术语和指代一致性，不改变当前片段的 wire schema 或数据库 schema。
- Qwen final 失败隔离边界：失败时仍保存英文 final，`chinese_text_final=""`，`translation_status=failed`，发送可恢复 `warning(code="qwen_final_translation_failed")`；WebSocket 不关闭，后续英文 ASR 和后续 final 继续运行。
- `session_stop`、浏览器断开、resume pause 和错误关闭都会取消 pending final translation task、关闭 final provider，并把当前/排队未完成 final 片段按 failed 状态归档，供后续 Step 25 重试。
- `APP_ENV=local` 继续使用 Step 15 mock provider；非 local 才注入真实 Qwen realtime ASR、Qwen interim 和 Qwen final provider。
- 本步不新增数据库 migration：`transcript_segment` 已有 `translation_status`、`asr_confidence`、英文 final、中文 final、时间戳和 sequence 字段。

### 文件作用

| 文件 | 作用 |
|---|---|
| `backend/src/meeting_mvp_backend/translation_providers.py` | Qwen 文本翻译 provider 模块。Step 18 在既有 interim provider 基础上新增 `FinalTranslationProvider`、`FinalTranslationRequest`、`FinalTranslationContextSegment`、`FinalTranslationError` 和 `QwenFinalTranslationProvider`；负责构造 final `/chat/completions` 请求、关闭 thinking、限制输出长度、解析 assistant content，并把 HTTP/JSON/空响应/缺失配置包装为脱敏错误。 |
| `backend/src/meeting_mvp_backend/ws_sessions.py` | 后端 WebSocket 会话编排层。Step 18 在 STT final 分支中调度 final translation queue，维护最近 5 个成功 final 上下文，成功时创建 `TranscriptSegment` 并发送 `segment_final`，失败或取消时写入 failed 片段并发送 warning/保留可重试状态。 |
| `backend/src/meeting_mvp_backend/main.py` | FastAPI ASGI 入口与依赖组装。非 local WebSocket orchestrator 注入 Qwen final translation provider factory；local 模式保持 mock provider。 |
| `backend/src/meeting_mvp_backend/db/models.py` | 数据库模型。Step 18 复用既有 `TranscriptSegment.translation_status`、`asr_confidence`、`english_text_final`、`chinese_text_final`、`sequence`、`start_ms` 和 `end_ms` 字段，不新增 migration。 |
| `backend/tests/test_translation_providers.py` | Qwen 文本 provider 单元测试。Step 18 新增 final 请求体、模型名、上下文、`enable_thinking=false`、`max_tokens=512`、成功解析、缺失配置脱敏、HTTP 错误、空内容和非法 JSON 覆盖。 |
| `backend/tests/test_websocket_sessions.py` | 后端 WebSocket 行为测试。Step 18 新增 fake final translation provider，覆盖 `asr_final` 后翻译归档、按顺序发送 `segment_final`、最近 5 个上下文、失败入库为 `translation_status=failed`、后续 final 不阻塞、停止时取消 in-flight final 并按 failed 归档。 |
| `backend/tests/integration/test_qwen_final_translation_smoke.py` | 真实 Qwen final gated smoke hook。只有显式设置 `RUN_QWEN_FINAL_SMOKE=1` 且提供真实 Qwen 文本配置时运行；断言返回非空中文、不泄漏英文原句前缀并保留术语，不打印密钥或完整 env。 |
| `backend/tests/integration/test_qwen_realtime_asr_smoke.py` | Qwen ASR smoke fake repository 兼容 Step 18 扩展后的 `create_transcript_segment()` 签名；ASR smoke 本身仍验证 Step 16 英文 final 不入库。 |
| `frontend/src/stores/session-store.ts` | Zustand 会话状态中枢。收到正式 `segment_final` 后按 `sequence` 移除匹配的临时 `englishFinalSegments`，避免英文区重复展示同一 final；其余四区状态逻辑不扩展到 Step 19。 |
| `frontend/src/stores/session-store.test.ts` | store 单元测试。更新实时消息用例，确认 `segment_final` 到达后匹配 `asr_final` 被去重。 |
| `frontend/e2e/app.spec.ts` | Playwright 浏览器测试。更新实时文本流 smoke，确认正式双语 final 到达后英文区展示 `segment_final.english_text_final`，不再保留对应临时 `asr_final` 文本。 |

### 状态与边界
- `asr_final` 是英文 final 的实时展示消息；`segment_final` 是中文 final 成功后的正式双语片段消息。
- 成功中文 final 才会发送 `segment_final`；失败片段不伪造中文 final，只写数据库 failed 状态和 warning。
- `translation_interim` 仍是临时 UI 状态，不进入 PostgreSQL，不参与 final 上下文。
- `final_translation_context` 是单 WebSocket 会话内存状态；服务重启后不恢复上下文，后续会后归档 API/重试由后续步骤处理。
- 当前重点句和会议时间线仍沿用 Step 15 mock/既有前端消费，不在生产 Qwen final 成功后新增 Step 19/F17/F18 行为。
- 真实 Qwen final provider 不进入前端构建产物；前端仍只读取 `VITE_*` 公开配置。

### 验证结论
- Step 18 已先跑 RED 测试确认后端 final provider/编排缺口和前端去重缺口，再实现到 GREEN。
- 本地完整验证已通过：后端 Ruff、mypy、pytest；前端 lint、Vitest、build、Playwright E2E；`git diff --check` 仅有 Windows LF/CRLF 提示，无空白错误。
- Lighthouse backend 镜像使用 `.env.production` 构建通过，容器内真实 Qwen final smoke 最终通过 `1 passed in 3.18s`；首次超时失败后通过关闭 thinking 和限制输出长度修复。
- Step 19 未开始；当前没有新增四区实时 UI 改造、归档 API/页面、搜索、复制、导出、COS 或完整 `usage_event` 链路。

## 2026-05-13 Step 19 四区实时 UI 更新

### 架构状态
- Step 19 是前端实时 UI 补强，不改变后端、数据库、Provider、环境变量或 WebSocket wire schema。
- 四区实时更新边界固定为显式消息驱动：英文区消费 `asr_interim`、`asr_final` 和 `segment_final.english_text_final`；中文区消费 `translation_interim` 和 `segment_final.chinese_text_final`；当前重点句区只消费 `key_sentence_update`；会议时间线区只消费 `timeline_update.items`。
- interim 状态仍可替换；正式 final 只追加。`segment_final` 现在按 `segment_id` 或 `sequence` 幂等处理，避免 WebSocket 重放、浏览器断线恢复或测试 mock 重复推送时重复显示正式双语片段。
- `timeline_update.items` 继续视为服务端权威快照，前端替换整个 `timelineItems` 列表，不自行推导 final 时间线节点；当前重点句也不从 final 自动派生，避免进入 Step 26/27 范围。
- 前端 WebSocket client 对四区实时 callbacks 做失败隔离：某个区域的 UI/store callback 抛错不会触发 `onError`，也不会影响后续 `translation_interim`、`segment_final`、`key_sentence_update` 或 `timeline_update` 的分发。
- 四个实时区都标记为 `aria-live="polite"`，让屏幕阅读器能感知实时内容变化；布局和视觉设计保持原工作台风格。
- Step 20 未开始：本步没有新增异常/降级提示体系、Provider 错误 UI、预算保险丝提示、导出失败提示或完整 `usage_event` 链路。

### 文件作用

| 文件 | 作用 |
|---|---|
| `frontend/src/stores/session-store.ts` | Zustand 会话状态中枢。Step 19 明确 interim 可替换、final 追加；`segment_final` 做幂等追加并移除匹配临时英文 final；`timeline_update.items` 继续按服务端快照替换。 |
| `frontend/src/lib/meeting-websocket.ts` | 前端 WebSocket client。Step 19 为四区实时 callbacks 增加隔离分发，保证某个区域更新失败不破坏 WebSocket 控制流或后续工作区消息。 |
| `frontend/src/App.tsx` | 会议工作台 UI。四个实时区域增加 `aria-live="polite"`，继续分别展示英文原文、中文翻译、当前重点句和会议时间线。 |
| `frontend/src/stores/session-store.test.ts` | store 单元测试。覆盖 interim 替换、final 追加、重复 `segment_final` 去重、匹配 `asr_final` 去重和 timeline 快照替换。 |
| `frontend/src/lib/meeting-websocket.test.ts` | WebSocket client 单元测试。覆盖四区 callback 抛错后，后续实时消息仍能继续分发且不触发 WebSocket error。 |
| `frontend/src/App.test.tsx` | React UI 测试。覆盖四个实时区 live region 标记，以及四区消息分别展示和空状态边界。 |
| `frontend/e2e/app.spec.ts` | Playwright 浏览器测试。Fake WebSocket 模拟完整实时消息流和重复 `segment_final`，验证真实页面四区独立更新且正式 final 不重复显示。 |

### 状态与边界
- `segment_final` 幂等只影响前端展示状态；后端归档仍以 Step 18 的 `transcript_segment` 写入为准。
- 重复 final 去重依据是同一 `segment_id` 或同一 `sequence`；当前会话内 `sequence` 仍由后端按 final 片段顺序维护。
- 四区 callback 隔离只保护实时工作区展示链路；`error` 和 `session_closed` 仍保持原来的不可继续控制语义，留给 Step 20 做用户提示增强。
- 前端仍只读取 `VITE_*` 公开配置；没有 Provider 密钥或生产配置进入浏览器产物。

### 验证结论
- Step 19 已先跑 RED 测试确认前端缺口，再实现 store 幂等、WebSocket callback 隔离和 live region 标记到 GREEN。
- 本地完整验证已通过：后端 Ruff、mypy、pytest；前端 lint、Vitest、build、Playwright E2E；`git diff --check` 仅有 Windows LF/CRLF 提示，无空白错误。
- Step 20 未开始；异常与降级提示仍等待用户明确允许。

## 2026-05-14 Step 20 F16 异常与降级提示

### 架构状态
- Step 20 在前端建立统一异常与降级提示层，不改变 WebSocket wire schema、数据库 schema、环境变量或公开 REST API。
- 用户提示的来源统一收敛到 `SessionNotice`：本地捕获失败、音频处理失败、30 秒无有效音频、WebSocket `warning`、WebSocket `error` 和 `session_closed.reason` 都映射为中文标题、说明、下一步动作和严重级别。
- 前端 store 新增 `activeNotice` 和 `lastClosedReason`。可恢复 warning 只更新提示，不清空四区实时内容；不可继续 error 会停止本地音频处理和媒体流，但保留已收到的 final 片段、临时英文 final、`archiveUrl` 和 `sessionId`。
- UI 在状态栏下方显示提示区域：warning/info 使用 `role="status"` 和 polite live 语义，不可继续 error 使用 `role="alert"` 和 assertive live 语义；提示不会覆盖四区内容。
- WebSocket client 新增 `MeetingWebSocketError`，把服务端 `error.code` 和原始 error message 带到 store，避免预算、额度、恢复失败和 Provider 错误都退化成通用连接失败。
- 后端只补齐 Step 20 必需的 provider warning：Qwen interim 翻译失败会发送 `warning(code="qwen_interim_translation_failed")`；该 warning 不关闭 WebSocket，不影响英文 ASR 或中文 final。
- `export_failed` 仅作为未来导出功能的提示 code 预留；本步未实现真实导出、COS、归档 API/页面或成本埋点。
- Step 21 未开始：当前没有写入 `usage_event`，也没有成本看板、预算事件统计或 Provider 失败埋点。

### 文件作用

| 文件 | 作用 |
|---|---|
| `frontend/src/lib/session-notices.ts` | Step 20 新增的提示映射层。把捕获错误、音频管线错误、WebSocket warning/error、关闭原因和预留导出失败 code 转成统一 `SessionNotice`，并包含腾讯会议 Web 标签页无音频时的系统音频降级建议。 |
| `frontend/src/lib/session-notices.test.ts` | 提示映射单元测试。覆盖授权拒绝、无音轨、30 秒静音、额度/预算拒绝、Qwen interim/final warning、断线恢复失败和导出失败等用户可理解文案与严重级别。 |
| `frontend/src/lib/meeting-websocket.ts` | 前端 WebSocket client。Step 20 新增 `MeetingWebSocketError`，服务端 `error` 消息触发 `onError` 时保留 `code` 和 server message；`warning` 仍作为可恢复消息分发。 |
| `frontend/src/lib/meeting-websocket.test.ts` | WebSocket client 测试。新增服务端 error code 保留断言，并继续覆盖 warning 不触发失败控制流和四区 callback 隔离。 |
| `frontend/src/stores/session-store.ts` | Zustand 会话状态中枢。新增 `activeNotice`、`lastClosedReason`，把捕获、音频、warning、error、closed 统一接入提示模型；错误清理本地音频资源但保留已收到内容与归档入口。 |
| `frontend/src/stores/session-store.test.ts` | store 单元测试。覆盖 warning 不清空实时/归档状态、blocking error 保留 final/archive、腾讯会议无音频降级、断线恢复失败提示和静音提示。 |
| `frontend/src/App.tsx` | 会议工作台 UI。新增状态栏下方的可访问提示区域，按 severity 使用 `role="status"` 或 `role="alert"`，并保持四区内容可见。 |
| `frontend/src/App.test.tsx` | React UI 测试。覆盖提示区域可访问角色、错误文案展示、腾讯会议无音频提示和异常状态下 final 内容仍可见。 |
| `frontend/e2e/app.spec.ts` | Playwright 浏览器测试。Fake WebSocket 增加 provider warning、预算保险丝 error 和恢复失败消息，验证真实页面提示明确且四区内容不被误清空。 |
| `backend/src/meeting_mvp_backend/ws_sessions.py` | 后端 WebSocket 会话编排层。Step 20 在 interim translation provider 失败时发送 `qwen_interim_translation_failed` warning；额度、预算、ASR error 和 session closed 控制流保持既有 schema。 |
| `backend/tests/test_websocket_sessions.py` | 后端 WebSocket 行为测试。新增 Qwen interim warning、每日额度耗尽和预算保险丝拒绝覆盖，确保可恢复 warning 与不可继续 error/closed 边界清晰。 |

### 状态与边界
- `activeNotice` 是前端展示状态，不写数据库；正式会议档案仍只来自 Step 18 的 `transcript_segment`。
- Provider warning 和 WebSocket error 使用既有 `warning` / `error` 消息类型；本步没有新增 message type 或字段。
- 用户主动停止会议不会显示错误提示；服务端非主动关闭原因会映射为不可继续提示。
- 捕获失败、无音轨和静音提示发生在上传正式有效音频前，不应消耗会议额度。
- Playwright E2E 通过 `npm run preview` 服务 `dist`，因此验证 UI 变更前需要先运行 `npm run build`。

### 验证结论
- Step 20 已先跑 RED 测试确认提示映射、WebSocket error code、store 状态和后端 interim warning 缺口，再实现到 GREEN。
- 本地完整验证已通过：后端 Ruff、mypy、pytest；前端 lint、Vitest、build、Playwright E2E；`git diff --check` 仅有 Windows LF/CRLF 提示，无空白错误。
- Step 21 未开始；使用量与成本埋点、`usage_event` 写入和看板仍等待用户明确允许。

## 2026-05-15 Step 21 usage_event 埋点基础

### 架构状态
- Step 21 在后端建立基础 usage event 写入层，不改变数据库 schema、WebSocket wire schema、前端公开配置或公开 REST API。
- 既有 `usage_event` 表继续作为漏斗、质量和成本分析的基础事件源；本步复用 Step 07 已有 `client_id`、可选 `session_id`、`event_type`、`payload`、`created_at` 字段，不新增 migration。
- 新增 `usage_events` 模块集中管理事件 allowlist、payload 安全校验、事件记录结构和 SQLAlchemy 写入器。业务代码只通过 recorder 写事件，避免在匿名初始化和 WebSocket 编排层直接拼 SQLAlchemy `UsageEvent`。
- `SQLAlchemyUsageEventRecorder` 由 FastAPI 依赖组装注入 `AnonymousClientService` 和 `WebSocketSessionOrchestrator`；local/mock 与生产路径共用同一事件写入接口。
- `usage_event` 写入为 best-effort：写入失败只记录脱敏 warning，不中断匿名初始化、额度拒绝、音频上传、Provider 调用、segment 归档或会话关闭。
- WebSocket 会话事件覆盖后端可确定的漏斗节点：`capture_started`、`quota_checked`、`session_started`、`audio_detected`、ASR/翻译/归档事件、`provider_error`、额度/预算拒绝和 `session_closed`。
- `capture_failed` 和 `archive_viewed` 只在本步完成事件类型和安全写入能力；浏览器本地捕获失败上报与真实归档查看触发点仍属于后续明确步骤，避免提前进入 Step 22。
- 事件 payload 只保存元数据：状态、长度、序号、时间点、错误 code/type、剩余额度、capture/source 类型等；不保存英文原文、中文译文、原始音频、PCM frame、明文 token、明文 IP/User-Agent 或任何 Provider 密钥。

### 文件作用

| 文件 | 作用 |
|---|---|
| `backend/src/meeting_mvp_backend/usage_events.py` | Step 21 新增的 usage event 核心模块。定义 `UsageEventType` allowlist、`STEP_21_USAGE_EVENT_TYPES`、`UsageEventRecord`、`UsageEventRecorder` 协议、`SQLAlchemyUsageEventRecorder`、payload 安全校验和 `record_usage_event_best_effort()`。 |
| `backend/src/meeting_mvp_backend/anonymous_clients.py` | 匿名用户初始化服务。Step 21 注入 usage event recorder，新匿名用户创建成功后记录 `client_created`，payload 只包含脱敏存在性标记和额度配置。 |
| `backend/src/meeting_mvp_backend/main.py` | FastAPI ASGI 入口与依赖组装。Step 21 为匿名初始化服务和 WebSocket orchestrator 创建并注入 `SQLAlchemyUsageEventRecorder`。 |
| `backend/src/meeting_mvp_backend/ws_sessions.py` | 后端 WebSocket 会话编排层。Step 21 在会话开始、额度检查、音频激活、ASR、翻译、归档、Provider 错误和关闭路径记录 usage event；不改变既有 WebSocket 消息结构。 |
| `backend/src/meeting_mvp_backend/db/models.py` | 数据库模型。Step 21 复用既有 `UsageEvent` 模型和 PostgreSQL JSONB payload；字段保持 Step 07 schema，不新增 migration。 |
| `backend/tests/test_usage_events.py` | usage event 模块单元测试。覆盖事件 allowlist、必要字段、SQLAlchemy writer 行为、payload 安全拒绝和 best-effort 失败隔离。 |
| `backend/tests/test_anonymous_clients_service.py` | 匿名初始化服务单元测试。覆盖新匿名用户写入 `client_created`，以及既有匿名用户不重复记录创建事件。 |
| `backend/tests/test_websocket_sessions.py` | WebSocket 行为测试。Step 21 新增 fake recorder，覆盖成功会话漏斗、Provider/归档事件、额度/预算拒绝和 Provider 错误事件。 |

### 状态与边界
- `usage_event` 是观测数据，不是主业务状态来源；正式会议档案仍以 `transcript_segment` 为准，额度实时状态仍以 Redis 为准。
- `session_started` WebSocket 响应仍返回明文 `archive_token` 给浏览器；usage event payload 明确不保存该 token、`archive_url` 或 token hash。
- `client_created` 只在新匿名用户创建后写一次；重复匿名初始化只更新 `anonymous_client.last_seen_at` / `user_agent_hash`，不重复写创建事件。
- local mock Provider 会写 ASR/翻译/归档/Provider warning 事件，便于本地漏斗测试；真实 Qwen provider 路径写入同一套事件类型。
- Step 21 结束时尚未有归档查询 API/页面、token 校验 API 或真实 `archive_viewed` 触发点；这些能力已在 Step 22 补齐。

### 验证结论
- Step 21 已先跑 RED 测试确认缺少 `usage_events` 模块和 WebSocket recorder 注入缺口，再实现到 GREEN。
- 本地后端验证通过：Ruff、mypy、pytest；pytest 结果为 100 passed，13 integration deselected。
- 本地前端回归验证通过：lint、Vitest、build、Playwright E2E；本步未修改前端代码。
- Step 22 已在 2026-05-16 小节落地；Step 23 搜索与复制已在后续小节补齐。

## 2026-05-16 Step 22 基础双语归档页/API

### 架构状态
- Step 22 实现 F10 基础双语归档闭环：浏览器通过 `/archive/:sessionId?token=...` 打开只读归档页，前端调用后端 `GET /api/archives/{session_id}?token=...` 获取 session 元数据和双语 final 片段。
- 本步不新增数据库 migration，继续复用 `meeting_session`、`transcript_segment` 和 `usage_event`。归档正文来源只来自 `transcript_segment` 的 final 字段，不读取或保存 raw audio、interim 文本或前端私有信息。
- archive token 逻辑从 WebSocket 会话编排中抽到 `archive_tokens`，WebSocket 建会继续生成明文 token 返回给浏览器，但数据库只保存 `archive_token_hash`；归档 API 只接收一次性查询 token 并做 hash 校验，不在响应、usage event 或日志中回显 token。
- `ArchiveService` 是后端归档业务边界：校验 token、判断 retention 是否过期、读取 final segments、派生 `end_reason`，并在成功查看后 best-effort 写入 `archive_viewed`。
- 归档访问错误遵循信息隐藏边界：缺 token 是 401；session 不存在、token 错误、归档过期统一 404，避免通过 API 区分 session 是否存在。
- `end_reason` 优先从最新 `usage_event(event_type=session_closed).payload.reason` 派生；如果历史会话缺少该事件，则 fallback 到 `meeting_session.status.value`。
- `archive_viewed` 是 Step 22 新增的真实触发点，payload 只保存 `segment_count`、`session_status`、`end_reason`、`translation_failed_count` 等统计元数据，不保存正文、译文、token、archive URL、IP/User-Agent 或 Provider 密钥。
- 前端归档页是轻量路径分流，不引入 React Router；`App.tsx` 在 `/archive/` 路径渲染 `ArchivePage`，其余路径仍渲染实时会议工作台。
- Step 22 结束时尚未实现搜索、复制、Markdown/JSON 导出、COS 导出文件、归档增强看板、成本看板或重点句/时间线增强；搜索与复制已在 Step 23 补齐。

### 文件作用

| 文件 | 作用 |
|---|---|
| `backend/src/meeting_mvp_backend/archive_tokens.py` | 归档 token 共享模块。提供 `hash_archive_token()` 和 `build_archive_url()`，让 WebSocket 建会与归档 API 使用同一套 token hash/URL 逻辑。 |
| `backend/src/meeting_mvp_backend/archives.py` | Step 22 后端归档核心模块。定义归档响应模型、repository protocol、SQLAlchemy repository、`ArchiveService` 和 `ArchiveAccessDenied`；负责 token 校验、过期判断、final 片段查询、`end_reason` 派生和 `archive_viewed` 写入。 |
| `backend/src/meeting_mvp_backend/main.py` | FastAPI ASGI 入口。新增 archive service 依赖和 `GET /api/archives/{session_id}` 路由；缺 `DATABASE_URL` 时返回 503，缺 token 返回 401，访问失败隐藏为 404。 |
| `backend/src/meeting_mvp_backend/ws_sessions.py` | 后端 WebSocket 会话编排层。Step 22 改为从 `archive_tokens` 导入并显式 re-export `hash_archive_token` / `build_archive_url`，保持既有会话启动和归档 URL 返回行为。 |
| `backend/src/meeting_mvp_backend/db/models.py` | 数据库模型。Step 22 复用 `MeetingSession.archive_token_hash`、`retention_expires_at`、`TranscriptSegment` final 字段和 `UsageEvent`，不新增 schema。 |
| `backend/tests/test_archives.py` | 后端归档单元/API 测试。覆盖正确 token、缺 token、空 token、错误 token、过期归档、segment 排序、不同关闭原因和 `archive_viewed` payload 安全边界。 |
| `frontend/src/api/archives.ts` | 前端归档 API client。构造 `/api/archives/{session_id}?token=...` URL，支持 `VITE_API_BASE_URL`，使用 Zod 校验响应，并把 HTTP 错误映射为 `ArchiveAccessError`。 |
| `frontend/src/archive/ArchivePage.tsx` | 前端基础归档页。解析 `/archive/:sessionId` 和 `token`，展示 loading、缺 token、无权限/过期、空归档、正常/异常结束状态，以及双语 final 片段、时间戳、翻译状态和重点句标记。 |
| `frontend/src/App.tsx` | 前端顶层分流。Step 22 在 `/archive/` 路径渲染归档页，其他路径保持原实时会议工作台；没有引入 React Router。 |
| `frontend/src/api/archives.test.ts` | 前端 API client 单元测试。覆盖 URL 构造、响应解析、HTTP 错误和 Zod schema 校验失败。 |
| `frontend/src/archive/ArchivePage.test.tsx` | 归档页组件测试。覆盖 loading、成功、空片段、缺 token、无权限/过期和异常结束原因展示。 |
| `frontend/e2e/archive.spec.ts` | Playwright 归档页 smoke test。Mock archive API 后打开 `/archive/:sessionId?token=...`，验证归档正文展示和桌面/移动无水平溢出。 |

### 数据与安全边界
- 归档 API 的成功响应只返回产品需要展示的 session 元数据和 final 片段；不返回 `archive_token_hash`、明文 token、`archive_url`、usage event payload 或匿名用户 IP/User-Agent hash。
- `translation_status=failed` 的片段会正常展示英文 final 与失败状态；后续 final 重试属于 M1-B/F13，不在 Step 22 中实现。
- 空归档是合法状态，表示 session 已存在且 token 通过，但当前没有 final 片段；页面展示空状态，不自动派生内容。
- `archive_viewed` 写入失败不影响归档读取；usage event 仍是观测数据，不作为归档授权或正文来源。
- 搜索、复制、Markdown/JSON 导出、COS 私有对象与短期签名 URL 仍属于后续步骤，不能在 Step 22 基础页中提前引入。

### 验证结论
- Step 22 已先跑 RED 测试确认缺少后端 `archives` 模块和前端归档 API/页面，再实现到 GREEN。
- 本地后端完整验证已通过：Ruff、mypy、pytest；pytest 结果为 110 passed，13 integration deselected。
- 本地前端完整验证已通过：lint、Vitest、build、Playwright E2E；Vitest 为 13 个测试文件、88 个测试通过，E2E 为 10 个 Chromium 测试通过。
- Step 23 已在后续小节补齐搜索与复制；导出、COS 和归档增强功能仍未开始。

## 2026-05-16 Step 23 搜索与复制

### 架构状态
- Step 23 在 Step 22 基础归档页上实现 F11：归档页本地搜索已加载的 final 片段，并允许复制单个双语片段进入用户工作流。
- 本步不新增数据库 migration、不新增后端搜索查询 API、不读取或写入 `export_file`，也不实现 Markdown/JSON 导出、COS 上传或短期签名 URL。
- 搜索只发生在前端当前 `ArchiveResponse.segments` 内，范围包括 `english_text_final`、`chinese_text_final`、开始/结束时间戳和时间范围；空搜索显示全部片段，有搜索无命中显示空结果状态。
- 复制使用浏览器 Clipboard API，复制文本固定包含时间、英文原文和中文翻译；复制失败只显示前端可访问错误提示，不清空已加载归档内容。
- 价值事件使用新的归档事件 API：`POST /api/archives/{session_id}/events?token=...`。该接口复用 Step 22 的 archive token 授权、retention 判断和信息隐藏边界。
- `usage_event` 新增 `archive_searched` 与 `segment_copied`。搜索 payload 只记录搜索词长度与命中统计；复制 payload 由后端根据 `segment_id` 派生 sequence、translation status、文本长度和重点句标记。
- 事件写入继续 best-effort：写入失败不影响归档查看、搜索过滤或复制动作。
- Step 24 未开始：当前没有导出格式、COS 对象、`export_created` / `export_failed` 真实触发或导出 UI。

### 文件作用

| 文件 | 作用 |
|---|---|
| `backend/src/meeting_mvp_backend/usage_events.py` | Step 23 扩展 usage event allowlist，新增 `archive_searched`、`segment_copied` 和 `STEP_23_USAGE_EVENT_TYPES`；payload 安全校验拒绝搜索词、正文、token、archive URL、音频和密钥字段。 |
| `backend/src/meeting_mvp_backend/archives.py` | 后端归档业务模块。Step 23 新增归档事件请求模型和 `ArchiveService.record_archive_event()`，复用 token 校验与过期判断，记录安全的搜索/复制元数据。 |
| `backend/src/meeting_mvp_backend/main.py` | FastAPI 入口。Step 23 新增 `POST /api/archives/{session_id}/events`，缺 token 返回 401，授权失败/过期/非法 segment 统一 404，成功返回 204。 |
| `backend/tests/test_usage_events.py` | usage event 单元测试。覆盖 Step 21 allowlist 稳定、Step 23 allowlist 扩展，以及搜索词/正文/token/audio/secret payload 拒绝。 |
| `backend/tests/test_archives.py` | 归档服务/API 测试。覆盖搜索事件、复制事件、非法 segment、缺 token、错误 token 和 best-effort 事件边界。 |
| `frontend/src/api/archives.ts` | 前端归档 API client。Step 23 新增 `ArchiveEvent`、事件 URL 构造和 `recordArchiveEvent()`，只发送安全元数据。 |
| `frontend/src/archive/ArchivePage.tsx` | 前端归档页。Step 23 增加搜索输入、本地过滤、无结果状态、片段复制按钮、复制失败提示和搜索/复制事件上报。 |
| `frontend/src/api/archives.test.ts` | 前端 API client 测试。覆盖事件 URL、POST body、204 成功和 HTTP 错误映射。 |
| `frontend/src/archive/ArchivePage.test.tsx` | 归档页组件测试。覆盖英文/中文/时间搜索、无结果状态、debounced 搜索事件、复制文本格式、复制成功事件和 clipboard 失败。 |
| `frontend/e2e/archive.spec.ts` | Playwright 归档页 smoke test。Mock archive API 和事件 API，验证搜索过滤、复制按钮和无水平溢出。 |

### 数据与安全边界
- `archive_searched` 不保存搜索词原文，只保存 `query_length`、`matched_segment_count`、`total_segment_count`。
- `segment_copied` 不保存英文正文或中文译文，只保存 `segment_id`、`sequence`、`translation_status`、`english_text_length`、`chinese_text_length`、`is_key_sentence`。
- 前端事件 POST body 不包含 token 字段；token 只作为既有归档授权查询参数发送给后端。
- 后端 payload 安全校验允许长度类元数据，但拒绝 `query`、`text`、`english_text`、`chinese_text`、`archive_url`、token、secret、raw audio、PCM frame 等字段。
- 搜索/复制事件只用于价值验证漏斗，不作为归档授权、归档正文或导出流程的状态来源。

### 验证结论
- Step 23 已按 TDD 先跑 RED：后端缺少 Step 23 事件/API 入口，前端缺少事件 API client、搜索输入和复制按钮；再实现到 GREEN。
- 本地后端完整验证已通过：Ruff、mypy、pytest；pytest 结果为 121 passed，13 integration deselected。
- 本地前端完整验证已通过：lint、Vitest、build、Playwright E2E；Vitest 为 13 个测试文件、95 个测试通过，E2E 为 10 个 Chromium 测试通过。
- Step 24 未开始；当前没有 Markdown/JSON 导出、COS、`export_file` 或签名 URL。

## 2026-05-16 Step 24 Markdown / JSON 导出

### 架构状态
- Step 24 在 Step 22/23 归档授权和页面基础上实现 F12：用户在归档页通过同一 `session_id + archive_token` 授权边界生成 Markdown 或 JSON 导出文件。
- 本步不新增数据库 migration，复用现有 `meeting_session`、`transcript_segment`、`export_file` 和 `usage_event` 表；正式导出内容仍只来自 final 片段，不读取 raw audio、interim 文本或前端私有信息。
- 新增 `exports` 模块作为后端导出业务边界：负责 token 校验、retention 判断、final 片段排序、Markdown/JSON 渲染、COS 私有对象上传、短期下载地址生成、`export_file` 写入和导出事件记录。
- `ArchiveExportService` 复用 Step 22 的信息隐藏策略：缺 token 是 401；session 不存在、token 错误、归档过期统一 404；归档存在但没有 final 片段返回 409；COS 配置缺失、上传失败、签名失败或数据库写入失败返回 503。
- COS 访问通过 `ArchiveObjectStorage` 协议隔离，生产实现为 `TencentCosArchiveObjectStorage`，使用 `cos-python-sdk-v5`；单元测试使用 fake storage，不依赖真实 COS 密钥。
- 导出 object key 由后端生成，格式为 `TENCENT_COS_EXPORT_PREFIX/{session_id}/{export_id}.md|json`；API 响应不暴露 object key，只返回短期下载地址、过期时间和导出元数据。
- `export_file` 成为导出审计和清理入口：记录导出格式、COS object key、当前短期 URL 字段、创建时间和导出保留时间；COS 对象仍保持私有。
- `usage_event` 新增 `export_created` 和 `export_failed`，继续作为观测数据。写入失败不影响导出成功响应，导出失败也只记录安全元数据。
- 前端归档页在已加载 archive response 上增加导出工具区：Markdown/JSON 按钮、空归档禁用态、成功下载链接和失败提示。导出成功不会自动跳转，也不会清空搜索、复制或已加载归档内容。
- Step 24 完成时尚未实现 final 翻译重试、补译任务、重试 UI 或失败片段自动刷新；后台自动补译已在 Step 25 补齐，且仍未新增公开手动 retry API。

### 文件作用

| 文件 | 作用 |
|---|---|
| `backend/src/meeting_mvp_backend/exports.py` | Step 24 新增的导出核心模块。定义导出请求/响应模型、导出异常、Markdown/JSON renderer、COS storage 协议、Tencent COS 实现、`ExportFileRepository` 协议、SQLAlchemy `export_file` 写入器和 `ArchiveExportService`。 |
| `backend/src/meeting_mvp_backend/main.py` | FastAPI 入口。新增 `get_archive_export_service()` 依赖和 `POST /api/archives/{session_id}/exports` 路由；负责把缺 token、授权失败、空归档和导出临时不可用映射为 401/404/409/503。 |
| `backend/src/meeting_mvp_backend/usage_events.py` | usage event 核心模块。Step 24 新增 `export_created`、`export_failed` 和 `STEP_24_USAGE_EVENT_TYPES`，并扩展 payload 安全校验，拒绝下载 URL、签名 URL、COS URL、object key、token、正文、音频和密钥字段。 |
| `backend/src/meeting_mvp_backend/db/models.py` | 数据库模型。Step 24 复用既有 `ExportFile` 与 `ExportFormat(markdown/json)`，不新增 schema；`export_file` 保存 COS 私有对象 key、短期 URL 字段和保留时间。 |
| `backend/pyproject.toml` / `backend/uv.lock` | 后端依赖锁。Step 24 新增 `cos-python-sdk-v5`，用于生产 Tencent COS 上传和签名 URL 生成。 |
| `backend/tests/test_exports.py` | 后端导出测试。覆盖 Markdown/JSON 渲染、成功导出、`export_file` 写入、`export_created`、空归档拒绝、COS 失败、授权复用和 API 状态码。 |
| `backend/tests/test_usage_events.py` | usage event 测试。覆盖 Step 24 allowlist 扩展，以及下载 URL、签名 URL、COS URL、object key 等敏感字段拒绝。 |
| `frontend/src/api/archives.ts` | 前端归档 API client。Step 24 新增 `ArchiveExportResponse`、`ArchiveExportFormat`、`buildArchiveExportApiUrl()` 和 `createArchiveExport()`；导出 POST body 只包含格式。 |
| `frontend/src/archive/ArchivePage.tsx` | 前端归档页。Step 24 新增导出工具区、Markdown/JSON 按钮、空归档禁用态、成功下载链接和导出失败提示。 |
| `frontend/src/api/archives.test.ts` | 前端 API client 测试。覆盖导出 URL、POST body、响应解析和 HTTP 错误映射。 |
| `frontend/src/archive/ArchivePage.test.tsx` | 归档页组件测试。覆盖导出按钮、空归档禁用、成功链接、409/503 失败提示和归档内容保留。 |
| `frontend/e2e/archive.spec.ts` | Playwright 归档页 smoke test。Mock 导出 API，验证搜索、复制、导出 JSON 和页面无水平溢出。 |

### 数据与安全边界
- Markdown / JSON 导出文件会包含 session 元数据和双语 final 正文，因此只写入后端受控的私有 COS 对象；前端不接触 COS 密钥，也不生成 object key。
- `POST /api/archives/{session_id}/exports` 的 request body 只允许 `format`；archive token 仍只作为授权 query 参数，且不写入 body、响应模型、usage event 或日志。
- `export_created` payload 只保存 `format`、`segment_count`、`file_size_bytes`、`translation_failed_count`、`signed_url_ttl_seconds`。
- `export_failed` payload 只保存 `format`、`stage`、`error_type`、`segment_count`；不保存异常正文、COS object key、短期下载地址、token、正文、译文或密钥。
- `export_file.cos_object_key` 是数据库内部清理和审计字段，不返回给前端；`export_file.cos_url` 是短期 URL 字段，不应视为永久公开地址。
- 空归档不会生成文件，也不会写 `export_file`；前端禁用导出按钮，后端仍保留 409 防线。

### 验证结论
- Step 24 已按 TDD 先跑 RED：后端缺少 Step 24 事件集合和 `exports` 模块，前端缺少导出 API client 与导出控件；再实现到 GREEN。
- 本地后端完整验证已通过：Ruff、mypy、pytest；pytest 结果为 141 passed，13 integration deselected。
- 本地前端完整验证已通过：lint、Vitest、build、Playwright E2E；Vitest 为 13 个测试文件、101 个测试通过，E2E 为 10 个 Chromium 测试通过。
- 真实 COS smoke 未在 Windows 本地执行；应在 Lighthouse 后端容器中使用安全环境变量 gated 运行，且不得输出密钥或短期签名 URL。
- Step 24 验证时尚未开始 final 翻译重试；后台自动补译链路已在 Step 25 补齐。

## 2026-05-16 Step 25 后台 Final 补译队列

### 架构状态
- Step 25 实现 F13 的后台自动补译路径：Qwen final 首次失败后，后端把 failed `transcript_segment` 自动入队，由后台 worker 复用现有 Qwen final provider 补译，成功后更新归档。
- 本步不新增数据库 migration、不新增公开手动 retry API、不新增前端事件上报 API；重试次数、失败原因和 exhausted 状态只从安全 `usage_event` 元数据派生。
- 新增 `translation_retries` 模块作为补译队列边界，包含 Redis queue、worker、processor、SQLAlchemy repository 和测试 fake；本地 local 环境默认不启动真实 worker。
- Redis scheduled set key 固定为 `meeting_mvp:translation_retry:scheduled`；segment lock key 固定为 `meeting_mvp:translation_retry:lock:{segment_id}`，用于避免多个 worker 并发处理同一片段。
- Redis job 只保存 `session_id`、`segment_id`、`due_at`，不保存英文正文、中文译文、archive token、archive URL、COS object key、签名 URL、密钥或用户隐私。
- 补译 processor 从 PostgreSQL 读取 failed/retrying 片段，携带原英文 final 与目标片段前最近 5 条已完成双语上下文调用 `FinalTranslationProvider`；不会从 Redis job 或 usage event 读取正文。
- 状态流转复用既有 `transcript_segment.translation_status`：`failed -> retrying -> completed`；provider 失败时恢复 `failed`，未达 3 次上限则按固定退避重新入队，达到上限后停止自动重试。
- FastAPI lifespan 只在 `DATABASE_URL`、`REDIS_URL`、非 local 环境且 Qwen final 配置完整时启动 worker；启动时扫描未过期 session 下的 failed/retrying 片段并补加入队，关闭应用时 cancel worker 并释放 Redis queue。
- WebSocket 会话编排在 Qwen final 首次失败并写入 failed 片段后入队；入队失败只记录 warning，不影响 WebSocket、归档或额度结算主流程。
- 归档 API segment 响应新增 `translation_retry_attempts` 与 `translation_retry_exhausted`，均从 `usage_event` 派生，不新增表字段。
- 前端归档页继续使用现有 GET API：显示等待后台补译、后台补译中、补译失败和翻译完成状态；存在 pending/retrying 片段时 polling 重新拉取归档，失败时保留当前内容。
- Step 26 已在后续小节补齐当前重点句增强；Step 27 未开始，当前没有会议时间线增强。

### 文件作用

| 文件 | 作用 |
|---|---|
| `backend/src/meeting_mvp_backend/translation_retries.py` | Step 25 后端补译核心模块。定义 `TranslationRetryJob`、Redis-backed queue、`TranslationRetryWorker`、`TranslationRetryProcessor`、SQLAlchemy repository、测试 fake、Redis key 常量、最大尝试次数和固定退避策略。 |
| `backend/src/meeting_mvp_backend/ws_sessions.py` | WebSocket 会话编排层。Step 25 在 Qwen final 首次失败并归档 failed 片段后调用补译 queue 入队；入队失败只记录脱敏 warning，不阻断会话主流程。 |
| `backend/src/meeting_mvp_backend/main.py` | FastAPI ASGI 入口。Step 25 在 lifespan 中按配置条件创建 Redis queue、SQLAlchemy repository、Qwen final provider factory 和 worker task；关闭时 cancel worker 并关闭 queue。 |
| `backend/src/meeting_mvp_backend/archives.py` | 后端归档业务模块。Step 25 在 segment 响应中增加 retry metadata，并通过 `usage_event` 派生 retry attempts/exhausted；归档片段顺序仍按 `sequence` 升序。 |
| `backend/src/meeting_mvp_backend/usage_events.py` | usage event 核心模块。Step 25 新增 `translation_final_retry_requested`、`translation_final_retry_failed` 和 `STEP_25_USAGE_EVENT_TYPES`，并继续执行 payload 安全校验。 |
| `backend/src/meeting_mvp_backend/translation_providers.py` | Qwen final provider 所在模块。Step 25 processor 复用既有 `FinalTranslationProvider`、`FinalTranslationRequest` 和最近 5 条上下文结构，不新增 provider 协议。 |
| `backend/src/meeting_mvp_backend/db/models.py` | 数据库模型。Step 25 复用既有 `TranscriptSegment.translation_status=failed|retrying|completed`、`UsageEvent` 和 `MeetingSession.retention_expires_at`，不新增 schema。 |
| `backend/tests/test_translation_retries.py` | 补译队列/processor 单元测试。覆盖安全 job、去重、到期拉取、segment lock、成功补译、provider 失败重入队、最大次数停止、启动扫描和 usage event best-effort。 |
| `backend/tests/test_archives.py` | 归档服务/API 测试。Step 25 扩展覆盖 `translation_retry_attempts` 和 `translation_retry_exhausted` 派生字段。 |
| `backend/tests/test_usage_events.py` | usage event 测试。覆盖 Step 25 allowlist 和 token、正文、译文、URL、object key、密钥、音频字段拒绝。 |
| `backend/tests/test_websocket_sessions.py` | WebSocket 会话测试。Step 25 扩展 Qwen final 失败场景，确认 failed segment 会被补译 queue 接收。 |
| `frontend/src/api/archives.ts` | 前端归档 API client。Step 25 扩展 Zod schema 支持 retry metadata；旧后端响应缺字段时使用默认值。 |
| `frontend/src/archive/ArchivePage.tsx` | 前端归档页。Step 25 展示补译等待/进行中/失败/完成状态，并在有未 exhausted 的 failed/retrying 片段时 polling 拉取最新归档。 |
| `frontend/src/api/archives.test.ts` | 前端 API client 测试。覆盖 retry metadata 解析和旧响应默认值。 |
| `frontend/src/archive/ArchivePage.test.tsx` | 归档页组件测试。覆盖补译状态文案、polling 成功补齐中文 final、polling 失败保留内容。 |
| `frontend/e2e/archive.spec.ts` | Playwright 归档页 smoke test。Step 25 增加 failed 片段自动刷新为 completed 的浏览器路径验证，并继续检查无水平溢出。 |

### 数据与安全边界
- `translation_final_retry_requested` payload 只保存 `attempt_number`、`segment_id`、`sequence`、`english_length`、`context_segment_count`、`max_attempts` 等元数据，不保存英文正文或上下文正文。
- 补译成功沿用 `translation_final_completed`，payload 新增 `retry=true`、`attempt_number`、`segment_id`、`sequence`、`english_length`、`chinese_length`、`context_segment_count` 等安全元数据。
- `translation_final_retry_failed` payload 只保存 `attempt_number`、`stage`、`error_type`、`will_retry`、`max_attempts` 等元数据，不保存 provider 原始错误正文、URL、token、正文、译文或密钥。
- retry attempts 和 exhausted 状态来自 `usage_event` 聚合，因此不会改变 `transcript_segment` schema；归档 API 只返回派生整数和布尔值。
- usage event 写入失败不影响补译主流程；队列入队失败不影响 WebSocket 主流程；polling 失败不影响归档阅读、搜索、复制或导出。
- Redis 只保存短期调度元数据，PostgreSQL 仍是正式 final 文本和归档来源；第一版仍默认不保存原始会议音频。

### 验证结论
- Step 25 已按 TDD 先跑 RED：后端缺少 Step 25 事件集合和 `translation_retries` 模块，前端缺少 retry metadata 和 polling 行为；再实现到 GREEN。
- 本地后端完整验证已通过：Ruff、mypy、pytest；pytest 结果为 151 passed，13 integration deselected。
- 本地前端完整验证已通过：lint、Vitest、build、Playwright E2E；Vitest 为 13 个测试文件、105 个测试通过，E2E 为 11 个 Chromium 测试通过。
- `git diff --check` 已通过，仅输出 Windows LF/CRLF 工作区提示，无空白错误。
- Step 26 已在后续小节补齐当前重点句增强；Step 27 未开始，当前没有会议时间线增强。

## 2026-05-17 Step 26 当前重点句增强

### 架构状态

- Step 26 实现 F17 的低成本规则路径：Qwen final 成功后由后端用确定性关键词规则识别重点句，不新增模型调用、环境变量、数据库 migration 或外部服务。
- 自动识别结果写入既有 `transcript_segment.is_key_sentence` 字段；PostgreSQL 仍是正式归档和重点句标记的唯一持久化来源。
- WebSocket 成功 final 链路保持顺序：英文 `asr_final` 先推送，中文 final 成功后写入 `transcript_segment` 并推送 `segment_final`；若规则命中，再推送既有 `key_sentence_update`。本步不修改 wire schema。
- Qwen final 失败链路保持 Step 25 行为：保存英文 final、空中文 final、`translation_status=failed` 并进入补译队列；失败片段不自动标记重点句，也不发送重点句更新。
- 归档页新增人工标记能力，通过 `PATCH /api/archives/{session_id}/segments/{segment_id}/key-sentence?token=...` 修改同一字段；授权继续使用 `session_id + archive_token`，缺 token 返回 401，错误 token、过期归档或非法 segment 统一 404。
- `usage_event` 新增 `key_sentence_marked`，只记录安全元数据；正文、译文、token、URL、密钥和音频继续被 payload 安全校验拒绝。
- 前端归档页在已加载 final 片段上做本地“只看重点句”筛选，并允许人工标记/取消重点句；成功后更新本地 segment，失败时显示可访问错误提示并保留原归档内容。
- Step 27 未开始：会议时间线仍只消费服务端显式 `timeline_update.items`，没有重点句节点、导出节点、异常节点、筛选或跳转能力。

### 文件作用

| 文件 | 作用 |
|---|---|
| `backend/src/meeting_mvp_backend/key_sentences.py` | Step 26 新增重点句规则模块。集中定义英文/中文关键词、`is_key_sentence_candidate()` 和 `key_sentence_display_text()`，用于 WebSocket final 成功路径判断和重点句展示文本选择。 |
| `backend/src/meeting_mvp_backend/ws_sessions.py` | WebSocket 会话编排层。Step 26 在 Qwen final 成功归档前调用规则模块，写入 `is_key_sentence`；命中时发送 `key_sentence_update`，失败 final 不标记也不推送。 |
| `backend/src/meeting_mvp_backend/archives.py` | 归档业务模块。Step 26 新增 `ArchiveKeySentenceUpdateRequest`、repository `set_segment_key_sentence()` 和 `ArchiveService.set_segment_key_sentence()`，复用 archive token 授权后更新 segment 并记录安全事件。 |
| `backend/src/meeting_mvp_backend/main.py` | FastAPI 入口。Step 26 新增 `PATCH /api/archives/{session_id}/segments/{segment_id}/key-sentence`，负责 token 缺失 401、授权失败 404 和 segment 响应返回。 |
| `backend/src/meeting_mvp_backend/usage_events.py` | usage event 核心模块。Step 26 新增 `key_sentence_marked` 和 `STEP_26_USAGE_EVENT_TYPES`，沿用 payload 安全校验禁止正文、token、URL、密钥和音频。 |
| `backend/tests/test_key_sentences.py` | 重点句规则单元测试，覆盖行动项/决策/截止时间等命中、普通会议填充语不命中，以及展示文本优先中文 final。 |
| `backend/tests/test_websocket_sessions.py` | WebSocket 会话测试。Step 26 扩展真实 final 翻译成功场景，确认重点句写入归档并推送 `key_sentence_update`。 |
| `backend/tests/test_archives.py` | 归档服务/API 测试。Step 26 覆盖人工标记/取消重点句、非法 segment 拒绝、PATCH endpoint 401/404 和安全 usage event payload。 |
| `backend/tests/test_usage_events.py` | usage event 测试。Step 26 覆盖 allowlist 扩展到 `STEP_26_USAGE_EVENT_TYPES`。 |
| `backend/tests/test_exports.py` | 导出测试 fake repository 补齐 `set_segment_key_sentence()`，保持 Step 24 导出服务继续满足归档 repository 协议。 |
| `frontend/src/api/archives.ts` | 前端归档 API client。Step 26 新增重点句 PATCH URL 构造和 `updateArchiveSegmentKeySentence()`；请求 body 只包含布尔标记，token 仍只在 query 中。 |
| `frontend/src/archive/ArchivePage.tsx` | 前端归档页。Step 26 增加“只看重点句”筛选、片段标记/取消重点句按钮、失败提示和本地 segment 状态更新；polling 空响应不清空现有内容。 |
| `frontend/src/api/archives.test.ts` | 前端 API client 测试。覆盖重点句 PATCH URL、body 安全边界、响应解析和 HTTP 错误映射。 |
| `frontend/src/archive/ArchivePage.test.tsx` | 归档页组件测试。覆盖重点句筛选、人工标记成功、本地状态更新和标记失败保留内容。 |
| `frontend/e2e/archive.spec.ts` | Playwright 归档页 smoke test。Step 26 mock PATCH endpoint，验证人工标记、只看重点句筛选、复制/导出既有流程和无水平溢出。 |
| `memory-bank/progress.md` | 开发进度记录。Step 26 记录本次完成内容、RED/GREEN 测试、完整验证结果和 Step 27 未开始的边界。 |
| `memory-bank/architecture.md` | 架构记录。Step 26 记录当前重点句数据流、API/事件边界、安全约束和文件职责。 |
| `AGENTS.md` | Codex/AI 项目记忆。Step 26 同步项目状态、后续限制和 Step 27 等待用户明确允许。 |

### 数据与安全边界

- `transcript_segment.is_key_sentence` 是自动规则识别和归档人工标记的统一持久化字段，不新增 schema。
- `PATCH /api/archives/{session_id}/segments/{segment_id}/key-sentence` 的 request body 只允许 `is_key_sentence`；archive token 不进入 body、响应或 usage event。
- `key_sentence_marked` payload 只保存 `segment_id`、`sequence`、`is_key_sentence`、`source=archive_manual`、`translation_status`、`english_text_length`、`chinese_text_length`。
- 自动规则会读取当前英文/中文 final 正文做瞬时判断，但不会把正文写入 `usage_event` 或 Redis；Redis 不参与重点句持久化。
- 前端只消费后端 API 和 WebSocket 显式消息，不在归档事件 body 中发送正文或 token。

### 验证结论

- Step 26 已按 TDD 先跑 RED：后端缺少规则模块、归档更新 request 和事件集合；前端缺少 PATCH client、筛选控件和人工标记按钮；再实现到 GREEN。
- 本地后端完整验证已通过：Ruff、mypy、pytest；pytest 结果为 163 passed，13 integration deselected。
- 本地前端完整验证已通过：lint、Vitest、build、Playwright E2E；Vitest 为 13 个测试文件、111 个测试通过，E2E 为 11 个 Chromium 测试通过。
- Step 27 未开始；当前没有会议时间线增强。

## 2026-05-17 Step 27 会议时间线增强

### 架构状态

- Step 27 实现 F18 的轻量时间线增强：后端继续复用既有 `timeline_update` wire schema，归档 API 在既有响应上追加 `timeline_items`，不新增数据库字段、Provider、环境变量或真实 smoke。
- 新增 `timeline` 模块作为时间线节点构建边界，统一生成 `segment_final`、`key_sentence`、`export_created` 和 `exception` 节点；节点只包含 `id`、`item_type`、`timestamp_ms`、`text` 和可选 `segment_id`。
- WebSocket final 成功路径在 `segment_final` 推送和归档写入后追加时间线节点；若该 final 命中重点句，则继续发送 `key_sentence_update` 并追加 `key_sentence` 时间线节点。
- Qwen interim/final warning 和 Qwen ASR error 会追加 `exception` 时间线节点；异常节点文本只由错误 code 映射为安全摘要，不使用 provider 原始异常正文。
- local mock provider 改为复用同一套时间线构建函数，保持本地 mock 与生产路径在 `timeline_update` 行为上的一致性。
- 归档 API `GET /api/archives/{session_id}?token=...` 新增 `timeline_items`：从 `transcript_segment` 派生 final/重点句节点，从 `export_file` 派生导出节点，从安全 usage event 元数据派生异常节点。
- 导出时间线节点只暴露导出类型、相对时间和摘要，不返回 COS object key、短期下载 URL、archive token 或正文。
- 前端实时会议页的会议时间线区增加“全部 / final / 重点句 / 导出 / 异常”筛选；关联 `segment_id` 的节点可以滚动定位到英文/中文 final 片段。
- 前端归档页新增“归档时间线”导航，消费 `archive.timeline_items` 并支持同类筛选和点击定位；旧 API 响应缺少 `timeline_items` 时默认空数组。
- 导出成功后归档页本地 upsert 一个 `export_created` 节点，避免等待重新拉取；导出失败继续保留既有可访问错误提示，不清空归档内容。
- Step 28 未开始：当前没有使用量与成本看板、成本聚合 API、运营漏斗页面或新指标 UI。

### 文件作用

| 文件 | 作用 |
|---|---|
| `backend/src/meeting_mvp_backend/timeline.py` | Step 27 新增时间线规则模块。集中定义时间线 item 类型、安全异常 code 文案、相对时间计算、final/重点句/导出/异常节点构建和排序函数。 |
| `backend/src/meeting_mvp_backend/ws_sessions.py` | WebSocket 会话编排层。Step 27 在 final 成功、重点句命中、warning/error 发生时构建并推送 `timeline_update`；mock provider 也复用同一构建路径。 |
| `backend/src/meeting_mvp_backend/archives.py` | 归档业务模块。Step 27 在 `ArchiveResponse` 中加入 `timeline_items`，并通过 repository 查询 segment、export_file 和 usage_event 安全元数据来派生归档时间线。 |
| `backend/src/meeting_mvp_backend/db/models.py` | 数据库模型。Step 27 复用既有 `TranscriptSegment.is_key_sentence`、`ExportFile` 和 `UsageEvent`，不新增 migration。 |
| `backend/tests/test_websocket_sessions.py` | WebSocket 会话测试。Step 27 覆盖 final、重点句和异常场景的 `timeline_update` 推送。 |
| `backend/tests/test_archives.py` | 归档服务/API 测试。Step 27 覆盖 final、重点句、导出和异常四类归档 `timeline_items` 派生，以及缺 token/错误 token 边界保持不变。 |
| `backend/tests/test_exports.py` | 导出服务测试。Step 27 扩展 fake repository 以满足归档时间线协议，不改变导出主流程。 |
| `frontend/src/api/archives.ts` | 前端归档 API client。Step 27 增加 `ArchiveTimelineItem` schema 和 `timeline_items` 默认空数组，兼容旧后端响应。 |
| `frontend/src/App.tsx` | 前端实时会议工作台。Step 27 给会议时间线区增加筛选、节点类型展示、摘要展示和关联 final 片段滚动定位。 |
| `frontend/src/archive/ArchivePage.tsx` | 前端归档页。Step 27 新增归档时间线导航，消费 `archive.timeline_items`，支持筛选、点击定位和导出成功后本地 upsert 导出节点。 |
| `frontend/src/App.test.tsx` | 实时会议页组件测试。Step 27 覆盖时间线筛选和点击定位。 |
| `frontend/src/api/archives.test.ts` | 前端归档 API client 测试。Step 27 覆盖 `timeline_items` 解析、旧 API 默认空数组和安全字段边界。 |
| `frontend/src/archive/ArchivePage.test.tsx` | 归档页组件测试。Step 27 覆盖归档时间线渲染、筛选、点击定位和导出成功本地节点更新。 |
| `memory-bank/progress.md` | 开发进度记录。Step 27 记录完成内容、RED/GREEN 过程、完整验证结果和 Step 28 未开始边界。 |
| `memory-bank/architecture.md` | 架构记录。Step 27 记录时间线节点来源、WebSocket 推送、归档 API 派生、前端筛选/跳转和安全约束。 |
| `AGENTS.md` | Codex/AI 项目记忆。Step 27 同步项目状态、文件职责摘要和 Step 28 等待用户明确允许。 |

### 数据与安全边界

- `timeline_update` 和 `archive.timeline_items` 都只使用短摘要和安全元数据；不承载英文正文、中文译文、archive token、COS object key、下载 URL、密钥或音频。
- `segment_final` 和 `key_sentence` 节点的正文摘要来自已允许展示的 final/重点句展示文本，但 usage event 仍不保存正文；归档响应本身已有授权边界。
- `exception` 节点不透传异常正文，只从固定 code 映射到中文安全摘要；未知 code fallback 为“会议处理出现异常”。
- `export_created` 节点从 `export_file` 或导出成功响应的安全字段派生，只显示导出格式，不暴露存储内部标识或签名地址。
- `timeline_items` 是派生字段，不改变 PostgreSQL schema；PostgreSQL 仍保存正式 final、重点句标记、导出记录和 usage event 元数据。
- 前端实时页只消费服务端 `timeline_update.items`，不从 `segment_final` 自行派生实时节点，保持服务端权威。

### 验证结论

- Step 27 已按 TDD 先跑 RED：后端缺少归档时间线结构，前端缺少 `timeline_items` schema、筛选和跳转 UI；再实现到 GREEN。
- 本地后端完整验证已通过：Ruff、mypy、pytest；pytest 结果为 163 passed，13 integration deselected。
- 本地前端完整验证已通过：lint、Vitest、build、Playwright E2E；Vitest 为 13 个测试文件、114 个测试通过，E2E 为 11 个 Chromium 测试通过。
- Step 28 未开始；当前没有使用量与成本看板。

## 2026-05-17 Step 28 使用量与成本看板

### 架构状态

- Step 28 实现 F14 的内部管理看板：后端提供 bearer 管理口令保护的安全聚合 API，前端新增独立管理页面 `/admin/usage-dashboard`，不加入普通会议或归档入口。
- 本步不新增数据库表、migration、Provider、真实 smoke 或前端公开环境变量；看板完全从既有 `meeting_session` 和 `usage_event` 安全元数据派生。
- 新增 `usage_dashboard` 模块作为聚合边界：SQLAlchemy repository 读取窗口内的 `meeting_session` 与 `usage_event`，`UsageDashboardService` 按 `APP_TIMEZONE` 聚合每日指标、总计、漏斗、质量和成本。
- API 入口为 `GET /api/admin/usage-dashboard?days=30`，`days` 通过 FastAPI `Query(ge=1, le=90)` 限制；未配置 `DASHBOARD_ADMIN_TOKEN` 返回 503，缺失/错误 `Authorization: Bearer ...` 返回 401。
- 管理口令只允许走 HTTP header，不支持 query token；后端使用 `secrets.compare_digest()` 比较，响应体不回显口令或任何配置值。
- 成本估算只使用安全字段：
  - ASR 秒数来自 `meeting_session.duration_seconds` / `quota_seconds_consumed` 的较大值。
  - Qwen interim/final 请求数来自 `usage_event.event_type`。
  - 文本 token 估算来自 `text_length`、`english_text_length`、`chinese_text_length` 等长度字段，规则固定为 `ceil(length / 4)`。
  - 汇率和单价通过后端私有非密钥配置覆盖，默认使用 Step 28 锁定的 Model Studio 价格假设。
- 漏斗数据仍基于既有 usage event：首次使用漏斗看 `client_created`、`capture_started`、`audio_detected`、`session_started`、首个 final；会议质量漏斗看 ASR/final/归档/查看；价值验证漏斗看归档查看、搜索、复制、导出和人工重点句。
- 腾讯会议成功率从 `meeting_session.source_platform=tencent_meeting_web` 与 ended/effective duration 派生，用于粗略观测重点平台质量，不读取正文或音频。
- 前端 `UsageDashboardPage` 只在 `/admin/usage-dashboard` 路径渲染；口令只保存在 React state，页面刷新即丢失，不写入 localStorage/sessionStorage。
- 前端看板展示 7/30/90 天切换、核心指标、每日趋势表、首次使用/会议质量/价值验证三类漏斗、错误与质量、成本与预算；401/503/网络失败均用可访问 `role="alert"` 提示。
- Step 29 未开始：当前没有 Provider 开关、Provider 配置页面、Provider 切换 API 或真实 OpenAI/Qwen 对比入口。

### 文件作用

| 文件 | 作用 |
|---|---|
| `backend/src/meeting_mvp_backend/usage_dashboard.py` | Step 28 新增看板核心模块。定义看板 repository 协议、SQLAlchemy 查询实现、聚合输入 record、响应 Pydantic model、漏斗/质量/成本计算和安全估算规则。 |
| `backend/src/meeting_mvp_backend/main.py` | FastAPI 入口。Step 28 新增 `authorize_usage_dashboard_admin()`、`get_usage_dashboard_service()` 和 `GET /api/admin/usage-dashboard`，负责 bearer 鉴权、未配置 503、DB session factory 注入和 service 调用。 |
| `backend/src/meeting_mvp_backend/config.py` | 后端配置边界。Step 28 新增 `DASHBOARD_ADMIN_TOKEN` 与成本估算配置，并将空管理口令归一化为未配置；这些变量不进入前端。 |
| `backend/.env.example` | 后端本地示例配置。Step 28 增加空管理口令和默认成本估算参数，仍不包含真实口令或密钥。 |
| `deploy/.env.example` | 部署示例配置。Step 28 增加看板管理口令 placeholder 和成本估算参数，供生产安全环境文件按需覆盖。 |
| `memory-bank/environment-variables.md` | 环境变量唯一清单。Step 28 记录看板口令、成本估算参数、前端禁止边界和安全使用规则。 |
| `backend/tests/test_usage_dashboard.py` | 后端看板测试。覆盖固定样本聚合、日指标、漏斗、成本估算、预算阈值、腾讯会议成功率、401/503 鉴权边界和响应敏感字段排除。 |
| `backend/tests/test_config.py` | 后端配置测试。Step 28 覆盖看板配置默认值、空 token 归一化和环境变量清单状态。 |
| `frontend/src/api/usage-dashboard.ts` | 前端看板 API client。构造 `/api/admin/usage-dashboard?days=...`，只在 Authorization header 发送管理口令，解析安全响应并映射 HTTP 错误。 |
| `frontend/src/admin/UsageDashboardPage.tsx` | 前端管理看板页。实现口令输入、7/30/90 天切换、指标/趋势/漏斗/质量/成本展示和可访问错误提示；口令只保存在组件 state。 |
| `frontend/src/App.tsx` | 前端路由分流。Step 28 在 archive 路由之外新增 `/admin/usage-dashboard` 独立页面，不改变实时会议工作台入口。 |
| `frontend/src/api/usage-dashboard.test.ts` | 前端 API client 测试。覆盖 URL、Authorization header、禁止 query/body token、days 校验和 401/503 错误映射。 |
| `frontend/src/admin/UsageDashboardPage.test.tsx` | 管理看板组件测试。覆盖口令流、本地存储不写入、天数切换、指标渲染和错误提示。 |
| `frontend/src/App.test.tsx` | 应用路由测试。Step 28 覆盖 `/admin/usage-dashboard` 只渲染管理看板，不渲染普通实时会议工作台。 |
| `memory-bank/progress.md` | 开发进度记录。Step 28 记录完成内容、RED/GREEN 过程、完整验证结果和 Step 29 未开始边界。 |
| `memory-bank/architecture.md` | 架构记录。Step 28 记录看板聚合数据流、鉴权、安全边界和文件职责。 |
| `AGENTS.md` | Codex/AI 项目记忆。Step 28 同步项目状态、文件职责摘要和 Step 29 等待用户明确允许。 |

### 数据与安全边界

- 看板 API 响应只返回聚合数字、日期、比例、估算 token 和估算成本；不返回英文/中文正文、archive token、archive URL、COS object key、下载 URL、密钥、IP/User-Agent 明文或音频。
- `usage_event.payload` 继续只允许安全元数据；Step 28 不新增正文采集，不改变 Step 21 的敏感字段拒绝策略。
- `DASHBOARD_ADMIN_TOKEN` 是后端私有管理口令：不得加 `VITE_` 前缀，不得写入前端 env、本地存储、URL query、日志、usage event 或项目记忆。
- 成本展示字段统一使用 `estimated_*` 语义；它依赖长度/次数/时长估算，不代表云厂商账单。
- 管理页面隐藏在独立路径但不是网络边界；生产环境如需更强限制，应在 Caddy/运维层增加路径访问控制。

### 验证结论

- Step 28 已按 TDD 先跑 RED：后端缺少看板模块与 dependency，前端缺少 API client、页面和路由；再实现到 GREEN。
- 本地后端完整验证已通过：Ruff、mypy、pytest；pytest 结果为 167 passed，13 integration deselected。
- 本地前端完整验证已通过：lint、Vitest、build、Playwright E2E；Vitest 为 15 个测试文件、123 个测试通过，E2E 为 11 个 Chromium 测试通过。
- `git diff --check` 已通过，无空白错误。
- Step 29 未开始；当前没有 Provider 开关。

## 2026-05-20 Step 29 Provider 开关

### 架构状态

- Step 29 实现 F15 的后端 Provider 开关：Qwen realtime ASR、Qwen interim、Qwen final 分别由后端私有环境变量控制；本步不新增数据库 schema、公开 Provider 配置页面、真实 OpenAI STT 音频链路或 Step 30 兼容性矩阵。
- 配置边界新增 `QWEN_ASR_ENABLED` 和 `QWEN_FINAL_ENABLED`，继续复用 `QWEN_INTERIM_ENABLED`；三者默认均为 `true`，并只在对应开关开启时触发生产必填项校验。
- OpenAI STT 仍是暂缓状态：`OPENAI_STT_ENABLED=true` 只要求 OpenAI key/base/model 配置完整，但 WebSocket 实时链路不会选择 OpenAI STT，也没有前端入口。
- 非 local 环境下 `QWEN_ASR_ENABLED=false` 会在 `session_start` 阶段拒绝新实时会议，返回 `qwen_asr_disabled`；拒绝发生在 session 创建和额度预占之前，因此不会写入 `meeting_session` 或 Redis active session。
- `QWEN_INTERIM_ENABLED=false` 只关闭中文 interim 调度；英文 ASR、英文 `asr_final`、Qwen final、归档写入和后台补译队列不受影响，也不会发送“interim 失败”warning。
- `QWEN_FINAL_ENABLED=false` 时，后端收到英文 `asr_final` 后不调用 final provider，而是保存英文 final、空中文 final、`translation_status=failed`，自动入现有后台补译队列，并发送 `qwen_final_translation_disabled` warning 和异常时间线节点。
- 后台 final 补译 worker 的启动条件新增 `QWEN_FINAL_ENABLED=true`，因此 final 关闭期间只积累 failed retry job；重新开启并满足 DB/Redis/Qwen final 配置后 worker 才会启动处理。
- `session_started` wire schema 新增 `provider_status`，值只允许 `enabled`、`disabled`、`local_mock`、`unconfigured`；该字段是安全运行状态摘要，不暴露 endpoint、模型名、账号、密钥、API key 是否存在等细节。
- 前端 Zustand store 持久于当前会话状态中的 `providerStatus` 只来自 `session_started.provider_status`；实时工作台用它展示 ASR/翻译服务状态，如“ASR 已关闭”“翻译已关闭”“正式翻译未配置”“本地 mock”。
- `session-notices` 新增 provider switch 文案：ASR disabled 是阻断错误；interim/final disabled 是可恢复/可继续提示。错误时前端仍停止本地音频资源，但保留已收到 final、归档入口和 session id。
- Step 30 未开始：当前没有平台兼容性矩阵、真实 Google Meet/Teams/Zoom/腾讯会议人工测试、平台风险评分或浏览器能力表。

### 文件作用

| 文件 | 作用 |
|---|---|
| `backend/src/meeting_mvp_backend/config.py` | 后端配置边界。Step 29 新增 `qwen_asr_enabled`、`qwen_final_enabled`，并将生产必填项拆分为基础配置、Qwen ASR、Qwen interim、Qwen final、OpenAI STT 五组条件校验；`settings_status()` 继续只输出 set/unset。 |
| `backend/src/meeting_mvp_backend/ws_messages.py` | 后端 WebSocket wire schema。Step 29 新增 `ProviderStatus` 与 `ProviderStatusValue`，并让 `SessionStartedMessage` 必须携带安全的 `provider_status`。 |
| `backend/src/meeting_mvp_backend/ws_sessions.py` | WebSocket 会话编排层。Step 29 新增 provider status 计算、ASR disabled 建会拒绝、interim disabled 跳过调度、final disabled 归档 failed segment/入队/发 warning/时间线节点的主逻辑。 |
| `backend/src/meeting_mvp_backend/main.py` | FastAPI 入口与依赖装配。Step 29 按 Qwen 开关注入或跳过真实 ASR/final provider factory，并要求 `QWEN_FINAL_ENABLED=true` 才启动后台补译 worker。 |
| `backend/src/meeting_mvp_backend/timeline.py` | 时间线安全摘要模块。Step 29 增加 `qwen_final_translation_disabled` 的异常节点文案，保证 final 关闭也能进入统一时间线。 |
| `backend/.env.example` | 后端 local 示例环境文件。Step 29 增加 `QWEN_ASR_ENABLED=true` 和 `QWEN_FINAL_ENABLED=true`，仍只包含空值或 placeholder，不含真实密钥。 |
| `deploy/.env.example` | Docker Compose 示例环境文件。Step 29 增加 Qwen ASR/final 开关 placeholder 默认值，用于生产安全 env 按需覆盖。 |
| `memory-bank/environment-variables.md` | 环境变量唯一清单。Step 29 记录 Qwen 三类开关、条件必填规则和 final 关闭后的 failed+retry 行为。 |
| `frontend/src/protocol/websocket-messages.ts` | 前端 WebSocket schema。Step 29 镜像后端 `provider_status` Zod schema，严格限制安全枚举并导出 `ProviderStatus` 类型。 |
| `frontend/src/stores/session-store.ts` | 前端会话状态 store。Step 29 新增 `providerStatus`，在 `onSessionStarted` 保存 provider 状态，并在开始/结束会话时清空。 |
| `frontend/src/App.tsx` | 实时会议工作台。Step 29 根据 `providerStatus` 生成 ASR/翻译状态栏和时间线摘要状态，展示 disabled/unconfigured/local_mock 提示，不显示任何敏感配置。 |
| `frontend/src/lib/session-notices.ts` | 前端异常与降级提示映射。Step 29 新增 `qwen_asr_disabled`、`qwen_interim_translation_disabled`、`qwen_final_translation_disabled` 的中文文案和 severity。 |
| `frontend/src/lib/meeting-websocket.test.ts` | 前端 WebSocket client 测试。Step 29 更新 session_started mock，确保测试 fixture 符合新增 `provider_status` schema。 |
| `frontend/e2e/app.spec.ts` | Playwright 实时工作台 e2e。Step 29 更新浏览器 WebSocket mock 的 `session_started` 响应，覆盖新增 provider status 字段。 |
| `backend/tests/test_config.py` | 后端配置测试。Step 29 覆盖 Qwen ASR/final 默认开启、示例 env 加载、生产必填项按开关条件变化、OpenAI STT 条件校验和 final 关闭时 worker 不启动。 |
| `backend/tests/test_ws_messages.py` | 后端 wire schema 测试。Step 29 覆盖 `session_started.provider_status` 解析。 |
| `backend/tests/test_websocket_sessions.py` | 后端 WebSocket 编排测试。Step 29 覆盖 ASR disabled 拒绝且不占额度、interim disabled 不阻塞 ASR/final、final disabled 保存 failed segment 并入补译队列。 |
| `frontend/src/protocol/websocket-messages.test.ts` | 前端协议测试。Step 29 覆盖 `session_started.provider_status` 的 Zod 解析。 |
| `frontend/src/stores/session-store.test.ts` | 前端 store 测试。Step 29 覆盖 provider 状态保存、provider switch warning 和 ASR disabled error notice。 |
| `frontend/src/lib/session-notices.test.ts` | 前端 notice 测试。Step 29 覆盖三个 provider switch code 的文案、severity 和行动提示。 |
| `frontend/src/App.test.tsx` | 实时工作台组件测试。Step 29 覆盖状态栏 provider switch 提示，以及 WebSocket mock 响应新增字段后的捕获流程。 |
| `memory-bank/progress.md` | 开发进度记录。Step 29 记录完成内容、RED/GREEN 过程、完整验证结果和 Step 30 未开始边界。 |
| `memory-bank/architecture.md` | 架构记录。Step 29 记录 Provider 开关架构、wire schema、前端状态流、安全约束和文件职责。 |
| `AGENTS.md` | Codex/AI 项目记忆。Step 29 同步项目状态、Provider 策略、后续限制和 Step 30 等待用户明确允许。 |

### 数据与安全边界

- Provider 开关只存在于后端私有配置，不新增前端 `VITE_QWEN_*` 或可由用户任意修改的前端配置。
- `provider_status` 是安全枚举，不携带 endpoint、模型名、provider key 是否存在、账号信息、错误详情或任何密钥相关状态。
- ASR disabled 拒绝新会议时不创建 `meeting_session`、不写 archive token、不占 Redis active session、不结算额度；归档、导出和管理看板仍可继续使用。
- Final disabled 仍会写入 PostgreSQL failed segment，以便归档可追溯并让后台补译队列后续恢复；Redis retry job 只保存 session/segment id 和 due_at，不保存正文或译文。
- Interim disabled 不写 warning 事件，不保存正文，不影响 final 链路；它只是跳过实时中文 interim provider 调度。
- usage event 继续只保存安全元数据；本步没有新增正文、音频、token、URL、object key、密钥或隐私明文字段。

### 验证结论

- Step 29 已按 TDD 先跑 RED：后端缺少 Qwen 开关、条件配置校验、`provider_status` 和 disabled 路径；前端缺少 provider status schema/store/notice/UI；再实现到 GREEN。
- 本地后端完整验证已通过：Ruff、mypy、pytest；pytest 结果为 173 passed，13 integration deselected。
- 本地前端完整验证已通过：lint、Vitest、build、Playwright E2E；Vitest 为 15 个测试文件、126 个测试通过，E2E 为 11 个 Chromium 测试通过。
- `git diff --check` 已通过，仅有 Windows LF/CRLF 工作区提示，无空白错误。
- Step 30 未开始；当前没有兼容性矩阵或真实会议平台人工测试。

## 2026-05-20 Step 30 兼容性测试矩阵资产（阻塞，未完成）

### 架构状态

- Step 30 已建立兼容性矩阵资产和自动校验脚本，但真实平台验收尚未执行完成；当前状态为 `blocked`，不能视为 Step 30 通过。
- 阻塞原因是本地访问 `https://meeting.youroristore.com` 超时，无法确认同源 HTTPS/WSS 工具页和真实 Qwen ASR backend 可用；按 Step 30 规则，不允许用 local mock 或未实测数据替代真实结果。
- 兼容性结果不进入后端业务数据库，也不影响 WebSocket、Provider、归档、导出或看板运行时路径；它们是 `tests/` 下的验收资产。
- `scripts/validate-step30-compatibility.ps1` 是本步的防误判边界：在缺少必测行、使用 mock 环境、Qwen ASR 未 enabled、缺少浏览器版本、失败码为空或腾讯会议结论阻塞时返回非 0。
- 当前 JSON 保持空结果和 `blocked` 状态，因此校验脚本失败是预期结果；后续录入真实人工结果并满足规则后，脚本才应通过。
- Step 31 未开始：当前没有 CI workflow、GitHub Actions、自动部署或主干提交。

### 文件作用

| 文件 | 作用 |
|---|---|
| `tests/compatibility/step-30-compatibility-results.json` | Step 30 结构化结果来源。保存 schema 版本、状态、阻塞信息、腾讯会议结论和人工测试结果数组；每条结果只允许保存平台、浏览器、版本、系统、捕获模式、授权结果、音频检测、首条 ASR interim 延迟、final 数量、失败码、测试时间、后端环境、provider 安全状态和备注。 |
| `tests/compatibility/step-30-compatibility-matrix.md` | Step 30 人工可读矩阵。列出 Google Meet、Teams Web、Zoom Web、腾讯会议网页版在 Windows Chrome/Edge 下的必测组合，说明真实 Qwen HTTPS/WSS 前置条件、腾讯会议三类结论和安全记录边界。 |
| `scripts/validate-step30-compatibility.ps1` | Step 30 本地校验脚本。读取结构化 JSON，校验必测组合覆盖、字段完整性、真实 Qwen 后端环境、Qwen ASR enabled、成功定义、失败码要求和腾讯会议专项结论；失败时列出全部错误并退出 1。 |
| `tests/README.md` | 测试资产目录说明。Step 30 增加兼容性矩阵文件位置、校验命令和不得用 local mock 代替真实平台结果的边界。 |
| `memory-bank/progress.md` | 开发进度记录。Step 30 记录当前只建立资产、真实目标不可用、校验脚本按预期失败和 Step 31 未开始。 |
| `memory-bank/architecture.md` | 架构记录。Step 30 记录兼容性资产的数据边界、文件职责和阻塞原因。 |
| `AGENTS.md` | Codex/AI 项目记忆。Step 30 同步当前阻塞状态、验收资产和后续不得跳入 Step 31 的约束。 |

### 数据与安全边界

- 兼容性矩阵只记录安全元数据，不记录会议正文、用户姓名、会议链接、archive token、下载 URL、Provider endpoint、模型账号、密钥、原始音频或截图中的隐私内容。
- `provider_status` 只能保留 Step 29 定义的安全状态摘要，例如 `qwen_realtime_asr=enabled`；不得扩展为密钥存在性、endpoint、模型名或供应商账号。
- `first_asr_interim_ms` 和 `final_segment_count` 只证明真实 Qwen ASR 链路在该平台组合下可产生结果，不记录转写文本。
- 失败行必须有明确 `failure_code`，用于区分授权失败、无音频、ASR 超时、final 缺失或平台不支持；空失败码不能通过校验。

### 验证结论

- 真实 HTTPS/WSS 目标探测失败：`https://meeting.youroristore.com` 在 15 秒内超时。
- `pwsh` 在当前 Windows 本机不可用；使用 Windows PowerShell 执行脚本可运行。
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\validate-step30-compatibility.ps1` 按预期失败，列出空结果、blocked 状态、缺少必测行和腾讯会议结论等问题。
- 因真实平台人工结果尚未录入，Step 30 未完成；不能进入 Step 31。

## 2026-05-20 Step 31 CI 检查

### 架构状态

- Step 31 新增 GitHub Actions 作为提交质量门：覆盖前端 lint/test/build/e2e、后端 Ruff/mypy/pytest 和 Docker Compose 配置检查。
- 用户已明确覆盖 Step 30 顺序门禁并允许推进 Step 31；Step 30 仍保持 `blocked`，兼容性矩阵未被标记为通过，也未加入 CI 必跑项。
- CI 只做检查，不做部署：workflow 不配置 secrets，不使用 SSH/scp/rsync，不运行 `docker compose up`，不执行 production migration，不运行真实 Qwen、COS 或 Lighthouse smoke。
- CI 使用仓库内既有锁文件与脚本：前端用 `frontend/package-lock.json` + `npm ci`，后端用 `backend/uv.lock` + `uv sync --locked`，Compose 用 `deploy/.env.example` placeholder 做 config 展开。
- `compose-config` job 只验证 `deploy/docker-compose.yml` 在示例环境变量下可解析；它不构建镜像、不拉起 PostgreSQL/Redis/后端/Caddy，也不验证生产密钥。
- 本步不修改运行时 API、WebSocket wire schema、数据库 schema、后端配置模型、环境变量清单、前端 `VITE_*` 公开配置或业务代码。
- GitHub Actions 是否在 GitHub 上阻止合并取决于仓库 branch protection 是否把这些 jobs 设为 required；Step 31 只新增 workflow，不修改仓库保护设置。
- Step 32 未开始：没有生产部署演练、HTTPS/WSS 线上验证、PostgreSQL 备份恢复演练或云端容器启动。

### 文件作用

| 文件 | 作用 |
|---|---|
| `.github/workflows/ci.yml` | Step 31 新增 CI 入口。定义 `frontend`、`backend`、`compose-config` 三个 jobs，分别运行前端质量检查、后端质量检查和 Docker Compose 配置检查；顶层权限为 `contents: read`，不使用 secrets 或部署步骤。 |
| `frontend/package-lock.json` | 前端 CI 依赖锁来源。`frontend` job 使用 `npm ci` 按 lockfile 安装依赖，并通过 setup-node npm cache 复用依赖缓存。 |
| `frontend/package.json` | 前端 CI 命令来源。`frontend` job 复用既有 `lint`、`test`、`build`、`test:e2e` scripts，不新增前端工具链。 |
| `frontend/playwright.config.ts` | 前端 E2E 配置。CI 中先运行生产构建，再由 Playwright 启动 Vite preview 进行 Chromium smoke tests。 |
| `backend/.python-version` | 后端 CI Python 版本来源。`backend` job 使用 `actions/setup-python` 读取该文件，保持 GitHub runner 与项目 Python 3.12 边界一致。 |
| `backend/uv.lock` | 后端 CI 依赖锁来源。`backend` job 使用 `uv sync --locked`，避免 CI 自动改写依赖锁。 |
| `backend/pyproject.toml` | 后端 CI 命令与测试配置来源。`backend` job 复用 Ruff、mypy、pytest 配置；默认 pytest 仍排除 `integration` 标记。 |
| `deploy/docker-compose.yml` | Compose config CI 检查对象。`compose-config` job 验证单机部署拓扑可被 Docker Compose 解析，但不启动容器。 |
| `deploy/.env.example` | Compose config CI 示例环境。只包含 placeholder，用于展开必填变量；不得放入真实密钥。 |
| `memory-bank/progress.md` | 开发进度记录。Step 31 记录 CI workflow 内容、本地验证结果、Step 30 覆盖说明和 Step 32 未开始边界。 |
| `memory-bank/architecture.md` | 架构记录。Step 31 记录 CI 数据流、文件职责、安全边界和非部署约束。 |
| `AGENTS.md` | Codex/AI 项目记忆。Step 31 同步当前 CI 状态、后续限制和 Step 32 必须等待用户明确允许。 |

### 安全与部署边界

- CI 不接收或读取 Qwen、OpenAI、Tencent COS、数据库、Redis、Dashboard 或 SSH 真实密钥。
- `deploy/.env.example` 中的 placeholder 只用于 Compose config 解析，不代表生产配置，也不能用于正式数据目录初始化。
- 前端 CI 不新增任何 `VITE_QWEN_*`、`VITE_OPENAI_*`、`VITE_DATABASE_*`、`VITE_REDIS_*` 或 `VITE_TENCENT_COS_*`。
- 后端 CI 的 `uv run pytest` 是本地轻量测试路径，默认排除真实 PostgreSQL/Redis/Qwen integration tests；真实集成测试仍需 Lighthouse/CI 安全环境显式开启。
- CI 通过不等价于 Step 30 兼容性矩阵通过，也不等价于 Step 32 生产部署演练通过。

### 验证结论

- 本地后端验证已通过：Ruff、mypy、pytest；pytest 结果为 173 passed，13 integration deselected。
- 本地前端验证已通过：lint、Vitest、build、Playwright E2E；Vitest 为 15 个测试文件、126 个测试通过，E2E 为 11 个 Chromium 测试通过。
- `git diff --check` 已通过，无空白错误。
- workflow 安全扫描未发现 SSH、secrets、部署、容器启动、production migration 或真实 Provider/COS smoke；只命中预期的 Compose config 命令。
- GitHub Actions 首轮 push CI 已通过：`codex/step31-ci-checks` 分支 run `26148035200` 中 `Docker Compose config`、`Backend`、`Frontend` jobs 均为 success。

## 2026-05-20 Step 32 生产部署演练

### 架构状态

- Step 32 已在腾讯云 Lighthouse `/opt/meeting_mvp/app` 完成单机生产部署演练：PostgreSQL、Redis、backend、Caddy 均由 Docker Compose 管理，backend/postgres/redis healthcheck 通过，Caddy 映射公网 80/443。
- Step 32 分支为 `codex/step32-production-drill`，基于 `codex/step31-ci-checks`；保留 Step 31 CI workflow，不从当前 `main` 丢失 CI 基线。
- `deploy/docker-compose.yml` 已补齐 Step 28/29 引入但未透传到容器的运行时变量：Provider 开关和 dashboard 成本/口令配置现在进入 backend 容器，后端 `Settings` 才能在生产运行时按开关做条件校验。
- Qwen ASR/interim/final 的必填校验边界从 Compose 展开层下沉到后端配置层：Compose 允许变量为空，后端只在对应开关为 `true` 时要求 key、base URL 和模型配置完整。数据库、Redis、COS 等基础生产依赖仍保持生产必填。
- Caddy 路由已从散列 matcher 改为 `handle` 分支：`/api/*`、`/health`、`/ws*` 优先反向代理到 FastAPI，剩余路径才进入 Vite 静态前端和 SPA fallback。这避免 `try_files` 把健康检查或 API 路径改写成 `/index.html`。
- 生产健康检查存在两个层次：
  - Docker healthcheck 使用容器内 `GET /health` 判断 backend 容器是否健康。
  - 公网 `https://meeting.youroristore.com/health` 通过 Caddy 代理到 FastAPI，用于验证 TLS/Caddy/backend 组合链路。
- WebSocket 公网入口为 `wss://meeting.youroristore.com/ws`，由 Caddy 反向代理到 backend `/ws`；Step 32 已验证远端经公网域名可完成 WSS 握手。
- PostgreSQL 是正式归档来源，Redis 只保存额度、active session、重试调度等短期状态。Step 32 已用测试归档确认删除 Redis 临时状态后，归档 API 仍能从 PostgreSQL 返回 final 片段。
- 备份恢复流程已被纳入生产部署演练：`pg_dump -Fc` 生成 `/opt/meeting_mvp/backups/step32_*.dump`，再恢复到临时数据库并检查 public schema 表数量，最后删除临时库。
- 真实 Provider/COS smoke 均在 Lighthouse 后端容器执行；Windows 本地继续只跑不依赖真实密钥的检查。Step 32 没有把任何 Qwen、COS、dashboard、数据库或 Redis 密钥写入 Git、前端构建产物或文档。
- Step 30 仍保持 `blocked`：虽然 Step 32 已让 HTTPS/WSS 生产入口可用，但尚未执行真实会议平台人工兼容性矩阵；Step 33 也未开始。

### 文件作用

| 文件 | 作用 |
|---|---|
| `deploy/docker-compose.yml` | 生产单机拓扑定义。管理 PostgreSQL 16、Redis 7、backend 和 Caddy；Step 32 新增 Provider 开关、dashboard 管理口令和 dashboard 成本参数透传，并让 Qwen 相关变量由后端按开关条件校验。继续只映射 Caddy 的 80/443，不把 PostgreSQL 5432 或 Redis 6379 暴露到公网。 |
| `deploy/Caddyfile` | 公网入口路由。Step 32 改为 `handle` 分支：`/api/*`、`/health`、`/ws*` 代理到 backend，默认分支服务 `/srv` 下的 Vite 静态产物并对 SPA 路由 fallback 到 `/index.html`。Caddy 负责自动 HTTPS 和 WSS 终止。 |
| `backend/Dockerfile` | 后端镜像构建。基于 Python 3.12/uv，使用 `uv.lock` 固定依赖；复制 Alembic、`src/` 和 `tests/`。Step 32 最终重建 backend 镜像，确保集成测试修正进入镜像文件系统。 |
| `frontend/Dockerfile` | 前端/Caddy 镜像构建。Node 24 阶段执行 `npm ci` 和 `npm run build` 生成 Vite 静态产物；最终 Caddy 镜像复制 `deploy/Caddyfile` 和 `/app/dist`。Step 32 最终重建 Caddy 镜像，确保路由修复不依赖容器内热加载。 |
| `.dockerignore` | Docker build context 安全边界。排除 `.env`、本地缓存、虚拟环境、`node_modules`、构建产物和常见密钥文件，避免生产密钥进入镜像上下文。 |
| `deploy/.env.example` | Compose 示例环境。继续只放 placeholder/default，用于 CI/远端 `docker compose config` 展开；不代表生产真实配置，不能用于正式数据目录初始化。 |
| Lighthouse `/opt/meeting_mvp/app/.env.production` | 生产私有环境文件，只存在远端服务器；Step 32 继续使用该文件注入数据库、Redis、Qwen、COS、dashboard 等配置。文档只记录变量名和是否补安全默认项，不记录任何值。 |
| Lighthouse `/opt/meeting_mvp/data/postgres` | PostgreSQL 持久化目录。Compose 将其挂载到 postgres 容器；正式会议、归档、片段、事件和导出元数据以 PostgreSQL 为权威来源。 |
| Lighthouse `/opt/meeting_mvp/data/redis` | Redis 持久化目录。Compose 将其挂载到 redis 容器；保存短期额度、active session、预算保险丝和补译队列状态，但不作为正式归档来源。 |
| Lighthouse `/opt/meeting_mvp/backups` | PostgreSQL 备份目录。Step 32 生成并验证 `step32_*.dump` 备份文件，恢复演练使用临时数据库完成，不覆盖生产数据库。 |
| `backend/tests/integration/test_websocket_session_redis_integration.py` | PostgreSQL+Redis WebSocket 生命周期集成测试。Step 32 将断线测试调整为“恢复 grace 到期后释放 active session”，与 Step 16 的 session resume 语义一致。 |
| `backend/tests/integration/test_qwen_realtime_asr_smoke.py` | Qwen realtime ASR gated smoke。Step 32 在 Lighthouse 后端容器中使用公开英文样本 manifest 分段验证 latency/resume、30s、3m、10m 连续流和术语识别。 |
| `backend/tests/integration/test_qwen_interim_translation_smoke.py` | Qwen interim gated smoke。验证 Qwen OpenAI-compatible 文本接口能返回中文 interim；Step 32 记录到偶发 ReadTimeout，重试通过，生产主链路仍不依赖 interim 成功。 |
| `backend/tests/integration/test_qwen_final_translation_smoke.py` | Qwen final gated smoke。验证 `QWEN_FINAL_MODEL` 可生成正式中文 final；Step 32 重建后通过。 |
| `backend/src/meeting_mvp_backend/exports.py` | Markdown/JSON 导出服务与 COS storage 封装。Step 32 使用 `ArchiveExportService` 做真实 COS smoke，验证私有对象上传和短期签名 URL 生成，并清理测试对象。 |
| `backend/src/meeting_mvp_backend/archives.py` | 归档读取 API 的数据访问边界。Step 32 用测试归档确认归档读取不依赖 Redis，仍从 PostgreSQL 的 `meeting_session` 与 `transcript_segment` 返回 final 片段。 |
| `.github/workflows/ci.yml` | Step 31 的检查门。Step 32 不修改其部署边界；CI 仍只做检查，不运行真实 Lighthouse 部署、Provider smoke 或 COS smoke。 |
| `memory-bank/progress.md` | 开发进度记录。Step 32 记录实际部署命令、失败/修复过程、远端 smoke、备份恢复和未进入 Step 33 的边界。 |
| `memory-bank/architecture.md` | 架构记录。Step 32 记录生产部署拓扑、Caddy 路由修复、环境变量边界、备份恢复流程和文件职责。 |
| `AGENTS.md` | Codex/AI 项目记忆。Step 32 同步完成状态、远端部署事实、剩余风险和 Step 33 等待用户明确允许。 |

### 安全与运维边界

- 生产 `.env.production` 不进入 Git；Codex 只通过变量名和脱敏状态判断配置是否存在，不输出任何密钥值、dashboard token、COS object key、签名 URL 或 archive token。
- `DASHBOARD_ADMIN_TOKEN` 是后端私有管理口令，只能通过 Authorization header 使用，不得变成 `VITE_*`、URL query、本地存储、usage event 或文档内容。
- Provider smoke 可输出通过/失败、错误类型和耗时，但不得输出 Qwen key、COS Secret、完整 endpoint、生产 env 或会议正文。
- COS smoke 使用测试归档数据，验证签名 URL 形态后清理测试对象；文档不记录 object key 或下载 URL。
- PostgreSQL 备份恢复只恢复到临时库；不得对生产库执行破坏性恢复。临时库验证完成后必须删除。
- Redis 可以重启或丢失短期状态，但已归档 final 片段必须继续由 PostgreSQL 提供查看能力。
- Windows 本地当前到生产 HTTPS 出现 TLS handshake reset，但远端经公网域名访问 HTTPS/WSS 成功；该差异应作为当前本机/网络出口现象记录，后续 Step 30/33 仍需在真实用户浏览器网络环境继续确认。

### 验证结论

- 本地后端验证已通过：Ruff、mypy、pytest；pytest 为 173 passed，13 deselected。
- 本地前端验证已通过：lint、Vitest、build、Playwright E2E；Vitest 为 15 个测试文件、126 个测试通过，E2E 为 11 个 Chromium 测试通过。
- 远端 Compose config、`docker compose up -d --build backend caddy`、容器 health、Alembic migration 和 PostgreSQL/Redis 集成组均通过。
- 远端 `https://meeting.youroristore.com/health` 返回 FastAPI JSON 200；远端 `wss://meeting.youroristore.com/ws` 握手成功。
- 公网端口边界符合预期：80/443 可连接，5432/6379 不可连接。
- Qwen ASR/interim/final 和 COS 导出 smoke 均已通过；Qwen interim 出现过瞬时 ReadTimeout，重试通过。
- PostgreSQL 备份和临时恢复演练通过；最终恢复演练备份文件大小为 15060 bytes，恢复后 public schema 表数量为 6。
- Step 33 未开始；Step 30 兼容性矩阵仍未完成。
