# Fanora Frontend

该模块由原 `xhibiter-ts` 模板整理而来，使用 Next.js、Web3Auth、Axios、RainbowKit、wagmi 和 viem。

当前前端包含 Fanora 首页、`/login` Web3Auth 快捷登录页和 `/profile` 用户身份维护页。登录成功后会自动创建或恢复嵌入式钱包，再通过 Axios 与本地 FastAPI 建立统一会话。Profile 支持维护用户资料、查看主钱包和社区身份，并为 Web3Auth 嵌入式钱包提供高风险私钥导出入口。未上传头像时，前端使用 Boring Avatars 根据用户 ID 生成稳定的默认头像。

后续需要新的组件或样式时，从仓库根目录的 `xhibiter-ts` 素材工程中按需复制，不重新把整套模板依赖引入 `frontend`。

`public/img` 只保留当前 `home-4` 页面、导航、页脚和样式实际引用的资源；后续复制新组件时，需要同步复制该组件依赖的图片。

## 启动

```bash
cp .env.example .env.local
npm install
npm run dev
```

浏览器访问 `http://localhost:3000`。

请确认 Web3Auth Dashboard 已允许 `http://localhost:3000` 和 `http://127.0.0.1:3000`，并让前后端使用同一个 Client ID。

当前 Client ID 对应 `sapphire_devnet`。`NEXT_PUBLIC_WEB3AUTH_NETWORK` 必须与 Web3Auth Dashboard 中的项目网络一致，它与 Monad EVM 链配置是两个独立概念。

## 私钥导出安全边界

- 仅 Web3Auth 嵌入式钱包可以在 Profile 页面请求导出；MetaMask、WalletConnect 等外部钱包必须在钱包应用中操作。
- 用户必须输入“我已了解风险”后才能向 Web3Auth Provider 请求私钥，返回值默认遮罩显示。
- 私钥不会经过 Axios、FastAPI、PostgreSQL、日志或 LocalStorage；关闭弹窗或 60 秒后会清除组件状态。
- 自动化验证不得点击最终导出按钮，也不得在测试输出、截图或日志中记录真实私钥。

## 目录建议

- `app/`：主页、登录、资料维护和 404。
- `components/homes/home-4/`：Hero 与动态 Badge Cover Flow。
- `components/homes/common/`：协议能力、Agent、工作流程和用户价值区块。
- `lib/web3/`：Monad 网络、合约地址和 ABI。
- `lib/api/`：Axios 客户端和前后端共享数据类型。
- `components/providers/AuthProvider.tsx`：Web3Auth 初始化、无感恢复和 Fanora 会话管理。
- `hooks/`：钱包与合约读取 hooks。
- `data/fanora.ts`：主页展示数据，后续逐步替换为后端接口。

## 质量检查

```bash
npm run lint
npm run test:api-timeout
npm run test:avatar
npm run test:header
npm run test:hero-animation
npm run test:fan-token
npm run test:video-sound
npm run test:key-export
npm run typecheck
npm run build
```
