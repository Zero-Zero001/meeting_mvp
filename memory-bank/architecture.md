# Meeting MVP 架构记录

## 2026-05-04 Step 01 基线架构洞察

### 当前仓库状态

- 仓库根目录为 `D:\meeting_mvp`。
- Git 远端为 `https://github.com/Zero-Zero001/meeting_mvp.git`。
- 当前应用工程目录边界已建立；根目录下已有 `frontend/`、`backend/`、`deploy/`、`scripts/`、`tests/`；前端工程骨架已初始化，后端工程骨架尚未初始化。
- 当前有效产品、技术、部署和实施依据集中在 `memory-bank/`。
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
| `memory-bank/meeting-prd.md` | PRD 和验收索引，包含用户画像、功能清单 F01-F18、字段说明、测试用例 TC-001 到 TC-026、埋点和风险。 |
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
