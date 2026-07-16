# Web3 接入说明

项目现在使用主流的 `wagmi + viem + RainbowKit + TanStack Query` 组合。

## 1. 本地环境变量

复制 `.env.example` 为 `.env.local`，至少填写：

```bash
NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=你的项目ID
```

Project ID 在 [WalletConnect Cloud](https://cloud.walletconnect.com) 免费创建。没有该 ID 时，浏览器插件钱包通常仍可测试，但 WalletConnect 扫码连接不能正常使用。

开发阶段使用 Monad Testnet。公共 RPC 可以直接启动项目；需要更稳定的请求额度时，再配置专用 RPC。

## 2. 关键文件

- `lib/web3/config.ts`：支持的链、RPC、RainbowKit 和 wagmi 配置。
- `components/providers/Web3Provider.tsx`：全局 Web3 状态和请求缓存。
- `components/web3/WalletButton.tsx`：统一的钱包连接、切链和账户入口。
- `lib/web3/contracts.ts`：不同链上的 Badge 合约地址。
- `lib/web3/abi/badge.ts`：Badge 合约 ABI，当前使用标准 ERC-1155 读取接口。
- `hooks/useBadgeBalance.ts`：按 Badge ID 读取当前钱包持有数量的示例。

## 3. 接入 Badge 合约

合约部署后，把对应网络地址写入 `.env.local`：

```bash
NEXT_PUBLIC_BADGE_CONTRACT_ADDRESS_MONAD_TESTNET=0x...
```

然后把 Solidity 编译生成的 ABI 放进 `lib/web3/abi/badge.ts`。只有 ABI 中真实存在 `claim` 或 `mint` 方法时，前端才应使用 `useWriteContract` 发起交易；不要在前端猜测合约函数签名。

标准交易流程是：

1. 使用 `useSimulateContract` 预检查交易。
2. 使用 `useWriteContract` 请求钱包签名。
3. 使用 `useWaitForTransactionReceipt` 等待链上确认。
4. 成功后刷新相关的 `useReadContract` 查询。

## 4. 常用命令

```bash
npm run dev
npm run build
```

钱包连接不是传统账号密码登录。若后续需要服务端会话和权限控制，可以再接 SIWE（Sign-In with Ethereum），由用户签名随机 nonce，服务端验证签名后创建会话。
