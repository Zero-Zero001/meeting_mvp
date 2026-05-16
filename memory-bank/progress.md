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

## 2026-05-06 Step 10：WebSocket 消息 Schema

### 本次完成

- 只推进 Step 10 的 WebSocket 消息契约，未新增 `/ws` endpoint，未实现会话编排，未接入 `QuotaService`、Redis、PostgreSQL、Provider 或 DB 写入，未开始 Step 11。
- 后端新增 `backend/src/meeting_mvp_backend/ws_messages.py`，使用 Pydantic v2 定义基于顶层 `type` 字段的 discriminated union：
  - 请求 JSON 消息：`session_start`、`heartbeat`、`session_stop`。
  - 响应 JSON 消息：`session_started`、`quota_update`、`audio_status`、`asr_interim`、`translation_interim`、`segment_final`、`key_sentence_update`、`timeline_update`、`warning`、`error`、`session_closed`。
  - `audio_chunk` 不作为 JSON 消息进入 schema，保留为 WebSocket binary frame；`is_audio_chunk_frame()` 只识别 `bytes`、`bytearray`、`memoryview`。
  - `session_start.audio_format` 固定为 `{ sample_rate_hz: 16000, channels: 1, encoding: "pcm16" }`。
- 前端新增 `frontend/src/protocol/websocket-messages.ts`，引入 Zod 镜像同一套 wire schema，并导出 `parseClientMessage()`、`parseServerMessage()`、`isAudioChunkFrame()` 与推导类型，供 Step 11 后真实 WebSocket 连接复用。
- 前端新增运行时依赖 `zod`，更新 `frontend/package.json` 与 `frontend/package-lock.json`；首次 `npm install zod` 遇到默认 npm cache `EPERM`，按既有约定使用 `$env:npm_config_cache='D:\meeting_mvp\.cache\npm'` 后安装成功。npm audit 仍提示 2 个 moderate vulnerabilities，本步未执行自动修复以避免越界依赖变更。
- 新增测试：
  - `backend/tests/test_ws_messages.py`
  - `frontend/src/protocol/websocket-messages.test.ts`

### TDD 与验证记录

- 失败测试先行：
  - 后端目标测试首次运行失败，原因为 `meeting_mvp_backend.ws_messages` 尚不存在。
  - 前端目标测试首次运行失败，原因为 `src/protocol/websocket-messages.ts` 尚不存在。
- 针对性验证已通过：
  - `uv run pytest tests/test_ws_messages.py`：9 passed。
  - `npm run test -- src/protocol/websocket-messages.test.ts`：9 passed。
- 本地完整验证已通过：
  - `uv run python --version`：`Python 3.12.11`。
  - `uv run ruff check .`：通过，`All checks passed!`。
  - `uv run mypy .`：通过，`Success: no issues found in 21 source files`。
  - `uv run pytest`：34 passed，3 integration deselected。
  - `npm run lint`：通过。
  - `npm run test`：6 个测试文件、22 个测试通过。
  - `npm run build`：通过。
  - `npm run test:e2e`：1 个 Chromium smoke test 通过。
  - `git diff --check`：通过，仅输出 Windows LF/CRLF 工作区提示，无空白错误。
  - `git status --short`：当前改动仅包含 Step 10 代码、前端 Zod 依赖锁文件和记忆文档。
- Step 10 不需要 Lighthouse Redis/PostgreSQL/Docker/Provider 集成测试，因为本步只新增纯协议 schema 和本地可测试解析逻辑。

### 后续注意

- Step 11 WebSocket 会话编排必须等待用户明确允许后再开始。
- Step 11 接入真实 `/ws` endpoint 时，应复用本步的后端 Pydantic schema 和前端 Zod schema；JSON 消息继续使用 snake_case 字段名与顶层 `type`，音频仍通过 16 kHz mono PCM16 binary frame 上传。

## 2026-05-07 Step 11：实现 F05 WebSocket 会话编排

### 本次完成

- 只推进 Step 11 的后端 WebSocket 会话编排，未开始 Step 12，未修改前端实时会议工作台 UI，未接入真实 Provider、STT、Qwen、音频前处理或 `transcript_segment` 写入。
- 后端新增 `backend/src/meeting_mvp_backend/ws_sessions.py`：
  - `WebSocketSessionOrchestrator` 负责 `/ws` 连接内的会话生命周期。
  - `SQLAlchemyMeetingSessionRepository` 负责读写 PostgreSQL `anonymous_client` 与 `meeting_session`。
  - `session_start` 会先校验匿名 client 是否已初始化，再调用 `QuotaService.reserve_active_session()`，通过后写入 `meeting_session(status=pending_audio)` 并返回 `session_started`。
  - `archive_token` 只在 `session_started` 中返回明文；数据库只保存 SHA-256 hash。
  - 首个非空 binary frame 暂作为 Step 11 的“有效音频”判定，把会话转为 `active` 并发送 `audio_status(has_audio=true)`；真实音量和静音检测留给 Step 14。
  - `session_stop` 按 active 后 wall-clock 秒数结算额度，更新 `ended_at`、`duration_seconds`、`quota_seconds_consumed`、`status=ended`，释放 Redis active session，并发送 `quota_update` 与 `session_closed(reason="user_stopped")`。
  - 浏览器断开或 task 取消时通过 `finally` 清理，释放 Redis active session；断开会话记录为 `status=error`。
- 后端修改 `backend/src/meeting_mvp_backend/main.py`：
  - 注册 `@app.websocket("/ws")`。
  - 增加 `get_websocket_session_orchestrator()`，从 app settings 创建数据库仓储和 Redis-backed quota service。
  - 缺少 `DATABASE_URL` 或 `REDIS_URL` 时，WebSocket 会发送 `error(code="configuration_error")` 和 `session_closed(reason="configuration_error")` 后关闭。
- 新增测试：
  - `backend/tests/test_websocket_sessions.py` 覆盖本地 fake 仓储/额度服务下的正常开始、音频激活、heartbeat、停止结算、断开清理、重复会话拒绝、未初始化 client、非法消息和 session mismatch。
  - `backend/tests/integration/test_websocket_session_redis_integration.py` 覆盖 Lighthouse 真实 PostgreSQL + Redis 下的正常开始/停止、重复会话拒绝和断开清理。
- 未新增数据库 migration，复用 Step 07 的 `meeting_session` 字段；未保存 raw audio、interim 或正式 transcript segment。

### TDD 与调试记录

- 失败测试先行：首次运行 `uv run pytest tests/test_websocket_sessions.py` 失败，原因为 `main.py` 尚无 `get_websocket_session_orchestrator`，且 `meeting_mvp_backend.ws_sessions` 尚不存在。
- 实现后本地目标测试通过：`uv run pytest tests/test_websocket_sessions.py` 为 7 passed。
- Lighthouse 第一次 migration 失败是因为远端 `/opt/meeting_mvp/app` 缺少 Step 10 的 `ws_messages.py`；已补同步 `ws_messages.py` 和对应测试后重建 backend 镜像，migration 通过。
- Lighthouse 集成测试曾暴露 Redis asyncio client 跨 TestClient event loop 复用问题；已取消把 `QuotaService` 缓存在 `app.state`，改为每个 WebSocket 连接创建 Redis-backed quota service。
- Lighthouse 断开清理测试曾受 TestClient 关闭时序影响；最终改为直接向编排器注入 ASGI `websocket.disconnect` 事件，同时仍使用真实 PostgreSQL 仓储和 Redis 额度服务验证清理行为。

### 验证命令与结果

- 后端本地：
  - `uv run python --version`：`Python 3.12.11`。
  - `uv run ruff check .`：通过，`All checks passed!`。
  - `uv run mypy .`：通过，`Success: no issues found in 24 source files`。
  - `uv run pytest tests/test_websocket_sessions.py`：7 passed。
  - `uv run pytest`：41 passed，5 integration deselected。
- 前端既有验证：
  - `npm run lint`：通过。
  - `npm run test`：6 个测试文件、22 个测试通过。
  - `npm run build`：通过；Vite 输出 `vite:css` plugin timing warning，不影响退出码。
  - `npm run test:e2e`：1 个 Chromium smoke test 通过。
- Lighthouse 真实 Redis/PostgreSQL 验证：
  - 使用独立 Compose project `meeting_mvp_step11`。
  - 临时数据目录：`/opt/meeting_mvp/data/postgres_step11`、`/opt/meeting_mvp/data/redis_step11`。
  - 临时 env：`/opt/meeting_mvp/app/.env.step11`。
  - 非真实 Google 凭据占位文件：`/opt/meeting_mvp/secrets/google-stt-sa-step11-placeholder.json`。
  - `docker compose -p meeting_mvp_step11 --env-file .env.step11 -f deploy/docker-compose.yml build backend`：通过。
  - `docker compose -p meeting_mvp_step11 --env-file .env.step11 -f deploy/docker-compose.yml up -d postgres redis`：PostgreSQL 和 Redis 均 healthy。
  - `docker compose -p meeting_mvp_step11 --env-file .env.step11 -f deploy/docker-compose.yml run --rm --no-deps backend uv run alembic upgrade head`：通过。
  - `docker compose -p meeting_mvp_step11 --env-file .env.step11 -f deploy/docker-compose.yml run --rm --no-deps backend sh -lc 'UV_HTTP_TIMEOUT=240 UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple uv run --group dev pytest -o addopts= tests/integration/test_websocket_session_redis_integration.py -q'`：2 passed。
  - 验收后已清理临时容器、临时网络、临时 backend 镜像、`.env.step11`、占位凭据文件、临时 PostgreSQL/Redis 数据目录。
- 仓库检查：
  - `git diff --check`：通过，仅有 Windows LF/CRLF 工作区提示，无空白错误。
  - `git status --short`：当前改动只包含 Step 11 后端代码、Step 11 测试和记忆文档。

### 后续注意

- Step 12 必须等待用户明确允许后再开始。
- Step 12 只应构建前端实时会议工作台骨架；真实音频捕获、AudioWorklet、Provider、final 归档和四区实时数据流仍分别留给后续步骤。
- Step 11 当前用“首个非空 binary frame”临时代表有效音频，后续 Step 14 接入真实音频电平与静音检测后，应复用 `audio_status` 但替换判定来源。

## 2026-05-07 Step 12：前端实时会议工作台骨架

### 本次完成

- 只推进 `memory-bank/implementation-plan.md` 的 Step 12，未开始 Step 13。
- 已按 TDD 更新前端测试并先确认失败：
  - `frontend/src/stores/session-store.test.ts` 新增捕获模式切换测试，首次失败原因为 `setCaptureMode` 尚不存在。
  - `frontend/src/App.test.tsx` 新增状态栏、四区语义、捕获模式、开始/结束按钮和匿名身份/额度展示测试，首次失败原因为 UI 仍是 Step 03/08 的旧骨架。
  - `frontend/e2e/app.spec.ts` 新增桌面和移动视口 smoke test，首次失败原因为浏览器可访问性树中缺少新的 `会议状态栏` 和四区契约。
- 前端已重构 `frontend/src/App.tsx`：
  - 首屏保持会议工作台，不做营销页。
  - 顶部状态栏显式暴露 `role="banner"` 和可访问名称 `会议状态栏`。
  - 状态栏包含捕获模式切换、开始捕获、结束会议、匿名身份、服务端同步、今日剩余额度、音频状态、ASR 状态和翻译状态。
  - 四区 UI 固定为可定位区域：`英文原文区`、`中文翻译区`、`当前重点句区`、`会议时间线区`。
  - 桌面使用左右分栏网格，移动端纵向堆叠，并通过 Playwright 检查无水平溢出。
