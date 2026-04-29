# Meeting MVP 开发环境准备手册

## 文档目标

本文用于指导你为 Codex 全程执行 `implementation-plan.md` 准备必要环境和工具。目标环境与 `tech-stack.md` 保持一致：Windows 本地只准备轻量开发工具和浏览器测试工具；腾讯云 Lighthouse Ubuntu 22.04 LTS 64 位 x86 负责 Docker、Docker Compose、PostgreSQL、Redis、FastAPI、Caddy 和前端静态产物部署。

## 0. 准备信息清单

开始安装前，先准备以下信息：

| 类别 | 需要准备的内容 | 用途 |
|---|---|---|
| GitHub | `Zero-Zero001/meeting_mvp` 仓库访问权限 | 拉取代码、推送分支、创建 PR。 |
| 域名 | 一个可解析到腾讯云 Lighthouse 的域名 | Caddy 自动签发 HTTPS，浏览器音频捕获需要安全上下文。 |
| 腾讯云 Lighthouse | Ubuntu 22.04 LTS 64 位 x86 实例 | 部署 Docker、PostgreSQL、Redis、后端和 Caddy。 |
| SSH 访问 | Lighthouse 公网 IP、SSH 用户、SSH key 路径 | 允许 Codex 指导或执行云端 Docker、数据库和部署验证。 |
| 腾讯 COS | Bucket、地域、SecretId、SecretKey | 保存 Markdown / JSON 导出文件。 |
| Google Cloud | Speech-to-Text v2 可用项目和服务账号 | 英文 streaming STT 主链路。 |
| 阿里云百炼 | Qwen Flash/Turbo API Key 和 endpoint | 中文 interim 临时理解。 |
| OpenAI | API Key 和可用文本模型 | 中文 final 正式翻译和备用 STT 对比。 |

验证测试：逐项确认以上信息已可登录或可复制到安全密码管理器。

预期结果：开始安装前不会因为缺少账号、域名或 Provider 权限中断。

## 0.1 Codex 执行前置条件

在让 Codex 执行 `implementation-plan.md` 前，需要确认以下条件：

| 前置条件 | 准备内容 | 验证方式 |
|---|---|---|
| 本地代码环境 | Git、Node.js 24 LTS、npm、系统 Python、uv、Chrome、Edge、VS Code、SSH 客户端 | 在 PowerShell 中能输出版本号或启动应用；项目后端 Python 由 uv 固定为 3.12。 |
| 云服务器访问 | Lighthouse 公网 IP、SSH 用户、SSH 私钥路径 | 能从 Windows PowerShell 通过 SSH 登录服务器。 |
| 云端运行环境 | Docker、Docker Compose plugin、PostgreSQL container、Redis container | 在 Lighthouse 上执行 Docker 和 Compose 检查。 |
| 外部服务凭证 | Google STT、Qwen、OpenAI、Tencent COS | 凭证只保存在安全位置，后续写入服务器环境变量。 |
| 域名与 HTTPS | 域名解析到 Lighthouse 公网 IP | Caddy 可自动签发 HTTPS，浏览器可使用安全上下文。 |

预期结果：Codex 可以在本地完成代码开发和轻量测试，并通过 SSH 在 Lighthouse 上完成 Docker、PostgreSQL、Redis 和部署相关验证。

## 0.2 执行边界矩阵

| 工作内容 | 执行位置 | 说明 |
|---|---|---|
| 代码编辑、文档修改、Git 操作 | Windows 本地 | Codex 在仓库目录内完成。 |
| 前端依赖安装、lint、单元测试、构建 | Windows 本地 | 使用 Node.js 24 LTS 和 npm。 |
| 后端依赖安装、Ruff、mypy、纯单元测试 | Windows 本地 | 使用 uv 创建项目级 Python 3.12 `.venv`；不依赖本地数据库。 |
| 浏览器音频捕获体验测试 | Windows 本地 | 使用 Chrome / Edge 和 HTTPS 或 localhost。 |
| Docker、Docker Compose | 腾讯云 Lighthouse | Windows 本地不安装 Docker。 |
| PostgreSQL、Redis | 腾讯云 Lighthouse | 通过 Docker Compose 容器部署，Windows 本地不安装。 |
| Alembic migration、数据库集成测试、Redis 集成测试 | 腾讯云 Lighthouse | 通过 SSH 在云端执行。 |
| 生产部署演练、HTTPS/WSS、Caddy 反代 | 腾讯云 Lighthouse | 云端完成。 |

