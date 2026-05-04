# Meeting MVP 正式设计文档

## 1. 产品定位

Meeting MVP 是一个免登录网页效率工具，面向需要参加英语线上会议的中国职场用户。用户打开工具网页后，通过浏览器授权捕获会议网页音频，工具实时展示英文转写、中文翻译、当前重点句和会议时间线，并在会后生成完整可追溯的双语会议档案。

第一版以高质量体验优先，允许承担一定 API 成本。产品优先把英语会议场景做准，重点追求英文实时转写准确、中文表达自然、阅读界面清晰、会后记录完整、免费额度可控。

## 2. 第一版范围

### 范围内

- 免登录免费使用，通过匿名用户做额度控制。
- 每个匿名用户每天免费 40 分钟。
- 单场会议最长 30 分钟。
- 第一版重点支持 Google Meet、Microsoft Teams Web、Zoom Web、腾讯会议网页版。
- 优先通过浏览器捕获会议标签页音频。
- 当标签页音频不可用时，允许降级为整个屏幕/系统音频捕获，重点覆盖腾讯会议网页版兼容性风险。
- 英文实时转写主用 Google Speech-to-Text。
- 保留 OpenAI STT provider 架构，用于备用或后续对比，但第一版生产主路径是 Google STT。
- 中文 interim 临时理解使用阿里云百炼 Qwen Flash/Turbo。
- 中文 final 正式翻译使用阿里云百炼 Qwen `qwen3.6-max-preview`，生成语义准确、自然、适合中国职场阅读的中文表达。
- OpenAI 翻译不作为第一版主路径，仅在 Lighthouse 网络可达或后续需要质量对比时作为可选扩展。
- 实时 UI 至少包含四块：英文原文区、中文翻译区、当前重点句区、会议时间线区。
- 会后纪要偏“会议原文归档型”，重点是完整可追溯，而不是第一版就做复杂总结。
- M1-A 必须包含基础归档页；用户通过 `session_id + archive_token` 查看已生成的 final 片段，搜索、复制和导出放到 M2。
- PostgreSQL 存结构化记录，Redis 做实时会话/额度/限流，腾讯 COS 存导出文件。
- 基础埋点、使用量统计和成本估算。

### 第一版暂不做

- 用户账号、登录、跨设备账号历史。
- 浏览器插件注入会议页面。
- 桌面客户端或虚拟音频设备。
- 完整 BI 系统。
- 高强度防刷；免登录额度只能防普通滥用。
- 云服务器本地自建重型 ASR。
- 多语言会议泛化；第一版先聚焦英语会议。

## 3. 产品体验

### 实时会议页

第一屏就是工具工作台，不做营销落地页。

- 顶部状态栏：
  - 开始捕获会议音频。
  - 当前捕获模式：标签页音频 / 系统音频。
  - 音频输入状态和音量电平。
  - 今日剩余额度。
  - ASR 和翻译状态。
  - 结束会议、导出入口。
- 主区域：
  - 英文原文区。
  - 中文翻译区。
- 侧边区域：
  - 当前重点句区。
  - 会议时间线区。
- 会后记录页：
  - 双语逐段归档。
  - 搜索。
  - 复制。
  - 第一阶段支持 Markdown / JSON 导出。
  - Word 导出可在归档模型稳定后加入。

### 实时文本状态

- 英文 interim：作为临时预览显示，样式要明显区别于正式内容。
- 英文 final：作为正式英文片段进入会议档案。
- 中文 interim：作为“临时理解”显示，允许不完美，不进入正式档案。
- 中文 final：替换临时中文，成为正式中文翻译并进入归档。
- 会后正式档案只保存英文 final 和中文 final。

## 4. 技术架构

第一版采用前后端分离。

- 前端：Vite、React、TypeScript。
- 后端：FastAPI、Python。
- 实时通信：浏览器与后端通过 WebSocket。
- 英文转写：Google Speech-to-Text streaming 作为主 provider。
- 中文 interim：阿里云百炼 Qwen Flash/Turbo。
- 中文 final：阿里云百炼 Qwen `qwen3.6-max-preview`。
- 数据库：PostgreSQL。
- 运行时状态：Redis。
- 导出文件：腾讯 COS。
- 部署：腾讯云 Lighthouse，Ubuntu 22.04 LTS 64 位，x86 架构；服务器中部署 Docker、PostgreSQL、Redis。

核心链路：

```text
浏览器会议音频
-> 工具页捕获音频
-> AudioWorklet 生成 16 kHz mono PCM16
-> WebSocket 上传音频片段
-> FastAPI 会话编排
-> Google STT streaming
-> 英文 interim/final 事件
-> Qwen 生成中文 interim
-> Qwen qwen3.6-max-preview 生成中文 final
-> WebSocket 推送 UI
-> PostgreSQL 保存 final 档案
-> 腾讯 COS 保存导出文件
-> Redis 管理会话、额度和限流状态
```

