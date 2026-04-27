# 需求背景

## 背景

### 用户画像与使用场景

许多中国职场工作者需要参加英语线上会议，但在真实会议中，发言速度、口音、专业术语、多人轮流发言和上下文跳转都会显著增加理解成本。用户需要一个打开网页即可使用的效率工具，在不安装插件或桌面客户端的前提下，帮助他们实时理解英语会议，并在会后获得可追溯的双语会议记录。

| 用户画像 | 典型背景 | 主要痛点 | 使用场景 | 成功结果 |
|---|---|---|---|---|
| 英语会议参与者 | 中国职场中的产品、研发、运营、项目成员，需要参加跨境或外企英语会议。 | 听不完整、跟不上节奏、无法快速理解业务含义。 | 会议开始前打开工具页，捕获 Google Meet、Teams、Zoom 或腾讯会议网页版音频，实时阅读英文原文和中文翻译。 | 会议中能持续理解讨论内容，关键观点不漏听，会后可回看对应原文。 |
| 会议记录者 / 项目负责人 | 需要负责会后复盘、同步结论或整理项目背景的人。 | 会议中难以同时听、理解、记录，会后缺少可追溯材料。 | 会议结束后查看双语归档，搜索关键片段，复制或导出 Markdown / JSON。 | 能基于完整片段整理纪要、任务和背景，不依赖模糊记忆。 |
| 跨境协作业务人员 | 销售、客服、解决方案或客户成功人员，需要和英语客户或海外团队沟通。 | 更关注中文表达是否能快速读懂，而不是逐词硬翻。 | 实时查看“更像中国职场表达”的中文 final，并通过当前重点句把握客户需求或风险。 | 能在会议中及时跟进问题，会后可复盘客户原话和中文理解。 |
| MVP 测试 / 运营观察者 | 产品负责人或开发者，需要判断第一版是否值得继续做。 | 不知道用户卡在哪一步、质量是否达标、成本是否失控。 | 查看首次使用漏斗、会议质量漏斗、价值验证漏斗和成本指标。 | 能判断核心价值是否成立，并定位下一阶段改造重点。 |

### 产品定位

Meeting MVP 是一个免登录网页工具。用户打开工具网页，授权捕获正在进行的网页会议音频，系统实时生成英文转写、中文临时理解、中文正式翻译、重点句和会议时间线，并在会后生成完整双语归档。

第一版以高质量体验优先，允许承担一定 API 成本。核心目标不是做泛用字幕工具，而是先把英语会议场景做准，让中国职场用户能快速读懂会议内容。

## 现状或问题

### 用户理解成本高

英语会议中，用户常见问题包括：

- 听不清发言者的完整英文句子。
- 能听到词，但无法快速理解业务含义。
- 会议节奏快，来不及边听边记录。
- 会后缺少完整、可追溯的双语记录。
- 会议平台自带字幕或翻译能力受账号、平台、语言和会议设置限制。

### 现有工具不完全匹配

竞品和会议平台通常能覆盖部分需求，但第一版产品需要解决以下差距：

- 平台内置字幕不一定支持高质量英中翻译。
- 会议记录工具更偏总结和自动纪要，未必保留逐段原文和翻译对应关系。
- 浏览器插件和桌面客户端安装门槛高，不适合作为第一版验证路径。
- 免登录使用和成本控制需要产品内建配额、预算保险丝和埋点。

## 需求价值

### 对用户的价值

- 实时降低英语会议理解成本。
- 将英文原文和中文职场表达并排呈现，降低误解。
- 会后可搜索、复制、导出完整双语记录。
- 在不登录、不安装插件的情况下完成第一版核心体验。

### 对产品验证的价值

- 验证“英语会议实时理解 + 中文归档”是否成立。
- 通过配额、成本和埋点验证 API 成本结构。
- 为后续登录、付费、插件、桌面客户端或团队版能力提供基础数据。

## 目的

### 第一版目标

构建一个可供 10 到 50 名测试用户使用的网页工具，满足以下目标：

- 支持 Windows Chrome / Edge。
- 重点支持 Google Meet、Microsoft Teams Web、Zoom Web、腾讯会议网页版。
- 支持标签页音频捕获，失败时支持系统音频降级。
- 实时输出英文 interim、英文 final、中文 interim、中文 final。
- 使用四区 UI 呈现英文原文、中文翻译、当前重点句和会议时间线。
- 会后生成以原文归档为主的双语会议档案。
- 对匿名用户执行每日 40 分钟、单场 30 分钟的免费额度限制。
- 支持 Markdown / JSON 导出。
- 记录基础使用、成本、延迟和错误事件。

# 整体设计思路

## 产品与技术总览

第一版采用静态前端 + FastAPI 后端 + PostgreSQL + Redis + Caddy 的单机部署架构。云服务器只做编排、存储、配额、Provider 调用和 UI 推送，不自建重型 ASR。

```mermaid
flowchart LR
  User["用户"] --> Browser["Vite + React 工具页"]
  Browser --> Capture["getDisplayMedia 捕获会议标签页或系统音频"]
  Capture --> Worklet["AudioWorklet 转 mono PCM16"]
  Worklet --> WS["WebSocket binary audio frames"]
  WS --> Backend["FastAPI 会话编排"]
  Backend --> Quota{"额度与预算是否允许"}
  Quota -- "否" --> Reject["拒绝新会话或停止消耗"]
  Quota -- "是" --> Google["Google STT streaming"]
  Google --> InterimEN["英文 interim"]
  Google --> FinalEN["英文 final"]
  InterimEN --> Qwen["Qwen Flash/Turbo 中文 interim"]
  FinalEN --> OpenAI["OpenAI 中文 final"]
  Qwen --> Push["WebSocket 推送实时 UI"]
  OpenAI --> Push
  OpenAI --> PG["PostgreSQL final 归档"]
  Backend --> Redis["Redis 会话/额度/限流"]
  PG --> Export["Markdown / JSON 导出"]
  Export --> COS["腾讯 COS"]
```

## 实时会议主流程

