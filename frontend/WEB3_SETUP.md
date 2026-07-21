# Web3Auth、MetaMask 与 Fanora 合约接入说明

Fanora 前端使用 Web3Auth Modal 统一处理嵌入式身份和外部钱包登录。正式入会必须在 Modal 中选择 MetaMask，由用户钱包弹窗确认 Gateway 交易。

## 1. 环境变量

复制 `.env.example` 为 `.env` 或 `.env.local`。主要配置包括：

```env
NEXT_PUBLIC_WEB3AUTH_CLIENT_ID=Web3Auth项目ClientID
NEXT_PUBLIC_WEB3AUTH_NETWORK=sapphire_devnet
NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=
NEXT_PUBLIC_MONAD_TESTNET_RPC_URL=https://testnet-rpc.monad.xyz
NEXT_PUBLIC_MEMBERSHIP_PAYMENT_CONTRACT_ADDRESS_MONAD_TESTNET=0x...
NEXT_PUBLIC_MEMBERSHIP_IDENTITY_CONTRACT_ADDRESS_MONAD_TESTNET=0x...
NEXT_PUBLIC_COLLECTIBLES_CONTRACT_ADDRESS_MONAD_TESTNET=0x...
```

`NEXT_PUBLIC_` 变量会进入浏览器，只能填写公开配置，严禁填写部署私钥、运营私钥、Pinata JWT 或其他服务端密钥。

合约发布后无需手工复制地址：

```bash
cd contracts
npm run sync:testnet
```

## 2. 登录与付款流程

1. 前端初始化 Web3Auth Modal。
2. 用户选择 MetaMask 或 Web3Auth 嵌入式身份完成登录。
3. 后端生成一次性 challenge，用户钱包执行 `personal_sign`。
4. 后端验证 challenge、签名和 Web3Auth Identity Token 后创建 Fanora 会话。
5. 入会页要求当前连接器为 MetaMask，并核对 MetaMask 当前账户与登录主钱包一致。
6. 前端读取后端返回的 Gateway 地址、`paymentId` 和链上当前会费。
7. 前端通过 `eth_sendTransaction` 请求 MetaMask 调用 `join(paymentId)`，不读取用户私钥。
8. 后端验证 `MembershipPaid` 事件后激活正式会员，并尝试铸造初始 ERC-721 身份。

## 3. 合约与 ABI

- `shared/contracts/FanoraMembershipGateway.json`
- `shared/contracts/FanoraMembershipIdentity.json`
- `shared/contracts/FanoraCollectibles.json`
- `shared/contracts/monadTestnet.deployment.json`

ABI 由 `contracts/scripts/export-abis.ts` 自动导出，禁止在前端手工维护第二份 ABI。

运营铸造、等级升级、metadata 管理、会费管理和提现都由后端最小权限运营钱包执行。前端只能发起用户自己的入会付款交易和读取公开状态。

## 4. 常用命令

```bash
npm run dev
npm run typecheck
npm run build
```

合约完整发布与同步命令：

```bash
cd contracts
npm run release:testnet
```

详细参数见 `docs/CONTRACT_DEPLOYMENT.md`。
