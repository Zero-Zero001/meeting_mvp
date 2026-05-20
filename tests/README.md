# Tests

本目录用于后续放置跨端测试、验收资产和集成测试说明。

边界：

- 放置端到端、部署验收、兼容性矩阵、跨前后端协议测试资产或测试说明。
- 前端单元测试优先随 `frontend/` 工程组织，后端单元测试优先随 `backend/` 工程组织。
- 需要真实 PostgreSQL、Redis、Google STT、Qwen 或 COS 的测试应在 Lighthouse 或后续 CI 环境执行。

## Step 30 兼容性矩阵

- `tests/compatibility/step-30-compatibility-results.json` 是真实人工兼容性测试结果的结构化来源。
- `tests/compatibility/step-30-compatibility-matrix.md` 是面向开发和验收的人工可读矩阵。
- `scripts/validate-step30-compatibility.ps1` 校验必测平台、浏览器、捕获模式、真实 Qwen HTTPS/WSS 环境和腾讯会议专项结论。

Step 30 只接受真实 Windows Chrome / Edge + 真实会议平台 + 真实 Qwen ASR backend 的结果。local mock、缺测行、未知浏览器版本、空失败码或未启用 Qwen realtime ASR 都不能标记为通过。
