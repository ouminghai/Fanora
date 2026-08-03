# Fanora 2026-07-23 交付总结

本次文档以当前代码、Monad Testnet 配置和本地实际运行结果为准，替代 2026-07-21 总结作为当前状态入口。历史总结保留原样，不回写成今天的事实。

## 1. 当前已交付

### 钱包、会话与正式会员

- 前端只使用 RainbowKit、wagmi 和 viem 连接 MetaMask、WalletConnect 等外部钱包。
- 登录通过一次性 challenge、钱包签名和 `POST /api/v1/auth/wallet` 创建会话；Fanora 不生成或导出用户私钥。
- Gateway 会费由链上 `membershipFee` 决定，前端使用“缴纳会费正式加入”动态文案，不再把 1 MON 写死为产品事实。
- 后端验证发送钱包、合约地址、金额、事件、链 ID、交易状态和确认数后激活正式会员。

### FAN、等级与会员证

- `fan_token_balance` 表示可消费 FAN，`fan_token_lifetime_earned` 表示只累计正向奖励的终身成长值。
- 会员等级由终身累计 FAN 决定且只升不降；发布或购买 NFT 消费 FAN 不会降低既有等级。
- 正式会员可以创建或同步唯一 ERC-721 SBT 身份，等级变化更新同一 tokenId 的 levelId 与 metadata。
- `/collection` 支持会员证生成、刷新、metadata、交易状态和 MonadVision 链接。

### 粉丝 NFT 市场

- `/collections` 提供公开 NFT 广场、主题筛选、创作者信息、价格、剩余供应量和点赞。
- `/collections/create` 允许正式会员发布粉丝限量 NFT；后端校验图片、字段、FAN 余额、价格和供应量。
- 发布成功后图片与 metadata 固定到 Pinata，创建 `FAN_LIMITED_NFT` ERC-1155 token type，并扣除默认 100 FAN 发布费。
- `/item/[id]` 提供详情、故事图片、公开属性、铸造记录、点赞、收藏和 FAN 购买。
- 购买成功后买家扣 FAN、创作者获得 FAN，并由后端铸造 ERC-1155 给买家；单钱包上限为 1。
- `/collection/[id]` 展示创作者集合；个人收藏品可以设置为头像。

### 合约与部署

- `FanoraMembershipGateway`、`FanoraMembershipIdentity`、`FanoraCollectibles` 已部署 Monad Testnet。
- ABI、合约地址和公开部署清单由脚本同步到 `shared/contracts`、前端和后端配置。
- 当前 Hardhat 测试 19 项通过，覆盖动态会费、SBT、会员证 URI 刷新、operationId、供应量、钱包上限、时间窗、claimKey、转让策略、暂停和 metadata 冻结。

## 2. 2026-07-23 本地运行证据

- Next.js 15.5.20 在 `http://localhost:3000` 启动成功。
- FastAPI 0.2.0 在 `http://127.0.0.1:8000` 启动成功，实际数据库可读取会员等级、任务、社区内容和 NFT 市场。
- 首页标题为 `Fanora Protocol | Proof of Fandom`，主要内容正常渲染；视频声音按钮可从“打开视频声音”切换为“关闭视频声音”。
- NFT 广场标题为 `粉丝 NFT 广场 | Fanora`，实际读取到已发布 NFT；“故事”分类可切换为激活状态并显示对应空结果。
- 页面没有框架错误覆盖层；开发控制台存在 Next.js 图片宽高/LCP 提示和 Lit 开发模式提示，但没有阻断交互的运行时错误。

## 3. 验证结果

| 范围 | 结果 | 说明 |
| --- | --- | --- |
| 前端 TypeScript | 通过 | `npm run typecheck` |
| 前端 ESLint | 通过但有 4 条 warning | Hook dependency 与 `<img>` 优化提示 |
| 前端专项测试 | 通过 | 已配置测试全部通过；另有 bytes32 与 collection/profile 14 项测试通过 |
| 前端生产构建 | 通过 | Next.js 生成 16 个页面路由，保留 4 条 ESLint warning |
| 后端 Pytest | 21 通过，16 setup error | 新测试数据库种子依赖被 `.gitignore` 排除的 `resources/` 图片；当前缺少 `Eason-Concert-Horizontal-01-2-3c-2048x1025.webp` |
| 后端核心专项测试 | 21 通过 | Fan Profile、终身 FAN、动态会费幂等、迁移、Monad Adapter、NFT 服务与超时配置 |
| 后端 Ruff | 通过 | `uv run ruff check .` |
| 后端 Pyright | 4 errors | 签到响应类型、两个可选依赖导入和社区图片 URL 返回类型 |
| 合约测试 | 19 通过 | Hardhat 全量测试通过 |

## 4. 当前已知问题

1. `backend/app/services/product_seed.py` 从被 Git 忽略的 `resources/` 读取种子图片。全新 clone 或缺少本地素材时，测试数据库初始化会抛出 `FileNotFoundError`；应改为提交可再分发的种子素材、使用已提交的前端公开资源，或为缺失素材提供确定性回退。
2. 首页若干图片存在 Next.js 宽高比例 warning，NFT 市场首屏图片存在 LCP priority warning。
3. 当前链上写入主要在 HTTP 请求中等待确认；后台重试、链重组处理、常驻事件监听和完整对账尚未完成。
4. 任务限定 Badge 与演唱会纪念卡的资格领取前端闭环尚未完成。
5. 粉丝 NFT 原始图片仍可作为 Base64 保存在 PostgreSQL；生产环境应迁移独立对象存储并增加配额、扫描和清理。
6. Testnet 运营角色仍需拆分最小权限账户，并将管理员权限迁移至多签。

## 5. 下一阶段建议

优先修复可复现的新环境种子资源问题并恢复后端全量测试，然后完成链上后台重试/对账和任务 Badge 领取。之后再处理 NFT 市场治理、对象存储与生产权限拆分。