- 前端已扩展 `frontend/src/stores/session-store.ts`：
  - 新增 `setCaptureMode(mode: CaptureMode): void`，用于开始捕获前切换 `tab_audio` / `system_audio`。
  - 保留 `beginCapture()` / `endSession()` 的占位行为；开始捕获只更新本地 UI 状态，不调用真实浏览器捕获。
- 本步没有修改后端 REST API、WebSocket schema、数据库 schema、环境变量清单或部署配置。
- 本步没有引入 `getDisplayMedia`、`AudioWorklet`、真实音频捕获、WebSocket client、binary 上传、Google STT、Qwen 或 Provider 链路。

### 验证命令与结果

| 验证项 | 命令 | 实际结果 |
|---|---|---|
| Step 12 前端 TDD RED | `npm run test -- src/stores/session-store.test.ts src/App.test.tsx` | 首次失败，缺少 `setCaptureMode` 和新的状态栏/四区 UI |
| Step 12 E2E RED | `npm run test:e2e -- e2e/app.spec.ts` | 首次失败，旧构建产物中缺少 `会议状态栏` 与新四区契约 |
| 目标前端单测 | `npm run test -- src/stores/session-store.test.ts src/App.test.tsx` | 2 个测试文件、7 个测试通过 |
| 目标 E2E | `npm run build` 后执行 `npm run test:e2e -- e2e/app.spec.ts` | 2 个 Chromium 测试通过 |
| 前端 lint | `npm run lint` | 通过 |
| 前端单元测试 | `npm run test` | 6 个测试文件、25 个测试通过 |
| 前端生产构建 | `npm run build` | 通过 |
| 前端 E2E | `npm run test:e2e` | 2 个 Chromium 测试通过 |
| Markdown/代码空白检查 | `git diff --check` | 通过；仅输出 Windows LF/CRLF 工作区提示，无空白错误 |

### 后续注意

- Step 13 必须等待用户明确允许后再开始。
- Step 13 才能实现 `getDisplayMedia`、真实音频捕获、捕获授权和浏览器音频错误处理；当前 `开始捕获` 仍只是 UI 入口和 Zustand 状态占位。
- Provider 状态在 Step 12 只是本地 UI 文案，不代表真实 ASR、Qwen 或 WebSocket 连接。
- Playwright E2E 使用 Vite preview 的 `dist/`，修改应用代码后需要先执行 `npm run build` 再执行 `npm run test:e2e`，否则可能测到旧构建产物。

## 2026-05-07 Step 13：前端会议音频捕获

### 本次完成

- 只推进 `memory-bank/implementation-plan.md` 的 Step 13，未开始 Step 14。
- 已按 TDD 更新并先确认失败：
  - 新增 `frontend/src/lib/audio-capture.test.ts`，首次失败原因为 `frontend/src/lib/audio-capture.ts` 尚不存在。
  - 扩展 `frontend/src/stores/session-store.test.ts`，首次失败原因为 store 尚无 `captureStatus`、`mediaStream`、`lastCaptureAttempt`、`setSourcePlatform()` 和 async `beginCapture()`。
  - 扩展 `frontend/src/App.test.tsx` 和 `frontend/e2e/app.spec.ts`，首次失败原因为 UI 尚无会议平台选择、真实捕获状态、授权失败提示和无音频轨道降级提示。
- 新增 `frontend/src/lib/audio-capture.ts`：
  - `requestDisplayMediaCapture()` 调用 `getDisplayMedia({ audio: true, video: true })`。
  - 成功条件仅为返回的 `MediaStream` 至少包含 1 条 audio track。
  - 无 audio track 时停止所有 tracks 并返回 `no_audio_track`。
  - `NotAllowedError` / `SecurityError` 归类为 `permission_denied`；缺少 API 或非安全上下文归类为 `not_supported`；其他异常归类为 `capture_failed`。
  - 只保留浏览器返回的 `MediaStream` 引用，不读取、不保存、不上传原始音频。
- 扩展 `frontend/src/stores/session-store.ts`：
  - 新增 `SourcePlatform`、`captureStatus`、`captureErrorCode`、`captureErrorMessage`、`lastCaptureAttempt` 和 `mediaStream`。
  - 新增 `setSourcePlatform(platform)`，支持记录 `google_meet`、`teams_web`、`zoom_web`、`tencent_meeting_web` 或 `unknown`。
  - 将 `beginCapture(mode)` 改为 async action，支持测试注入 fake capture service。
  - `lastCaptureAttempt` 记录平台、捕获模式、浏览器、授权结果、失败码和尝试时间；正式 `usage_event` 仍留到 Step 21。
  - `endSession()` 会停止当前 `mediaStream.getTracks()` 并清空流引用。
- 更新 `frontend/src/App.tsx`：
  - 状态栏新增“会议平台”选择控件。
  - “开始捕获”调用 async `beginCapture(captureMode)`；授权中禁用开始按钮，成功后显示“已捕获音频”。
  - 拒绝授权时显示重试入口和授权失败提示。
  - 无 audio track 时显示“请切换系统音频模式后重新捕获。”。
  - 系统音频模式显示可能包含其他应用声音的风险提示，但不会自动切换或自动发起系统音频捕获。
- 本步没有修改后端 REST API、WebSocket schema、数据库 schema、环境变量清单或部署配置。
- 本步没有实现 `AudioWorklet`、16 kHz mono PCM16 转换、音量电平/静音检测、WebSocket client、binary 上传、Google STT、Qwen 或 Provider 链路。

### 验证命令与结果

| 验证项 | 命令 | 实际结果 |
|---|---|---|
| Step 13 前端 TDD RED | `npm run test -- src/lib/audio-capture.test.ts src/stores/session-store.test.ts src/App.test.tsx` | 首次失败，缺少捕获封装、store 状态和 UI 控件 |
| Step 13 目标单测 | `npm run test -- src/lib/audio-capture.test.ts src/stores/session-store.test.ts src/App.test.tsx` | 3 个测试文件、15 个测试通过 |
| 前端 lint | `npm run lint` | 通过 |
| 前端单元测试 | `npm run test` | 7 个测试文件、33 个测试通过 |
| 前端生产构建 | `npm run build` | 通过 |
| 前端 E2E | `npm run test:e2e` | 5 个 Chromium 测试通过 |
| Markdown/代码空白检查 | `git diff --check` | 通过；仅输出 Windows LF/CRLF 工作区提示，无空白错误 |
| Step 14 边界扫描 | `Select-String` 搜索 `AudioWorklet`、`new WebSocket`、`createMediaStreamSource`、`ScriptProcessor`、`PCM16` | 未命中新 Step 13 代码；仅命中 Step 10 既有 WebSocket 协议测试/schema 中的固定 `pcm16` 字段 |

### 后续注意

- Step 14 必须等待用户明确允许后再开始。
- Step 14 才能实现 AudioWorklet、16 kHz mono PCM16 转换、音量电平/静音检测、WebSocket client 或 binary 上传。
- Step 13 的“无音频”只表示没有 audio track；真实静音、音量过低和 30 秒无有效音频检测仍未实现。
- 真实 Chrome/Edge + Google Meet/Teams/Zoom/腾讯会议 Web 的兼容性矩阵仍需人工执行。本步自动化测试使用 mock `getDisplayMedia`，不能等同于真实会议平台验收。

## 2026-05-09 Step 14：前端音频前处理与 binary 上传

### 本次完成

- 只推进 `memory-bank/implementation-plan.md` 的 Step 14，未进入 Step 15。
- 已按 TDD 先补测试并确认 RED：
  - 新增 `frontend/src/lib/audio-frames.test.ts`，首次失败原因为 `frontend/src/lib/audio-frames.ts` 尚不存在。
  - 新增 `frontend/src/lib/audio-processing.test.ts`，首次失败原因为 `frontend/src/lib/audio-processing.ts` 尚不存在。
  - 新增 `frontend/src/lib/meeting-websocket.test.ts`，首次失败原因为 `frontend/src/lib/meeting-websocket.ts` 尚不存在。
  - 扩展 `frontend/src/stores/session-store.test.ts`、`frontend/src/App.test.tsx` 和 `frontend/e2e/app.spec.ts`，首次失败原因为 store/UI 尚未具备 WebSocket、AudioWorklet、音量电平、静音 30 秒提示和 binary 上传状态。
- 新增 `frontend/src/lib/audio-frames.ts`：
  - 固定前端上传音频格式为 `{ sample_rate_hz: 16000, channels: 1, encoding: 'pcm16' }`。
  - 提供 mono 混合、线性重采样到 16 kHz、RMS 音量计算、有效音频阈值判断、little-endian PCM16 编码和 100ms 帧切分。
  - 固定帧长为 1600 samples / 3200 bytes，默认有效音频阈值为 RMS `0.015`。
- 新增 `frontend/public/audio-worklet/pcm16-processor.js`：
  - 作为浏览器 AudioWorklet processor，接收实时输入音频并把每个 render quantum 的通道样本通过 `postMessage` 交给主线程。
  - 不保存、不上传、不持久化原始音频；转换和静音过滤在主线程前端处理层完成。
- 新增 `frontend/src/lib/audio-processing.ts`：
  - 使用 `AudioContext`、`MediaStreamAudioSourceNode` 和 `AudioWorkletNode` 启动实时音频处理。
  - 将 worklet 样本推入 16 kHz mono PCM16 100ms 帧处理器，仅对超过 RMS 阈值的有效音频调用 binary frame callback。
  - 静音帧不发送；30 秒无有效音频触发 `silenceWarning` 和 `audio_silent_timeout`。
  - `stop()` 清理静音计时器、断开 source/worklet node，并关闭 `AudioContext`。
- 新增 `frontend/src/lib/meeting-websocket.ts`：
  - 默认使用 `VITE_WS_BASE_URL`，为空时从当前页面推导 `/ws`，`https:` 对应 `wss:`，`http:` 对应 `ws:`。
  - WebSocket open 后发送 `session_start` JSON，包含 `client_id`、`capture_mode`、`source_platform` 和固定 `audio_format`。
  - 收到 `session_started` 后暴露 `sessionId`、`archiveUrl` 和 `sendAudioFrame()`；`stop()` 发送 `session_stop` 并关闭连接。
  - 本步只处理 `session_started`、`quota_update`、`audio_status`、`error`、`session_closed` 等既有 schema，不修改 wire schema。
- 扩展 `frontend/src/stores/session-store.ts`：
  - 新增 `audioProcessingStatus`、`audioLevel`、`hasEffectiveAudio`、`silenceWarning`、`webSocketStatus`、`sessionId`、`archiveUrl`、`audioPipelineErrorCode`。
  - `beginCapture()` 在 Step 13 捕获成功后继续建立 WebSocket session，再启动 AudioWorklet 音频处理；测试可注入 fake WebSocket client 和 fake audio processor。
  - 匿名身份未同步时不开始捕获，返回 `identity_not_ready`。
  - `endSession()` 完整清理 audio processor、WebSocket client 和 `MediaStream` tracks。
- 更新 `frontend/src/App.tsx`：
  - 状态栏新增 WebSocket 状态、音频处理状态、音量电平、有效音频、会话编号和归档入口展示。
  - 开始按钮在匿名身份未同步、授权中、连接中、处理中或管线运行中禁用；结束按钮负责完整清理本地音频和 WebSocket session。
  - 显示 30 秒无有效音频提示；四区布局保持 Step 12 的桌面/移动响应式结构。
