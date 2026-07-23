# Fanora Frontend

该模块由原 `xhibiter-ts` 模板整理而来，使用 Next.js、Axios、RainbowKit、wagmi 和 viem。

当前前端包含 Fanora 首页、`/login` 钱包签名登录页、`/profile` 用户身份维护页、`/membership/join` 正式会员缴纳页、`/collection` 个人会员证与收藏页，以及 `/collections`、`/collections/create`、`/item/[id]`、`/collection/[id]` 组成的粉丝 NFT 市场。用户通过 RainbowKit 选择 MetaMask、WalletConnect 等钱包，签署后端一次性 challenge 后建立 Fanora 会话。注册用户默认为待入会，首页与任务入口根据后端 `is_official_member` 显示动态会费入口；缴纳页通过当前直连钱包发送交易，再交由 FastAPI 验证链上结果。Profile 支持维护用户资料、查看主钱包和社区身份。未上传头像时，前端使用 Boring Avatars 根据用户 ID 生成稳定的默认头像。

后续需要新的组件或样式时，从仓库根目录的 `xhibiter-ts` 素材工程中按需复制，不重新把整套模板依赖引入 `frontend`。

`public/img` 只保留当前首页、导航、页脚和样式实际引用的资源；后续复制新组件时，需要同步复制该组件依赖的图片。热门粉丝任务使用 `nft-game/crypto_icons.png` 漂浮素材，会员等级区块使用 `gradient_creative.jpg` 背景。

## 启动

```bash
cp .env.example .env.local
npm install
npm run dev
```

浏览器访问 `http://localhost:3000`。

请在 WalletConnect Cloud 创建项目并配置 `NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID`。钱包私钥和账户备份始终由用户选择的钱包应用管理，Fanora 前后端不提供私钥导出能力。

## 目录建议

- `app/`：主页、登录、资料维护、社区、正式入会、个人收藏和 NFT 市场路由。
- `components/homes/home/`：Hero 与动态 Badge Cover Flow。
- `components/homes/common/`：协议能力、Agent、工作流程和用户价值区块。
- `lib/web3/`：Monad 网络、合约地址和 ABI。
- `lib/api/`：Axios 客户端和前后端共享数据类型。
- `components/providers/AuthProvider.tsx`：钱包挑战登录、会话恢复和会员付款管理。
- `components/nft/FanNftMarket.tsx`：NFT 广场、发布、详情、创作者集合、点赞收藏和 FAN 购买交互。
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
npm run test:membership
npm run test:official-membership
npm run test:community
npm run test:video-sound
npm run test:wallet-login
npm run typecheck
npm run build
```