```mermaid
flowchart TD
  Start["用户打开工具页"] --> Client{"本地是否已有 client_id"}
  Client -- "否" --> CreateClient["生成匿名 client_id 并本地保存"]
  Client -- "是" --> CheckBudget["请求额度状态"]
  CreateClient --> CheckBudget
  CheckBudget --> Budget{"全站预算和用户额度是否允许"}
  Budget -- "否" --> BudgetStop["展示额度或预算不足，不允许开始会议"]
  Budget -- "是" --> CaptureStart["用户点击开始捕获"]
  CaptureStart --> CaptureOk{"标签页音频捕获是否成功"}
  CaptureOk -- "否" --> Fallback["提示切换系统音频捕获"]
  Fallback --> FallbackOk{"系统音频捕获是否成功"}
  FallbackOk -- "否" --> CaptureFail["展示捕获失败原因和浏览器建议"]
  CaptureOk -- "是" --> AudioDetect["检测音频电平"]
  FallbackOk -- "是" --> AudioDetect
  AudioDetect --> HasAudio{"是否检测到有效音频"}
  HasAudio -- "否" --> NoCharge["不消耗额度，提示检查共享音频"]
  HasAudio -- "是" --> Session["创建 meeting_session"]
  Session --> Stream["上传 PCM16 音频帧"]
  Stream --> STT{"Google STT 是否正常"}
  STT -- "否" --> SttError["推送错误，关闭会话或进入备用路径"]
  STT -- "是" --> EnEvents["接收英文 interim/final"]
  EnEvents --> InterimCN{"是否满足 interim 节流条件"}
  InterimCN -- "是" --> QwenCN["请求 Qwen 中文临时理解"]
  InterimCN -- "否" --> UIInterim["只更新英文 interim"]
  QwenCN --> UIInterim
  EnEvents --> FinalSeg{"是否产生英文 final"}
  FinalSeg -- "否" --> Continue["继续监听"]
  FinalSeg -- "是" --> FinalCN["请求 OpenAI 中文正式翻译"]
  FinalCN --> Save["保存 final 英文 + final 中文"]
  Save --> Timeline["更新时间线和归档"]
  Timeline --> Continue
  Continue --> End{"用户结束或达到额度/单场上限"}
  End -- "否" --> Stream
  End -- "是" --> Close["关闭 Provider、结算额度、生成会后记录"]
```

## WebSocket 时序

```mermaid
sequenceDiagram
  participant FE as Browser Frontend
  participant API as FastAPI WebSocket
  participant Redis as Redis
  participant STT as Google STT
  participant Qwen as Qwen Interim
  participant OpenAI as OpenAI Final
  participant DB as PostgreSQL

  FE->>API: session_start(client_id, capture_mode, source_platform)
  API->>Redis: check quota, active session, budget fuse
  Redis-->>API: allowed / denied
  API-->>FE: quota_update + session_started
  FE->>API: audio_chunk(binary PCM16)
  API->>STT: stream audio
  STT-->>API: asr_interim
  API-->>FE: asr_interim
  API->>Qwen: throttled interim translation
  Qwen-->>API: translation_interim
  API-->>FE: translation_interim
  STT-->>API: asr_final
  API->>OpenAI: final translation with recent context
  OpenAI-->>API: chinese_text_final
  API->>DB: insert transcript_segment
  API-->>FE: segment_final + timeline_update
  FE->>API: session_stop
  API->>Redis: settle quota and clear active session
  API->>DB: update meeting_session ended_at/status
  API-->>FE: session_closed
```

## 分层设计

### 前端层

前端负责音频捕获、浏览器音频前处理、实时状态展示、会后归档查询和导出入口。第一版使用 Vite + React + TypeScript，静态产物由 Caddy 服务。

### 后端编排层

后端负责 WebSocket 会话、额度、限流、Provider 调用、归档、导出、埋点和错误处理。后端不做重型 ASR 推理。

### Provider 层

Provider 层保持轻量接口：

- Google STT 主用，输出英文 interim/final。
- OpenAI STT 保留备用/对比接口。
- Qwen 负责中文 interim。
- OpenAI 文本模型负责中文 final。

### 数据层

PostgreSQL 保存正式记录，Redis 保存短期状态，腾讯 COS 保存导出文件。第一版默认不存原始会议音频。

# 名词解释

| 名词 | 定义 |
|---|---|
| Meeting MVP | 本项目第一版会议实时理解工具。 |
| 匿名用户 | 未登录用户，通过浏览器本地 `client_id` 加服务端 IP hash、User-Agent hash 做弱识别。 |
| `client_id` | 前端首次访问生成并本地保存的匿名用户标识。 |
| 会议标签页音频 | 浏览器通过 `getDisplayMedia` 捕获指定会议网页标签页时附带的音频。 |
| 系统音频 | 浏览器捕获整个屏幕或系统声音时获得的音频，可能包含非会议声音。 |
| interim | 临时结果，可替换，不进入正式档案。 |
| final | 稳定确认结果，追加进入正式档案。 |
| 英文 interim | Google STT 实时返回的临时英文转写。 |
| 英文 final | Google STT 返回的稳定英文转写片段。 |
| 中文 interim | Qwen 基于英文 interim 生成的临时中文理解。 |
| 中文 final | OpenAI 基于英文 final 和上下文生成的正式中文翻译。 |
| AudioWorklet | 浏览器 Web Audio API 的音频处理机制，用于将捕获音频转为 mono PCM16。 |
| mono PCM16 | 单声道 16-bit PCM 音频帧，适合流式 STT 识别。 |
| WebSocket binary frame | WebSocket 的二进制消息，用于上传 PCM16 音频帧。 |
| Provider | 外部能力适配器，例如 Google STT、Qwen、OpenAI、腾讯 COS。 |
| 预算保险丝 | 当全站月度预估成本超过阈值时，系统拒绝新会话以控制成本。 |
| 原文归档型纪要 | 以逐段英文原文和中文翻译对应关系为核心的会后记录，而不是仅保留摘要。 |
| 会议时间线 | 按时间顺序展示 final 片段、重点句和导出节点的记录线。 |

## WebSocket 消息名解释

| 消息名 | 方向 | 定义 |
|---|---|---|
| `session_start` | 前端到后端 | 请求创建实时会议会话，携带匿名身份、捕获模式、会议平台和音频格式。 |
| `audio_chunk` | 前端到后端 | 上传浏览器处理后的 mono PCM16 音频帧，使用 WebSocket binary frame 承载。 |
| `heartbeat` | 前端到后端 | 连接保活与断连探测消息，用于避免异常会话长期占用额度和并发。 |
| `session_stop` | 前端到后端 | 用户主动结束会议时发送，触发 Provider 关闭、额度结算和会后归档收尾。 |
| `quota_update` | 后端到前端 | 推送匿名用户当前额度状态，包括今日剩余额度和额度变化。 |
| `audio_status` | 后端到前端 | 推送音频检测状态，例如是否检测到有效声音和当前音量电平。 |
| `asr_interim` | 后端到前端 | 推送英文临时转写结果，内容可被后续更稳定结果替换。 |
| `translation_interim` | 后端到前端 | 推送中文临时理解结果，用于实时辅助阅读，不进入正式归档。 |
| `segment_final` | 后端到前端 | 推送已确认并归档的双语 final 片段，是会后记录的核心数据来源。 |
| `key_sentence_update` | 后端到前端 | 推送当前重点句，用于帮助用户快速抓住正在讨论的关键表达。 |
| `timeline_update` | 后端到前端 | 推送会议时间线节点更新，包括 final 片段、重点句、导出或异常节点。 |
| `warning` | 后端到前端 | 推送可恢复问题，例如无音频、额度接近上限、临时 Provider 失败。 |
| `error` | 后端到前端 | 推送不可忽略错误，例如核心 Provider 不可用、会话无法继续。 |
| `session_closed` | 后端到前端 | 通知会话已关闭，并说明关闭原因，例如用户停止、额度耗尽或 Provider 错误。 |

# 字段说明

## 数据表字段

### `anonymous_client`

