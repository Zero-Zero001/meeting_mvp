# Meeting MVP 架构记录

## 2026-05-04 Step 01 基线架构洞察

### 当前仓库状态

- 仓库根目录为 `D:\meeting_mvp`。
- Git 远端为 `https://github.com/Zero-Zero001/meeting_mvp.git`。
- 当前应用工程目录边界已建立；根目录下已有 `frontend/`、`backend/`、`deploy/`、`scripts/`、`tests/`，但前端和后端工程骨架尚未初始化。
- 当前有效产品、技术、部署和实施依据集中在 `memory-bank/`。
- Step 01 完成基线确认和文档记录；Step 02 已建立工程目录边界，未进入 Step 03。

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
| `frontend/` | 前端工程边界目录；后续 Step 03 初始化 Vite + React + TypeScript 工程，承载实时会议工作台、归档页、前端状态管理、音频捕获和前端测试。 |
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

- 下一步 Step 03 才能初始化 `frontend/` 工程；当前不得创建 `frontend/package.json` 或安装前端依赖。
- Step 04 才能初始化 `backend/` 工程；当前不得创建 `backend/pyproject.toml`、`backend/uv.lock` 或项目级 `.venv`。
- 前端不得暴露任何 Provider 密钥。
- 第一版默认不保存原始会议音频，只保存 final 文本档案和导出文件。
- 服务端只保存 `archive_token` hash，不保存明文 token。
- Windows 本地不安装 Docker、PostgreSQL、Redis；相关验证在腾讯云 Lighthouse 或后续 CI 环境执行。
