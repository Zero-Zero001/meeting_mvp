# Meeting MVP Backend

本目录是 Meeting MVP 的后端工程，已初始化为 Python 3.12 + FastAPI + uv 项目。

## 当前边界

- 运行时目标：FastAPI 后端，后续由 Caddy 反向代理 `/api/*` 和 `/ws/*`。
- 当前包含最小健康检查服务：`GET /health` 返回 `{"status":"ok"}`。
- 配置边界：`config.py` 使用 `pydantic-settings` 读取环境变量，`APP_ENV=local` 支持本地 mock 模式。
- 依赖管理：`uv`、`pyproject.toml`、`uv.lock`、项目级 `.venv`。
- Python 版本：`.python-version` 固定为 `3.12`，`pyproject.toml` 限定 `>=3.12,<3.13`。
- 本步骤不包含真实 Provider 调用、Docker Compose、数据库迁移或 Redis 集成。
- `.venv` 和真实 `.env` 是本地生成物，不提交 Git。

## 常用命令

```powershell
uv python install 3.12
uv python pin 3.12
uv sync
uv run python --version
uv run ruff check .
uv run mypy .
uv run pytest
uv run uvicorn meeting_mvp_backend.main:app --host 127.0.0.1 --port 8000
```

使用示例配置启动本地 mock 模式：

```powershell
$env:MEETING_MVP_ENV_FILE='backend/.env.example'
uv run uvicorn meeting_mvp_backend.main:app --host 127.0.0.1 --port 8000
```

## 文件入口

- `src/meeting_mvp_backend/main.py`：FastAPI 应用入口、startup 配置加载和健康检查路由。
- `src/meeting_mvp_backend/config.py`：环境变量模型、加载、校验和脱敏状态输出。
- `tests/test_health.py`：健康检查的本地轻量单元测试。
- `tests/test_config.py`：配置加载、生产缺失配置、OpenAI STT 开关和脱敏状态测试。
- `.env.example`：后端本地 mock 示例配置，不包含真实密钥。
- `pyproject.toml`：项目依赖、构建、Ruff、mypy 和 pytest 配置。