| 字段 | 类型建议 | 必填 | 定义 |
|---|---:|---:|---|
| `client_id` | string/uuid | 是 | 匿名用户唯一标识，由前端首次访问生成，服务端保存并用于额度统计。 |
| `first_seen_at` | timestamptz | 是 | 首次访问时间。 |
| `last_seen_at` | timestamptz | 是 | 最近访问或活跃时间。 |
| `daily_minutes_used` | numeric/int | 是 | 当前自然日已消耗分钟数，可由事件聚合，也可缓存冗余。 |
| `created_ip_hash` | string | 是 | 首次访问 IP 的 hash，不保存明文 IP。 |
| `user_agent_hash` | string | 是 | User-Agent 的 hash，用于辅助匿名识别和防普通滥用。 |

### `meeting_session`

| 字段 | 类型建议 | 必填 | 定义 |
|---|---:|---:|---|
| `id` | string/uuid | 是 | 会议会话唯一标识。 |
| `client_id` | string/uuid | 是 | 所属匿名用户。 |
| `title` | string | 否 | 会议标题，默认可由时间和平台生成，用户后续可编辑。 |
| `source_platform` | enum/string | 是 | 会议来源平台，取值建议：`google_meet`、`teams_web`、`zoom_web`、`tencent_meeting_web`、`unknown`。 |
| `capture_mode` | enum/string | 是 | 捕获模式，取值：`tab_audio`、`system_audio`。 |
| `started_at` | timestamptz | 是 | 会话正式开始时间，应在检测到有效音频并创建后端会话后记录。 |
| `ended_at` | timestamptz | 否 | 会话结束时间。 |
| `duration_seconds` | int | 是 | 会话有效时长，按实际消耗额度的音频时长计算。 |
| `status` | enum/string | 是 | 状态，建议：`active`、`ended`、`quota_stopped`、`error`。 |
| `quota_seconds_consumed` | int | 是 | 本场会议实际消耗的免费额度秒数。 |

### `transcript_segment`

| 字段 | 类型建议 | 必填 | 定义 |
|---|---:|---:|---|
| `id` | string/uuid | 是 | 转写片段唯一标识。 |
| `session_id` | string/uuid | 是 | 所属会议会话。 |
| `sequence` | int | 是 | 片段序号，从 1 递增，用于重建会议顺序。 |
| `start_ms` | int | 是 | 片段在会议中的开始毫秒。 |
| `end_ms` | int | 是 | 片段在会议中的结束毫秒。 |
| `english_text_final` | text | 是 | 英文 final 正式转写。 |
| `chinese_text_final` | text | 是 | 中文 final 正式翻译。 |
| `speaker_label` | string | 否 | 说话人标识，第一版可为空。 |
| `is_key_sentence` | bool | 是 | 是否被系统或用户标记为重点句。 |
| `asr_confidence` | numeric | 否 | STT 置信度，Provider 提供时保存。 |
| `translation_status` | enum/string | 是 | 翻译状态，建议：`completed`、`failed`、`retrying`。 |
| `created_at` | timestamptz | 是 | 片段写入时间。 |

### `usage_event`

| 字段 | 类型建议 | 必填 | 定义 |
|---|---:|---:|---|
| `id` | string/uuid | 是 | 事件唯一标识。 |
| `client_id` | string/uuid | 是 | 匿名用户标识。 |
| `session_id` | string/uuid | 否 | 关联会议会话，非会议级事件可为空。 |
| `event_type` | enum/string | 是 | 事件类型，例如 `capture_started`、`asr_error`、`export_created`。 |
| `payload` | jsonb | 是 | 事件扩展字段，必须避免保存敏感密钥和原始音频。 |
| `created_at` | timestamptz | 是 | 事件发生时间。 |

### `export_file`

| 字段 | 类型建议 | 必填 | 定义 |
|---|---:|---:|---|
| `id` | string/uuid | 是 | 导出文件唯一标识。 |
| `session_id` | string/uuid | 是 | 所属会议会话。 |
| `format` | enum/string | 是 | 导出格式，第一版支持 `markdown`、`json`。 |
| `cos_url` | string | 是 | 腾讯 COS 文件地址或对象 key。 |
| `created_at` | timestamptz | 是 | 导出文件生成时间。 |

## WebSocket 请求字段

| 消息 | 字段 | 类型 | 必填 | 定义 |
|---|---|---:|---:|---|
| `session_start` | `client_id` | string | 是 | 匿名用户标识。 |
| `session_start` | `capture_mode` | string | 是 | `tab_audio` 或 `system_audio`。 |
| `session_start` | `source_platform` | string | 是 | 用户选择或自动推断的平台。 |
| `session_start` | `audio_format` | object | 是 | 音频格式，至少包含 sample rate、channels、encoding。 |
| `audio_chunk` | binary body | bytes | 是 | mono PCM16 音频帧。 |
| `heartbeat` | `session_id` | string | 是 | 当前会话 ID，用于保持连接和探测断连。 |
| `session_stop` | `session_id` | string | 是 | 当前会话 ID。 |

## WebSocket 响应字段

| 消息 | 字段 | 类型 | 必填 | 定义 |
|---|---|---:|---:|---|
| `quota_update` | `remaining_seconds_today` | int | 是 | 今日剩余额度秒数。 |
| `audio_status` | `has_audio` | bool | 是 | 是否检测到有效音频输入。 |
| `audio_status` | `level` | number | 否 | 音量电平，用于前端显示。 |
| `asr_interim` | `text` | string | 是 | 英文临时转写文本。 |
| `translation_interim` | `text` | string | 是 | 中文临时理解文本。 |
| `segment_final` | `segment_id` | string | 是 | 已归档片段 ID。 |
| `segment_final` | `sequence` | int | 是 | 片段序号。 |
| `segment_final` | `start_ms` | int | 是 | 片段开始毫秒。 |
| `segment_final` | `end_ms` | int | 是 | 片段结束毫秒。 |
| `segment_final` | `english_text_final` | string | 是 | 英文正式转写。 |
| `segment_final` | `chinese_text_final` | string | 是 | 中文正式翻译。 |
| `key_sentence_update` | `text` | string | 是 | 当前重点句内容。 |
| `timeline_update` | `items` | array | 是 | 会议时间线节点列表。 |
| `warning` | `code` | string | 是 | 可恢复问题编码。 |
| `error` | `code` | string | 是 | 不可忽略错误编码。 |
| `session_closed` | `reason` | string | 是 | 会话关闭原因，例如 `user_stop`、`quota_limit`、`provider_error`。 |

# 功能清单

