# Meeting MVP Frontend

本目录是 Meeting MVP 的前端工程，已在 Step 03 初始化为 Vite + React + TypeScript 应用。

## 当前边界

- 运行时目标：浏览器静态前端，后续由 Caddy 托管 `dist/` 构建产物。
- UI 基础：Tailwind CSS v4、shadcn/ui、lucide-react。
- 状态基础：Zustand。
- 测试基础：Vitest + React Testing Library、Playwright Chromium smoke test。
- 当前只包含轻量工作台骨架，用于验证依赖、构建和测试链路；正式四区实时 UI、音频捕获和 WebSocket 协议实现留给后续步骤。
- 前端不得写入 Provider 密钥、服务端密钥或生产环境变量。

## 常用命令

```powershell
npm install
npm run lint
npm run test
npm run build
npx playwright install chromium
npm run test:e2e
```

如果本机默认 npm cache 目录出现 `EPERM` 权限问题，可临时使用仓库内已忽略的本地缓存：

```powershell
$env:npm_config_cache='D:\meeting_mvp\.cache\npm'
```

## 文件入口

- `src/main.tsx`：React 应用挂载入口。
- `src/App.tsx`：当前最小会议工作台页面。
- `src/stores/session-store.ts`：当前最小会话状态 store。
- `src/components/ui/button.tsx`：shadcn/ui Button 组件。
- `e2e/app.spec.ts`：Playwright Chromium smoke test。
