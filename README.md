# Fanora Protocol

Fanora 是一个由 AI Agent 驱动的 Web3 链上粉丝身份与互动协议。系统结合用户互动数据、链上行为和 Agent 分析，生成可验证的粉丝画像，并通过 Monad 上的动态 Badge / SBT 记录粉丝身份。

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

- `frontend`：钱包连接、用户 Dashboard、任务中心、徽章墙和创作者控制台。
- `backend`：钱包登录、任务验证、积分计算、Agent 工作流、数据库和链上写入编排。
- `contracts`：Proof of Fandom Badge、身份等级以及受权限控制的链上状态。
- `docs`：跨模块的架构、接口约定和 MVP 开发顺序。

## 推荐启动顺序

1. 启动后端健康检查。
2. 启动前端并完成 Monad Testnet 钱包连接。
3. 编译、测试并部署 Badge 合约。
4. 将合约地址分别写入前端和后端的本地环境变量。

详细内容见 [技术架构文档](docs/ARCHITECTURE.md)、[开发需求文档](docs/PRODUCT_REQUIREMENTS.md)、[本地开发说明](docs/DEVELOPMENT.md) 和 [MVP 路线图](docs/MVP_ROADMAP.md)。
