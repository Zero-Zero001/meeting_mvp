# Deploy

本目录保存 Step 06 建立的单机部署骨架。真实部署目标是腾讯云 Lighthouse 上的 `/opt/meeting_mvp/app`，通过 Docker Compose 编排 PostgreSQL、Redis、FastAPI 后端和 Caddy 静态前端入口。

## 文件作用

| 文件 | 作用 |
|---|---|
| `docker-compose.yml` | 定义 `postgres`、`redis`、`backend`、`caddy` 服务、持久化挂载、健康检查和容器网络。 |
| `Caddyfile` | 由 Caddy 服务 Vite 静态前端，并把 `/api/*` 与 `/ws/*` 反向代理到后端容器。 |
| `.env.example` | Compose 验证用占位配置，不包含真实密钥。生产环境变量仍应放在服务器安全位置。 |

## 验证命令

在服务器项目目录执行配置检查：

```bash
cd /opt/meeting_mvp/app
docker compose --env-file deploy/.env.example -f deploy/docker-compose.yml config
```

Step 06 只要求配置合法；不要在本步骤执行 `docker compose up -d`、`docker compose ps` 或 Alembic migration。

## 安全边界

- 只允许 Caddy 映射公网 `80` 和 `443`。
- PostgreSQL `5432` 与 Redis `6379` 不映射到宿主机公网端口，只允许容器网络内访问。
- PostgreSQL 数据目录使用 `/opt/meeting_mvp/data/postgres`。
- Redis 数据目录使用 `/opt/meeting_mvp/data/redis`。
- Step 16 替换后，生产 ASR 使用 Qwen realtime ASR，后端容器不再挂载 Google STT 服务账号 JSON；Qwen API key 只通过服务器安全环境变量提供。
- 不在本目录放置真实 `.env`、生产密钥、Qwen API key、Google 服务账号 JSON、COS SecretId 或 SecretKey。
