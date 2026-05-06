# Meeting MVP 开发进度

## 2026-05-04 Step 01：确认基线文档和仓库状态

### 本次完成内容

- 已完整阅读 `memory-bank/` 中现有 7 份文档：
  - `memory-bank/2026-04-24-meeting-mvp-design.md`
  - `memory-bank/architecture.md`
  - `memory-bank/implementation-plan.md`
  - `meeting-prd.md`
  - `memory-bank/progress.md`
  - `memory-bank/set-up-env.md`
  - `memory-bank/tech-stack.md`
- 已按 `memory-bank/implementation-plan.md` 的 Step 01 完成基线确认。
- 已确认当前仓库根目录为 `D:\meeting_mvp`。
- 已确认 Git 远端指向 `https://github.com/Zero-Zero001/meeting_mvp.git`。
- 已确认 `meeting-prd.md` 中 F01 到 F18 功能编号均存在，可作为后续验收索引。
- 未创建 `frontend/`、`backend/`、`deploy/`、`scripts/`、`tests/`，未开始 Step 02。

### 验证命令与结果

| 验证项 | 命令 | 实际结果 |
|---|---|---|
| 分支和工作区状态 | `git status --short --branch` | `## main...origin/main [ahead 1]` |
| Git 远端 | `git remote -v` | fetch/push 均为 `https://github.com/Zero-Zero001/meeting_mvp.git` |
| 当前目录 | `Get-Location` | `D:\meeting_mvp` |
| PRD 功能编号 | 搜索 `meeting-prd.md` 中 `F01` 到 `F18` | F01-F18 全部找到 |

### 后续注意事项

- 当前分支 `main` 相对 `origin/main` ahead 1，说明存在本地提交尚未推送；后续开发前应继续关注该状态，避免误判远端同步情况。
- 下一步只能在用户明确允许后执行 Step 02：建立工程目录边界。
- 在进入后续代码实现前，仍需按 `AGENTS.md` 要求先阅读 `memory-bank/2026-04-24-meeting-mvp-design.md` 和 `memory-bank/architecture.md`。

## 2026-05-04 Step 02：建立工程目录边界

### 本次完成内容

- 已按 `memory-bank/implementation-plan.md` 的 Step 02 创建固定工程边界目录：
  - `frontend/`
  - `backend/`
  - `deploy/`
  - `scripts/`
  - `tests/`
- 已为每个目录添加 `README.md`，说明目录职责、后续初始化步骤和安全边界。
- 未创建嵌套 `meeting_mvp/` 子目录。
- 未初始化前端或后端工程，未创建 `frontend/package.json`、`backend/pyproject.toml` 或 `backend/uv.lock`，未开始 Step 03。
- 已同步更新 `memory-bank/architecture.md` 和 `AGENTS.md`，记录目录边界已建立但工程骨架尚未初始化。

### 验证命令与结果

| 验证项 | 命令 | 实际结果 |
|---|---|---|
| 目录列表 | `Get-ChildItem -Directory -Name` | 输出包含 `backend`、`deploy`、`frontend`、`scripts`、`tests` |
| 嵌套根目录检查 | `Test-Path .\meeting_mvp` | `False` |
| 前端初始化防越界 | `Test-Path .\frontend\package.json` | `False` |
| 后端初始化防越界 | `Test-Path .\backend\pyproject.toml` | `False` |
| Git 和文档检查 | `git status --short --branch`、`git diff --check` | 仅 Step 02 相关文件变更；`git diff --check` 无空白错误，仅有 Windows LF/CRLF 提示 |

### 后续注意事项

- Step 03 才能在 `frontend/` 中初始化 Vite + React + TypeScript 前端工程。
- Step 04 才能在 `backend/` 中初始化 Python 3.12 + FastAPI + uv 后端工程。
- 当前目录 README 是为了让 Git 能跟踪目录边界，同时给后续开发者提供职责说明。

## 2026-05-04 Step 03：初始化前端工程骨架

### 本次完成内容

- 已重新阅读 `memory-bank/` 全部 7 份文档，并阅读 `memory-bank/progress.md` 确认 Step 01 与 Step 02 已完成。
- 已检查上一步边界目录：`frontend/`、`backend/`、`deploy/`、`scripts/`、`tests/` 均已存在；Step 03 开始前没有 `frontend/package.json` 或 `backend/pyproject.toml`。
- 已在 `frontend/` 中初始化 Vite + React + TypeScript 前端工程，并使用 npm 管理依赖。
- 已接入 Tailwind CSS v4、`@tailwindcss/vite`、shadcn/ui、lucide-react、Zustand、Vitest、React Testing Library 与 Playwright。
- 已配置 `@/* -> ./src/*` 路径别名、Vitest `jsdom` 环境、Chromium Playwright smoke test、前端 lint/test/build/e2e scripts。
- 已创建最小可验证工作台：
  - `src/App.tsx` 提供轻量会议工作台骨架，包含英文原文区、中文翻译区、当前重点句区、会议时间线区四个占位区域。
  - `src/stores/session-store.ts` 提供最小 Zustand 会话状态，覆盖捕获状态、捕获模式与今日剩余额度。
  - `src/App.test.tsx` 与 `src/stores/session-store.test.ts` 覆盖工作台渲染与 store 状态切换。
  - `e2e/app.spec.ts` 覆盖浏览器首屏 smoke test。