| 序号 | 功能板块 | 功能解释 | 优先级 | 备注 |
|---:|---|---|---|---|
| 1 | 匿名用户初始化 | 首次访问生成 `client_id`，建立匿名额度身份。 | M1-A | 不做登录。 |
| 2 | 额度与预算校验 | 检查每日 40 分钟、单场 30 分钟、并发 1 场和全站预算保险丝。 | M1-A | Redis 承担实时状态。 |
| 3 | 会议音频捕获 | 通过 `getDisplayMedia` 捕获会议标签页音频，失败时支持系统音频。 | M1-A | 重点验证腾讯会议网页版。 |
| 4 | 音频前处理 | 使用 AudioWorklet 转 mono PCM16 并通过 WebSocket binary frame 上传。 | M1-A | 不以 FFmpeg 为主路径。 |
| 5 | WebSocket 会话编排 | 建立、维持、关闭实时会议会话。 | M1-A | FastAPI 实现。 |
| 6 | 英文实时转写 | Google STT streaming 输出英文 interim/final。 | M1-A | 生产主路径。 |
| 7 | 中文 interim | Qwen Flash/Turbo 生成临时中文理解。 | M1-A | 节流触发，不归档。 |
| 8 | 中文 final | OpenAI 文本模型生成正式中文翻译。 | M1-A | 归档。 |
| 9 | 四区实时 UI | 英文原文、中文翻译、当前重点句、会议时间线。 | M1-A | 第一屏即工作台。 |
| 10 | 会后双语归档 | 按 final 片段生成完整可追溯记录。 | M2 | 原文归档型。 |
| 11 | 搜索与复制 | 对会后记录进行检索和复制。 | M2 | 面向复盘。 |
| 12 | Markdown / JSON 导出 | 生成导出文件并写入腾讯 COS。 | M2 | Word 后续扩展。 |
| 13 | final 翻译重试 | OpenAI final 翻译失败后允许重试或后台补译。 | M1-B | 保证档案完整性。 |
| 14 | 使用量与成本看板 | 展示分钟数、token、费用估算、错误和延迟。 | M1-B | M1-A 先写事件，M1-B 做轻量看板。 |
| 15 | Provider 开关 | 管理 Google STT、OpenAI STT、Qwen、OpenAI 翻译状态。 | M1-B | 支持备用/对比。 |
| 16 | 异常与降级提示 | 捕获失败、无音频、额度不足、Provider 错误时给出可执行提示。 | M1-A | 必须面向普通用户可理解。 |
| 17 | 当前重点句增强 | 基于 final 片段提取或人工标记当前重点句。 | M1-B | M1-A 可先展示最新 final。 |
| 18 | 会议时间线增强 | 增加关键节点、导出节点、异常节点和筛选能力。 | M1-B | M1-A 只要求基础 final 时间线。 |

# 功能描述

## 功能流程总览

```mermaid
flowchart LR
  Init["匿名初始化"] --> Quota["额度校验"]
  Quota --> Capture["音频捕获"]
  Capture --> Audio["音频前处理"]
  Audio --> WS["WebSocket 会话"]
  WS --> STT["英文 STT"]
  STT --> Interim["中文 interim"]
  STT --> Final["中文 final"]
  Final --> Archive["正式归档"]
  Archive --> Export["导出"]
  WS --> Metrics["埋点与成本"]
```

## F01 匿名用户初始化（M1-A）

### 条件

当用户首次打开工具页，且浏览器本地不存在 `client_id`。

### 动作

前端生成新的 `client_id` 并保存到浏览器本地；后端在用户第一次请求额度状态时创建或更新 `anonymous_client` 记录，并保存 IP hash 与 User-Agent hash。

### 预期

用户无需登录即可进入工具页；服务端能基于 `client_id` 统计每日额度。若本地存储不可用，前端提示用户启用浏览器存储，否则无法保证免费额度统计。

## F02 额度与预算校验（M1-A）

### 条件

当用户点击开始会议，且已经存在 `client_id`。

### 动作

后端检查：

- 今日剩余额度是否大于 0。
- 当前匿名用户是否已有活跃会议。
- 单场会议是否可新建。
- 全站月度预算保险丝是否触发。

### 预期

若检查通过，后端允许创建实时会话。若每日额度用完，返回 `quota_update` 和 `warning`，前端展示“今日免费额度已用完”。若预算保险丝触发，前端展示“当前测试额度已暂停新会议，已有记录仍可查看和导出”。

## F03 会议音频捕获（M1-A）

### 条件

当用户点击“开始捕获会议音频”，并使用 Windows Chrome / Edge。

### 动作

前端调用 `getDisplayMedia`，引导用户优先选择会议所在标签页并勾选共享音频。若标签页音频捕获失败或没有音频电平，则引导用户切换为整个屏幕/系统音频捕获。

### 预期

系统能捕获 Google Meet、Teams Web、Zoom Web、腾讯会议网页版的远端讲话者音频。若用户拒绝授权，前端不创建正式会话，不消耗额度，并展示重新授权入口。

## F04 音频前处理（M1-A）

### 条件

当浏览器捕获到有效音频流，且前端准备建立或已经建立 WebSocket 会话。

### 动作

前端通过 AudioContext 和 AudioWorklet 将音频转换为 mono PCM16 音频帧，并通过 WebSocket binary frame 持续上传。

### 预期

后端收到稳定 PCM16 音频帧并转发给 Google STT。若音频电平持续为 0，前端展示“未检测到会议声音”，后端不应继续消耗会议额度。

## F05 WebSocket 会话编排（M1-A）

### 条件

当用户通过额度校验，并且前端已确认存在可用音频输入。

### 动作

前端发送 `session_start` 创建会话，后端初始化 `meeting_session`、Redis active session、Provider streaming session 和额度计时状态。会话期间前端发送 `heartbeat` 和 `audio_chunk`，用户停止时发送 `session_stop`。

### 预期

会话能被创建、保持、关闭和清理。若 WebSocket 断开，后端应释放 Provider 资源，结算已消耗额度，保留已归档 final 片段，并通过状态字段标记结束原因。

## F06 英文实时转写（M1-A）

### 条件

当后端收到有效 PCM16 音频帧，且 Google STT provider 可用。

### 动作

后端将音频帧写入 Google STT streaming session，接收英文 interim 和英文 final 事件，并通过 WebSocket 推送给前端。

### 预期

用户讲话期间能看到英文 interim；英文 final 出现后进入正式片段处理。若 Google STT 异常，后端推送 `error`，关闭或暂停会话，并记录 `usage_event`。第一版可保留 OpenAI STT 作为实验入口，不要求自动无缝切换。

## F07 中文 interim（M1-A）

### 条件

当英文 interim 文本变化达到阈值，且距离上次 interim 翻译请求超过节流时间。

### 动作

后端调用阿里云百炼 Qwen Flash/Turbo，生成简洁中文临时理解，并通过 `translation_interim` 推送前端。

### 预期

中文 interim 能帮助用户快速理解当前讲话大意，但样式必须标记为临时状态。若 Qwen 请求失败，前端保留英文 interim，中文区域显示“临时理解生成中”或保持上一次结果，不影响英文转写和中文 final。

## F08 中文 final（M1-A）

### 条件

当 Google STT 返回英文 final segment。

### 动作

后端携带当前英文 final 和最近 3 到 5 个 final segment 上下文，请求 OpenAI 文本模型生成正式中文翻译。翻译结果与英文 final 一起写入 `transcript_segment`。

### 预期

中文 final 表达自然、语义准确、适合中国职场阅读。若 OpenAI 请求失败，片段标记为 `translation_status=failed`，前端展示待重试状态，后续可由 M2 重试机制补齐。

## F09 四区实时 UI（M1-A）

### 条件