- 更新 `frontend/e2e/app.spec.ts`：
  - mock `getDisplayMedia`、`fetch` 匿名同步、`WebSocket`、`AudioContext` 和 `AudioWorkletNode`。
  - 覆盖有效音频上传 3200 bytes binary frame、静音不上传、授权拒绝、无 audio track 降级提示、桌面/移动无水平溢出。
- 本步未修改后端 REST API、WebSocket schema、数据库 schema、环境变量清单或部署配置。
- 本步未实现 mock STT/Qwen Provider、interim/final 文本生成、归档写入、Google STT、Qwen 或四区实时文本流。

### 验证命令与结果

| 验证项 | 命令 | 实际结果 |
|---|---|---|
| Step 14 TDD RED | `npm run test -- --run src/lib/audio-frames.test.ts src/lib/audio-processing.test.ts src/lib/meeting-websocket.test.ts src/stores/session-store.test.ts src/App.test.tsx` | 首次失败，缺少 Step 14 模块和 store/UI 状态 |
| Step 14 目标单测 GREEN | `npm run test -- --run src/lib/audio-frames.test.ts src/lib/audio-processing.test.ts src/lib/meeting-websocket.test.ts src/stores/session-store.test.ts src/App.test.tsx` | 5 个测试文件、33 个测试通过 |
| 前端 lint | `npm run lint` | 通过 |
| 前端单元测试 | `npm run test` | 10 个测试文件、55 个测试通过 |
| 前端生产构建 | `npm run build` | 通过 |
| 前端 E2E | `npm run test:e2e` | 6 个 Chromium 测试通过 |
| Markdown/代码空白检查 | `git diff --check` | 通过；仅输出 Windows LF/CRLF 工作区提示，无空白错误 |

### 后续注意

- Step 15 必须等待用户明确允许后再开始。
- Step 15 才能实现 mock STT/Qwen Provider、interim/final 文本、Provider 状态流或四区实时文本更新。
- 当前 Step 14 只保证前端把捕获到的 `MediaStream` 转换为 16 kHz mono PCM16，并仅上传超过阈值的 100ms binary frame。
- 静音帧不会发送，因此 Step 11 后端不会因静音帧把会话从 `pending_audio` 转为 `active`，也不会因此开始额度消耗。
- 自动化测试使用 fake clock 和 mock 浏览器 API 覆盖静音 30 秒、有效音频上传和静音不上传；真实会议无声 30 秒、Windows Chrome/Edge + Google Meet/Teams/Zoom/腾讯会议 Web 兼容性矩阵仍需人工验收，不能把 mock 自动化等同于真实平台验收。

## 2026-05-09 Step 15：本地 mock Provider 链路

### 本次完成

- 只推进 `memory-bank/implementation-plan.md` 的 Step 15，未开始 Step 16，未接入真实 Google STT、真实 Qwen、COS、会后归档 API/页面、搜索、复制、导出或 `usage_event` 全链路。
- 已按 TDD 先补测试并确认 RED：
  - 扩展 `backend/tests/test_websocket_sessions.py`，首次目标测试等待 mock Provider 实时消息失败，确认当时 `/ws` 激活后尚不会产生 mock STT/Qwen 输出，也不会写入 `transcript_segment`。
  - 扩展 `frontend/src/lib/meeting-websocket.test.ts`、`frontend/src/stores/session-store.test.ts`、`frontend/src/App.test.tsx` 和 `frontend/e2e/app.spec.ts`，首次失败原因为 WebSocket callbacks、store 实时文本状态和四区渲染尚不存在。
- 新增 `backend/src/meeting_mvp_backend/mock_providers.py`：
  - 定义固定、可重复的本地 mock Provider 脚本。
  - 脚本包含英文 interim、可恢复 Qwen interim warning、中文 interim、英文 final、中文 final、重点句和时间线所需元数据。
  - 输出固定文本，不引入随机内容，保证测试稳定。
- 扩展 `backend/src/meeting_mvp_backend/ws_sessions.py`：
  - `MeetingSessionRepository` 新增 `create_transcript_segment(...)` 协议方法。
  - `SQLAlchemyMeetingSessionRepository` 复用既有 `TranscriptSegment` 模型写入 final 片段，不新增数据库 migration。
  - 首个有效 binary frame 将会话激活后，启动可取消的 mock Provider task。
  - mock task 依次发送 `asr_interim`、`warning`、`translation_interim`、`segment_final`、`key_sentence_update` 和 `timeline_update`。
  - `segment_final` 发送前会写入 `transcript_segment`，sequence 从 1 开始；interim 和 warning 不入库。
  - `session_stop`、浏览器断开或 task 取消时取消 mock task，保留已写入片段，并沿用既有 Redis active session 释放和额度结算逻辑。
- 扩展 `frontend/src/lib/meeting-websocket.ts`：
  - 新增 `onAsrInterim`、`onTranslationInterim`、`onSegmentFinal`、`onKeySentenceUpdate`、`onTimelineUpdate` 和 `onWarning` callbacks。
  - 不修改 WebSocket wire schema，只消费 Step 10 已定义的服务端消息。
- 扩展 `frontend/src/stores/session-store.ts`：
  - 新增 `englishInterimText`、`translationInterimText`、`finalSegments`、`keySentenceText` 和 `timelineItems`。
  - WebSocket callbacks 会替换当前 interim、追加 final segments、更新重点句和时间线。
  - 开始新会话时清空上一场实时文本状态；`endSession()` 继续清理 processor、WebSocket 和 `MediaStream`。
- 更新 `frontend/src/App.tsx`：
  - 英文原文区显示英文 interim 与 final 英文片段。
  - 中文翻译区显示中文 interim 与 final 中文片段。
  - 当前重点句区显示最新 `key_sentence_update`。
  - 会议时间线区显示既有状态信息和 `timeline_update.items`。
- 更新 `frontend/e2e/app.spec.ts`：
  - FakeWebSocket 在收到有效 binary frame 后推送 mock 实时消息。
  - 覆盖页面四区更新，并继续验证桌面/移动无水平溢出。

### 验证命令与结果

| 验证项 | 命令 | 实际结果 |
|---|---|---|
| Step 15 后端 TDD RED | `uv run pytest tests/test_websocket_sessions.py -q` | 首次目标测试超时/失败，缺少 mock Provider 消息和 final 入库行为 |
| Step 15 后端目标 GREEN | `uv run pytest tests/test_websocket_sessions.py -q` | 9 passed |
| Step 15 前端 TDD RED | `npm run test -- --run src/lib/meeting-websocket.test.ts src/stores/session-store.test.ts src/App.test.tsx` | 3 个新增目标测试失败，缺少 callbacks、store 状态和四区渲染 |
| Step 15 前端目标 GREEN | `npm run test -- --run src/lib/meeting-websocket.test.ts src/stores/session-store.test.ts src/App.test.tsx` | 3 个测试文件、23 个测试通过 |
| 后端 Python | `uv run python --version` | Python 3.12.11 |
| 后端 Ruff | `uv run ruff check .` | 通过，`All checks passed!` |
| 后端 mypy | `uv run mypy .` | 通过，`Success: no issues found in 25 source files` |
| 后端 pytest | `uv run pytest` | 43 passed，5 integration deselected |
| 前端 lint | `npm run lint` | 通过 |
| 前端单元测试 | `npm run test` | 10 个测试文件、58 个测试通过 |
| 前端生产构建 | `npm run build` | 通过；Vite 输出 `vite:css` plugin timing warning，不影响退出码 |
| 前端 E2E | `npm run test:e2e` | 6 个 Chromium 测试通过 |
| Markdown/代码空白检查 | `git diff --check` | 通过；仅输出 Windows LF/CRLF 工作区提示，无空白错误 |

### 后续注意

- Step 16 必须等待用户明确允许后再开始。
- Step 15 mock Provider 只用于本地开发和自动化测试；不读取、不保存、不上传原始音频，不暴露任何 Provider 密钥。
- 当前“归档生成”仅指后端写入 `transcript_segment`；会后归档查询 API/页面、搜索、复制、Markdown/JSON 导出、COS 和完整 `usage_event` 链路仍属于后续步骤。
- Qwen interim warning 在本步是可恢复 mock warning，不阻塞英文 final、中文 final 或 `transcript_segment` 写入。

## 2026-05-09 Step 16：Google STT 实时英文转写历史记录

> 2026-05-10 已确认北京地区腾讯云 Lighthouse 无法稳定完成 Google Speech API gRPC/HTTP2 streaming，Step 16 生产主路径已改为 Qwen3-ASR-Flash-Realtime。以下内容保留为历史执行记录，最新架构和验证结果见后续“Qwen realtime ASR 替换”章节。

### 本次完成

- 只推进 `memory-bank/implementation-plan.md` 的 Step 16，未开始 Step 17；本步不调用 Qwen、不新增中文 interim/final 逻辑、不新增会后归档页、搜索、复制、导出、COS 或完整 `usage_event` 链路。
- 后端新增 `backend/src/meeting_mvp_backend/stt_providers.py`：
  - 定义 `StreamingSttProvider` 协议、`SttInterimEvent`、`SttFinalEvent` 和 Google STT provider。
  - 使用 `google-cloud-speech` 的 `SpeechAsyncClient.streaming_recognize()`；首包发送 recognizer 与 streaming config，后续包只发送 audio。
  - 音频配置固定为 LINEAR16、16 kHz、1 channel、`language_codes=["en-US"]`、`interim_results=True`。
  - `GOOGLE_STT_RECOGNIZER` 已是 `projects/.../recognizers/...` 时直接使用，否则由 `GOOGLE_CLOUD_PROJECT`、`GOOGLE_STT_LOCATION` 和 recognizer 名拼接。
  - Google interim 转为 `SttInterimEvent`，Google final 转为 `SttFinalEvent`；`start_ms` 使用上一条 final 的 `end_ms`，`end_ms` 来自 `result_end_offset`，缺失时回退到上一结束时间。
- WebSocket 公开协议新增服务端消息 `asr_final`：
  - 后端 `backend/src/meeting_mvp_backend/ws_messages.py` 和前端 `frontend/src/protocol/websocket-messages.ts` 均已镜像新增字段 `type`、`sequence`、`start_ms`、`end_ms`、`text`、`confidence|null`。
  - `asr_final` 只表示英文最终转写，不写入 `transcript_segment`，避免用空中文污染正式双语片段；正式双语 final 入库仍留给后续步骤。
- 后端 `backend/src/meeting_mvp_backend/ws_sessions.py` 已接入 STT provider factory：
  - 首个非空 binary frame 仍负责激活 `meeting_session` 和 Redis active session。
  - Google 路径下，首帧和后续非空 binary frame 都会转发给 STT provider。
  - STT interim 会发送 `asr_interim`，STT final 会发送 `asr_final`。
  - Google STT 异常会发送 `error(code="google_stt_error")` 并关闭会话，释放 Redis active session，关闭 provider，再发送 `session_closed`。
  - `session_stop`、浏览器断开或 WebSocket task 取消会取消 STT task 并关闭 provider。
  - `APP_ENV=local` 继续保留 Step 15 mock Provider 行为，确保没有真实 Google 凭证时本地开发和自动化测试仍可跑通。