- 已删除 Vite 模板中未接入的演示资源，保留 `public/favicon.svg` 与 `public/icons.svg` 作为当前静态资源占位。
- 已更新 `frontend/README.md`、`memory-bank/architecture.md` 与 `AGENTS.md`。
- 未创建 `backend/pyproject.toml`、`backend/uv.lock`、根目录 `package.json` 或根目录 `pyproject.toml`，未开始 Step 04。

### 环境与执行记录

- `node -v`：`v24.14.1`。
- `npm -v`：`11.11.0`。
- 首次 `npm create vite@latest . -- --template react-ts --no-interactive` 使用默认 npm cache 时遇到 `EPERM` 权限错误。
- 后续 npm 与 npx 命令使用已被根目录 `.gitignore` 忽略的本地缓存：`D:\meeting_mvp\.cache\npm`。
- `npx shadcn@latest init -d --base radix` 首次因 Tailwind 入口尚未配置而失败；补充 `src/index.css` 的 Tailwind 入口后重试成功。

### 验证命令与结果

| 验证项 | 命令 | 实际结果 |
|---|---|---|
| Step 02 目录边界 | `Get-ChildItem -Directory -Name` | 输出包含 `backend`、`deploy`、`frontend`、`scripts`、`tests` |
| 前端 lint | `npm run lint` | 通过 |
| 前端单元测试 | `npm run test` | 2 个测试文件、4 个测试通过 |
| 前端生产构建 | `npm run build` | 通过，生成 `frontend/dist/` 构建产物 |
| Playwright 浏览器安装 | `npx playwright install chromium` | 通过，Chromium 下载到本机 Playwright 缓存 |
| 前端 e2e smoke test | `npm run test:e2e` | 1 个 Chromium 测试通过 |
| 本地 dev server smoke | `Invoke-WebRequest http://127.0.0.1:5173/` | HTTP `200`，页面包含 `Meeting MVP` |
| 后端初始化防越界 | `Test-Path .\backend\pyproject.toml` | `False` |
| 后端锁文件防越界 | `Test-Path .\backend\uv.lock` | `False` |
| 根目录前端防越界 | `Test-Path .\package.json` | `False` |
| 根目录后端防越界 | `Test-Path .\pyproject.toml` | `False` |

### 后续注意事项

- 下一步只能在用户明确允许后执行 Step 04：初始化后端 Python 3.12 + FastAPI + uv 工程。
- 后续前端正式功能应继续复用 `src/stores/`、`src/components/ui/`、`src/lib/` 和 `@/*` 别名。
- Playwright 当前只配置 Chromium smoke test；多浏览器矩阵、真实音频捕获、WebSocket mock 与导出流程留到后续相关步骤。
- Windows 本机如果再次遇到 npm cache 权限问题，继续使用 `D:\meeting_mvp\.cache\npm` 作为临时 npm cache；该目录已被根目录 `.gitignore` 忽略。

## 2026-05-05 Step 04：初始化后端工程骨架

### 本次完成内容

- 已重新阅读 `memory-bank/` 全部 7 份文档，并阅读 `memory-bank/progress.md` 确认 Step 03 已完成。
- 已检查 Step 03 文件边界：`frontend/package.json` 与 `frontend/vite.config.ts` 存在；Step 04 开始前没有 `backend/pyproject.toml`、`backend/uv.lock`、`backend/.python-version`、根目录 `package.json` 或根目录 `pyproject.toml`。
- 已在 `backend/` 内初始化 uv 后端工程：
  - `.python-version` 固定为 `3.12`。
  - `pyproject.toml` 限定 Python `>=3.12,<3.13`。
  - `uv.lock` 锁定后端依赖。
  - `.venv` 由 `uv sync` 本地生成，仍由 `.gitignore` 忽略。
- 已加入运行依赖：FastAPI、Uvicorn、Pydantic v2、pydantic-settings、SQLAlchemy async、Alembic、psycopg、redis、httpx、tenacity、structlog。
- 已加入开发依赖：pytest、pytest-asyncio、Ruff、mypy。
- 已创建最小可验证后端服务：
  - `src/meeting_mvp_backend/main.py` 暴露 `meeting_mvp_backend.main:app`。
  - `GET /health` 返回 `{"status":"ok"}`。
  - `tests/test_health.py` 使用 `httpx.ASGITransport` 验证健康检查，不依赖真实 PostgreSQL、Redis 或外部 Provider。
- 已配置 Ruff、mypy、pytest 基础规则。
- 已更新根目录 `.gitignore`，忽略后端验证生成的 `.mypy_cache/` 与 `.ruff_cache/` 本地缓存。
- 已更新 `backend/README.md`、`memory-bank/architecture.md` 与 `AGENTS.md`。
- 未创建 `.env`、`.env.example`、Docker Compose、Alembic migration、真实数据库/Redis 集成测试，未开始 Step 05。

### 环境与执行记录

- `uv --version`：`uv 0.11.8`。
- `uv python install 3.12`：Python 3.12 已安装。
- `uv python pin 3.12`：已写入 `.python-version`。
- `uv init --bare --name meeting-mvp-backend --python 3.12 --no-workspace .`：已创建后端 uv 项目。
- `uv add ...` 与 `uv add --dev ...`：已写入依赖并生成/更新 `uv.lock`。
- `uv sync`：已创建/同步项目级 `.venv`，并安装当前后端包。