当前端收到 `asr_interim`、`translation_interim`、`segment_final`、`key_sentence_update` 或 `timeline_update`。

### 动作

前端按消息类型更新四个区域：

- 英文原文区展示英文 interim 和 final。
- 中文翻译区展示中文 interim 和 final。
- 当前重点句区展示当前重要句或最新 final 重点。
- 会议时间线区追加 final 片段和关键事件。

### 预期

interim 内容可替换，final 内容只追加。任何区域更新失败不应阻塞其他区域。正式档案只基于 final 片段重建。

## F10 会后双语归档（M2）

### 条件

当用户主动结束会议、额度到达上限、Provider 错误导致会话关闭，或 WebSocket 断开并超过恢复窗口。

### 动作

后端关闭 Provider session，结算额度，更新 `meeting_session` 状态，保留已完成的 final 片段，并按 `sequence`、`start_ms`、`end_ms` 重建双语归档视图。

### 预期

用户能进入会后记录页查看已生成的双语 final 片段。若会议异常结束，记录页必须保留已归档内容，并标明结束原因。

## F11 搜索与复制（M2）

### 条件

当会议存在至少一个 `transcript_segment`，且用户进入会后归档页。

### 动作

前端提供关键词搜索、片段定位和复制入口。搜索范围至少覆盖英文 final、中文 final 和时间戳；复制内容应保留片段时间、英文原文和中文翻译。

### 预期

用户能快速找到会后需要复盘的片段，并把双语内容复制到工作文档。搜索和复制行为应记录 `archive_searched`、`segment_copied` 等价值验证事件。

## F12 Markdown / JSON 导出（M2）

### 条件

当会议存在至少一个 `transcript_segment`，且用户点击导出。

### 动作

后端按时间顺序读取 final 片段，生成 Markdown 或 JSON 文件，上传腾讯 COS，并写入 `export_file`。

### 预期

用户能获得可下载导出文件。若 COS 上传失败，前端提示重试，后端记录 `export_failed` 事件。

## F13 final 翻译重试（M1-B）

### 条件

当英文 final 已归档，但 OpenAI 中文 final 生成失败，且 `translation_status=failed`。

### 动作

系统提供手动重试或后台补译入口。重试时携带原英文 final 和最近上下文，成功后更新 `chinese_text_final` 与 `translation_status=completed`，失败时保留失败原因和重试次数。

### 预期

失败片段不会破坏归档顺序。用户能看到哪些片段待补译，重试成功后归档内容自动补齐，并记录 `translation_final_retry_requested` 和 `translation_final_completed`。

## F14 使用量与成本看板（M1-B）

### 条件

当系统持续产生会话时长、STT 分钟数、Qwen token、OpenAI token、导出、错误和延迟事件。

### 动作

M1-A 写入 `usage_event` 并维护成本估算；M1-B 提供轻量看板，展示每日会议数、STT 分钟数、Provider 请求量、预估成本、错误率、延迟和预算保险丝状态。

### 预期

产品负责人能判断成本是否接近 0-500 RMB 月预算边界。当月度预算达到 400 RMB 建议阈值时，系统拒绝新会话，但不影响已有会议记录查看和导出。

## F15 Provider 开关（M1-B）

### 条件

当需要临时关闭某个 Provider、切换备用路径，或对比 Google STT 与 OpenAI STT 的效果。

### 动作

后端通过环境变量或管理配置控制 Google STT、OpenAI STT、Qwen interim、OpenAI final 的启停状态。前端不暴露密钥，只展示用户需要知道的服务状态或降级提示。

### 预期

Provider 异常时可以快速降级，不需要重新部署前端。Qwen interim 关闭时，英文转写和中文 final 仍能工作；OpenAI STT 作为备用/对比入口时，不影响 Google STT 主路径。

## F16 异常与降级提示（M1-A）

### 条件

当出现捕获失败、未检测到音频、额度不足、Provider 异常、WebSocket 断开、导出失败或预算保险丝触发。

### 动作

后端发送 `warning` 或 `error`，前端展示用户能理解的原因和下一步操作，例如切换系统音频、检查共享音频、稍后重试或查看已归档内容。腾讯会议标签页音频不可用时，引导用户使用系统音频降级。

### 预期

异常不应造成用户已归档内容丢失。可恢复异常用 `warning`，不可继续的异常用 `error` 和 `session_closed`，并且所有关键异常都写入 `usage_event` 便于排查。

## F17 当前重点句增强（M1-B）

### 条件

当产生新的 final 片段，或用户在实时阅读/会后归档中标记某个片段为重点。

### 动作

M1-A 可先把最新 final 或最新中文 final 展示为当前重点句；M1-B 基于规则或模型提取更适合展示的重点句，并支持人工标记 `is_key_sentence=true`。

### 预期

当前重点句区能帮助用户在会议中快速抓住正在讨论的核心内容。重点句变更通过 `key_sentence_update` 推送，归档中保留重点标记，便于会后复盘。

## F18 会议时间线增强（M1-B）

### 条件

当产生 final segment、重点句、导出事件、异常事件或用户查看会后归档。

### 动作

M1-A 时间线至少展示 final 片段；M1-B 增加关键节点、导出节点、异常节点、筛选能力和关联 segment 跳转。后端生成 timeline item，并通过 `timeline_update` 推送给前端。

### 预期

用户能按时间顺序回看会议内容，并快速定位重点、异常和导出节点。时间线节点应至少包含时间点、类型、摘要文本和关联 segment ID。

# 功能边界

## 第一版范围内

- 免登录匿名使用。
- 网页会议音频捕获。
- 英语会议实时转写。
- 中文 interim 和中文 final。
- 四区实时阅读 UI。
- 原文归档型会后记录。
- Markdown / JSON 导出。
- 基础额度、成本、埋点和预算保险丝。
- 单机 Docker Compose 部署。

## M1 拆分边界

### M1-A：必须上线闭环

M1-A 是产品是否能进入小范围测试的最低闭环，必须一次性打通：

- 匿名 `client_id` 和每日额度。
- 标签页音频捕获与系统音频降级。
- AudioWorklet 生成 mono PCM16。
- WebSocket 音频上传和会话关闭。
- Google STT 英文 interim/final。
- Qwen 中文 interim。
- OpenAI 中文 final。
- 四区实时 UI 基础展示。
- final 片段写入 PostgreSQL。
- 基础 usage_event 写入。
- 捕获失败、无音频、额度不足、Provider 错误的基础提示。

### M1-B：上线后增强

M1-B 在 M1-A 小范围可用后推进，不阻塞 MVP 首次上线：

- 当前重点句优化。
- 会议时间线增强。
- final 翻译失败后的重试和补译。
- 轻量使用量与成本看板。
- Provider 开关和 OpenAI STT 对比入口。
- 导出体验增强。
- 兼容性报告和漏斗看板。

## 第一版范围外

- 用户登录与账号体系。
- 跨设备云端历史同步。
- 浏览器插件。
- 桌面客户端。
- 虚拟音频设备。
- 本地自建 Whisper 生产服务。
- 多语言会议优化。
- 自动生成复杂管理纪要、责任人识别和任务分派。
- Word 导出，第一版后续扩展。

