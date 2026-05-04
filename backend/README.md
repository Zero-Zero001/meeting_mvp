# Backend

本目录用于后续初始化 Python 3.12 + FastAPI 后端工程。

边界：

- 放置 HTTP API、WebSocket 会话编排、Provider 适配、数据库访问、Redis 额度状态、归档和导出逻辑。
- 后续 Step 04 才能初始化 `pyproject.toml`、`uv.lock`、`.python-version` 和项目级 `.venv`。
- 所有后端命令后续必须通过 `uv run ...` 执行；`.venv` 不提交 Git。