### 验证命令与结果

| 验证项 | 命令 | 实际结果 |
|---|---|---|
| Python 版本 | `uv run python --version` | `Python 3.12.11` |
| Ruff | `uv run ruff check .` | 通过，`All checks passed!` |
| mypy | `uv run mypy .` | 通过，`Success: no issues found in 3 source files` |
| pytest | `uv run pytest` | 1 个测试通过 |
| 健康检查服务 | `uv run uvicorn meeting_mvp_backend.main:app --host 127.0.0.1 --port 8000` 后请求 `/health` | HTTP `200`，响应 `{"status":"ok"}` |
| 前端初始化边界 | `Test-Path .\frontend\package.json` | `True` |
| 后端 pyproject | `Test-Path .\backend\pyproject.toml` | `True` |
| 后端锁文件 | `Test-Path .\backend\uv.lock` | `True` |
| 后端 Python 版本锁 | `Test-Path .\backend\.python-version` | `True` |
| 根目录前端防越界 | `Test-Path .\package.json` | `False` |
| 根目录后端防越界 | `Test-Path .\pyproject.toml` | `False` |
| Step 05 防越界 | 检查根目录和 `backend/` 下 `.env`、`.env.example` | 均为 `False` |

### 后续注意事项

- 下一步只能在用户明确允许后执行 Step 05：定义环境变量和配置边界。
- Step 04 只加入 Alembic 依赖，未执行 `alembic init`；迁移目录和数据库连接留给后续数据库步骤。
- 本地后端验证仍只覆盖不依赖真实 PostgreSQL、Redis、Google STT、Qwen、COS 密钥的轻量测试。
- 后续所有后端命令继续在 `backend/` 内使用 `uv run ...` 执行。

## 2026-05-05 Step 05：定义环境变量和配置边界

### 本次完成内容

- 已重新阅读 `memory-bank/` 全部 7 份文档，并阅读 `memory-bank/progress.md` 确认 Step 04 已完成。
- 已检查 Step 04 后端骨架：`backend/pyproject.toml`、`backend/uv.lock`、`backend/.python-version` 存在，后端测试可运行。
- 已新增唯一环境变量清单：`memory-bank/environment-variables.md`。
- 已新增后端配置模块：
  - `backend/src/meeting_mvp_backend/config.py` 使用 `pydantic-settings` 定义 `Settings`、`AppEnv`、`load_settings()` 和 `settings_status()`。
  - `APP_ENV=local` 作为本地 mock 模式，不要求真实 Provider、数据库、Redis、COS 密钥。
  - `APP_ENV=staging` 或 `APP_ENV=production` 缺少必填配置时抛出 `SettingsError`，错误信息只包含缺失变量名。
  - `OPENAI_STT_ENABLED=true` 时才要求 OpenAI STT 配置，默认关闭。
- 已让 FastAPI startup 加载配置，并通过 `structlog` 输出配置项 `set` / `unset` 脱敏状态。
- 已新增示例文件：
  - `backend/.env.example`：后端 local mock 示例配置，只包含 placeholder 或空值。
  - `frontend/.env.example`：前端 Vite 公开配置，只包含 `VITE_*`。
- 已新增前端公开配置模块：
  - `frontend/src/config/public-config.ts` 只读取 `VITE_APP_ENV`、`VITE_PUBLIC_BASE_URL`、`VITE_API_BASE_URL`、`VITE_WS_BASE_URL`。
  - `frontend/src/vite-env.d.ts` 声明 Vite 公开环境变量类型。
  - `frontend/src/config/public-config.test.ts` 验证前端公开配置不包含 Provider、数据库、Redis、COS 私有变量名。
- 已补充测试：
  - 后端配置测试先按 TDD 写入并确认因缺少 `config.py` 失败，再补实现使其通过。
  - 前端 public config 测试先确认因缺少模块失败，再补实现使其通过。
- 已更新 `.gitignore`，明确允许提交嵌套 `.env.example`，继续忽略真实 `.env` 与 `.env.*`。
- 已更新 `backend/README.md`、`memory-bank/architecture.md` 与 `AGENTS.md`。
- 未创建 `deploy/docker-compose.yml`、`backend/alembic.ini`、`backend/migrations/`、真实 `.env`、`.env.production`、根目录 `package.json` 或根目录 `pyproject.toml`，未开始 Step 06。

### 验证命令与结果

| 验证项 | 命令 | 实际结果 |
|---|---|---|
| 后端 Python 版本 | `uv run python --version` | `Python 3.12.11` |
| 后端 Ruff | `uv run ruff check .` | 通过，`All checks passed!` |
| 后端 mypy | `uv run mypy .` | 通过，`Success: no issues found in 5 source files` |
| 后端 pytest | `uv run pytest` | 5 个测试通过 |
| 后端 local mock 启动 | `MEETING_MVP_ENV_FILE=backend/.env.example uv --project backend run uvicorn ...` 后请求 `/health` | HTTP `200`，响应 `{"status":"ok"}` |
| production 缺失配置 | `APP_ENV=production` 后调用 `load_settings()` | 抛出 `SettingsError`，输出缺失配置名，不输出密钥值 |
| 前端 lint | `npm run lint` | 通过 |
| 前端单元测试 | `npm run test` | 3 个测试文件、6 个测试通过 |
| 前端生产构建 | `npm run build` | 通过 |
| 前端 e2e smoke test | `npm run test:e2e` | 1 个 Chromium 测试通过 |