## 平台边界

第一版重点支持 Windows Chrome / Edge。Google Meet、Teams Web、Zoom Web、腾讯会议网页版必须测试。腾讯会议网页版标签页音频如果不可用，允许使用系统音频降级。

## 数据边界

第一版默认不保存原始会议音频，不保存明文 IP，不把中文 interim 作为正式档案。正式归档仅保存英文 final、中文 final、时间戳、序号、状态和导出文件信息。

# 非功能性要求

## 性能与实时性

- 英文 interim 应在音频输入后尽快出现，前端应优先显示英文 interim。
- 中文 interim 需节流，避免请求过密导致成本和 UI 抖动。
- 中文 final 可晚于英文 final 出现，但必须保持片段顺序。
- 四区 UI 更新互不阻塞。

## 稳定性

- WebSocket 断开时应关闭或回收 Provider session。
- Provider 失败不应丢失已归档 final 片段。
- Redis active session 必须设置过期时间，避免异常断开后永久占用并发。
- 会话关闭应执行额度结算。

## 安全与隐私

- 生产环境必须使用 HTTPS/WSS。
- API keys 只能通过后端环境变量注入，前端不得暴露 Provider 密钥。
- 不保存原始会议音频。
- IP 和 User-Agent 只保存 hash。
- 导出文件地址应具备可控访问策略。

## 成本控制

- 匿名用户每日 40 分钟。
- 单场会议最多 30 分钟。
- 同一匿名用户最多 1 个活跃会议。
- 全站月度预算保险丝初始阈值建议 400 RMB。
- 记录 Google STT 分钟数、Qwen token、OpenAI token、导出次数和失败重试次数。

## 可维护性

- Provider 抽象保持轻量。
- 前端使用 Vite 静态构建。
- 后端使用 FastAPI、Pydantic、SQLAlchemy async 和 Alembic。
- 配置统一由环境变量管理。
- 业务逻辑、Provider 调用、数据访问和 WebSocket 消息 schema 分层。

## 兼容性

- 第一版主测 Windows Chrome / Edge。
- 不承诺 Safari、Firefox、移动端浏览器。
- 系统音频模式需要明确风险提示。

## 兼容性测试矩阵

兼容性测试必须区分“标签页音频成功”和“系统音频降级成功”。腾讯会议网页版如果标签页音频不可用，MVP 允许通过系统音频完成验证，但必须记录为 `system_audio_fallback`，不能计入标签页音频成功率。

| 平台 | Windows Chrome 标签页音频 | Windows Chrome 系统音频 | Windows Edge 标签页音频 | Windows Edge 系统音频 | MVP 通过标准 |
|---|---|---|---|---|---|
| Google Meet | 必测 | 选测 | 必测 | 选测 | 至少一个浏览器标签页音频成功。 |
| Microsoft Teams Web | 必测 | 选测 | 必测 | 选测 | 至少一个浏览器标签页音频成功。 |
| Zoom Web | 必测 | 选测 | 必测 | 选测 | 至少一个浏览器标签页音频成功。 |
| 腾讯会议网页版 | 必测 | 必测 | 必测 | 必测 | 标签页音频成功最好；若失败，系统音频成功也可通过 MVP 验证。 |

每次兼容性测试都必须记录：

- `source_platform`
- `browser`
- `browser_version`
- `os`
- `capture_mode`
- `permission_result`
- `audio_detected`
- `first_asr_interim_ms`
- `final_segment_count`
- `failure_code`

腾讯会议专项结论必须分为三类：

- `tab_audio_supported`：标签页音频可用，可作为默认路径。
- `system_audio_only`：标签页音频不可用，但系统音频可完成 MVP 验证。
- `unsupported`：标签页音频和系统音频都无法完成有效会议，需要阻塞上线或降级说明。

# 上线方案

## 环境准备

### 条件

腾讯云 Lighthouse 已准备 Ubuntu 22.04 LTS 64 位 x86 服务器，并可安装 Docker。

### 动作

部署 Docker、Docker Compose、Caddy、PostgreSQL、Redis、后端容器和前端静态产物。配置 Google STT、阿里云百炼、OpenAI、腾讯 COS、PostgreSQL、Redis 的环境变量。

### 预期

服务可通过 HTTPS 域名访问，WebSocket 使用 WSS，健康检查通过。

## 发布阶段

### 内部验证

- 使用本地 mock Provider 验证 UI 和 WebSocket 协议。
- 使用真实 Google STT 验证英文 interim/final。
- 使用真实 Qwen 验证中文 interim。
- 使用真实 OpenAI 验证中文 final。
- 使用腾讯 COS 验证 Markdown / JSON 导出。

### 小范围测试

- 先开放给 10 到 50 名测试用户。
- 每人每日 40 分钟。
- 监控 API 成本、失败率、延迟、捕获失败原因和腾讯会议兼容性。

### 回滚策略

- 前端静态产物保留上一版本。
- 后端容器保留上一镜像 tag。
- 数据库 migration 上线前必须备份。
- Provider 配置支持关闭 Qwen interim 或拒绝新会议。

## 上线检查

- HTTPS/WSS 可用。
- Caddy 正确服务静态前端并代理 `/api/*`、`/ws/*`。
- PostgreSQL migration 已执行。
- Redis 可连接。
- Provider credentials 已配置。
- 预算保险丝默认启用。
- 使用量和错误事件可写入。

# 验收标准

## 核心链路验收

- Windows Chrome / Edge 可以捕获 Google Meet、Teams Web、Zoom Web、腾讯会议网页版音频。
- 腾讯会议网页版支持标签页音频优先，失败时可降级系统音频。
- 用户开始会议后能看到英文 interim。
- 英文 final 产生后能触发中文 final 并归档。
- 中文 interim 能以受控频率出现，并标记为临时理解。
- 四区 UI 能独立更新。
- 会后归档能按时间顺序显示双语 final 片段。
- Markdown / JSON 导出成功写入腾讯 COS。

## 额度与成本验收

- 每个匿名用户每天最多消耗 40 分钟。
- 单场会议最多 30 分钟。
- 同一匿名用户不能同时开启多场会议。
- 全站预算保险丝触发后，新会议被拒绝，已有记录仍可查看。

## 异常验收

- 用户拒绝捕获授权时，不消耗额度并显示重试入口。
- 无音频输入时，不消耗额度并提示检查共享音频。
- Qwen 失败时，不阻塞英文转写和中文 final。
- OpenAI final 失败时，片段进入待重试状态。
- WebSocket 断开时，会话能被清理并保留已归档内容。

## MVP 成功指标

以下指标用于第一批 10 到 50 名测试用户的产品判断。阈值是第一版建议值，后续可根据真实基线调整。

### 激活指标

| 指标 | 定义 | 建议成功阈值 | 解释 |
|---|---|---:|---|
| 首次会议启动率 | 首次访问用户中成功点击开始捕获并发起会话的比例 | >= 50% | 判断用户是否愿意尝试核心能力。 |
| 首次有效音频捕获率 | 发起捕获用户中检测到有效音频的比例 | >= 70% | 判断浏览器捕获链路是否可用。 |
| 首场有效会议率 | 首次会话中产生至少 3 个 final 片段且时长 >= 3 分钟的比例 | >= 50% | 判断用户是否真正跑通会议理解闭环。 |