## 5. 音频捕获策略

第一版采用三级策略。

1. 首选：会议浏览器标签页音频。
   - 用户在浏览器弹窗中选择正在开会的标签页。
   - 用户勾选共享音频。
   - 作为 Google Meet、Teams Web、Zoom Web、腾讯会议网页版的默认路径。

2. 降级：整个屏幕/系统音频。
   - 当腾讯会议网页版或某些浏览器环境无法稳定捕获标签页音频时使用。
   - UI 必须明确提示：系统音频模式可能捕获其他应用声音。

3. 失败提示。
   - 如果检测不到音频，提示用户更换 Chrome/Edge、检查共享音频选项或切换捕获模式。
   - 没有检测到有效音频前，不应正式消耗会议额度。

第一版主要浏览器目标：Windows Chrome 和 Edge。

浏览器侧音频前处理使用 `getDisplayMedia` 获取会议标签页或系统音频，再通过 Web Audio API / `AudioWorklet` 转成 Google STT 友好的 16 kHz、mono、PCM16 音频帧，通过 WebSocket binary frame 上传。第一版不把 FFmpeg/WebM 服务端转码作为主路径，避免在单台 Lighthouse 服务器上引入额外 CPU、延迟和故障点。

## 6. Provider 设计

Provider 抽象保持轻量。第一版目标是可替换、可对比、可降级，而不是做复杂插件框架。

### STT Provider

STT provider 需要支持：

- 启动会话并接收语言、音频格式等配置。
- 接收音频 chunk。
- 输出英文 interim 事件。
- 输出英文 final 事件。
- 关闭会话。

第一版实现：

- `GoogleStreamingSTTProvider`：生产主路径。
- `OpenAISTTProvider`：备用/对比路径，可以先作为管理员实验入口，不要求第一阶段完整替代 Google STT。

### 翻译 Provider

中文 interim：

- Provider：Qwen Flash/Turbo。
- 触发条件：节流后的英文 interim。
- 目标：快速解释当前英文大意。
- Prompt 要求：简洁、自然、不扩写、不添加原文没有的信息。
- 归档规则：不进入正式会议档案。

中文 final：

- Provider：阿里云百炼 Qwen `qwen3.6-max-preview`。
- 环境变量：`QWEN_FINAL_MODEL=qwen3.6-max-preview`。
- 触发条件：英文 final segment。
- 目标：语义准确、表达自然、适合中国职场用户快速阅读。
- Prompt 要求：保留含义、决策、行动项、语气、人名、数字和业务上下文。
- 上下文：默认带最近 5 个 final segment。
- 归档规则：与英文 final 一起进入正式会议档案。
- OpenAI 翻译：保留为后续备用/质量对比，不阻塞第一版 MVP。

## 7. WebSocket 协议

浏览器发给后端：

- `session_start`
- `audio_chunk`
- `heartbeat`
- `session_stop`

后端推给浏览器：

- `session_started`
- `quota_update`
- `audio_status`
- `asr_interim`
- `translation_interim`
- `segment_final`
- `key_sentence_update`
- `timeline_update`
- `warning`
- `error`
- `session_closed`

前端处理规则：

- interim 消息是可替换状态。
- final 消息是追加状态。
- 归档页只基于 final 数据重建。
- `session_started` 必须返回 `session_id`、`archive_token`、`archive_url` 和今日剩余额度；服务端只保存 `archive_token` 的 hash。

## 8. 数据模型

### `anonymous_client`

- `client_id`
- `first_seen_at`
- `last_seen_at`
- `daily_minutes_used`
- `created_ip_hash`
- `user_agent_hash`

### `meeting_session`

- `id`
- `client_id`
- `title`
- `source_platform`
- `capture_mode`
- `started_at`
- `ended_at`
- `duration_seconds`
- `status`，包含 `pending_audio`、`active`、`ended`、`quota_stopped`、`error`
- `quota_seconds_consumed`
- `archive_token_hash`
- `retention_expires_at`

### `transcript_segment`

- `id`
- `session_id`
- `sequence`
- `start_ms`
- `end_ms`
- `english_text_final`
- `chinese_text_final`
- `speaker_label`
- `is_key_sentence`
- `asr_confidence`
- `translation_status`
- `created_at`

### `usage_event`

- `id`
- `client_id`
- `session_id`
- `event_type`
- `payload`
- `created_at`

### `export_file`

- `id`
- `session_id`
- `format`
- `cos_object_key`
- `cos_url`，用于短期签名 URL 或临时访问地址
- `created_at`
- `retention_expires_at`

## 9. 配额、成本和防滥用