- 后端 `backend/src/meeting_mvp_backend/main.py` 在 WebSocket orchestrator 依赖中按环境注入 provider：local 使用 mock 路径，非 local 使用 Google STT provider。
- 后端依赖已通过 `uv add google-cloud-speech` 写入 `backend/pyproject.toml` 并锁定到 `backend/uv.lock`。
- 前端消费已更新：
  - `frontend/src/lib/meeting-websocket.ts` 新增 `onAsrFinal` callback。
  - `frontend/src/stores/session-store.ts` 新增 `englishFinalSegments`，新会话开始时清空。
  - `frontend/src/App.tsx` 英文原文区渲染 `asr_interim` 和 `asr_final`；中文区仍只消费 `translation_interim` 与 `segment_final`，不伪造中文。
- 新增 `backend/tests/integration/test_google_stt_smoke.py` 作为真实 Google STT smoke hook；只有在真实 Google STT 环境变量和 `GOOGLE_STT_SMOKE_AUDIO_PATH` 指向的 16 kHz LINEAR16 英文样本同时存在时才运行。

### 验证命令与结果

| 验证项 | 命令 | 实际结果 |
|---|---|---|
| Step 16 后端 TDD RED | `uv run pytest tests/test_google_stt_provider.py tests/test_ws_messages.py tests/test_websocket_sessions.py -q` | 首次失败，缺少 `stt_providers`、`AsrFinalMessage` 和 STT 会话编排行为 |
| Step 16 后端目标 GREEN | `uv run pytest tests/test_google_stt_provider.py tests/test_ws_messages.py tests/test_websocket_sessions.py -q` | 26 passed |
| Step 16 前端目标 GREEN | `npm run test -- --run src/protocol/websocket-messages.test.ts src/lib/meeting-websocket.test.ts src/stores/session-store.test.ts src/App.test.tsx` | 4 个测试文件、34 个测试通过 |
| 后端 Python | `uv run python --version` | Python 3.12.11 |
| 后端 Ruff | `uv run ruff check .` | 通过，`All checks passed!` |
| 后端 mypy | `uv run mypy .` | 通过，`Success: no issues found in 28 source files` |
| 后端 pytest | `uv run pytest` | 51 passed，6 integration deselected |
| 前端 lint | `npm run lint` | 通过 |
| 前端单元测试 | `npm run test` | 10 个测试文件、60 个测试通过 |
| 前端生产构建 | `npm run build` | 通过 |
| 前端 E2E | `npm run test:e2e` | 6 个 Chromium 测试通过 |
| 本地 Google STT smoke hook | `pytest.main(['-o', 'addopts=', '-m', 'integration', 'tests/integration/test_google_stt_smoke.py', '-q'])` | 1 skipped，因本地未提供真实 Google STT 环境变量和测试音频 |
| Lighthouse 公开样本下载 | 下载 Google 官方公开 `brooklyn_bridge.raw`，并拼接为临时 loop 样本 | 原始样本 57,958 bytes；loop 样本 231,832 bytes；未使用真实会议音频 |
| Lighthouse Google STT smoke | 临时 Docker 容器挂载当前后端代码、Google 凭证只读路径和公开样本后运行 `test_google_stt_smoke.py` | 未通过；Google STT gRPC 返回 `ServiceUnavailable: 503 failed to connect to all addresses` |
| Lighthouse Google API 连通性 | 远端 host/container 分别检查 `storage.googleapis.com` 和 `speech.googleapis.com:443` | `storage.googleapis.com` 可访问；`speech.googleapis.com:443` host curl 超时，容器 socket 连接超时 |
| 2026-05-09 用户第二次调整网络后复测 | Lighthouse 容器内 TLS 探针与真实 Google STT streaming smoke | 容器内简单 TLS 探针到 `speech.googleapis.com:443` 成功；真实 Google STT gRPC streaming 仍失败，返回 `ServiceUnavailable: 503 failed to connect to all addresses; ... tcp handshaker shutdown` |

### 后续注意

- Step 17 必须等待用户明确允许后再开始。
- Step 16 只接入英文 Google STT 与 `asr_final`，没有新增 Qwen 调用、中文 interim 节流、中文 final 生成、会后归档查询 API/页面、COS 或导出逻辑。
- 本地默认测试不会访问真实 Google STT；真实 smoke 需要在 Lighthouse/CI 后端环境中提供现有 Google 变量和测试专用 `GOOGLE_STT_SMOKE_AUDIO_PATH`，且不得打印服务账号 JSON、API key、完整环境变量或生产 `.env` 内容。
- `asr_final` 是英文最终转写展示消息，不写数据库；后续双语 final 步骤需要继续决定何时把英文 final 与中文 final 组合写入 `transcript_segment`。
- 2026-05-09 已尝试在 Lighthouse 使用互联网公开样本完成真实 Google STT smoke；当前阻塞不是代码、样本或凭证文件存在性，而是 Google STT gRPC streaming 连接仍被网络层中断。第二次网络调整后容器内 TCP/TLS 探针可达 `speech.googleapis.com:443`，但真实 gRPC 仍返回 `tcp handshaker shutdown`，因此仍需继续修通对 Google Speech API gRPC/HTTP2 流量的出口或换用可稳定访问该 API 的运行环境。

## 2026-05-10 Step 16：Qwen realtime ASR 替换

### 本次完成

- 按用户要求将 Step 16 英文实时 ASR 主路径从 Google STT v2 streaming 替换为阿里云百炼 `qwen3-asr-flash-realtime`，未开始 Step 17。
- 后端 `backend/src/meeting_mvp_backend/stt_providers.py` 改为 Qwen realtime ASR provider：
  - 保留 `StreamingSttProvider`、`SttInterimEvent`、`SttFinalEvent` 抽象。
  - 使用 `websockets` 连接 `QWEN_ASR_BASE_URL`，并追加 `?model=QWEN_ASR_MODEL`。
  - 首包发送 `session.update`，配置 16 kHz、mono、`pcm`、可选语言；后续 PCM16 binary frame Base64 后发送 `input_audio_buffer.append`。
  - Qwen interim 映射为 `asr_interim`，completed/final 映射为 `asr_final`。
  - Qwen 缺少时间戳时，用累计已发送音频字节数估算 `start_ms/end_ms`，保持时间范围单调递增。
  - Qwen error 映射为 `RuntimeError`，由 WebSocket 编排层转为 `error(code="qwen_asr_error")`。
  - 因前端 Step 14 会过滤静音 frame，provider 在音频输入短暂停顿后补发短静音尾帧，帮助 Qwen server VAD 产出 final。
  - `close()` 先发送 `session.finish` 并等待 final/`session.finished`，再关闭 realtime WebSocket，避免截断最终转写。
- 后端配置更新：
  - `backend/src/meeting_mvp_backend/config.py` 新增 `ASR_PROVIDER=qwen_realtime`、`QWEN_ASR_MODEL`、`QWEN_ASR_BASE_URL`、`QWEN_ASR_SAMPLE_RATE_HZ`、`QWEN_ASR_AUDIO_FORMAT`、`QWEN_ASR_LANGUAGE`、`SESSION_RESUME_GRACE_SECONDS`。
  - `GOOGLE_*` 不再是 production 必填；`google-cloud-speech` 从 `backend/pyproject.toml` / `backend/uv.lock` 移除，新增 `websockets>=16.0`。
  - `backend/.env.example`、`deploy/.env.example` 和 `deploy/docker-compose.yml` 改为 Qwen ASR 配置；Compose 移除 Google 服务账号只读挂载。
- WebSocket 协议更新：
  - 保留 `asr_interim` / `asr_final`，`asr_final` 仍只用于英文展示，不写 `transcript_segment`。
  - 新增 client `session_resume` 和 server `session_resumed`。
  - 后端在 `SESSION_RESUME_GRACE_SECONDS=30` 内允许同一 `client_id + session_id + archive_token` 恢复同一业务 session；本步只恢复浏览器到后端 `/ws`，不补传断线期间音频，不做 Provider 到 Qwen 的自动重连补偿。
  - 断线恢复记录会先写入内存 registry，再清理旧 provider，避免浏览器快速重连时发生 `session_resume_failed` race。
- 前端更新：
  - `frontend/src/protocol/websocket-messages.ts` 新增 `session_resume` / `session_resumed` schema。
  - `frontend/src/lib/meeting-websocket.ts` 在非主动关闭时自动重连并发送 `session_resume`，恢复后继续复用同一 client 发送音频 frame。
  - `frontend/src/stores/session-store.ts` 保存并清理 `archiveToken`，继续追加 `englishFinalSegments`。
- 真实 Qwen smoke：
  - 删除旧 `backend/tests/integration/test_google_stt_smoke.py`，新增 `backend/tests/integration/test_qwen_realtime_asr_smoke.py`。
  - gated smoke 默认跳过；只有设置 `RUN_QWEN_ASR_SMOKE=1`、真实 Qwen ASR 配置和测试音频 manifest 时才访问真实服务。
  - smoke 覆盖 `/ws` 建连、首个 interim 延迟、首个 final 延迟、30 秒/3 分钟/10 分钟连续流稳定性、英文会议专有名词错误数、自动标点、中英混杂稳定性和断线恢复。
  - 新增 `scripts/prepare-qwen-asr-smoke-audio.ps1`，下载公开 `brooklyn_bridge.raw` 并生成 30 秒、3 分钟、10 分钟 loop 样本和 smoke manifest；脚本不包含密钥。
- 文档同步：
  - 更新 `meeting-prd.md`、`memory-bank/implementation-plan.md`、`memory-bank/architecture.md`、`memory-bank/environment-variables.md`、`memory-bank/set-up-env.md`、`memory-bank/tech-stack.md`、`memory-bank/2026-04-24-meeting-mvp-design.md`、`deploy/README.md` 和 `AGENTS.md`，统一将 M1-A 英文 ASR 主路径改为 Qwen realtime ASR，并记录 Google STT 作为历史失败背景/后续备用候选。

### 验证命令与结果

| 验证项 | 命令 | 实际结果 |
|---|---|---|
| Step 16 后端目标 GREEN | `uv run pytest tests/test_qwen_realtime_asr_provider.py tests/test_ws_messages.py tests/test_config.py tests/test_websocket_sessions.py -q` | 37 passed |
| Step 16 前端目标 GREEN | `npm run test -- --run src/protocol/websocket-messages.test.ts src/lib/meeting-websocket.test.ts src/stores/session-store.test.ts` | 3 个测试文件、29 个测试通过 |
| Qwen smoke hook 本地 gated 检查 | `uv run pytest tests/integration/test_qwen_realtime_asr_smoke.py -m integration -q` | 6 skipped，因未设置 `RUN_QWEN_ASR_SMOKE=1` 和真实 smoke 环境 |
| 真实 Qwen latency/resume smoke | 使用 `D:\meeting_mvp_secrets\provider.env`、`RUN_QWEN_ASR_SMOKE=1` 和公开样本 manifest 运行 `test_qwen_realtime_asr_smoke_ws_latency_and_resume` | 1 passed；覆盖 `/ws` 建连、首个 interim、首个 final 和断线恢复 |
| 真实 Qwen 完整 smoke | 使用同一 provider env 和公开样本 manifest 运行 `tests/integration/test_qwen_realtime_asr_smoke.py` | 5 passed，1 skipped，耗时 13:51；30 秒/3 分钟/10 分钟连续流、术语、自动标点通过；中英混杂因 manifest 未配置样本跳过 |
| 后端 Ruff | `uv run ruff check .` | 通过，`All checks passed!` |
| 后端 mypy | `uv run mypy .` | 通过，`Success: no issues found in 28 source files` |
| 后端 pytest | `uv run pytest` | 58 passed，11 integration deselected |
| 前端 lint | `npm run lint` | 通过 |
| 前端单元测试 | `npm run test` | 10 个测试文件、64 个测试通过 |
| 前端生产构建 | `npm run build` | 通过；仍有 Vite `vite:css` plugin timing warning，不影响退出码 |
| 前端 E2E | `npm run test:e2e` | 6 个 Chromium 测试通过 |
| Markdown/代码空白检查 | `git diff --check` | 通过；仅输出 Windows LF/CRLF 工作区提示，无空白错误 |
| Step 17 边界检查 | 搜索新增 Qwen 文本翻译、中文 interim/final、导出/COS/归档页相关实现 | 未发现新增 Step 17 生产逻辑；仅保留既有 mock、配置和 `segment_final` 协议/测试 |