### 核心使用指标

| 指标 | 定义 | 建议成功阈值 | 解释 |
|---|---|---:|---|
| 有效会议完成率 | 已开始会议中非捕获失败、非 Provider 早期失败的会议比例 | >= 70% | 判断核心链路稳定性。 |
| 平均有效会议时长 | 有效会议的平均消耗分钟数 | >= 8 分钟 | 判断用户是否持续使用，而不是快速退出。 |
| final 片段生成率 | 有音频会议中产生 final 片段的比例 | >= 80% | 判断 STT 和归档链路是否成立。 |
| 导出率 | 有效会议中发生 Markdown/JSON 导出的比例 | >= 20% | 判断会后记录是否有实际价值。 |

### 质量指标

| 指标 | 定义 | 建议成功阈值 | 解释 |
|---|---|---:|---|
| 中文 final 主观满意度 | 测试用户对正式中文翻译的 1-5 分评分 | >= 4.0 | 判断核心翻译质量。 |
| 中文 final 平均延迟 | 英文 final 到中文 final 推送完成的平均时间 | <= 5 秒 | 判断实时阅读体验。 |
| Provider 错误率 | Provider 错误次数 / 有效会议数 | <= 10% | 判断外部服务稳定性。 |
| 腾讯会议可用率 | 腾讯会议测试中可通过标签页或系统音频完成有效会议的比例 | >= 70% | 判断重点平台是否可验证。 |

### 留存指标

| 指标 | 定义 | 建议成功阈值 | 解释 |
|---|---|---:|---|
| 次日复用率 | 首日有效会议用户中次日再次访问或开会的比例 | >= 20% | 判断短期价值。 |
| 7 日复用率 | 首周内完成第二场有效会议的用户比例 | >= 15% | 判断是否值得继续迭代。 |
| 第二场会议比例 | 有效会议用户中开启第二场会议的比例 | >= 25% | 判断用户是否愿意重复使用。 |

### 成本指标

| 指标 | 定义 | 建议成功阈值 | 解释 |
|---|---|---:|---|
| 每有效会议成本 | 总 Provider 成本 / 有效会议数 | <= 3 RMB | 判断预算内可持续性。 |
| 每分钟成本 | 总 Provider 成本 / 有效会议分钟数 | <= 0.25 RMB | 判断免费额度是否可承受。 |
| 预算保险丝触发次数 | 月度预算保险丝触发次数 | 0-1 次/月 | 判断成本是否失控。 |

# 测试用例

| 用例编号 | 测试类型 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|---|---|---|---|---|---|
| TC-001 | 匿名初始化 | 浏览器无 `client_id` | 打开工具页 | 生成 `client_id`，服务端可返回额度状态 | M1-A |
| TC-002 | 额度校验 | 今日额度未用完 | 点击开始会议 | 会话允许创建，返回剩余额度 | M1-A |
| TC-003 | 额度拦截 | 今日额度已用完 | 点击开始会议 | 拒绝新会话，展示额度用完提示 | M1-A |
| TC-004 | 并发限制 | 同一 `client_id` 已有活跃会议 | 再次开始会议 | 拒绝第二个活跃会话 | M1-A |
| TC-005 | 标签页音频捕获 | Windows Chrome + Google Meet 有远端讲话 | 选择会议标签页并共享音频 | 检测到有效音频，产生英文 interim | M1-A |
| TC-006 | 腾讯会议标签页音频 | Windows Chrome + 腾讯会议网页版 | 选择腾讯会议标签页并共享音频 | 成功则记录 `tab_audio_supported`，失败进入系统音频降级 | M1-A |
| TC-007 | 腾讯会议系统音频降级 | 腾讯会议标签页音频失败 | 切换为系统音频捕获 | 若检测到音频并产生 final，MVP 验证通过但记录 `system_audio_only` | M1-A |
| TC-008 | 用户拒绝授权 | 浏览器弹窗出现 | 用户拒绝共享 | 不创建正式会话，不消耗额度，显示重试入口 | M1-A |
| TC-009 | 无音频输入 | 捕获成功但会议无声音 | 保持静音 30 秒 | 不消耗额度，提示未检测到会议声音 | M1-A |
| TC-010 | AudioWorklet 输出 | 捕获到音频 | 开始处理音频 | 前端持续发送 mono PCM16 binary frame | M1-A |
| TC-011 | WebSocket 断开 | 会议进行中 | 主动断开网络或关闭标签页 | 后端清理 active session，保留已归档片段 | M1-A |
| TC-012 | Google STT interim | 有效音频上传 | 英文发言 10 秒 | 前端显示英文 interim | M1-A |
| TC-013 | Google STT final | 有效音频上传 | 英文发言并停顿 | 产生英文 final，触发中文 final 流程 | M1-A |
| TC-014 | Qwen interim 成功 | 英文 interim 满足节流条件 | 持续英文发言 | 前端显示中文临时理解，且不写入正式档案 | M1-A |
| TC-015 | Qwen interim 失败 | 模拟 Qwen provider 错误 | 持续英文发言 | 英文转写和中文 final 不受阻塞，记录 provider 错误 | M1-A |
| TC-016 | OpenAI final 成功 | 英文 final 已产生 | 请求正式翻译 | 生成中文 final，写入 `transcript_segment` | M1-A |
| TC-017 | OpenAI final 失败 | 模拟 OpenAI 错误 | 英文 final 触发翻译 | 片段标记 `translation_status=failed`，前端显示待重试 | M1-B |
| TC-018 | 四区 UI 更新 | 收到 interim/final/timeline 消息 | 观察页面四区 | 英文、中文、重点句、时间线独立更新 | M1-A |
| TC-019 | 会后归档 | 会话包含多个 final 片段 | 结束会议并打开归档页 | 按序显示英文 final、中文 final、时间戳 | M2 |
| TC-020 | Markdown 导出 | 会话有归档片段 | 点击 Markdown 导出 | 文件生成并上传 COS，写入 `export_file` | M2 |
| TC-021 | JSON 导出 | 会话有归档片段 | 点击 JSON 导出 | JSON 包含 session 和 segment 数据 | M2 |
| TC-022 | COS 上传失败 | 模拟 COS 错误 | 点击导出 | 前端提示重试，记录 `export_failed` | M2 |
| TC-023 | 预算保险丝 | 预估月成本达到阈值 | 点击开始会议 | 拒绝新会话，已有归档可查看 | M1-A |
| TC-024 | 首次使用漏斗 | 新用户完整跑一场会议 | 观察埋点 | 产生 page、client、capture、audio、session、interim、final 事件链 | M1-B |
| TC-025 | 会议质量漏斗 | 有效会议进行中 | 观察埋点 | 能计算音频、STT、翻译、归档各步骤转化 | M1-B |
| TC-026 | 价值验证漏斗 | 用户完成会议后操作归档 | 打开归档、搜索、复制、导出 | 能计算归档查看、搜索/复制、导出和复用事件 | M1-B |