### 后续注意事项

- 下一步只能在用户明确允许后执行 Step 06。
- 后续新增环境变量必须先更新 `memory-bank/environment-variables.md`，再同步示例文件、配置模型和测试。
- 前端只允许读取 `VITE_*` 变量；不得把 `QWEN_*`、`OPENAI_*`、`GOOGLE_*`、`DATABASE_URL`、`REDIS_URL`、`TENCENT_COS_*` 暴露到前端。
- 真实密钥仍只能放入本地未提交 `.env` 或服务器安全配置；示例文件继续只使用 placeholder 或空值。

## 2026-05-05 Step 06：建立 Docker Compose 与 Caddy 部署骨架

### 本次完成内容

- 已重新阅读 `memory-bank/2026-04-24-meeting-mvp-design.md` 和 `memory-bank/architecture.md`，并检查 Step 05 已完成。
- 已确认 Step 06 开始前 `deploy/` 只有 `README.md`，没有 `deploy/docker-compose.yml`、`deploy/Caddyfile`、`backend/Dockerfile` 或 `frontend/Dockerfile`。
- 已新增部署骨架文件：
  - `deploy/docker-compose.yml`：定义 `postgres`、`redis`、`backend`、`caddy` 四个服务。
  - `deploy/Caddyfile`：服务前端静态文件，并反向代理 `/api/*` 和 `/ws/*`。
  - `deploy/.env.example`：Docker Compose 示例配置，只包含 placeholder。
  - `backend/Dockerfile`：基于 Python 3.12 / uv 的 FastAPI 后端镜像构建文件。
  - `frontend/Dockerfile`：基于 Node 24 构建 Vite 静态产物，并生成 Caddy 静态服务镜像。
  - `.dockerignore`：排除 `.env`、本地缓存、虚拟环境、node_modules、构建产物和常见密钥文件形态，降低 Docker build context 风险。
- 已更新 `deploy/README.md`，记录 Compose 验证命令、端口边界和数据目录边界。
- Compose 约束已按 Step 06 落地：
  - Caddy 只映射 `80:80` 和 `443:443`。
  - PostgreSQL 未映射 `5432` 到宿主机公网。
  - Redis 未映射 `6379` 到宿主机公网。
  - PostgreSQL 数据挂载路径为 `/opt/meeting_mvp/data/postgres`。
  - Redis 数据挂载路径为 `/opt/meeting_mvp/data/redis`。
  - 后端容器只读挂载 `GOOGLE_APPLICATION_CREDENTIALS` 指向的 Google STT 服务账号 JSON，确保容器内路径可访问且不会写入密钥文件。
- 未执行 `docker compose up -d`、`docker compose ps`、Alembic migration，未开始 Step 07。

### 验证命令与结果

| 验证项 | 命令 | 实际结果 |
|---|---|---|
| 本地静态部署检查 | PowerShell 检查 `deploy/docker-compose.yml` 端口、挂载、真实 `.env` 和常见密钥形态 | 通过，输出 `local static deployment checks passed` |
| 本地 Docker 可用性 | `docker compose version` | 未安装 Docker，符合 Windows 本地不安装 Docker 的项目边界 |
| Lighthouse SSH 探测 | 使用用户提供的 SSH 私钥连接 `ubuntu@meeting.youroristore.com` | 通过，输出 `ubuntu`、`VM-0-9-ubuntu`、`/home/ubuntu` |
| 远端文件同步 | 将 `.dockerignore`、`backend/Dockerfile`、`frontend/Dockerfile`、`deploy/docker-compose.yml`、`deploy/Caddyfile`、`deploy/.env.example`、`deploy/README.md` 复制到 `/opt/meeting_mvp/app` | 通过，远端文件均存在；补充只读 Google 凭据挂载后已再次同步 `deploy/docker-compose.yml` |
| 远端 Compose 配置 | `cd /opt/meeting_mvp/app && docker compose --env-file deploy/.env.example -f deploy/docker-compose.yml config --quiet` | 通过，无输出，退出码 0 |
| 远端端口与挂载边界 | 基于远端 `docker compose config` 输出检查发布端口和数据目录 | 通过，输出 `remote-compose-boundary-checks-passed` |
| 后端 Python 版本 | `uv run python --version` | `Python 3.12.11` |
| 后端 Ruff | `uv run ruff check .` | 通过，`All checks passed!` |
| 后端 mypy | `uv run mypy .` | 通过，`Success: no issues found in 5 source files` |
| 后端 pytest | `uv run pytest` | 5 个测试通过 |
| 前端 lint | `npm run lint` | 通过 |
| 前端单元测试 | `npm run test` | 3 个测试文件、6 个测试通过 |
| 前端生产构建 | `npm run build` | 通过 |
| 前端 e2e smoke test | `npm run test:e2e` | 1 个 Chromium 测试通过 |

### Lighthouse 验收状态