预期结果：本地环境保持轻量，真实数据库、Redis、容器和部署验证全部集中在云服务器。

## 1. Windows 本地开发环境

### 1.1 安装 Git

目标：支持仓库管理、分支、提交和推送。

安装指令：

```powershell
winget install --id Git.Git -e
```

验证测试：

```powershell
git --version
git config --global user.name
git config --global user.email
```

预期结果：`git --version` 正常输出版本号；`user.name` 和 `user.email` 已配置为你的 GitHub 身份。

### 1.2 安装 Node.js 24 LTS 和 npm

目标：支持 Vite、React、TypeScript、Vitest 和 Playwright。

安装指令：

```powershell
winget install --id OpenJS.NodeJS.LTS -e
```

验证测试：

```powershell
node -v
npm -v
```

预期结果：Node.js 主版本为 24，npm 能正常输出版本号。

### 1.3 确认系统 Python

目标：确认本机存在可用 Python；系统 Python 可以是 3.13.9，但项目后端运行版本由 uv 固定为 Python 3.12。

验证测试：

```powershell
python --version
```

预期结果：可以输出 Python 版本。若当前显示 `Python 3.13.9`，不需要卸载；后续用 uv 为项目安装和锁定 Python 3.12。

### 1.4 安装 uv

目标：管理 Python 后端依赖、项目级虚拟环境和运行命令。

安装指令：

```powershell
powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

验证测试：

```powershell
uv --version
```

预期结果：uv 能正常输出版本号。

### 1.5 准备项目级 Python 3.12 虚拟环境

目标：让后端项目使用可复现的 Python 3.12 `.venv`，避免本机系统 Python 3.13.9 与生产环境版本漂移。

执行位置：后端工程目录创建后，在后端目录运行。

```powershell
uv python install 3.12
uv python pin 3.12
uv sync
uv run python --version
```

规则：

- 后端依赖、Ruff、mypy、pytest、pytest-asyncio、Alembic 等工具都写入 `pyproject.toml`。
- 使用 `uv sync` 创建或更新项目 `.venv`。
- 使用 `uv run ...` 执行所有后端命令。
- `.venv` 是本地生成物，不提交 Git。
- `.python-version` 用于锁定项目解释器，可以提交 Git。
- 不使用全局 `pip install` 安装项目依赖或开发工具。

预期结果：`uv run python --version` 输出 Python 3.12.x；后端工具从项目 `.venv` 运行。

### 1.6 确认 SSH 客户端

目标：支持 Codex 通过 PowerShell 指导或执行云服务器验证。

验证测试：

```powershell
ssh -V
```

如系统缺少 OpenSSH 客户端，使用 Windows 设置中的“可选功能”安装 OpenSSH Client，或执行：

```powershell
Get-WindowsCapability -Online | Where-Object Name -like 'OpenSSH.Client*'
```

预期结果：PowerShell 中 `ssh -V` 能输出版本号。

### 1.7 安装浏览器

目标：支持第一版重点测试 Windows Chrome / Edge 音频捕获。

安装指令：

```powershell
winget install --id Google.Chrome -e
winget install --id Microsoft.Edge -e
```

验证测试：

```powershell
Start-Process chrome
Start-Process msedge
```

预期结果：Chrome 和 Edge 均可启动，并能访问本地开发地址。

### 1.8 安装编辑器

目标：支持 TypeScript、Python、Markdown 和 Git 开发。

安装指令：

```powershell
winget install --id Microsoft.VisualStudioCode -e
```

推荐扩展：

- Python
- Pylance
- Ruff
- ESLint
- Prettier
- GitHub Pull Requests
- Markdown All in One

验证测试：打开 `D:\meeting_mvp`，确认 VS Code 能识别 Git 仓库。

预期结果：编辑器能正常打开项目、显示 Git 状态，并支持 Python 与 TypeScript 语法检查。

### 1.9 克隆或确认本地仓库

目标：确认本机工作目录是 `D:\meeting_mvp`。

验证指令：

```powershell
cd D:\meeting_mvp
git status --short --branch
git remote -v
```

预期结果：当前目录是 `D:\meeting_mvp`，远端地址指向 `https://github.com/Zero-Zero001/meeting_mvp.git`。