匿名额度：

- 每日额度：每个匿名用户 40 分钟。
- 单场会议：最多 30 分钟。
- 并发限制：同一匿名用户最多 1 个活跃会议。
- 匿名识别：`client_id` + IP hash + User-Agent hash。
- 日期刷新：服务端按 Asia/Shanghai 自然日刷新。

成本控制：

- 记录 Google STT 分钟数。
- 记录 Qwen interim 请求量和 token。
- 记录 Qwen final 翻译请求量和 token。
- 估算每场会议、每日、每月成本。
- 增加全站月度预算保险丝，初始建议阈值 400 RMB。
- 触发预算保险丝后，拒绝新会话，但保留已有档案查看和导出。

防滥用边界：

- 免登录额度不能完全防刷。
- 第一版以 10 到 50 人测试群体为目标，先防普通滥用。
- 如果使用规模扩大，再增加邀请码、登录或付费额度。

## 10. 部署设计

第一版目标部署环境：

- 腾讯云 Lighthouse。
- Ubuntu 22.04 LTS 64 位。
- x86 架构。
- 服务器安装 Docker。
- PostgreSQL 和 Redis 通过 Docker 部署在同一台服务器中。
- 后端作为 Docker 容器部署。
- 前端由 Vite 构建为静态产物，通过 Caddy 直接服务。
- Caddy 同时负责 HTTPS/WSS 终止，并把 API 与 WebSocket 请求反向代理到 FastAPI 后端容器。
- TLS：必须启用，因为浏览器音频捕获和安全 WebSocket 都依赖 HTTPS/WSS 场景。
- 对象存储：腾讯 COS 存导出文件。

单机部署足够支撑第一版 10 到 50 个测试用户，但数据库、Redis、对象存储和 API provider 配置必须通过环境变量外置，方便后续迁移到托管服务。

## 11. 里程碑

### M1：实时核心闭环

- Vite + React 实时会议页。
- 浏览器捕获标签页音频和系统音频降级。
- FastAPI WebSocket 会话端点。
- 匿名 client ID。
- 每日和单场额度限制。
- Google STT streaming 主链路。
- Qwen 中文 interim 链路。
- Qwen `qwen3.6-max-preview` 中文 final 链路。
- 四区实时阅读 UI。
- PostgreSQL 保存 final 片段。
- 基础归档页按顺序展示 final 片段，访问方式为 `session_id + archive_token`。

### M2：会后归档增强与导出

- 搜索。
- 复制。
- Markdown 导出。
- JSON 导出。
- 腾讯 COS 存私有导出文件，后端返回短期签名 URL。
- final 翻译失败后的重试机制。

### M3：成本与运营

- 使用量看板。
- 每日和每月成本估算。
- Provider 状态和开关。
- 错误率和延迟指标。
- 全站预算保险丝。
- OpenAI STT/翻译备用或对比入口。

## 12. 验收标准

- Windows Chrome / Edge 中，用户能捕获 Google Meet、Teams Web、Zoom Web、腾讯会议网页版音频。
- 腾讯会议网页版优先支持标签页音频；失败时支持系统音频降级。
- 讲话时英文 interim 能实时出现。
- 英文 final 片段稳定追加到档案。
- 中文 interim 由 Qwen 生成，并以受控频率更新。
- 中文 final 在英文 final 后生成，表达自然、符合中国职场阅读习惯。
- 四个 UI 区域能独立更新，不互相阻塞。
- 基础归档页能通过 `session_id + archive_token` 查看英文 final、中文 final、时间戳、序号和时间线。
- 未登录用户每天不能超过 40 分钟，单场不能超过 30 分钟。
- 全站月度预算达到阈值后，系统能拒绝新会话。
- 能基于归档 final 片段生成 Markdown 和 JSON 导出文件，并通过腾讯 COS 短期签名 URL 下载。

## 13. 关键假设

- 第一批测试用户为 10 到 50 人。
- 每月预算为 0 到 500 RMB。
- 产品方接受会议音频和文本发送给第三方 AI API 处理。
- Google STT、阿里云百炼、PostgreSQL、Redis、腾讯 COS 的凭据都通过环境变量提供。
- 第一版中文 final 模型通过 `QWEN_FINAL_MODEL` 配置，默认 `qwen3.6-max-preview`。
- 腾讯云 Lighthouse 当前无法稳定访问 OpenAI 官方 `api.openai.com:443`，因此 OpenAI 不作为第一版生产主路径。
- 第一版不需要登录。
- 第一版默认不存原始会议音频，只存正式文本档案和导出文件。
- 会议归档和 COS 导出默认保留 30 天。
- `ScienceIO/whisper_streaming_web` 作为 WebSocket 和音频流处理参考，不作为最终项目结构直接照搬。
