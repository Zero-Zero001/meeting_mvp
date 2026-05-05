# Meeting MVP 环境变量清单

本文是 Step 05 建立的唯一环境变量清单。真实密钥只能进入后端运行环境或服务器安全配置，不能进入前端代码、前端构建产物、Git 或项目记忆文档。

## 使用规则

- 后端私有变量使用原始名称，例如 `QWEN_API_KEY`、`DATABASE_URL`、`TENCENT_COS_SECRET_KEY`。
- 前端只能读取 `VITE_*` 公开变量；任何 Provider、数据库、Redis、COS 密钥都不得添加 `VITE_` 前缀。
- `APP_ENV=local` 是 Windows 本地 mock 模式，不要求真实 Provider、数据库、Redis、COS 密钥。
- `APP_ENV=staging` 或 `APP_ENV=production` 必须提供生产必填配置；缺失时后端拒绝启动并报告缺失变量名。
- `OPENAI_STT_ENABLED=false` 是默认值；只有显式设置为 `true` 时才要求 OpenAI STT 相关配置。
- 示例文件只放 placeholder 或空值：`backend/.env.example`、`frontend/.env.example`。

## 应用与公开配置

| 变量名 | 默认值 | 可进入前端 | 用途 |
|---|---:|---|---|
| `APP_ENV` | `local` | 否 | 后端运行环境：`local`、`staging`、`production`。 |
| `APP_TIMEZONE` | `Asia/Shanghai` | 否 | 服务端业务时区。 |
| `PUBLIC_BASE_URL` | 空 | 否 | 对外访问前端的基础 URL。 |
| `API_BASE_URL` | 空 | 否 | HTTP API 基础 URL。 |
| `WS_BASE_URL` | 空 | 否 | WebSocket 基础 URL，生产使用 `wss://`。 |
| `LOG_LEVEL` | `INFO` | 否 | 后端日志级别。 |
| `VITE_APP_ENV` | `local` | 是 | 前端公开环境标识。 |
| `VITE_PUBLIC_BASE_URL` | 空 | 是 | 前端可见站点基础 URL。 |
| `VITE_API_BASE_URL` | 空 | 是 | 前端可见 HTTP API 基础 URL。 |
| `VITE_WS_BASE_URL` | 空 | 是 | 前端可见 WebSocket 基础 URL。 |

## 数据库与 Redis

| 变量名 | 默认值 | 可进入前端 | 用途 |
|---|---:|---|---|
| `DATABASE_URL` | 空 | 否 | PostgreSQL 连接串。 |
| `REDIS_URL` | 空 | 否 | Redis 连接串。 |
| `POSTGRES_DB` | 空 | 否 | PostgreSQL 数据库名，主要用于部署编排。 |
| `POSTGRES_USER` | 空 | 否 | PostgreSQL 用户名，主要用于部署编排。 |
| `POSTGRES_PASSWORD` | 空 | 否 | PostgreSQL 密码。 |
| `REDIS_PASSWORD` | 空 | 否 | Redis 密码。 |

## 配额、预算与归档

| 变量名 | 默认值 | 可进入前端 | 用途 |
|---|---:|---|---|
| `DAILY_FREE_SECONDS` | `2400` | 否 | 每个匿名用户每日免费额度。 |
| `SESSION_MAX_SECONDS` | `1800` | 否 | 单场会议最长时长。 |
| `MAX_ACTIVE_SESSIONS_PER_CLIENT` | `1` | 否 | 同一匿名用户最大活跃会议数。 |
| `MONTHLY_BUDGET_RMB` | `500` | 否 | 月度预算参考值。 |
| `BUDGET_FUSE_RMB` | `400` | 否 | 预算保险丝阈值。 |
| `ARCHIVE_RETENTION_DAYS` | `30` | 否 | 会议归档和 COS 导出默认保留天数。 |
| `COS_SIGNED_URL_TTL_SECONDS` | `3600` | 否 | COS 短期签名 URL 有效期。 |

## Provider 与 COS

| 变量名 | 默认值 | 可进入前端 | 用途 |
|---|---:|---|---|
| `GOOGLE_APPLICATION_CREDENTIALS` | 空 | 否 | Google 服务账号 JSON 路径。 |
| `GOOGLE_CLOUD_PROJECT` | 空 | 否 | Google Cloud 项目 ID。 |
| `GOOGLE_STT_LOCATION` | 空 | 否 | Google STT region。 |
| `GOOGLE_STT_RECOGNIZER` | 空 | 否 | Google STT recognizer。 |
| `QWEN_API_KEY` | 空 | 否 | 阿里云百炼 API Key。 |
| `QWEN_BASE_URL` | 空 | 否 | Qwen OpenAI-compatible endpoint。 |
| `QWEN_INTERIM_MODEL` | 空 | 否 | 中文 interim 模型。 |
| `QWEN_INTERIM_ENABLED` | `true` | 否 | 是否启用中文 interim。 |
| `QWEN_FINAL_MODEL` | `qwen3.6-max-preview` | 否 | 中文 final 模型。 |
| `OPENAI_API_KEY` | 空 | 否 | OpenAI API Key，仅备用或对比。 |
| `OPENAI_BASE_URL` | 空 | 否 | OpenAI API base URL。 |
| `OPENAI_FINAL_MODEL` | 空 | 否 | 可选中文 final 对比模型。 |
| `OPENAI_STT_ENABLED` | `false` | 否 | 是否启用 OpenAI STT 实验入口。 |
| `OPENAI_STT_MODEL` | 空 | 否 | 备用/对比 STT 模型。 |
| `TENCENT_COS_SECRET_ID` | 空 | 否 | COS SecretId。 |
| `TENCENT_COS_SECRET_KEY` | 空 | 否 | COS SecretKey。 |
| `TENCENT_COS_REGION` | 空 | 否 | COS 地域。 |
| `TENCENT_COS_BUCKET` | 空 | 否 | COS Bucket 名称。 |
| `TENCENT_COS_EXPORT_PREFIX` | `exports/` | 否 | 导出文件对象 key 前缀。 |

## 校验边界

- `local` 模式允许以上私有配置为空，便于 Windows 本地跑 mock 和轻量测试。
- `staging`、`production` 模式要求后端启动前具备数据库、Redis、Google STT、Qwen final/interim 和 COS 关键配置。
- 后端启动日志只允许输出配置名和 `set` / `unset` 状态，不允许输出任何变量值。
- 前端构建产物中不应包含 `QWEN_*`、`OPENAI_*`、`GOOGLE_*`、`DATABASE_URL`、`REDIS_URL`、`TENCENT_COS_*`。