- 已使用用户提供的 SSH 私钥完成 Lighthouse 连接和 Step 06 文件同步。
- 已在 `/opt/meeting_mvp/app` 执行 `docker compose --env-file deploy/.env.example -f deploy/docker-compose.yml config --quiet`，配置合法。
- 已基于远端 `docker compose config` 输出确认：
  - 仅发布 Caddy `80` 和 `443`。
  - 未发布 PostgreSQL `5432`。
  - 未发布 Redis `6379`。
  - PostgreSQL 挂载 `/opt/meeting_mvp/data/postgres`。
  - Redis 挂载 `/opt/meeting_mvp/data/redis`。
  - 后端只读挂载 `/opt/meeting_mvp/secrets/google-stt-sa.json`。
- 本次远端验收只使用 `deploy/.env.example` 占位配置，没有输出生产 `.env.production` 内容。

### 后续注意事项

- Step 06 的部署骨架和远端 Compose 配置验收已完成；后续仍需等用户明确允许后才能开始 Step 07。
- 在用户明确允许开始 Step 07 前，不得创建 Alembic migration、数据库模型或执行数据库升级。
- 生产真实 `.env.production`、Google 服务账号 JSON、COS SecretId / SecretKey 仍只能放在服务器安全位置，不得进入 Git。

## 2026-05-05 Step 07：建立数据库迁移和数据模型

### 本次完成内容

- 已重新阅读 `memory-bank/2026-04-24-meeting-mvp-design.md` 和 `memory-bank/architecture.md`，并检查 Step 06 已完成。
- 已确认 Step 07 开始前后端没有 `alembic.ini`、`migrations/`、`meeting_mvp_backend.db` 包或 ORM 模型。
- 已按 TDD 先新增 `backend/tests/test_database_models.py`，首次运行因缺少 `meeting_mvp_backend.db` 包失败，随后补实现使测试通过。
- 已新增 SQLAlchemy 2 数据模型和数据库工具：
  - `backend/src/meeting_mvp_backend/db/base.py`
  - `backend/src/meeting_mvp_backend/db/models.py`
  - `backend/src/meeting_mvp_backend/db/session.py`
- 已新增 Alembic 配置和初始迁移：
  - `backend/alembic.ini`
  - `backend/migrations/env.py`
  - `backend/migrations/script.py.mako`
  - `backend/migrations/versions/20260505_0001_initial_schema.py`
- 已落地五张核心表：`anonymous_client`、`meeting_session`、`transcript_segment`、`usage_event`、`export_file`。
- `meeting_session` 已支持 `pending_audio` 状态、`archive_token_hash` 和 `retention_expires_at`；未保存明文 `archive_token`。
- `usage_event.payload` 使用 PostgreSQL `JSONB`，未新增原始音频或密钥字段。
- 已新增 `backend/tests/integration/test_database_schema.py`，用于 Lighthouse PostgreSQL 集成测试，确认五张表存在且关键字段可写入/读取。
- 已更新 `backend/pyproject.toml`，登记 `integration` pytest marker，并让本地默认 `uv run pytest` 排除真实数据库集成测试。
- 已更新 `backend/Dockerfile`：
  - 复制 `alembic.ini`、`migrations/` 和 `tests/`，确保容器内可运行 migration 和集成测试。
  - 增加 `UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple` 和 `UV_HTTP_TIMEOUT=120`，解决 Lighthouse Docker build 中 `uv sync` 依赖下载卡住的问题。
- 未实现 F01 匿名用户初始化 API 或前端 `client_id` 生成，未开始 Step 08。

### 远端执行说明

- Lighthouse `/opt/meeting_mvp/app/.env.production` 当前只包含 Provider/COS 相关变量名，未包含 Compose 所需的数据库、Redis 和站点变量名。
- 为避免使用 `deploy/.env.example` 的占位密码污染正式持久化目录，本次 Step 07 使用临时 PostgreSQL 环境覆盖：
  - PostgreSQL 临时数据目录：`/opt/meeting_mvp/data/postgres_step07`
  - Redis 临时数据目录：`/opt/meeting_mvp/data/redis_step07`
  - 仅启动 `postgres` 服务用于 migration 和集成测试。
- 本次未启动 Caddy、Redis 或常驻 backend 服务；未执行 Step 08。
- 验收完成后已停止并删除临时 PostgreSQL 容器，清理 Step 07 临时数据目录、远端临时脚本和远端挂载式测试产生的 `.venv`/缓存。

### 调试记录

- 首次远端 backend build 失败：`backend/.python-version` 未同步到 `/opt/meeting_mvp/app/backend/`，补同步后继续。
- 后续远端 build 一度卡在 Docker BuildKit 的 `uv sync --frozen --no-dev --no-install-project`；确认不是 Alembic、pytest、磁盘或内存问题后，在 `backend/Dockerfile` 中加入 uv 镜像源和超时配置，再次 `docker compose build backend` 通过。
- 首次 Alembic migration 失败：手动创建 PostgreSQL enum 后，`op.create_table()` 又触发同名 enum 自动创建，报 `DuplicateObject: type "source_platform" already exists`。已将 migration 中的 PostgreSQL enum 声明改为 `create_type=False`，保留显式 `checkfirst=True` 创建，重跑通过。

