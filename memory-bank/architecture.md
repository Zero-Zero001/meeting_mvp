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
- 后端容器基于 Python 3.12 与 `uv.lock` 构建，运行 `meeting_mvp_backend.main:app`，并通过 Compose 环境变量接收数据库、Redis、Provider、COS、额度和归档配置；Google STT 服务账号 JSON 通过 `GOOGLE_APPLICATION_CREDENTIALS` 指向的只读 bind mount 进入容器。
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
- Google STT 服务账号 JSON 不进入镜像和 Git，只在服务器 `/opt/meeting_mvp/secrets/google-stt-sa.json` 以只读挂载方式提供给后端容器。

### Step 06 验证结论

- 本地静态部署检查已确认 Compose 不发布 `5432` / `6379`，只发布 `80` / `443`，并包含 PostgreSQL 与 Redis 持久化挂载路径。
- 后端 `uv run python --version`、`uv run ruff check .`、`uv run mypy .`、`uv run pytest` 已通过。
- 前端 `npm run lint`、`npm run test`、`npm run build`、`npm run test:e2e` 已通过。
- Lighthouse `docker compose --env-file deploy/.env.example -f deploy/docker-compose.yml config --quiet` 已在 `/opt/meeting_mvp/app` 执行通过。
- 远端边界检查已确认只发布 `80` / `443`，不发布 `5432` / `6379`，保留 PostgreSQL 与 Redis 的 `/opt/meeting_mvp/data/*` 挂载路径，并包含后端只读 Google STT 凭据挂载。

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