## 2. 本地轻量测试准备

### 2.1 安装 Playwright 浏览器依赖

目标：支持前端端到端测试。

执行位置：前端工程初始化后，在前端目录运行。

验证指令：

```powershell
npx playwright install
npx playwright --version
```

预期结果：Playwright 能安装 Chromium 等测试浏览器，并输出版本号。

### 2.2 明确本地不安装项

目标：避免把云端服务误装到 Windows 本地。

本地不安装：

- Docker
- PostgreSQL
- Redis

验证测试：在 Windows 本地不要求执行 `docker`、`psql` 或 `redis-cli` 相关检查。

预期结果：本地只承担代码开发、前端构建、后端纯单元测试和浏览器测试；容器、数据库和 Redis 验证都在 Lighthouse 上完成。

## 3. Provider 凭证准备

### 3.1 Google Cloud Speech-to-Text v2

目标：提供英文 streaming STT 主链路。

准备步骤：

1. 创建或选择 Google Cloud 项目。
2. 启用 Speech-to-Text API。
3. 创建服务账号。
4. 给服务账号授予调用 Speech-to-Text 所需权限。
5. 生成服务账号 JSON 凭证。
6. 将 JSON 文件安全保存，不提交到 Git。

环境变量建议：

| 变量名 | 用途 |
|---|---|
| `GOOGLE_APPLICATION_CREDENTIALS` | Google 服务账号 JSON 文件路径。 |
| `GOOGLE_CLOUD_PROJECT` | Google Cloud 项目 ID。 |
| `GOOGLE_STT_LOCATION` | Speech-to-Text v2 使用的 region。 |
| `GOOGLE_STT_RECOGNIZER` | Recognizer 名称或默认 recognizer 配置。 |

验证测试：使用 Google 官方控制台或最小调用脚本验证 Speech-to-Text API 可用。

预期结果：Google STT 凭证具备 streaming recognize 权限。

### 3.2 阿里云百炼 Qwen

目标：提供中文 interim 临时理解。

准备步骤：

1. 登录阿里云百炼控制台。
2. 开通可用的 Qwen Flash/Turbo 模型。
3. 创建 API Key。
4. 确认 OpenAI-compatible endpoint 可访问。
5. 记录模型名、endpoint 和 API Key。

环境变量建议：

| 变量名 | 用途 |
|---|---|
| `QWEN_API_KEY` | 阿里云百炼 API Key。 |
| `QWEN_BASE_URL` | OpenAI-compatible endpoint。 |
| `QWEN_INTERIM_MODEL` | 中文 interim 使用的模型。 |
| `QWEN_INTERIM_ENABLED` | 是否启用中文 interim。 |

验证测试：用控制台示例或后端 Provider smoke test 请求一次中文改写。

预期结果：Qwen 返回文本结果，失败时能看到明确错误码。

### 3.3 OpenAI

目标：提供中文 final 正式翻译，并保留 STT 备用/对比入口。

准备步骤：

1. 登录 OpenAI 控制台。
2. 创建 API Key。
3. 选择中文 final 使用的文本模型。
4. 配置预算或用量提醒。
5. 保存 API Key 到安全位置。

环境变量建议：

| 变量名 | 用途 |
|---|---|
| `OPENAI_API_KEY` | OpenAI API Key。 |
| `OPENAI_BASE_URL` | OpenAI API base URL，默认可使用官方地址。 |
| `OPENAI_FINAL_MODEL` | 中文 final 翻译模型。 |
| `OPENAI_STT_MODEL` | 备用/对比 STT 模型。 |
| `OPENAI_STT_ENABLED` | 是否启用 OpenAI STT 实验入口。 |