### 后续注意

- Step 17 必须等待用户明确允许后再开始；当前只提供英文 ASR 的 `asr_interim` / `asr_final` 和浏览器断线恢复。
- `asr_final` 仍不写数据库；后续 Step 18 需要决定如何把英文 final 与中文 final 组合写入 `transcript_segment`。
- `session_resume` 只保证浏览器重连后继续同一业务 session，不补传断线期间音频；Provider 到 Qwen 的自动重连和音频补偿可在后续稳定性增强中单独设计。
- 真实 Qwen smoke 不得打印 `QWEN_API_KEY`、完整生产 `.env` 或任何密钥值；测试音频 manifest 只记录测试文件路径和质量断言。
- 当前公开 manifest 未包含中英混杂样本；后续补充真实中英混杂音频后，`mixed` smoke 用例会从 skipped 变为实际验收。

## 2026-05-13 Step 17：中文 interim

### 本次完成

- 只推进 `memory-bank/implementation-plan.md` 的 Step 17，未开始 Step 18；本步不做中文 final、不写 `transcript_segment`、不新增归档 API/页面、搜索、复制、导出、COS 或完整 `usage_event` 链路。
- 已重新阅读 `memory-bank/` 全部 7 份文档，并根据 `progress.md` 确认最新完成项为 Step 16 Qwen realtime ASR 替换。
- 已按 TDD 先补后端 Step 17 目标测试并确认 RED：
  - 新增 `backend/tests/test_translation_providers.py`，首次失败原因为缺少 `meeting_mvp_backend.translation_providers`。
  - 扩展 `backend/tests/test_websocket_sessions.py`，首次随目标集一起失败，确认 WebSocket 编排尚未支持真实 interim 翻译 provider。
  - 扩展 `frontend/src/App.test.tsx` 检查中文 interim/final 样式区分；该测试首次即通过，说明 Step 15/16 UI 已满足本步前端样式边界。
- 新增 `backend/src/meeting_mvp_backend/translation_providers.py`：
  - 定义 `InterimTranslationProvider` 协议、`InterimTranslationError` 和 `QwenInterimTranslationProvider`。
  - 使用既有 `QWEN_API_KEY`、`QWEN_BASE_URL`、`QWEN_INTERIM_MODEL` 调用 Qwen OpenAI-compatible `/chat/completions`。
  - Prompt 固定要求简洁自然中文、不扩写、不添加原文没有的信息、只输出中文译文。
  - HTTP 错误、网络错误、非法 JSON、空内容和缺失配置统一包装为可恢复 `InterimTranslationError`；错误信息只包含配置名或错误类型，不输出密钥值。
- 扩展 `backend/src/meeting_mvp_backend/ws_sessions.py`：
  - `SttInterimEvent` 仍立即发送 `asr_interim`，随后异步调度中文 `translation_interim`。
  - 默认节流常量为 `INTERIM_TRANSLATION_MIN_INTERVAL_SECONDS = 1.5`；空文本跳过、重复文本跳过、同一时间最多一个翻译请求，请求中收到的新 interim 只保留最新待处理文本。
  - Qwen interim 失败只记录脱敏 `qwen_interim_translation_failed` warning，不发送 WebSocket `error`，不关闭会话，不影响英文 ASR 或 `asr_final`。
  - `session_stop`、浏览器断开、resume pause 和错误关闭都会取消 pending translation task 并关闭 translation provider。
- 扩展 `backend/src/meeting_mvp_backend/main.py`：
  - `APP_ENV=local` 继续保留 Step 15 mock Provider 行为。
  - 非 local 且 `QWEN_INTERIM_ENABLED=true` 时注入真实 Qwen interim translation provider factory。
  - 未新增环境变量、数据库 migration 或 WebSocket wire schema。
- 新增 `backend/tests/integration/test_qwen_interim_translation_smoke.py`：
  - gated smoke 默认跳过；只有 `RUN_QWEN_INTERIM_SMOKE=1` 且提供真实 Qwen 文本模型环境变量时才访问真实服务。
  - smoke 只断言返回非空中文文本，不打印 Qwen API key、完整 env 或模型响应正文。
- Lighthouse 真实 Qwen interim smoke：
  - 远端 `/opt/meeting_mvp/app` 不是 Git 工作树；为运行容器 smoke，已同步本地后端包目录到远端 app 目录并用 `deploy/.env.example` 重建 backend 镜像。
  - 直接使用 `.env.production` 做 Compose build 当时会因缺少 `POSTGRES_USER` 被 Compose 插值拒绝；该远端配置缺口已在 Step 18 前后补齐到可完成 backend build 的状态，正式部署前仍需确认变量均为真实生产值。
  - 容器运行时通过 `--env-file .env.production` 注入 Qwen 配置，执行脱敏 smoke 脚本，结果输出 `qwen-interim-smoke-passed`；临时 `/tmp/qwen_interim_smoke.py` 已删除。

### 验证命令与结果

| 验证项 | 命令 | 实际结果 |
|---|---|---|
| Step 17 后端 RED | `uv run pytest tests/test_translation_providers.py tests/test_websocket_sessions.py -q` | 首次失败：`ModuleNotFoundError: No module named 'meeting_mvp_backend.translation_providers'` |
| Step 17 前端样式测试 | `npm run test -- --run src/App.test.tsx` | 10 passed；新增样式测试首次通过，确认现有 UI 已区分 interim/final |
| Step 17 后端目标 GREEN | `uv run pytest tests/test_translation_providers.py tests/test_websocket_sessions.py -q` | 24 passed |
| Qwen interim smoke hook 本地 gated 检查 | `uv run pytest tests/integration/test_qwen_interim_translation_smoke.py -m integration -q` | 1 skipped，因未设置 `RUN_QWEN_INTERIM_SMOKE=1` |
| 后端 Ruff | `uv run ruff check .` | 通过，`All checks passed!` |
| 后端 mypy | `uv run mypy .` | 通过，`Success: no issues found in 31 source files` |
| 后端 pytest | `uv run pytest` | 69 passed，12 integration deselected |
| 前端 lint | `npm run lint` | 通过 |
| 前端单元测试 | `npm run test` | 10 个测试文件、65 个测试通过 |
| 前端生产构建 | `npm run build` | 通过；仍有 Vite `vite:css` plugin timing warning，不影响退出码 |
| 前端 E2E | `npm run test:e2e` | 6 个 Chromium 测试通过 |
| Markdown/代码空白检查 | `git diff --check` | 通过；仅输出 Windows LF/CRLF 工作区提示，无空白错误 |
| Lighthouse backend build | `docker compose --env-file deploy/.env.example -f deploy/docker-compose.yml build backend` | 通过，生成 `meeting_mvp-backend:latest` |
| Lighthouse Qwen interim container smoke | `docker run --rm --env-file .env.production ... meeting_mvp-backend:latest python /tmp/qwen_interim_smoke.py` | 通过，输出 `qwen-interim-smoke-passed` |

### 后续注意

- 截至 Step 17 完成时，Step 18 必须等待用户明确允许后再开始；当时没有中文 final、没有 final 上下文窗口、没有 `QWEN_FINAL_MODEL` 调用，也没有正式双语片段入库。上述能力已在后续 Step 18 补齐。
- `translation_interim` 仍是临时 UI 消息，只替换当前中文临时理解，不进入 PostgreSQL。
- Qwen interim provider 失败是可恢复降级：英文 `asr_interim` / `asr_final` 主链路继续运行。
- 远端 `.env.production` 曾缺少 Compose 所需数据库变量名；Step 18 前后已补齐到可完成 backend build 的状态，正式部署前仍需确认变量均为真实生产值，不能用 `deploy/.env.example` 占位值初始化正式数据目录。

## 2026-05-13 Step 18：中文 final

### 本次完成

- 只推进 `memory-bank/implementation-plan.md` 的 Step 18，未开始 Step 19；本步不新增归档 API/页面、搜索、复制、导出、COS、完整 `usage_event`、重点句或时间线增强。
- 已在 Step 17 基础上扩展 `backend/src/meeting_mvp_backend/translation_providers.py`：
  - 新增 `FinalTranslationProvider` 协议、`FinalTranslationRequest`、`FinalTranslationContextSegment`、`FinalTranslationError` 和 `QwenFinalTranslationProvider`。
  - 使用既有 `QWEN_API_KEY`、`QWEN_BASE_URL`、`QWEN_FINAL_MODEL` 调用 Qwen OpenAI-compatible `/chat/completions`，不新增环境变量。
  - final prompt 固定为正式会议中文翻译：准确自然、适合中国职场归档阅读，保留人名/产品名/数字/日期/业务术语，只输出当前片段中文译文。
  - final 请求显式设置 `enable_thinking=false`、`max_tokens=512`、`temperature=0.1`，并将默认请求超时提高到 60 秒；真实 smoke 首次 20 秒和 60 秒超时后，通过关闭 thinking 后恢复通过。
  - HTTP 错误、网络错误、非法 JSON、空内容和缺失配置统一包装为可恢复 `FinalTranslationError`，错误信息只包含配置名、HTTP 状态或错误类型，不输出密钥。
- 扩展 `backend/src/meeting_mvp_backend/ws_sessions.py`：
  - `SttFinalEvent` 仍立即发送英文 `asr_final`，保证英文 final 实时可见。
  - 配置 final provider 时，按 `sequence` 排队翻译英文 final；成功后写入 `transcript_segment(translation_status=completed)` 并发送既有 `segment_final`。
  - 成功 final 会进入内存上下文窗口，后续请求最多携带最近 5 个已成功双语 final 片段，供术语和指代一致性使用。
  - Qwen final 失败时写入英文 final、空中文 final、`translation_status=failed` 和 `asr_confidence`，发送可恢复 `warning(code="qwen_final_translation_failed")`，不关闭 WebSocket，不阻塞后续 ASR/final。
  - `session_stop`、浏览器断开、resume pause 和错误关闭会取消 in-flight final translation task、关闭 final provider，并把当前/排队未完成 final 片段按 failed 状态归档，供后续 Step 25 重试。
  - 扩展 SQLAlchemy 仓储写入 `translation_status` 和 `asr_confidence`；现有数据库模型已有字段，因此未新增 migration。
- 扩展 `backend/src/meeting_mvp_backend/main.py`：
  - `APP_ENV=local` 保持 Step 15 mock provider 行为。
  - 非 local WebSocket 会话注入真实 Qwen final provider factory；Qwen interim provider 仍由 `QWEN_INTERIM_ENABLED` 控制。
