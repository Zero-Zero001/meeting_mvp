# Meeting MVP Backend

本目录是 Meeting MVP 的后端工程，已在 Step 04 初始化为 Python 3.12 + FastAPI + uv 项目。

## 当前边界

- 运行时目标：FastAPI 后端，后续由 Caddy 反向代理 `/api/*` 和 `/ws/*`。
- 当前只包含最小健康检查服务：`GET /health` 返回 `{"status":"ok"}`。
- 依赖管理：`uv`、`pyproject.toml`、`uv.lock`、项目级 `.venv`。
- Python 版本：`.python-version` 固定为 `3.12`，`pyproject.toml` 限定 `>=3.12,<3.13`。
- 本步骤不包含环境变量清单、真实 Provider 配置、Docker Compose、数据库迁移或 Redis 集成。
- `.venv` 是本地生成物，不提交 Git。

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

## 文件入口

- `src/meeting_mvp_backend/main.py`：FastAPI 应用入口与健康检查路由。
- `tests/test_health.py`：健康检查的本地轻量单元测试。
- `pyproject.toml`：项目依赖、构建、Ruff、mypy 和 pytest 配置。
