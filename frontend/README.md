# Fanora Frontend

该模块由原 `xhibiter-ts` 模板整理而来，使用 Next.js、RainbowKit、wagmi 和 viem。

第一阶段只保留一个主要用户流程：连接 Monad Testnet 钱包，查看任务与积分，并展示 Proof of Fandom Badge。模板中其他 NFT 市场页面可以逐步改造或删除，不需要一次处理完。

## 启动

```bash
cp .env.example .env.local
npm install
npm run dev
```

浏览器访问 `http://localhost:3000`。

## 目录建议

- `app/`：页面和路由。
- `components/`：可复用界面模块。
- `lib/web3/`：Monad 网络、合约地址和 ABI。
- `hooks/`：钱包与合约读取 hooks。
- `data/`：当前模板演示数据，后续逐步替换为后端接口。