- 前端只做必要状态修正：
  - `frontend/src/stores/session-store.ts` 在收到匹配 `sequence` 的 `segment_final` 后移除对应 `englishFinalSegments` 临时英文 final，避免英文区重复展示同一 final。
  - `frontend/e2e/app.spec.ts` 同步断言：正式双语 `segment_final` 到达后，匹配的英文 `asr_final` 不再重复保留。
  - WebSocket wire schema 未变化，仍复用既有 `asr_final`、`translation_interim` 和 `segment_final`。
- 新增 `backend/tests/integration/test_qwen_final_translation_smoke.py`：
  - gated smoke 默认跳过；只有 `RUN_QWEN_FINAL_SMOKE=1` 且提供真实 Qwen 文本配置时才访问真实服务。
  - smoke 使用上下文样例断言返回非空中文、不泄漏英文原句前缀，并保留 `Acme` 术语；不打印 API key、完整 env 或模型响应正文。
- Lighthouse 真实 Qwen final smoke：
  - 已同步 Step 18 相关文件到远端 `/opt/meeting_mvp/app`；该目录不是 Git 工作树。
  - 使用远端 `.env.production` 完成 `docker compose --env-file .env.production -f deploy/docker-compose.yml build backend`，说明先前 Compose 所需数据库/站点变量缺口已补齐；本次未输出任何密钥值。
  - 首次 smoke 因 Qwen final 读超时失败，随后通过 `enable_thinking=false`、`max_tokens=512` 和 60 秒超时调整后，后端容器内真实 Qwen final smoke 通过。

### 验证命令与结果

| 验证项 | 命令 | 实际结果 |
|---|---|---|
| Step 18 后端 RED | `uv run pytest tests/test_translation_providers.py tests/test_websocket_sessions.py -q` | 首次失败：缺少 `FinalTranslationRequest`、`FinalTranslationContextSegment` 等 final provider 类型 |
| Step 18 前端 RED | `npm run test -- --run src/stores/session-store.test.ts` | 1 failed，`segment_final` 到达后仍保留匹配 `asr_final` |
| Step 18 后端目标 GREEN | `uv run pytest tests/test_translation_providers.py tests/test_websocket_sessions.py -q` | 35 passed |
| Step 18 前端目标 GREEN | `npm run test -- --run src/stores/session-store.test.ts` | 8 passed |
| Qwen final smoke hook 本地 gated 检查 | `uv run pytest tests/integration/test_qwen_final_translation_smoke.py -m integration -q` | 1 skipped，因未设置 `RUN_QWEN_FINAL_SMOKE=1` |
| 后端 Ruff | `uv run ruff check .` | 通过，`All checks passed!` |
| 后端 mypy | `uv run mypy .` | 通过，`Success: no issues found in 32 source files` |
| 后端 pytest | `uv run pytest` | 80 passed，13 integration deselected |
| 前端 lint | `npm run lint` | 通过 |
| 前端单元测试 | `npm run test` | 10 个测试文件、65 个测试通过 |
| 前端生产构建 | `npm run build` | 通过 |
| 前端 E2E 首次完整验证 | `npm run test:e2e` | 首次 1 failed，旧断言仍期待已去重的英文 `asr_final`；更新断言后通过 |
| 前端 E2E 最终验证 | `npm run test:e2e` | 6 个 Chromium 测试通过 |
| Markdown/代码空白检查 | `git diff --check` | 通过；仅输出 Windows LF/CRLF 工作区提示，无空白错误 |
| Lighthouse backend build | `docker compose --env-file .env.production -f deploy/docker-compose.yml build backend` | 通过，生成 `meeting_mvp-backend:latest` |
| Lighthouse Qwen final container smoke 首次 | `docker compose --env-file .env.production -f deploy/docker-compose.yml run --rm --no-deps -e RUN_QWEN_FINAL_SMOKE=1 backend uv run pytest -o addopts= -m integration tests/integration/test_qwen_final_translation_smoke.py -q` | 先后因 `ReadTimeout` 失败；无密钥输出 |
| Lighthouse Qwen final container smoke 最终 | 同上 | 通过，`1 passed in 3.18s` |

### 后续注意

- Step 19 必须等待用户明确允许后再开始；当前只复用既有前端消费链路，不新增四区实时 UI 功能。
- `translation_interim` 仍不入库；正式归档只来自英文 final + 中文 final 的 `transcript_segment`。
- Qwen final 失败片段当前只保存 `translation_status=failed` 和空中文 final，自动/手动重试仍属于 Step 25。
- 本步没有新增公开 REST API、数据库 migration、COS、搜索/复制/导出或完整 `usage_event` 链路。

## 2026-05-13 Step 19：四区实时 UI 更新

### 本次完成

- 只推进 `memory-bank/implementation-plan.md` 的 Step 19，未开始 Step 20；本步不新增异常/降级提示体系，不扩展 Provider/WebSocket 错误展示，不做导出失败、预算保险丝或 Step 20 相关场景。
- 已按确认边界执行：当前重点句区和会议时间线区只消费显式 `key_sentence_update` / `timeline_update`，不从 `segment_final` 派生基础重点句或时间线，避免抢 Step 26/27。
- 已按 TDD 先补前端目标测试并确认 RED：
  - `frontend/src/stores/session-store.test.ts` 新增重复 `segment_final` 场景，首次失败为正式双语 final 被重复追加。
  - `frontend/src/lib/meeting-websocket.test.ts` 新增四区 callback 抛错隔离场景，首次失败为 `onAsrInterim` 抛错会冒泡并打断消息分发。
  - `frontend/src/App.test.tsx` 新增四个实时区 `aria-live="polite"` 断言，首次失败为实时区缺少 live region 标记。
- 更新 `frontend/src/stores/session-store.ts`：
  - `asr_interim` / `translation_interim` 继续作为可替换状态。
  - `asr_final` 继续追加到临时英文 final 列表。
  - `segment_final` 按 `segment_id` 或 `sequence` 做幂等保护；重复消息不再重复追加正式双语片段，同时仍按 `sequence` 移除匹配临时英文 final。
  - `timeline_update.items` 继续按服务端权威快照替换 `timelineItems`，不在前端自行推导或补节点。
- 更新 `frontend/src/lib/meeting-websocket.ts`：
  - 为四区实时消息 callbacks 增加隔离分发：`asr_interim`、`asr_final`、`translation_interim`、`segment_final`、`key_sentence_update`、`timeline_update` 的某个 UI/store callback 抛错时，不把 WebSocket 标记为失败，也不阻塞后续工作区消息。
  - `session_started`、`session_resumed`、`error`、`session_closed` 控制流保持不变。
- 更新 `frontend/src/App.tsx`：
  - 英文原文区、中文翻译区、当前重点句区、会议时间线区增加 `aria-live="polite"`，补强实时更新的可访问语义。
  - 四区布局、样式、空状态和消息来源保持 Step 18 后的既有边界。
- 更新 `frontend/e2e/app.spec.ts`：
  - Fake WebSocket 重复推送同一个 `segment_final`，验证真实页面只显示一次正式英文 final 和一次正式中文 final。
  - 继续覆盖 `asr_interim`、`translation_interim`、`segment_final`、`key_sentence_update`、`timeline_update` 驱动四区独立更新。

### 验证命令与结果

| 验证项 | 命令 | 实际结果 |
|---|---|---|
| Step 19 前端 RED | `npm run test -- --run src/stores/session-store.test.ts src/lib/meeting-websocket.test.ts src/App.test.tsx` | 首次 3 failed：重复 `segment_final`、callback 抛错冒泡、缺少 `aria-live` |
| Step 19 前端目标 GREEN | 同上 | 3 个测试文件、27 个测试通过 |
| 后端 Ruff | `uv run ruff check .` | 通过，`All checks passed!` |
| 后端 mypy | `uv run mypy .` | 通过，`Success: no issues found in 32 source files` |
| 后端 pytest | `uv run pytest` | 80 passed，13 integration deselected |
| 前端 lint | `npm run lint` | 通过 |
| 前端单元测试 | `npm run test` | 10 个测试文件、67 个测试通过 |
| 前端生产构建 | `npm run build` | 通过 |
| 前端 E2E | `npm run test:e2e` | 6 个 Chromium 测试通过 |
| Markdown/代码空白检查 | `git diff --check` | 通过；仅输出 Windows LF/CRLF 工作区提示，无空白错误 |

### 后续注意

- Step 20 必须等待用户明确允许后再开始；当前没有新增异常与降级提示体系。
- 当前重点句仍只来自 `key_sentence_update`；会议时间线仍只来自 `timeline_update.items`，不由前端根据 final 自动派生。
- 本步没有新增公开 REST API、WebSocket wire schema、数据库 migration、Qwen/COS 调用、会后归档 API/页面、搜索、复制、导出或完整 `usage_event` 链路。

## 2026-05-14 Step 20：F16 异常与降级提示

### 本次完成

- 只推进 `memory-bank/implementation-plan.md` 的 Step 20，未开始 Step 21；本步不写 `usage_event`，不做成本埋点或看板，不新增归档 API/页面、COS、搜索、复制或真实导出流程。
- 新增 `frontend/src/lib/session-notices.ts`：
  - 统一把捕获失败、无音频轨道、30 秒静音、WebSocket `warning`、WebSocket `error` 和 `session_closed.reason` 映射为中文用户提示。
  - 提示模型包含 `code`、`severity`、`title`、`message` 和 `action`，区分可恢复 warning/status 与不可继续 error/alert。
  - 覆盖 `permission_denied`、`no_audio_track`、`not_supported`、`audio_silent_timeout`、`daily_quota_exhausted`、`active_session_limit_reached`、`budget_fuse_triggered`、`qwen_asr_error`、`qwen_interim_translation_failed`、`qwen_final_translation_failed`、`session_resume_failed`、`websocket_failed`、`export_failed` 等固定 code。
  - 腾讯会议 Web 标签页无音频轨道时，明确提示切换到系统音频模式后重新捕获。
- 更新 `frontend/src/lib/meeting-websocket.ts`：
  - 新增 `MeetingWebSocketError`，保留服务端 `error.code` 和原始 server message，供 store 映射为精确用户提示。
  - `warning` 继续作为可恢复消息分发，不触发 WebSocket 失败控制流。
- 更新 `frontend/src/stores/session-store.ts`：
  - 新增 `activeNotice` 和 `lastClosedReason`。
  - 捕获授权拒绝、无音轨、浏览器不支持、音频处理失败、30 秒无有效音频、provider warning、服务端 error 和关闭原因均进入同一提示模型。
  - `onWarning` 只更新提示，不清空四区内容，不停止会话。
  - `onError` 会停止本地音频处理和媒体流，保留已收到的 `finalSegments`、`englishFinalSegments`、`archiveUrl` 和 `sessionId`。
  - 用户主动停止 `session_closed(reason="user_stopped")` 不显示错误提示。
- 更新 `frontend/src/App.tsx`：
  - 在状态栏下方新增可访问提示区域，warning/info 使用 `role="status"`，不可继续错误使用 `role="alert"`。
  - 异常提示不覆盖英文/中文 final 内容，四区工作台仍保持可见。
- 后端只做 Step 20 必要补强：
  - `backend/src/meeting_mvp_backend/ws_sessions.py` 在 Qwen interim 翻译失败时发送 `warning(code="qwen_interim_translation_failed")`，不关闭 WebSocket，不阻塞英文 ASR 或 final。
  - 保持 Qwen final 失败已有 `warning(code="qwen_final_translation_failed")`；Qwen ASR、额度和预算拒绝仍走 `error` + `session_closed`。