### 验证命令与结果

| 验证项 | 命令 | 实际结果 |
|---|---|---|
| TDD RED | `uv run pytest tests/test_database_models.py` | 首次失败，`ModuleNotFoundError: No module named 'meeting_mvp_backend.db'` |
| 后端 Python 版本 | `uv run python --version` | `Python 3.12.11` |
| Alembic history | `uv run alembic history` | 通过，显示 `<base> -> 20260505_0001 (head)` |
| 后端 Ruff | `uv run ruff check .` | 通过，`All checks passed!` |
| 后端 mypy | `uv run mypy .` | 通过，`Success: no issues found in 13 source files` |
| 后端本地 pytest | `uv run pytest` | 11 个测试通过，1 个 integration 测试被默认排除 |
| 前端 lint | `npm run lint` | 通过 |
| 前端单元测试 | `npm run test` | 3 个测试文件、6 个测试通过 |
| 前端生产构建 | `npm run build` | 通过 |
| 前端 e2e smoke test | `npm run test:e2e` | 1 个 Chromium 测试通过 |
| 安全静态检查 | 检查 Git 跟踪/新增文件和 DB schema | 通过，未发现真实 `.env`、密钥文件、原始音频字段或明文 `archive_token` 字段 |
| Lighthouse backend build | `docker compose --env-file .env.production -f deploy/docker-compose.yml build --progress plain backend` | 通过，输出 `Image meeting_mvp-backend Built` |
| Lighthouse migration | `docker compose --env-file .env.production -f deploy/docker-compose.yml run --rm --no-deps backend uv run alembic upgrade head` | 通过，Alembic 使用 PostgreSQL dialect，升级到 head |
| Lighthouse DB integration | `docker compose --env-file .env.production -f deploy/docker-compose.yml run --rm --no-deps backend uv run --group dev pytest -o addopts= -m integration` | 通过，1 个集成测试通过，确认五张表存在且关键字段可写入/读取 |

### 后续注意事项

- 下一步只能在用户明确允许后执行 Step 08：实现 F01 匿名用户初始化。
- Step 08 可复用本次新增的 `AnonymousClient` ORM 模型和 `create_session_factory_from_settings()`。
- 生产发布前仍需使用真实生产数据库环境变量执行 migration；本次 Step 07 只在临时 PostgreSQL 数据目录完成 schema 验收。
- 远端 `.env.production` 后续需要补齐数据库、Redis 和站点相关变量，才能直接作为 Compose 生产环境文件使用。

## 2026-05-06 Step 08：实现 F01 匿名用户初始化

### 本次完成内容

- 已按计划只推进 Step 08，未开始 Step 09 的额度校验、Redis 活跃会话、并发限制或预算保险丝。
- 已按 TDD 先补充匿名初始化接口、本地存储和 Zustand 状态测试，确认缺少实现时失败，再补实现使测试通过。
- 前端已新增稳定匿名身份：
  - `frontend/src/lib/anonymous-client.ts` 负责从 `localStorage` 读取或通过 `crypto.randomUUID()` 创建 `client_id`。
  - `frontend/src/api/anonymous-clients.ts` 负责调用 `POST /api/anonymous-clients`，把后端 snake_case 响应映射为前端 camelCase 状态。
  - `frontend/src/stores/session-store.ts` 已扩展 `clientId`、匿名初始化状态、服务端同步状态、同步错误和默认今日剩余额度。
  - `frontend/src/App.tsx` 首屏加载时初始化匿名身份，并在工作台状态区显示匿名身份和服务端同步状态；本地存储不可用时提示启用浏览器存储。
- 后端已新增匿名初始化 API：
  - `POST /api/anonymous-clients` 接收 `{"client_id": "<uuid>"}`。
  - 响应返回 `client_id`、`daily_free_seconds`、`remaining_seconds_today` 和 `is_new`。
  - `backend/src/meeting_mvp_backend/anonymous_clients.py` 负责根据 `client_id`、请求 IP 和 User-Agent 计算 SHA-256 hash，并 upsert `anonymous_client`。
  - 首次请求写入 `first_seen_at`、`last_seen_at`、`created_ip_hash`、`user_agent_hash`；重复请求更新 `last_seen_at` 和最近 `user_agent_hash`，保留首次 IP hash。
  - 未配置 `DATABASE_URL` 时接口返回 HTTP 503；这只影响服务端同步，不阻塞前端本地 `client_id` 生成。
- 未新增 migration，复用 Step 07 已建立的 `anonymous_client` 表。
- Lighthouse 远端验证使用已记录的 SSH 私钥路径，只使用路径连接服务器，未读取、复制或输出 PEM 私钥内容。

### 远端执行说明

- 本次远端验证继续避免正式生产数据目录，使用临时 PostgreSQL 环境：
  - PostgreSQL 临时数据目录：`/opt/meeting_mvp/data/postgres_step08`
  - Redis 临时数据目录：`/opt/meeting_mvp/data/redis_step08`
  - 临时环境文件：`/opt/meeting_mvp/app/.env.step08`
