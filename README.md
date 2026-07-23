# Fanora Protocol

Fanora 是一个由 AI Agent 驱动的 Web3 链上粉丝身份与互动协议。系统结合用户互动数据、链上行为和 Agent 分析，生成可验证的粉丝画像，并通过 Monad 上的动态 Badge / SBT 记录粉丝身份。

## 阶段交付摘要

如果只想快速了解项目当前真实完成度、验证结果和剩余风险，请直接阅读 [2026-07-23 交付总结](docs/DELIVERY_SUMMARY_2026-07-23.md)。

## 项目结构

```text
Fanora/
├── frontend/       # Next.js、RainbowKit、wagmi、viem
├── backend/        # FastAPI、LangGraph、web3.py
├── contracts/      # Solidity、Hardhat、Monad
└── docs/           # 架构与开发路线文档
```

三个主要模块各自维护依赖和环境变量，不要把前端、Python 和 Hardhat 的依赖安装到同一个目录。

## 模块职责

- `frontend`：RainbowKit 钱包登录、用户资料、社区与任务、会员证、个人收藏和粉丝 NFT 市场。
- `backend`：FastAPI 统一身份、任务验证、FAN 与终身等级、LangGraph 粉丝画像、Pinata 和 Monad 链上写入编排。
- `contracts`：动态会费 Gateway、ERC-721 SBT 会员身份和 ERC-1155 粉丝纪念资产。
- `docs`：跨模块的架构、接口约定和 MVP 开发顺序。

## 推荐启动顺序

1. 启动后端健康检查。
2. 启动前端并完成 Monad Testnet 钱包连接。
3. 按需编译、测试或部署三个正式合约。
4. 使用同步脚本将 ABI、合约地址和起始区块写入前端、后端与公开部署清单。

详细内容见 [技术架构文档](docs/ARCHITECTURE.md)、[开发需求文档](docs/PRODUCT_REQUIREMENTS.md)、[本地开发说明](docs/DEVELOPMENT.md) 和 [MVP 路线图](docs/MVP_ROADMAP.md)。