# 埋点与数据看板

## 事件清单

| 事件类型 | 触发时机 | 关键 payload |
|---|---|---|
| `client_created` | 新匿名用户创建 | `client_id`、UA hash、IP hash |
| `quota_checked` | 用户请求额度 | 剩余额度、是否允许 |
| `capture_started` | 用户开始捕获 | capture mode、platform |
| `capture_failed` | 捕获失败 | error code、browser |
| `audio_detected` | 检测到有效音频 | level、capture mode |
| `session_started` | 后端会话创建 | session_id、quota remaining |
| `asr_interim_received` | 收到英文 interim | text length、latency |
| `asr_final_received` | 收到英文 final | duration、confidence |
| `translation_interim_requested` | 请求 Qwen | token estimate、throttle reason |
| `translation_final_completed` | OpenAI final 完成 | token usage、latency |
| `segment_archived` | final 片段入库 | sequence、duration |
| `export_created` | 导出完成 | format、file size |
| `provider_error` | Provider 失败 | provider、code、recoverable |
| `quota_exhausted` | 用户额度耗尽 | consumed seconds |
| `budget_fuse_triggered` | 全站预算触发 | estimated monthly cost |
| `session_closed` | 会话关闭 | reason、duration |

## 看板指标

- 日活匿名用户数。
- 每日会议数。
- 每日 STT 分钟数。
- Qwen 请求量和 token。
- OpenAI 请求量和 token。
- 预估日成本和月成本。
- 捕获失败率。
- Provider 错误率。
- 平均英文 interim 延迟。
- 平均中文 final 延迟。
- 腾讯会议网页版成功率。

## 漏斗分析

漏斗指标用于回答三个问题：用户卡在哪一步、产品价值是否成立、成本是否失控。

### 漏斗 1：首次使用

目标是定位首次使用阻塞点。

```mermaid
flowchart LR
  A["访问工具页"] --> B["生成 client_id"]
  B --> C["点击开始捕获"]
  C --> D["浏览器授权成功"]
  D --> E["检测到有效音频"]
  E --> F["创建会话成功"]
  F --> G["看到首条英文 interim"]
  G --> H["看到首条中文 final"]
```

| 漏斗步骤 | 关键事件 | 主要判断 |
|---|---|---|
| 访问工具页 | `page_viewed` | 入口是否正常。 |
| 生成匿名身份 | `client_created` | 本地存储和匿名身份是否可用。 |
| 点击开始捕获 | `capture_started` | 用户是否理解并愿意尝试。 |
| 授权成功 | `capture_permission_granted` | 浏览器授权是否成为阻塞。 |
| 检测有效音频 | `audio_detected` | 捕获方式是否可用。 |
| 创建会话 | `session_started` | 配额和预算是否放行。 |
| 首条英文 interim | `asr_interim_received` | STT 链路是否跑通。 |
| 首条中文 final | `translation_final_completed` | 核心价值是否首次出现。 |

### 漏斗 2：会议质量

目标是判断会议过程是否稳定。

```mermaid
flowchart LR
  A["有效音频输入"] --> B["持续上传音频帧"]
  B --> C["英文 interim 稳定出现"]
  C --> D["英文 final 稳定出现"]
  D --> E["中文 interim 可读"]
  D --> F["中文 final 完成"]
  F --> G["final 片段归档"]
  G --> H["会议正常结束"]
```

| 漏斗步骤 | 关键事件 | 主要判断 |
|---|---|---|
| 有效音频输入 | `audio_detected` | 捕获链路是否持续有效。 |
| 上传音频帧 | `audio_chunk_uploaded` | WebSocket 是否稳定。 |
| 英文 interim | `asr_interim_received` | STT 实时性是否可接受。 |
| 英文 final | `asr_final_received` | STT 是否能稳定出正式片段。 |
| 中文 interim | `translation_interim_requested` | 临时理解是否按节流工作。 |
| 中文 final | `translation_final_completed` | 正式翻译质量和延迟是否可接受。 |
| 片段归档 | `segment_archived` | 会后记录是否完整。 |
| 正常结束 | `session_closed` | 会话清理和结算是否正确。 |

### 漏斗 3：价值验证

目标是判断用户是否认为会议记录有价值。

```mermaid
flowchart LR
  A["完成有效会议"] --> B["打开会后记录"]
  B --> C["浏览双语片段"]
  C --> D["搜索或复制"]
  D --> E["导出 Markdown/JSON"]
  E --> F["7 日内再次使用"]
```

| 漏斗步骤 | 关键事件 | 主要判断 |
|---|---|---|
| 完成有效会议 | `session_closed` | 是否产生足够内容。 |
| 打开会后记录 | `archive_viewed` | 用户是否回看。 |
| 浏览双语片段 | `segment_viewed` | 归档是否可读。 |
| 搜索或复制 | `archive_searched` / `segment_copied` | 记录是否进入工作流。 |
| 导出 | `export_created` | 用户是否愿意带走结果。 |
| 再次使用 | `return_session_started` | 产品是否有复用价值。 |

# 风险与依赖

## 关键依赖

- Google Cloud Speech-to-Text v2 streaming。
- 阿里云百炼 Qwen Flash/Turbo。
- OpenAI 文本模型。
- 腾讯 COS。
- Windows Chrome / Edge 的音频捕获能力。
- 腾讯会议网页版对浏览器音频捕获的兼容性。

## 主要风险

| 风险 | 影响 | 应对 |
|---|---|---|
| 腾讯会议标签页音频无法稳定捕获 | 影响重点平台体验 | 提供系统音频降级，并单独记录兼容性指标。 |
| API 成本超预算 | 影响测试持续性 | 每日额度、单场限制、预算保险丝、成本看板。 |
| Qwen interim 质量不稳定 | 影响实时理解 | 明确标记临时状态，失败不阻塞主链路。 |
| OpenAI final 延迟较高 | 影响正式中文出现速度 | UI 先展示英文 final 和中文生成中，完成后补齐。 |
| WebSocket 断开 | 可能中断会议 | 清理资源，保留已归档内容，显示结束原因。 |
| 无登录额度被绕过 | 成本风险 | 第一版防普通滥用，规模扩大后加邀请码或登录。 |

# 其他必要说明

## AI 开发者实施原则

- 先完成 M1 核心闭环，再做 M2 导出和 M3 看板。
- 所有 Provider 调用必须经过后端，前端不得出现密钥。
- 所有正式归档以 final 片段为准，不用 interim 重建正式记录。
- WebSocket message schema 必须可测试，前后端共享或镜像定义。
- 所有异常都要产生用户可理解的提示和开发者可排查的 `usage_event`。

## PRD 结构评价

本 PRD 结构清晰，达到成熟且专业的 PRD 基础要求。它覆盖了背景、价值、目标、整体设计、名词、字段、功能清单、详细功能逻辑、边界、非功能、上线、验收、埋点和风险。面向 AI 开发者时，字段说明、WebSocket 消息、异常流和验收标准是必要补充，可以降低实现歧义。