- 已同步 Step 08 后端必要文件到 `/opt/meeting_mvp/app`，并构建 backend 镜像。
- 远端只启动临时 `postgres` 和一次性 `backend` 测试容器；未启动 Redis、Caddy 或常驻 backend 服务。
- 首次合并执行的远端命令在 backend 镜像和临时 PostgreSQL 已就绪后本地超时；随后拆分执行 Alembic migration 和匿名接口集成测试，均通过。
- 验收完成后已删除临时 PostgreSQL 容器、`.env.step08`、`/opt/meeting_mvp/data/postgres_step08` 和 `/opt/meeting_mvp/data/redis_step08`，并清理远端测试缓存。

### 验证命令与结果

| 验证项 | 命令 | 实际结果 |
|---|---|---|
| 后端 TDD RED | `uv run pytest tests/test_anonymous_clients_api.py` | 首次失败，`ModuleNotFoundError: No module named 'meeting_mvp_backend.anonymous_clients'` |
| 前端 TDD RED | `npm run test -- src/lib/anonymous-client.test.ts src/stores/anonymous-client-store.test.ts` | 首次失败，缺少匿名 client 工具和 store action |
| 后端 Python 版本 | `uv run python --version` | `Python 3.12.11` |
| 后端 Ruff | `uv run ruff check .` | 通过，`All checks passed!` |
| 后端 mypy | `uv run mypy .` | 通过，`Success: no issues found in 16 source files` |
| 后端本地 pytest | `uv run pytest` | 15 个测试通过，2 个 integration 测试被默认排除 |
| 前端 lint | `npm run lint` | 通过 |
| 前端单元测试 | `npm run test` | 5 个测试文件、13 个测试通过 |
| 前端生产构建 | `npm run build` | 通过 |
| 前端 e2e smoke test | `npm run test:e2e` | 1 个 Chromium 测试通过 |
| Lighthouse migration | `docker compose --env-file .env.step08 -f deploy/docker-compose.yml run --rm --no-deps backend uv run alembic upgrade head` | 通过，Alembic 使用 PostgreSQL dialect |
| Lighthouse 匿名接口集成测试 | `docker compose --env-file .env.step08 -f deploy/docker-compose.yml run --rm --no-deps backend uv run --group dev pytest -o addopts= tests/integration/test_anonymous_clients_integration.py -q` | 通过，1 个真实 PostgreSQL 集成测试通过 |
| Lighthouse 临时资源清理 | 检查 `.env.step08`、`/opt/meeting_mvp/data/postgres_step08` 和临时容器 | 通过，临时 env 和临时数据目录已清理，未保留 Step 08 临时容器 |
| Markdown 空白检查 | `git diff --check` | 通过；仅输出 Windows LF/CRLF 工作区提示，无空白错误 |
| PEM 内容静态扫描 | 扫描 Git 跟踪文件和未忽略新增文件中的 `-----BEGIN ... PRIVATE KEY-----` / `-----END ... PRIVATE KEY-----` | 通过，未发现 PEM 私钥正文 |

### 后续注意事项

- 下一步只能在用户明确允许后执行 Step 09：实现 F02 额度与预算校验。
- Step 09 应在当前 `client_id` 与 `anonymous_client` 基础上接入真实日额度、单场时长、Redis 活跃会话、并发限制和预算保险丝。
- 当前 `remaining_seconds_today` 仍基于 PostgreSQL `daily_minutes_used` 的占位剩余额度计算；会议级消耗和 Redis 限流留到 Step 09。
- 前端在服务端同步失败时仍保留本地匿名身份，后续 Step 09 需要在真正创建会议前做服务端额度校验。

## 2026-05-06 文档重定位：PRD 移至根目录

### 本次完成内容

- 已将 `memory-bank/meeting-prd.md` 移动到项目根目录 `meeting-prd.md`。
- 已更新 `AGENTS.md`、`memory-bank/architecture.md`、`memory-bank/implementation-plan.md` 和本文件中的 PRD 路径引用。
- 后续引用 PRD 时使用根目录路径 `meeting-prd.md`，不再使用旧路径 `memory-bank/meeting-prd.md`。

### 验证命令与结果

| 验证项 | 命令 | 实际结果 |
|---|---|---|
| 旧路径引用检查 | 搜索 `memory-bank/meeting-prd.md` 和 `memory-bank\meeting-prd.md` | 无残留引用 |
| 文件位置检查 | 检查 `meeting-prd.md` 与 `memory-bank/meeting-prd.md` | 根目录文件存在，旧路径已移除 |

## 2026-05-06 Step 09：实现 F02 额度与预算校验

### 本次完成内容

- 已按计划只推进 Step 09，未新增公开 REST API，未新增 WebSocket 消息 schema，未开始 Step 10。
- 已按 TDD 先新增 `backend/tests/test_quota.py` 并运行 `uv run pytest tests/test_quota.py`，确认缺少 `meeting_mvp_backend.quota` 时按预期失败，再补实现使测试通过。
- 后端已新增内部额度模块 `backend/src/meeting_mvp_backend/quota.py`：
  - `QuotaDecision` 和 `QuotaDenialReason` 表达允许/拒绝结果与拒绝原因。
  - `QuotaPolicy` 负责纯逻辑判定：每日 40 分钟、单场 30 分钟、同用户 1 个活跃会议和预算保险丝。
  - `QuotaService` 提供后续会话编排可复用的方法：`check_start_allowed()`、`reserve_active_session()`、`release_active_session()`、`record_consumed_seconds()`、`check_session_duration()`。
  - `RedisQuotaStore` 使用 `REDIS_URL` 指向的 Redis 保存短期额度、活跃会话和预算保险丝状态，不保存正式会议档案。
  - `create_quota_service_from_settings()` 提供从后端 `Settings.REDIS_URL` 创建 Redis-backed 额度服务的入口。
