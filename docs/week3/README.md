# Fanora Week 3 初步版本交付

> 更新时间：2026-07-23  
> 项目阶段：可运行、可演示、可继续联调的 MVP 初步版本  
> Repo：[github.com/ouminghai/Fanora](https://github.com/ouminghai/Fanora)

## 1. 本周交付目标

本阶段不追求一次完成全部产品能力，重点是让团队能够看到并测试 Fanora 的核心流程：

```text
连接钱包并签名登录
  → 缴纳链上会费成为正式会员
  → 参与社区、任务并获得 FAN
  → 查看或同步 ERC-721 会员身份
  → 发布粉丝限量 NFT
  → 使用 FAN 购买并获得 ERC-1155 收藏品
```

当前 Repo 已包含可运行网页、FastAPI、Monad 合约、部署地址、测试、README 和演示说明。

## 2. 目前完成了什么

### 2.1 可运行网页 / DApp

- Fanora 首页与 Proof of Fandom 产品介绍。
- RainbowKit 钱包连接与钱包签名登录。
- 用户 Profile、主钱包、FAN 余额、终身 FAN 和会员等级展示。
- Fanora 单一官方社区、Markdown 创作、多图、回复、点赞和收藏。
- 每日签到、任务领取、自动验证、幂等 FAN 奖励和积分流水。
- Monad Testnet 动态会费缴纳与后端交易验证。
- ERC-721 SBT 会员身份同步、会员证生成与刷新。
- 个人 ERC-1155 收藏页与收藏品头像设置。
- 粉丝 NFT 广场、分类筛选、创作者集合、详情、点赞与收藏。
- 正式会员发布限量 NFT，图片与 metadata 上传 Pinata。
- 使用站内 FAN 购买 NFT，并在 Monad Testnet 铸造 ERC-1155 给买家。

主要页面：

| 页面 | 地址 | 用途 |
| --- | --- | --- |
| 首页 | `http://localhost:3000` | 产品入口、任务与会员等级展示 |
| 登录 | `http://localhost:3000/login` | RainbowKit 钱包连接和签名登录 |
| Profile | `http://localhost:3000/profile` | 用户资料、钱包、FAN 与等级 |
| 正式入会 | `http://localhost:3000/membership/join` | 支付 Gateway 当前链上会费 |
| 官方社区 | `http://localhost:3000/community` | 签到、社区状态和内容入口 |
| 任务中心 | `http://localhost:3000/community/tasks` | 领取并完成粉丝任务 |
| 创作社区 | `http://localhost:3000/community/creations` | Markdown、多图、评论与互动 |
| 我的收藏 | `http://localhost:3000/collection` | 会员证、链上身份和收藏品 |
| NFT 广场 | `http://localhost:3000/collections` | 浏览、筛选、点赞粉丝 NFT |
| 发布 NFT | `http://localhost:3000/collections/create` | 正式会员发布限量 NFT |

### 2.2 后端与 Agent

- FastAPI 统一 API、认证、限流、日志、配置与健康检查。
- PostgreSQL/SQLModel/Alembic 用户、钱包、社区、任务、FAN、会员、NFT 和链上操作模型。
- 一次性 challenge、签名恢复、会话创建和退出登录。
- FAN 可用余额与终身累计分离；消费不会降低已经获得的等级。
- LangGraph 粉丝画像、结构化评分、解释和确定性降级结果。
- Monad Adapter 读取交易、回执、事件并执行受控合约写入。
- Pinata Adapter 上传 NFT 图片和 metadata，并保存 CID 与版本。

API 文档在后端启动后访问：`http://localhost:8000/docs`。

### 2.3 智能合约

- `FanoraMembershipGateway`：动态会费、付款防重、资金托管、改价和提现。
- `FanoraMembershipIdentity`：不可转让 ERC-721 SBT，一个钱包最多一个身份，等级或会员证刷新不改变 tokenId。
- `FanoraCollectibles`：ERC-1155 纪念资产，约束类别、供应量、单钱包上限、时间窗、claimKey、转让策略和 metadata 冻结。
- Hardhat 合约测试 19 项通过。

## 3. Monad Testnet 合约与交易地址

网络：Monad Testnet，Chain ID `10143`。

| 合约 | 地址 | 部署交易 |
| --- | --- | --- |
| Membership Gateway | [`0xd966...7A93`](https://testnet.monadvision.com/address/0xd966Fb616cBFd6c54d317Fc1d87344455e1F7A93) | [查看交易](https://testnet.monadvision.com/tx/0xd0f463fbeaad2f5a28d246f7843fdc3312468abeb05d36a0f588551cc19ad904) |
| Membership Identity | [`0xeE3c...5c85`](https://testnet.monadvision.com/address/0xeE3c3F36fF43aCB44F0F8271fbE7cdbAAcaF5c85) | [查看交易](https://testnet.monadvision.com/tx/0x31e4fd7670fd93021e8067312393a5b3c3ca2d9d3ea7ce81e764f69fd3fd323e) |
| Collectibles | [`0xB2ff...3A84`](https://testnet.monadvision.com/address/0xB2ffc47D5a9407f0118e12749847821530533A84) | [查看交易](https://testnet.monadvision.com/tx/0x2bc9713047531368dd54628f2679e2810e40f5b29b8c4e36a7830e3f987ad288) |

完整 ABI、地址和部署区块见：

- `shared/contracts/monadTestnet.deployment.json`
- `contracts/deployments/monadTestnet.json`
- `shared/contracts/*.json`

## 4. 如何查看或运行

### 4.1 最快启动方式

准备 Node.js 20+、Python 3.13、npm、uv，并为前后端复制环境变量模板。

启动后端：

```bash
cd backend
cp .env.example .env
make install
make migrate
make dev
```

启动前端：

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

浏览器访问 [http://localhost:3000](http://localhost:3000)。

如果只需要查看静态页面和构建结果，可以只启动前端；钱包登录、社区、FAN、会员证和 NFT 数据需要后端与数据库同时可用。

### 4.2 钱包与测试网准备

1. 钱包切换到 Monad Testnet，Chain ID 为 `10143`。
2. 准备少量测试 MON，用于正式入会交易。
3. 在 `frontend/.env.local` 配置 WalletConnect Project ID、API 地址和三个公开合约地址。
4. 在 `backend/.env` 配置数据库、Monad RPC、合约地址、Pinata 和必要的测试网运营钱包。
5. 私钥、Pinata JWT 和数据库密码只能放在本地或部署密钥环境，不能提交到 Git。

详细配置见：

- [本地开发说明](../DEVELOPMENT.md)
- [钱包与合约接入](../../frontend/WEB3_SETUP.md)
- [合约发布指南](../CONTRACT_DEPLOYMENT.md)

## 5. 哪些功能真实可用

以下功能不是纯 UI Mock，已经连接后端、数据库或 Monad Testnet：

| 功能 | 当前真实链路 |
| --- | --- |
| 钱包登录 | RainbowKit → challenge → 钱包签名 → FastAPI 恢复地址 → 会话 |
| 正式入会 | 钱包调用 Gateway → Monad 交易 → 后端验证事件与确认数 → 激活会员 |
| 社区互动 | FastAPI + PostgreSQL 保存帖子、回复、点赞、收藏和加入关系 |
| 签到与任务 | 服务端验证、任务状态记录、幂等 FAN 流水 |
| FAN 与等级 | PostgreSQL 可用余额、终身累计和等级规则 |
| 会员身份 | Pinata metadata + Monad ERC-721 SBT |
| NFT 发布 | 正式会员校验 + FAN 发布费 + Pinata + ERC-1155 token type |
| NFT 购买 | 买家扣 FAN + 创作者得 FAN + ERC-1155 mint + 收藏记录 |
| 合约地址 | 已部署 Monad Testnet，可通过区块浏览器验证 |

## 6. 哪些功能仍是 Mock 或原型实现

- 首页部分粉丝画像卡片、介绍文案和展示数据仍是静态演示内容。
- 本地开发数据库会写入种子社区帖子和任务，部分图片来自本地 `resources/`。
- 未配置 OpenAI API 时，LangGraph 使用确定性规则返回画像，不代表真实 LLM 调用成功。
- FEAR and DREAMS 任务页目前主要展示未来 NFT 奖励流程，任务限定 Badge 尚未完整铸造。
- 演唱会纪念卡和任务 Badge 的运营创建、资格领取与前端状态尚未形成完整闭环。
- NFT 原始图片当前可作为 Base64 保存在 PostgreSQL，属于原型方案；生产环境应迁移对象存储。
- 当前 NFT 市场是 FAN 驱动的一级发布/购买体验，不是链上二级市场、拍卖或版税系统。

## 7. 当前验证结果

| 检查 | 结果 |
| --- | --- |
| 前端启动与页面渲染 | 通过 |
| 前端 TypeScript | 通过 |
| 前端专项测试 | 通过 |
| 前端生产构建 | 通过，生成 16 个页面路由 |
| 前端 ESLint | 0 error，4 warning |
| 后端核心专项测试 | 21 项通过 |
| 后端 Ruff | 通过 |
| 后端全量 Pytest | 21 通过，16 项因种子图片缺失在 setup 阶段报错 |
| 后端 Pyright | 4 个待处理错误 |
| 合约 Hardhat 测试 | 19 项通过 |

## 8. 目前还有什么问题

1. 全新数据库初始化依赖被 Git 忽略的 `resources/` 图片；缺少素材时测试会在启动阶段失败。
2. 首页加入流程仍残留“邮箱/社交账号创建钱包”的旧文案，与当前 RainbowKit 钱包登录不一致。
3. 前端存在 4 条 Hook/图片优化 warning，浏览器还有图片比例、LCP 和 Lit 开发模式提示。
4. 后端 Pyright 尚有 4 个错误，包括签到响应类型和可选依赖类型解析。
5. 链上写入主要在 HTTP 请求中等待确认，缺少可靠后台队列、自动重试、链重组处理和完整事件对账。
6. NFT 发布/购买失败后的完整补偿、退款、下架和治理界面尚未完成。
7. Testnet 运营角色目前共用部署钱包，生产环境需要拆分最小权限账户并迁移管理员权限到多签。

## 9. 建议演示范围

Week 3 建议重点展示以下四条流程，不需要演示尚未完成的生产治理能力：

1. 首页 → 连接钱包 → 签名登录 → 进入个人收藏。
2. 官方社区 → 每日签到或任务 → FAN 余额与等级变化。
3. 正式会员 → 生成/刷新 ERC-721 会员证 → 打开 MonadVision 链接。
4. NFT 广场 → 查看详情 → 发布或使用 FAN 购买 → 在个人收藏查看 ERC-1155。

具体演示步骤见 [DEMO_GUIDE.md](./DEMO_GUIDE.md)。