- 扩展测试：
  - 后端 WebSocket 测试覆盖 Qwen interim warning、每日额度耗尽、预算保险丝拒绝。
  - 前端新增提示映射单元测试，并扩展 WebSocket client、store、App 和 E2E，覆盖 provider warning、预算保险丝、断线恢复失败、授权拒绝和腾讯会议无音频降级。
- 本次没有修改 WebSocket wire schema，没有新增公开 REST API、数据库 migration、环境变量或 Provider 密钥暴露。

### 验证命令与结果

| 验证项 | 命令 | 实际结果 |
|---|---|---|
| Step 20 前端 RED | `npm run test -- src/lib/session-notices.test.ts src/lib/meeting-websocket.test.ts src/stores/session-store.test.ts src/App.test.tsx` | 首次失败：缺少 `session-notices`、`MeetingWebSocketError`、`activeNotice` 和 UI 提示区域 |
| Step 20 后端 RED | `uv run pytest tests/test_websocket_sessions.py -q` | 新增 interim warning 场景首次失败，确认后端未发送 `qwen_interim_translation_failed` warning |
| Step 20 后端目标 GREEN | `uv run pytest tests/test_websocket_sessions.py -q` | 24 passed |
| Step 20 前端目标 GREEN | `npm run test -- src/lib/session-notices.test.ts src/lib/meeting-websocket.test.ts src/stores/session-store.test.ts src/App.test.tsx` | 4 个测试文件、40 个测试通过 |
| 后端 Ruff | `uv run ruff check .` | 通过，`All checks passed!` |
| 后端 mypy | `uv run mypy .` | 通过，`Success: no issues found in 32 source files` |
| 后端 pytest | `uv run pytest` | 83 passed，13 integration deselected |
| 前端 lint | `npm run lint` | 通过 |
| 前端单元测试 | `npm run test` | 11 个测试文件、80 个测试通过 |
| 前端生产构建 | `npm run build` | 通过 |
| 前端 E2E | `npm run test:e2e` | 9 个 Chromium 测试通过 |
| Markdown/代码空白检查 | `git diff --check` | 通过；仅输出 Windows LF/CRLF 工作区提示，无空白错误 |

### 后续注意

- Step 21 必须等待用户明确允许后再开始；当前没有写入 `usage_event`，也没有新增成本埋点或看板。
- `export_failed` 当前只是前端提示映射预留，未实现真实导出流程。
- 已归档内容“不丢失”在本步体现为前端异常状态不清空已收到 final、归档入口和会话标识；后端仍保持已入库片段。
- Playwright E2E 使用 `npm run preview` 服务 `dist`，改动 UI 后需要先运行 `npm run build`，否则可能复用旧构建产物。

## 2026-05-15 Step 21：usage_event 埋点基础

### 本次完成

- 只推进 `memory-bank/implementation-plan.md` 的 Step 21，未开始 Step 22；本步不新增会后归档 API/页面、搜索、复制、导出、COS、成本看板、WebSocket wire schema、数据库 migration 或前端公开埋点 API。
- 新增 `backend/src/meeting_mvp_backend/usage_events.py`：
  - 定义 Step 21 事件 allowlist：`client_created`、`quota_checked`、`capture_started`、`capture_failed`、`audio_detected`、`session_started`、`asr_interim_received`、`asr_final_received`、`translation_interim_requested`、`translation_final_completed`、`segment_archived`、`archive_viewed`、`provider_error`、`quota_exhausted`、`budget_fuse_triggered`、`session_closed`。
  - 新增 `UsageEventRecord`、`UsageEventRecorder` 协议、`SQLAlchemyUsageEventRecorder` 和 `record_usage_event_best_effort()`。
  - 新增 payload 安全校验，拒绝二进制音频、raw audio、PCM frame、API key、secret、token、password、private key、credential 等字段进入 `usage_event.payload`。
- 接入匿名用户初始化：
  - `AnonymousClientService` 支持注入 usage event recorder。
  - 新匿名用户创建并提交成功后记录 `client_created`。
  - payload 只记录 `daily_free_seconds`、`ip_hash_present`、`user_agent_hash_present` 等脱敏元数据，不保存明文 IP、User-Agent 或 hash 值本身。
- 接入 WebSocket 会话编排：
  - `session_start` 已初始化匿名用户后记录 `capture_started`，额度结果记录 `quota_checked`。
  - 每日额度耗尽和预算保险丝分别记录 `quota_exhausted` / `budget_fuse_triggered`，仍沿用既有 `error` + `session_closed` 控制流。
  - 成功创建 pending session 后记录 `session_started`，payload 不包含 `archive_token` 或 `archive_url`。
  - 首个有效 binary audio frame 激活会话时记录 `audio_detected`。
  - STT interim/final、interim 翻译请求、final 翻译完成、segment 归档、Provider 错误、session 关闭均写入对应 usage event；payload 只包含长度、状态、序号、时间戳、错误类型等元数据，不保存英文原文、中文译文、原始音频或密钥。
  - local mock Provider 路径同样记录 ASR、翻译、Provider warning 和 segment 归档事件，便于本地端到端漏斗验证。
- `archive_viewed` 与 `capture_failed` 仅在 Step 21 中完成事件类型和安全写入能力；浏览器本地捕获失败的前端上报和真实归档查看触发点留给后续明确步骤，避免提前进入 Step 22。

### 验证命令与结果

| 验证项 | 命令 | 实际结果 |
|---|---|---|
| Step 21 usage_events/匿名 RED | `uv run pytest tests/test_usage_events.py tests/test_anonymous_clients_service.py -q` | 首次 2 errors：缺少 `meeting_mvp_backend.usage_events` |
| Step 21 WebSocket RED | `uv run pytest tests/test_websocket_sessions.py -q` | 首次 29 failed：`WebSocketSessionOrchestrator` 尚不接受 `usage_event_recorder` |
| Step 21 目标 GREEN | `uv run pytest tests/test_websocket_sessions.py tests/test_usage_events.py tests/test_anonymous_clients_service.py -q` | 41 passed |
| 后端 Ruff | `uv run ruff check .` | 通过，`All checks passed!` |
| 后端 mypy | `uv run mypy src tests` | 通过，`Success: no issues found in 33 source files` |
| 后端 pytest | `uv run pytest` | 100 passed，13 integration deselected |
| 前端 lint | `npm run lint` | 通过 |
| 前端单元测试 | `npm run test` | 11 个测试文件、80 个测试通过 |
| 前端生产构建 | `npm run build` | 通过 |
| 前端 E2E | `npm run test:e2e` | 9 个 Chromium 测试通过 |

### 后续注意

- Step 21 结束时尚未实现会后归档 API/页面；Step 22 已补齐基础归档 API/页面与真实 `archive_viewed` 触发点。
- Step 21 没有新增前端埋点 API，因此浏览器本地授权拒绝、无音轨等 `capture_failed` 暂不由前端上报；如后续需要统计这些本地失败，应单独设计安全 allowlist API 或复用后续归档/会话接口。
- `usage_event` 是观测数据，写入失败只记录脱敏 warning，不中断匿名初始化或 WebSocket 主流程。
- 当前事件 payload 设计刻意不存原文、译文、音频、明文 token、明文 IP/User-Agent 或任何 Provider 密钥；后续新增事件必须继续复用 `usage_events` 的安全校验。

## 2026-05-16 Step 22：基础双语归档页/API

### 本次完成

- 只推进 `memory-bank/implementation-plan.md` 的 Step 22，未开始 Step 23；本步不新增数据库 migration、搜索、复制、Markdown/JSON 导出、COS、成本看板或归档增强功能。
- 新增 `backend/src/meeting_mvp_backend/archive_tokens.py`：
  - 将 `hash_archive_token()` 和 `build_archive_url()` 从 WebSocket 编排中抽为共享模块。
  - `ws_sessions.py` 改为从该模块导入并显式 re-export，保持既有建会返回 `archive_token` / `archive_url` 行为和测试入口兼容。
- 新增 `backend/src/meeting_mvp_backend/archives.py`：
  - 定义归档响应 Pydantic model、repository protocol、SQLAlchemy repository、`ArchiveService` 和 `ArchiveAccessDenied`。
  - 复用 `meeting_session`、`transcript_segment` 和 `usage_event` 表，不新增 migration。
  - 使用 `hash_archive_token(token)` 与 `hmac.compare_digest()` 校验 archive token hash；session 不存在、token 错误和归档过期统一隐藏为 404。
  - 按 `sequence` 升序返回 final 片段；响应包含 session 元数据和双语 final 片段，不返回明文 token 或 token hash。
- `backend/src/meeting_mvp_backend/main.py` 新增 `GET /api/archives/{session_id}?token=...`：
  - 缺少或空 `token` 返回 401。
  - session 不存在、错误 token、归档过期返回 404。
  - 缺少 `DATABASE_URL` 返回 503。
- 归档 `end_reason` 派生规则已落地：
  - 优先读取最新 `usage_event(event_type=session_closed).payload.reason`。
  - 缺失时 fallback 到 `meeting_session.status.value`。
- 成功查看归档后 best-effort 写入 `archive_viewed`：
  - payload 只包含 `segment_count`、`session_status`、`end_reason`、`translation_failed_count` 等安全元数据。
  - 不保存明文 token、`archive_url`、英文原文、中文译文、明文 IP/User-Agent 或任何 Provider 密钥。
- 前端新增 `frontend/src/api/archives.ts`：
  - 构造 `/api/archives/{session_id}?token=...`，支持 `VITE_API_BASE_URL`。
  - 使用 Zod 校验归档响应，HTTP 非 2xx 映射为带 status 的 `ArchiveAccessError`。
- 前端新增 `frontend/src/archive/ArchivePage.tsx`：
  - 从当前 URL 的 `/archive/:sessionId` 和 `token` 查询归档。
  - 展示 loading、缺 token、无权限/过期、空归档、正常归档和异常结束状态。
  - 展示双语 final 片段、时间戳、翻译状态和重点句标记；不做搜索、复制或导出。
- `frontend/src/App.tsx` 增加轻量路径分流：`/archive/:sessionId` 渲染归档页，其余路径保持实时会议工作台；未引入 React Router。
- 新增测试文件：
  - `backend/tests/test_archives.py`
  - `frontend/src/api/archives.test.ts`
  - `frontend/src/archive/ArchivePage.test.tsx`
  - `frontend/e2e/archive.spec.ts`

### 验证命令与结果

| 验证项 | 命令 | 实际结果 |
|---|---|---|
| Step 22 后端 RED | `uv run pytest tests/test_archives.py` | 首次失败：缺少 `meeting_mvp_backend.archives` |
| Step 22 前端 RED | `npm run test -- src/api/archives.test.ts src/archive/ArchivePage.test.tsx` | 首次失败：缺少 `src/api/archives.ts` 和 `src/archive/ArchivePage.tsx` |
| 后端 Ruff | `uv run ruff check .` | 通过，`All checks passed!` |
| 后端 mypy | `uv run mypy src tests` | 通过，`Success: no issues found in 36 source files` |
| 后端 pytest | `uv run pytest` | 110 passed，13 integration deselected |
| 前端 lint | `npm run lint` | 通过 |
| 前端单元测试 | `npm run test` | 13 个测试文件、88 个测试通过 |
| 前端生产构建 | `npm run build` | 通过 |
| 前端 E2E | `npm run test:e2e` | 10 个 Chromium 测试通过 |
| Markdown/代码空白检查 | `git diff --check` | 通过；仅输出 Windows LF/CRLF 工作区提示，无空白错误 |