验证测试：使用后端 Provider smoke test 请求一次中文 final 翻译。

预期结果：OpenAI 能返回中文 final 文本，token 用量可被记录。

## 4. 腾讯 COS 准备

目标：保存 Markdown / JSON 导出文件。

准备步骤：

1. 在腾讯云创建 COS Bucket。
2. 选择离 Lighthouse 较近的地域。
3. 创建用于后端访问 COS 的 SecretId 和 SecretKey。
4. 配置 Bucket 访问策略，避免公开写权限。
5. 决定导出文件访问方式：后端代理下载或短期签名 URL。

环境变量建议：

| 变量名 | 用途 |
|---|---|
| `TENCENT_COS_SECRET_ID` | COS SecretId。 |
| `TENCENT_COS_SECRET_KEY` | COS SecretKey。 |
| `TENCENT_COS_REGION` | COS Bucket 地域。 |
| `TENCENT_COS_BUCKET` | COS Bucket 名称。 |
| `TENCENT_COS_EXPORT_PREFIX` | 导出文件对象 key 前缀。 |

验证测试：使用腾讯云控制台上传和删除一个测试文件；后端实现后再运行 COS Provider smoke test。

预期结果：Bucket 可写入、读取和删除测试对象，权限不会暴露到前端。

## 5. 云服务器准备

### 5.1 创建腾讯云 Lighthouse

目标：提供第一版单机部署环境。

推荐配置：

| 项目 | 建议 |
|---|---|
| 操作系统 | Ubuntu 22.04 LTS 64 位 |
| 架构 | x86 |
| CPU / 内存 | 以预算内可用规格为准，优先保证 2 GB 以上内存 |
| 系统盘 | 40 GB 以上 |
| 地域 | 尽量靠近目标测试用户 |

验证测试：在腾讯云控制台确认实例运行中，并记录公网 IP。

预期结果：能通过 SSH 连接服务器。

### 5.2 数据库与 Redis 容器化部署原则

目标：明确 Lighthouse 上 PostgreSQL 和 Redis 的部署边界，避免后续误把数据库直接安装到宿主机或暴露到公网。

部署原则：

- PostgreSQL 16 通过 Docker Compose 容器运行，不直接安装到 Ubuntu 宿主机。
- Redis 7 通过 Docker Compose 容器运行，不直接安装到 Ubuntu 宿主机。
- PostgreSQL 必须使用 Docker volume 或 `/opt/meeting_mvp/data/postgres` 持久化正式数据。
- Redis 建议使用 Docker volume 或 `/opt/meeting_mvp/data/redis` 持久化短期状态，但 Redis 不能替代 PostgreSQL 保存正式会议档案。
- PostgreSQL 的 5432 端口只允许 Docker 内网中的后端容器访问，不对公网开放。
- Redis 的 6379 端口只允许 Docker 内网中的后端容器访问，不对公网开放。
- PostgreSQL 上线前必须执行备份；版本升级、迁移和发布前必须能生成可用备份文件。
- Redis 数据可被视为可恢复的短期状态，Redis 重启不应造成已归档 final 片段丢失。

验证测试：

```bash
docker compose config
docker compose ps
docker inspect meeting_mvp-postgres-1
docker inspect meeting_mvp-redis-1
```

预期结果：PostgreSQL 和 Redis 均由 Compose 管理；两者存在持久化挂载；Compose 不把 5432 和 6379 绑定到公网地址。

### 5.3 配置安全组和防火墙

目标：只开放必要入口。

开放端口：

| 端口 | 用途 | 访问范围 |
|---:|---|---|
| 22 | SSH 管理 | 仅你的固定 IP 或可信地址。 |
| 80 | Caddy HTTP challenge 和跳转 | 公网。 |
| 443 | HTTPS/WSS | 公网。 |

不要向公网开放：

- 5432 PostgreSQL
- 6379 Redis
- 后端容器内部端口

验证测试：从本地运行端口连通性检查，确认 22、80、443 策略符合预期，5432 和 6379 不对公网开放。

