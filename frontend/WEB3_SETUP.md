# RainbowKit 钱包与 Fanora 合约接入说明

Fanora 前端只使用 RainbowKit 连接 MetaMask、WalletConnect 等外部钱包。登录通过后端一次性 challenge 和钱包签名完成，不依赖第三方身份令牌。正式入会由当前登录钱包调用 Gateway 合约并确认交易。

## 1. 环境变量

复制 `.env.example` 为 `.env.local`。主要配置包括：

```env
NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=WalletConnect Cloud 项目 ID
NEXT_PUBLIC_MONAD_TESTNET_RPC_URL=https://testnet-rpc.monad.xyz
NEXT_PUBLIC_MEMBERSHIP_PAYMENT_CONTRACT_ADDRESS_MONAD_TESTNET=0x...
NEXT_PUBLIC_MEMBERSHIP_IDENTITY_CONTRACT_ADDRESS_MONAD_TESTNET=0x...
NEXT_PUBLIC_COLLECTIBLES_CONTRACT_ADDRESS_MONAD_TESTNET=0x...
```

`NEXT_PUBLIC_` 变量会进入浏览器，只能填写公开配置，严禁填写部署私钥、运营私钥、Pinata JWT 或其他服务端密钥。

合约发布后可自动同步地址：

```bash
cd contracts
npm run sync:testnet
```

## 2. 登录与付款流程

1. 用户点击直连钱包按钮，RainbowKit 展示支持的钱包。
2. 前端请求 `POST /api/v1/auth/challenge`。
3. 当前钱包签署一次性登录消息，不产生 Gas。
4. 前端将 challenge、钱包地址和签名提交到 `POST /api/v1/auth/wallet`。
5. 后端验证成功后创建或恢复统一用户会话。
6. 入会页核对当前连接账户与 Fanora 主钱包一致。
7. 当前钱包调用 `FanoraMembershipGateway.join(paymentId)` 并支付链上当前会费。
8. 后端验证 `MembershipPaid` 事件后激活正式会员，并尝试铸造初始 ERC-721 身份。

## 3. 合约与 ABI

- `shared/contracts/FanoraMembershipGateway.json`
- `shared/contracts/FanoraMembershipIdentity.json`
- `shared/contracts/FanoraCollectibles.json`
- `shared/contracts/monadTestnet.deployment.json`

ABI 由 `contracts/scripts/export-abis.ts` 自动导出，禁止在前端手工维护第二份 ABI。运营铸造、等级升级、metadata 管理、会费管理和提现由后端最小权限运营钱包执行；前端只能发起用户自己的登录签名和入会交易。

## 4. 常用命令

```bash
npm run dev
npm run test:wallet-login
npm run typecheck
npm run build
```

合约完整发布与同步：

```bash
cd contracts
npm run release:testnet
```

详细参数见 `docs/CONTRACT_DEPLOYMENT.md`。