### 后续注意

- Step 22 结束时尚未实现搜索、复制、Markdown/JSON 导出、COS、成本看板、归档增强或重点句/时间线增强；搜索与复制已在 Step 23 补齐。
- `archive_viewed` 的真实触发点已由 Step 22 归档 API 补齐，但 payload 仍必须继续遵守 Step 21 的 usage event 安全边界。
- `end_reason` 依赖 Step 21 的 `session_closed` usage event；历史会话或异常缺失该事件时使用 `meeting_session.status` fallback。
- Playwright E2E 通过 `npm run preview` 服务 `dist`，验证归档 UI 变更前需要先运行 `npm run build`，避免复用旧构建产物。

## 2026-05-16 Step 23：F11 搜索与复制

### 本次完成

- 只推进 `memory-bank/implementation-plan.md` 的 Step 23，未开始 Step 24；本步不新增 Markdown/JSON 导出、COS、`export_file`、签名 URL、导出 UI、数据库 migration 或后端搜索查询 API。
- 扩展 `backend/src/meeting_mvp_backend/usage_events.py`：
  - `UsageEventType` 新增 `archive_searched` 和 `segment_copied`。
  - 保留 `STEP_21_USAGE_EVENT_TYPES` 为 Step 21 原始事件集合，新增 `STEP_23_USAGE_EVENT_TYPES` 表示截至 Step 23 的完整 allowlist。
  - payload 安全校验继续拒绝音频、密钥、token，并新增对 `query`、`text`、`english_text`、`chinese_text`、`archive_url` 等正文/搜索词字段的拒绝；`text_length`、`english_text_length`、`chinese_text_length` 等长度元数据仍允许。
- 扩展 `backend/src/meeting_mvp_backend/archives.py`：
  - 新增 `ArchiveSearchEventRequest`、`ArchiveSegmentCopiedEventRequest` 和 `ArchiveEventRequest`。
  - `ArchiveService.record_archive_event()` 复用既有 archive token 校验、retention 过期判断和信息隐藏边界。
  - `archive_searched` payload 只记录 `query_length`、`matched_segment_count`、`total_segment_count`。
  - `segment_copied` 会验证 `segment_id` 属于当前归档，并由后端派生 `sequence`、`translation_status`、`english_text_length`、`chinese_text_length`、`is_key_sentence` 等安全元数据。
- `backend/src/meeting_mvp_backend/main.py` 新增 `POST /api/archives/{session_id}/events?token=...`：
  - 缺少或空 token 返回 401。
  - session 不存在、错误 token、过期归档和 segment 不属于当前 session 统一返回 404。
  - 成功接收搜索/复制事件返回 204；usage event 写入失败仍按 best-effort 处理，不影响前端搜索/复制体验。
- 扩展 `frontend/src/api/archives.ts`：
  - 新增 `ArchiveEvent` 类型、`buildArchiveEventApiUrl()` 和 `recordArchiveEvent()`。
  - 事件 POST body 只包含安全元数据，不包含 raw query、英文正文、中文译文、token 或 archive URL。
- 扩展 `frontend/src/archive/ArchivePage.tsx`：
  - 增加 `aria-label="搜索归档片段"` 的搜索输入。
  - 搜索在已加载的 final 片段中本地完成，范围覆盖英文 final、中文 final、开始/结束时间戳和时间范围；英文大小写不敏感，中文按包含匹配。
  - 空搜索显示全部片段，有搜索无命中时显示“未找到匹配片段”。
  - 每个片段新增复制按钮，复制内容固定包含时间、英文原文和中文翻译；复制成功后显示“已复制”，复制失败时显示可访问错误提示且不清空归档内容。
  - 非空搜索 400ms debounce 后记录 `archive_searched`；复制成功后记录 `segment_copied`；事件上报失败不阻塞 UI。
- 扩展测试文件：
  - `backend/tests/test_usage_events.py`
  - `backend/tests/test_archives.py`
  - `frontend/src/api/archives.test.ts`
  - `frontend/src/archive/ArchivePage.test.tsx`
  - `frontend/e2e/archive.spec.ts`

### 验证命令与结果

| 验证项 | 命令 | 实际结果 |
|---|---|---|
| Step 23 后端 RED | `uv run pytest tests/test_usage_events.py tests/test_archives.py -q` | 首次 2 errors：缺少 `STEP_23_USAGE_EVENT_TYPES`、`ArchiveSearchEventRequest` 等 Step 23 入口 |
| Step 23 后端目标 GREEN | `uv run pytest tests/test_usage_events.py tests/test_archives.py -q` | 31 passed |
| Step 23 前端 RED | `npm run test -- src/api/archives.test.ts src/archive/ArchivePage.test.tsx` | 首次 7 failed：缺少事件 API client、搜索输入和复制按钮 |
| Step 23 前端目标 GREEN | 同上 | 2 个测试文件、15 个测试通过 |
| 后端 Ruff | `uv run ruff check .` | 通过，`All checks passed!` |
| 后端 mypy | `uv run mypy src tests` | 通过，`Success: no issues found in 36 source files` |
| 后端 pytest | `uv run pytest` | 121 passed，13 integration deselected |
| 前端 lint | `npm run lint` | 通过 |
| 前端单元测试 | `npm run test` | 13 个测试文件、95 个测试通过 |
| 前端生产构建 | `npm run build` | 通过 |
| 前端 E2E | `npm run test:e2e` | 10 个 Chromium 测试通过 |

### 后续注意

- Step 24 必须等待用户明确允许后再开始；当前没有 Markdown/JSON 导出、COS 上传、`export_file` 写入、短期签名 URL 或导出失败事件。
- 搜索事件只记录搜索词长度和命中统计，不记录搜索词原文。
- 复制事件只在浏览器 clipboard 写入成功后上报；后端只记录 segment 元数据和文本长度，不记录英文/中文正文。
- `usage_event` 仍是观测数据，写入失败不得影响归档查看、搜索或复制主流程。

## 2026-05-16 Step 24：F12 Markdown / JSON 导出

### 本次完成

- 只推进 `memory-bank/implementation-plan.md` 的 Step 24，未开始 Step 25；本步不新增 final 翻译重试、导出历史列表、COS 管理页、数据库 migration、成本看板、重点句/时间线增强或前端公开埋点 API。
- 新增后端 `backend/src/meeting_mvp_backend/exports.py`：
  - 定义 `ArchiveExportRequest`、`ArchiveExportResponse`、`ArchiveExportService`、导出文件仓储协议、COS storage 协议、SQLAlchemy `export_file` 写入器和 Tencent COS storage 实现。
  - `POST /api/archives/{session_id}/exports?token=...` 复用 archive token 授权边界：缺 token 返回 401；session 不存在、错误 token、过期归档统一 404；空归档返回 409；COS 配置或导出临时不可用返回 503。
  - 按 final 片段 `sequence` 升序生成 Markdown 和 JSON，内容包含 session 元数据和双语 final 片段；空中文 final 使用“中文 final 暂不可用”占位。
  - 使用 `TENCENT_COS_EXPORT_PREFIX/{session_id}/{export_id}.md|json` 形式生成 COS object key，并上传私有对象；返回短期签名下载地址，但不在 API 响应中暴露 object key。
  - 写入 `export_file` 的 `format`、`cos_object_key`、`cos_url`、`created_at` 和 `retention_expires_at`，不新增 migration。
- 后端依赖新增 `cos-python-sdk-v5`，并已更新 `backend/pyproject.toml` 与 `backend/uv.lock`；本地测试通过 fake storage，不依赖真实 COS 密钥。
- 扩展 `backend/src/meeting_mvp_backend/usage_events.py`：
  - 新增 `export_created`、`export_failed` 和 `STEP_24_USAGE_EVENT_TYPES`。
  - `export_created` payload 只记录格式、片段数、文件字节数、翻译失败数和签名 URL TTL。
  - `export_failed` payload 只记录格式、失败阶段、错误类型和安全统计。
  - payload 安全校验新增拒绝 `download_url`、`signed_url`、`cos_url`、`object_key`、`cos_object_key` 等字段，继续禁止 token、正文、音频和密钥进入 `usage_event`。
- 扩展前端 `frontend/src/api/archives.ts`：
  - 新增 `ArchiveExportResponse`、`ArchiveExportFormat`、`buildArchiveExportApiUrl()` 和 `createArchiveExport()`。
  - 导出 POST body 只包含 `{format}`，token 只作为既有归档授权 query 参数发送，不进入 JSON body。
- 扩展前端 `frontend/src/archive/ArchivePage.tsx`：
  - 在归档 ready 状态新增 Markdown 与 JSON 导出按钮。
  - 无 final 片段时禁用导出按钮并保留空归档提示。
  - 导出成功后显示“导出已生成”和短期下载链接；不会自动跳转，不清空归档内容。
  - 导出失败时显示可访问 `role="alert"` 提示；409 显示“暂无可导出的 final 片段”，503 或网络错误显示“导出暂时不可用，请稍后重试”。
- 扩展测试文件：
  - `backend/tests/test_exports.py`
  - `backend/tests/test_usage_events.py`
  - `frontend/src/api/archives.test.ts`
  - `frontend/src/archive/ArchivePage.test.tsx`
  - `frontend/e2e/archive.spec.ts`

### 验证命令与结果

| 验证项 | 命令 | 实际结果 |
|---|---|---|
| Step 24 后端 RED | `uv run pytest tests/test_usage_events.py tests/test_exports.py -q` | 首次 2 errors：缺少 `STEP_24_USAGE_EVENT_TYPES` 和 `meeting_mvp_backend.exports` |
| Step 24 后端目标 GREEN | `uv run pytest tests/test_usage_events.py tests/test_exports.py -q` | 35 passed |
| Step 24 前端 RED | `npm run test -- src/api/archives.test.ts src/archive/ArchivePage.test.tsx` | 首次 7 failed：缺少导出 API client、导出按钮和导出状态 |
| Step 24 前端目标 GREEN | 同上 | 2 个测试文件、21 个测试通过 |
| 后端 Ruff | `uv run ruff check .` | 通过，`All checks passed!` |
| 后端 mypy | `uv run mypy src tests` | 通过，`Success: no issues found in 38 source files` |
| 后端 pytest | `uv run pytest` | 141 passed，13 integration deselected |
| 前端 lint | `npm run lint` | 通过 |
| 前端单元测试 | `npm run test` | 13 个测试文件、101 个测试通过 |
| 前端生产构建 | `npm run build` | 通过 |
| 前端 E2E | `npm run test:e2e` | 10 个 Chromium 测试通过 |

### 后续注意

- Step 25 必须等待用户明确允许后再开始；当前没有 final 翻译重试、重试次数、重试 API、后台补译或失败片段自动更新。
- 本地没有运行真实 COS smoke；真实 COS 上传和短期签名 URL 仍需在 Lighthouse 后端容器中使用安全环境变量执行 gated smoke，不能在本地或文档中输出任何密钥或签名 URL。
- `export_created` / `export_failed` 只保存安全元数据；不得把 COS object key、短期下载地址、archive token、会议正文、译文、IP/User-Agent 明文或密钥写入 usage event。
- `export_file.cos_url` 存放本次生成的短期访问地址字段；COS 对象仍保持私有，前端只能通过后端返回的短期下载地址下载。