预期结果：公网只能访问 SSH、HTTP、HTTPS/WSS 必要端口。

### 5.4 配置 SSH 登录

目标：安全登录云服务器。

本地生成密钥：

```powershell
ssh-keygen -t ed25519 -C "meeting-mvp"
```

连接服务器：

```powershell
ssh ubuntu@服务器公网IP
```

验证测试：

```bash
whoami
uname -a
lsb_release -a
```

预期结果：登录用户为 `ubuntu` 或你创建的部署用户，系统为 Ubuntu 22.04 LTS。

### 5.5 初始化服务器基础包

目标：安装 Docker 前的基础依赖。

执行命令：

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y ca-certificates curl gnupg git ufw unzip jq
```

验证测试：

```bash
git --version
curl --version
jq --version
```

预期结果：基础工具均能输出版本号。

### 5.6 安装 Docker 和 Docker Compose plugin

目标：在服务器运行 Compose 部署。

执行命令：

```bash
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
```

操作要求：执行 `usermod` 后退出 SSH，再重新登录。

验证测试：

```bash
docker --version
docker compose version
docker run --rm hello-world
```

预期结果：Docker 和 Compose 正常输出版本号，`hello-world` 可运行。

### 5.7 配置服务器目录

目标：给应用、数据、备份和日志建立固定目录。

执行命令：

```bash
sudo mkdir -p /opt/meeting_mvp/app
sudo mkdir -p /opt/meeting_mvp/data/postgres
sudo mkdir -p /opt/meeting_mvp/data/redis
sudo mkdir -p /opt/meeting_mvp/backups
sudo mkdir -p /opt/meeting_mvp/logs
sudo chown -R $USER:$USER /opt/meeting_mvp
```

验证测试：

```bash
ls -la /opt/meeting_mvp
```

预期结果：目录存在，当前部署用户具备写入权限。

### 5.8 PostgreSQL 备份与恢复演练

目标：确认正式档案数据可以备份和恢复，降低单机部署数据风险。

备份原则：

- 每次生产发布前生成 PostgreSQL 备份。
- 每次执行 Alembic migration 前生成 PostgreSQL 备份。
- 备份文件保存到 `/opt/meeting_mvp/backups`，并按日期和版本命名。
- 至少在测试库或临时容器中演练一次恢复流程，确认备份文件不是空文件或损坏文件。
- Redis 不作为正式档案备份对象；Redis 状态丢失后，系统应能通过 PostgreSQL final 片段继续提供归档查看。

验证测试：

```bash
ls -lh /opt/meeting_mvp/backups
```

发布后验证要求：

- 备份目录中存在本次发布前生成的 PostgreSQL 备份文件。
- 备份文件大小符合实际数据量，不是 0 字节。
- 恢复演练能在测试库或临时容器中完成。

预期结果：PostgreSQL 正式数据具备可验证备份；恢复流程不会依赖 Redis。

### 5.9 配置域名解析

目标：让 Caddy 能自动签发 HTTPS 证书。

准备步骤：

1. 在域名 DNS 控制台添加 A 记录。
2. 主机记录指向你的工具域名。
3. 记录值填写 Lighthouse 公网 IP。
4. 等待 DNS 生效。

验证测试：

```powershell
nslookup 你的工具域名
```

预期结果：域名解析到 Lighthouse 公网 IP。

## 6. 环境变量清单

目标：统一本地、测试和生产配置名称。

### 6.1 应用基础配置

| 变量名 | 用途 |
|---|---|
| `APP_ENV` | 运行环境，例如 local、staging、production。 |
| `APP_TIMEZONE` | 服务端业务时区，使用 Asia/Shanghai。 |
| `PUBLIC_BASE_URL` | 前端公开访问地址。 |
| `API_BASE_URL` | HTTP API 地址。 |
| `WS_BASE_URL` | WebSocket 地址，生产使用 WSS。 |
| `LOG_LEVEL` | 日志级别。 |

### 6.2 数据库和 Redis

| 变量名 | 用途 |
|---|---|
| `DATABASE_URL` | PostgreSQL 连接串。 |
| `REDIS_URL` | Redis 连接串。 |
| `POSTGRES_DB` | PostgreSQL 数据库名。 |
| `POSTGRES_USER` | PostgreSQL 用户名。 |
| `POSTGRES_PASSWORD` | PostgreSQL 密码。 |
| `REDIS_PASSWORD` | Redis 密码。 |

### 6.3 配额和成本

| 变量名 | 用途 |
|---|---|
| `DAILY_FREE_SECONDS` | 每个匿名用户每日额度，默认 2400。 |
| `SESSION_MAX_SECONDS` | 单场会议上限，默认 1800。 |
| `MAX_ACTIVE_SESSIONS_PER_CLIENT` | 同一匿名用户并发上限，默认 1。 |
| `MONTHLY_BUDGET_RMB` | 月度预算参考值，默认 500。 |
| `BUDGET_FUSE_RMB` | 预算保险丝阈值，建议 400。 |

### 6.4 Provider 和 COS

| 变量名 | 用途 |
|---|---|
| `GOOGLE_APPLICATION_CREDENTIALS` | Google 服务账号 JSON 路径。 |
| `GOOGLE_CLOUD_PROJECT` | Google Cloud 项目 ID。 |
| `GOOGLE_STT_LOCATION` | Google STT region。 |
| `GOOGLE_STT_RECOGNIZER` | Google STT recognizer。 |
| `QWEN_API_KEY` | 阿里云百炼 API Key。 |
| `QWEN_BASE_URL` | Qwen OpenAI-compatible endpoint。 |
| `QWEN_INTERIM_MODEL` | 中文 interim 模型。 |
| `OPENAI_API_KEY` | OpenAI API Key。 |
| `OPENAI_BASE_URL` | OpenAI API base URL。 |
| `OPENAI_FINAL_MODEL` | 中文 final 模型。 |
| `TENCENT_COS_SECRET_ID` | COS SecretId。 |
| `TENCENT_COS_SECRET_KEY` | COS SecretKey。 |
| `TENCENT_COS_REGION` | COS 地域。 |
| `TENCENT_COS_BUCKET` | COS Bucket 名称。 |

验证测试：后端启动时打印已加载配置项名称和脱敏状态，不打印任何密钥值。

预期结果：必填配置缺失时服务拒绝启动并给出明确配置名；密钥永不进入前端构建产物。

## 7. Codex 执行验证流程

### 7.1 前端验证

执行位置：Windows 本地前端目录。

验证命令：

```powershell
npm install
npm run lint
npm run test
npm run build
npm run test:e2e
```

预期结果：依赖安装成功，lint、单元测试、构建和端到端测试均通过。

### 7.2 后端本地轻量验证

执行位置：Windows 本地后端目录。

验证命令：

```powershell
uv python install 3.12
uv python pin 3.12
uv sync
uv run python --version
uv run ruff check .
uv run mypy .
uv run pytest
```

预期结果：项目 `.venv` 使用 Python 3.12.x；依赖同步成功；Ruff、mypy 和不依赖真实 PostgreSQL/Redis 的 pytest 均通过。

### 7.3 云服务器 Docker Compose 验证

执行位置：通过 SSH 登录腾讯云 Lighthouse 后，在云服务器的项目部署目录执行。

验证命令：

```bash
docker compose config
docker compose up -d
docker compose ps
```

预期结果：配置合法，PostgreSQL、Redis、后端和 Caddy 容器处于 running 或 healthy 状态。

### 7.4 云服务器数据库与 Redis 验证

执行位置：通过 SSH 登录腾讯云 Lighthouse 后执行。

验证命令：

```bash
docker compose ps
docker compose exec backend uv run alembic upgrade head
docker compose exec backend uv run pytest -m integration
```

预期结果：Alembic migration 在云端 PostgreSQL 上执行成功；需要真实 PostgreSQL/Redis 的集成测试在云端通过。

## 8. 生产部署前检查

| 检查项 | 验证方式 | 通过标准 |
|---|---|---|
| 域名解析 | `nslookup 你的工具域名` | 解析到 Lighthouse 公网 IP。 |
| HTTPS | 浏览器访问生产域名 | Caddy 自动签发证书，页面通过 HTTPS 打开。 |
| WSS | 前端连接 `/ws/*` | WebSocket 连接成功，不被浏览器安全策略阻止。 |
| PostgreSQL | 后端健康检查或 migration | 数据库可连接，migration 已执行。 |
| Redis | 后端健康检查 | Redis 可连接，可写入 active session。 |
| Google STT | Provider smoke test | 英文 interim 和 final 可产生。 |
| Qwen | Provider smoke test | 中文 interim 可返回。 |
| OpenAI | Provider smoke test | 中文 final 可返回。 |
| COS | 导出 smoke test | Markdown / JSON 文件可上传。 |
| 预算保险丝 | 后端配置检查 | 阈值为 400 RMB，触发后拒绝新会话。 |

## 9. 常见故障排查

### 9.1 Windows 无法捕获会议音频

检查顺序：

1. 确认使用 Chrome 或 Edge。
2. 确认页面通过 HTTPS 或 localhost 打开。
3. 重新选择会议标签页，并勾选共享音频。
4. 腾讯会议网页版标签页音频不可用时，改用整个屏幕或系统音频。
5. 检查浏览器是否阻止屏幕共享权限。

预期结果：能检测到音频电平；若只能系统音频成功，应记录为 `system_audio_only`。

### 9.2 云服务器端口不可访问

检查顺序：

1. 检查腾讯云安全组是否开放 80 和 443。
2. 检查 Ubuntu 防火墙是否允许 80 和 443。
3. 检查 Caddy 容器是否运行。
4. 检查域名是否解析到当前公网 IP。

预期结果：浏览器能访问 HTTPS 页面，WebSocket 能通过 WSS 连接。

### 9.3 Provider 调用失败

检查顺序：

1. 检查环境变量名称是否一致。
2. 检查 API Key 是否仍有效。
3. 检查模型名和 endpoint 是否正确。
4. 检查服务器能访问外部 Provider 网络。
5. 查看后端结构化日志中的 provider、code、recoverable 字段。

预期结果：错误能定位到具体 Provider 和错误码；Qwen interim 失败不阻塞英文转写和中文 final。

### 9.4 PostgreSQL 或 Redis 数据丢失风险

检查顺序：

1. 确认 Docker Compose 使用持久化 volume 或宿主机数据目录。
2. 确认 `/opt/meeting_mvp/data/postgres` 和 `/opt/meeting_mvp/data/redis` 存在。
3. 上线前备份 PostgreSQL。
4. 版本升级前先在测试环境执行 migration。

预期结果：容器重启不会丢失 PostgreSQL 数据；Redis 可接受短期状态丢失但不应影响已归档 final 片段。

## 10. 环境准备完成标准

- Windows 本地具备 Git、Node.js 24 LTS、npm、系统 Python、uv、Chrome、Edge、VS Code、SSH 客户端。
- 系统 Python 允许为 Python 3.13.9，但后端项目 `.venv` 必须由 uv 固定为 Python 3.12。
- 后端目录具备 `pyproject.toml`、`uv.lock` 和 `.python-version`；`.venv` 可由 `uv sync` 重建且不提交 Git。
- Windows 本地不安装 Docker、PostgreSQL、Redis。
- 本地能运行前端检查、后端轻量检查和浏览器测试。
- 腾讯云 Lighthouse 使用 Ubuntu 22.04 LTS 64 位 x86，Docker 和 Compose 可用。
- 域名解析到服务器，80 和 443 可访问，5432 和 6379 不对公网开放。
- PostgreSQL 16、Redis 7、Caddy、FastAPI、前端静态产物具备部署位置。
- 需要真实 PostgreSQL、Redis、Docker Compose 的验证都能通过 SSH 在 Lighthouse 上执行。
- Google STT、Qwen、OpenAI、Tencent COS 凭证已准备并安全保存。
- 所有密钥只进入后端环境变量或服务器安全配置，不进入 Git。
- 腾讯会议网页版标签页音频失败时，已接受系统音频作为第一版验证降级入口。