- Redis key 边界已按 Step 09 固定设计实现：
  - `meeting_mvp:quota:{client_id}:{yyyyMMdd}:used_seconds`：Asia/Shanghai 自然日已用秒数，TTL 到下一个上海自然日零点。
  - `meeting_mvp:active_sessions:{client_id}`：sorted set，member 为 `session_id`，score 为过期 epoch；检查前清理过期会话。
  - `meeting_mvp:budget:{yyyyMM}:estimated_cost_cents`：全站当月预估成本，单位分。
  - `meeting_mvp:budget:{yyyyMM}:fuse_triggered`：预算保险丝显式开关，值为 `1` 时拒绝新会话。
- 拒绝优先级已固定为：预算保险丝 > 活跃会话上限 > 每日额度耗尽 > 单场时长上限。
- Step 09 没有修改数据库 schema，没有新增 migration；PostgreSQL 仍是正式归档来源。

### 远端执行说明

- Lighthouse 验证使用已记录的 SSH 私钥路径，只使用路径连接服务器，未读取、复制或输出 PEM 私钥内容。
- 已同步 Step 09 必要后端文件到 `/opt/meeting_mvp/app`。
- 远端验证使用独立 Compose project `meeting_mvp_step09`，避免触碰正式 `meeting_mvp` 容器名。
- 远端临时资源：
  - Redis 临时数据目录：`/opt/meeting_mvp/data/redis_step09`
  - 临时环境文件：`/opt/meeting_mvp/app/.env.step09`
  - 非真实 Google 凭据占位文件：`/opt/meeting_mvp/secrets/google-stt-sa-step09-placeholder.json`
- 已构建 backend 镜像，只启动临时 `redis` 和一次性 `backend` 测试容器；未启动 Caddy、PostgreSQL 或常驻 backend 服务。
- 验收完成后已删除临时 Redis 容器、临时网络、临时 backend 镜像、`.env.step09`、占位凭据文件和 `/opt/meeting_mvp/data/redis_step09`；Redis 数据目录内由容器写入的文件需要 `sudo rm -rf` 清理，清理后已验证无 Step 09 临时容器和临时路径残留。

### 验证命令与结果

| 验证项 | 命令 | 实际结果 |
|---|---|---|
| 后端 TDD RED | `uv run pytest tests/test_quota.py` | 首次失败，`ModuleNotFoundError: No module named 'meeting_mvp_backend.quota'` |
| 后端 Python 版本 | `uv run python --version` | `Python 3.12.11` |
| 后端 Ruff | `uv run ruff check .` | 通过，`All checks passed!` |
| 后端 mypy | `uv run mypy .` | 通过，`Success: no issues found in 19 source files` |
| 后端额度单测 | `uv run pytest tests/test_quota.py` | 10 个测试通过 |
| 后端本地 pytest | `uv run pytest` | 25 个测试通过，3 个 integration 测试被默认排除 |
| 前端 lint | `npm run lint` | 通过 |
| 前端单元测试 | `npm run test` | 5 个测试文件、13 个测试通过 |
| 前端生产构建 | `npm run build` | 通过 |
| 前端 e2e smoke test | `npm run test:e2e` | 1 个 Chromium 测试通过 |
| Lighthouse backend build | `docker compose -p meeting_mvp_step09 --env-file .env.step09 -f deploy/docker-compose.yml build backend` | 通过，`Image meeting_mvp_step09-backend Built` |
| Lighthouse Redis 启动 | `docker compose -p meeting_mvp_step09 --env-file .env.step09 -f deploy/docker-compose.yml up -d redis` | 通过，临时 Redis 进入 `healthy` |
| Lighthouse Redis 集成测试 | `docker compose -p meeting_mvp_step09 --env-file .env.step09 -f deploy/docker-compose.yml run --rm --no-deps backend uv run --group dev pytest -o addopts= tests/integration/test_quota_redis_integration.py -q` | 通过，1 个真实 Redis 集成测试通过 |
| Lighthouse 临时资源清理 | 检查 Step 09 临时容器、临时 backend 镜像、`.env.step09`、占位凭据和 `/opt/meeting_mvp/data/redis_step09` | 通过，临时资源已清理 |
| Markdown 空白检查 | `git diff --check` | 通过；仅输出 Windows LF/CRLF 工作区提示，无空白错误 |

### 后续注意事项

- 下一步只能在用户明确允许后执行 Step 10；当前不得提前新增 Step 10 WebSocket 消息 schema。
- Step 10/后续会话编排可以复用 `QuotaService`，在真正创建会议或处理 `session_start` 时接入额度检查和活跃会话登记。
- `record_consumed_seconds()` 已具备累计能力，但“检测到有效音频前不正式消耗额度”的会话编排仍留给后续步骤。
- Step 08 的匿名初始化 API 仍返回基础剩余额度；真正的会议级 Redis 额度扣减尚未接入公开接口或 WebSocket。
