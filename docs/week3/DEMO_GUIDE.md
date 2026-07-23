# Fanora Week 3 Demo Guide

## 1. 演示前检查

- FastAPI：`http://localhost:8000/api/v1/health`
- OpenAPI：`http://localhost:8000/docs`
- Next.js：`http://localhost:3000`
- 钱包已切换 Monad Testnet，Chain ID `10143`
- 钱包有少量测试 MON
- `NEXT_PUBLIC_API_URL` 指向当前 FastAPI
- WalletConnect、Monad RPC、三个合约地址已经配置
- 需要演示 NFT 发布时，后端 Pinata 和收藏品运营钱包已经配置

## 2. 推荐演示脚本

### 流程 A：钱包登录

1. 打开首页。
2. 点击“直连钱包”。
3. 选择 MetaMask、WalletConnect 或其他 RainbowKit 钱包。
4. 签署登录 challenge；强调该签名不消耗 Gas，也不授权资产转移。
5. 登录成功后进入 `/collection`，展示统一用户、主钱包和收藏页。

成功标准：后端恢复的签名地址与连接钱包一致，并创建或恢复同一个 Fanora 会话。

### 流程 B：社区、任务与 FAN

1. 打开 `/community`，展示官方社区与签到入口。
2. 完成每日签到或进入 `/community/tasks` 领取任务。
3. 打开 `/community/creations`，展示 Markdown、多图、点赞、收藏和两层回复。
4. 完成一个当前支持的自动验证任务。
5. 返回 Profile 或 FAN 流水，展示幂等奖励和终身 FAN。

成功标准：重复请求不重复发奖；可用 FAN 与终身累计均由后端返回。

### 流程 C：正式会员与 ERC-721 会员证

1. 待入会用户打开 `/membership/join`。
2. 前端读取 Gateway 当前会费，不把 1 MON 写死在 UI 中。
3. 钱包提交 `join(paymentId)` 交易。
4. 后端验证交易、事件、金额、发送方、链 ID 和确认数。
5. 打开 `/collection`，同步身份并生成会员证。
6. 展示 tokenId、metadata、交易状态和 MonadVision 链接。

成功标准：同一用户/钱包不会重复创建身份；刷新会员证不会改变 tokenId。

### 流程 D：粉丝 NFT 发布与购买

1. 打开 `/collections`，展示真实 NFT、分类筛选、价格、供应量和创作者。
2. 打开一个 `/item/[id]`，展示图片、Markdown 故事、属性和铸造记录。
3. 使用正式会员进入 `/collections/create`。
4. 上传图片，填写名称、描述、主题、FAN 价格、供应量和版权声明。
5. 发布后展示 Pinata、token type 创建和 Monad 确认进度。
6. 切换另一个用户使用 FAN 购买。
7. 在 `/collection` 查看新获得的 ERC-1155，并尝试设置为头像。

成功标准：发布扣除发布费；购买扣买家 FAN、增加创作者 FAN，并铸造给经过认证的买家主钱包。

### 流程 E：LangGraph 粉丝画像与 FEAR and DREAMS

1. 登录正式会员并加入官方社区。
2. 打开 `/profile`，展示由数据库行为汇总生成的分数、粉丝类型、解释和可参与任务推荐。
3. 打开 `/community/tasks/fear-and-dreams`，领取任务并提交一段有具体信息的现场记忆。
4. 展示最近一次 AI 审核的结论、分数和原因；再提交“哈哈哈哈”可演示防灌水拒绝且不发 FAN。
5. 审核通过后展示 500 FAN 与 NFT 奖励状态。
6. 链上配置完整时打开 MonadVision 纪念票链接；配置不完整时展示 `WAITING_CONFIGURATION`，说明系统没有伪造交易。

成功标准：拒绝结果可以重新提交；通过结果只奖励一次；纪念票使用 `/img/fanora/eason-concert.webp`，同一用户、任务和版本不重复铸造。

### 流程 F：AI 生成限量粉丝 NFT 草稿

1. 正式会员打开 NFT 发布入口。
2. 填写主题、粉丝故事和视觉风格，点击“AI 生成草稿与图片”。
3. 展示自动填入的名称、描述、属性和图片，并手动修改其中任意字段。
4. 强调 Agent 不决定价格、供应量，也不会自动发布；用户确认后才进入原有发布流程。

成功标准：配置图片模型时返回 Base64 图片；未配置时返回可编辑 metadata 草稿并允许用户自行上传图片。

## 3. 无法演示真实链上交易时的降级方案

- 展示 MonadVision 中三个已部署合约和部署交易。
- 展示 `/collections` 已存在的真实市场数据与 NFT 详情。
- 展示后端 OpenAPI 的 NFT、会员和认证接口。
- 展示 `/profile` 粉丝画像和 Quest 审核结果；这些数据库流程不依赖真实链上写入。
- 运行前端生产构建、专项测试和 Hardhat 测试作为可复现证据。
- 明确说明哪些步骤因测试 MON、Pinata、运营钱包或数据库环境缺失而没有现场执行。



## 4. 演示结束后的反馈记录

建议记录：

- 使用的钱包类型和地址后四位。
- 登录、入会、会员证、发布和购买是否成功。
- 交易哈希或失败步骤。
- 页面报错、控制台错误或明显卡顿。
- 团队最希望下一阶段优先补齐的流程。
