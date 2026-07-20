# Fanora 本地开发说明

> 更新日期：2026-07-20\
> 本文只描述当前代码可以执行的命令；尚未实现的 ERC-721、ERC-1155 v1.3 和 Pinata 配置会明确标为“目标配置”。

## 1. 前置环境

- Node.js 20+
- npm
- Python 3.13（推荐）
- [uv](https://docs.astral.sh/uv/)
- Docker Desktop（推荐用于本地 PostgreSQL）
- Monad Testnet 测试钱包（仅在实际部署或交易时需要）

不要把前端、后端和 Hardhat 依赖安装到同一个目录。

## 2. 推荐启动顺序

```text
PostgreSQL
  → FastAPI / migration
  → Next.js
  → 按需编译合约原型
```

### 2.1 启动 PostgreSQL

```bash
cd backend
make db-up
```

创建被 Git 忽略的 `backend/.env.local`，覆盖默认 SQLite 或远程数据库：

```env
DATABASE_URL=postgresql+psycopg://fanora:fanora-local-password@127.0.0.1:5432/fanora
AUTO_CREATE_SCHEMA=false
```

应用迁移：

```bash
make migrate
```

常用数据库命令：

```bash
make db-status
make db-logs
make db-down
```

### 2.2 启动后端

```bash
cd backend
curl -LsSf https://astral.sh/uv/install.sh | sh
cp .env.example .env
make install
make migrate
make dev
```

默认地址：

- API：`http://localhost:8000`
- OpenAPI：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/api/v1/health`

也可以启动 API、PostgreSQL 和 Valkey：

```bash
make docker-up
```

包含 Prometheus 和 Grafana 的完整开发栈：

```bash
make stack-up
```

### 2.3 启动前端

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

默认地址：`http://localhost:3000`。

常用页面：

- 登录：`http://localhost:3000/login`
- Profile：`http://localhost:3000/profile`
- 正式入会：`http://localhost:3000/membership/join`
- 官方社区：`http://localhost:3000/community`
- 粉丝任务中心：`http://localhost:3000/community/tasks`
- FEAR and DREAMS 纪念票任务：`http://localhost:3000/community/tasks/fear-and-dreams`
- 创作社区瀑布流：`http://localhost:3000/community/creations`

前端业务请求统一通过 Axios 访问 `NEXT_PUBLIC_API_URL`。

## 3. 当前后端接口

### 3.1 认证与用户

- `POST /api/v1/auth/challenge`
- `POST /api/v1/auth/web3auth`
- `POST /api/v1/auth/logout`
- `GET /api/v1/users/me`
- `PATCH /api/v1/users/me`

### 3.2 官方社区与会员

- `GET /api/v1/communities`：当前兼容接口，MVP 只读取其中唯一的 Fanora 官方社区。
- `PATCH /api/v1/communities/{official_community_id}`：维护官方社区资料。
- `POST /api/v1/communities/{official_community_id}/join`：加入官方社区。
- `GET /api/v1/membership-levels`
- `GET /api/v1/membership/me`
- `POST /api/v1/membership/verify`

### 3.3 签到、创作、任务与 Fan Token

- `GET /api/v1/community`：读取唯一官方社区及成员/内容统计。
- `POST /api/v1/community/join`：幂等加入官方社区。
- `GET|POST /api/v1/community/posts`：浏览或发布社区创作。
- `GET /api/v1/community/posts/{post_id}`：帖子详情与回复列表。
- `POST /api/v1/community/posts/{post_id}/replies`：发布回复；如已领取对应任务，服务端直接验证并发奖。
- `POST /api/v1/community/posts`：正文使用 Markdown 保存，首图通过 `cover_url` 独立提交；本地上传会转换为最大 1 MB 的 JPEG、PNG、WebP 或 GIF Base64 Data URL。
- `POST /api/v1/community/posts/{post_id}/like`：幂等切换创作点赞状态。
- `POST /api/v1/community/posts/{post_id}/bookmark`：幂等切换创作收藏状态。
- `POST /api/v1/community/replies/{reply_id}/like`：切换评论点赞状态。

评论通过 `parent_reply_id` 支持两层结构：顶层评论可拥有子评论，子评论不能继续产生第三层嵌套。创作封面支持 JPEG、PNG、WebP 或 GIF，大小上限 1 MB。
- `GET /api/v1/check-ins/me`、`POST /api/v1/check-ins`：北京时间每日签到，同一自然日只成功一次。
- `GET /api/v1/tasks`、`POST /api/v1/tasks/{task_id}/claim`：浏览与幂等领取任务；响应包含统一的 `presentation` 动作与展示配置。
- `POST /api/v1/tasks/{task_id}/complete`：完成专属页面任务；当前要求提交互动记录，仅支持 `page_action`，后续 NFT 领取仍需接入独立链上验证。
- `POST /api/v1/tasks`、`PUT /api/v1/tasks/{task_id}`、`POST /api/v1/tasks/{task_id}/status`：创作者任务管理。
- `GET /api/v1/fan-tokens/me/ledger`：当前用户的不可变 FAN 流水。
- `POST /api/v1/fan-tokens/admin/adjustments`：管理员通过新增流水做正负纠错。
- `PUT /api/v1/admin/users/{user_id}/roles/creator`：管理员授予创作者角色。

任务完成统一收敛到任务完成模块：`post_reply` 由有效回复触发，`daily_check_in` 由签到触发，`content_publish` 由符合分类的社区创作触发，`page_action` 由专属活动页触发；`streak`、`event_check_in` 和 `future` 用于即将开放任务。所有已支持模式均不需要人工审核，奖励使用领取时快照，FAN 流水使用唯一幂等键，重放请求不会重复发奖。`frontend/data/fanora.ts` 的 `fanTaskCatalog` 是首页活动、热门任务和任务中心共用的展示目录，后端仍是领取状态、验证结果和积分流水的事实来源。

当前代码仍保留通用社区表和部分复数路由，但不要在 MVP 中创建第二个社区，也不要继续开发社区搜索、分页、独立积分、独立任务、独立等级、Badge 命名空间或多管理员能力。目标 API 将逐步收敛为单数 `/community` 路径。

创作正文前端使用 `MarkdownEditor` 编辑和预览，详情与编辑预览统一通过 `MarkdownContent` 渲染 GitHub Flavored Markdown。渲染器不启用原始 HTML；文章详情采用“分类与标题 → 作者 → 大幅首图 → Markdown 正文”的顺序。列表摘要由服务端移除常见 Markdown 标记后生成。

开发种子从仓库根目录 `resources/` 及其子目录读取选定图片，转换为 Base64 Data URL 后写入 PostgreSQL：社区帖子写入 `community_posts.cover_url`，任务卡图片写入 `fan_tasks.validation_rule.presentation.image_url`。迁移 `20260720_0012` 会将现有官方帖子和任务一并更新；当前方案用于原型阶段，生产环境应迁移到对象存储并在数据库保存 URL、哈希和媒体元数据。

链上资产持有/交易任务、ERC-721 身份、ERC-1155 纪念资产、自定义 NFT 申请和 Pinata 接口仍属于待实现范围，以 `PRODUCT_REQUIREMENTS.md` 为准。

## 4. 正式入会本地配置

真实测试 1 MON 入会交易前，在 `backend/.env.local` 配置 Monad Testnet 收款地址：

```env
MEMBERSHIP_TREASURY_ADDRESS=0x你的Monad测试网收款地址
MEMBERSHIP_FEE_WEI=1000000000000000000
MEMBERSHIP_MIN_CONFIRMATIONS=1
```

未配置收款地址时，缴纳页只展示配置提示，不会调用钱包发送交易。

## 5. 钱包与私钥安全

- Web3Auth 嵌入式钱包私钥导出只在 Profile 中由用户主动确认后执行。
- 导出请求由浏览器直接调用钱包 Provider，不经过 FastAPI、Axios、数据库或 Agent。
- 开发与测试时禁止输出、截图、复制到日志或持久化真实私钥。
- `OPERATOR_PRIVATE_KEY` 与 `DEPLOYER_PRIVATE_KEY` 只能使用独立 Monad Testnet 钱包。
- 不要使用持有真实资产的主钱包进行测试。

## 6. 合约开发

### 6.1 当前代码状态

`contracts/contracts/ProofOfFandomBadge.sol` 是早期 ERC-1155 SBT 原型，目前用于验证：

- OpenZeppelin ERC-1155 与 AccessControl。
- 受控 mint/upgrade。
- 基础 URI 更新。
- 用户间转让被拒绝。

它不满足 v1.3 的双合约需求，不能作为 `FanoraMembershipIdentity` 或 `FanoraCollectibles` 的最终部署版本。

### 6.2 编译与测试当前原型

```bash
cd contracts
cp .env.example .env
npm install
npm run compile
npm test
```

准备独立测试网部署钱包后：

```bash
npm run deploy:testnet
```

部署前确认 `.env` 没有被 Git 跟踪。

### 6.3 v1.3 目标合约

后续实现应新增：

- `FanoraMembershipIdentity`：ERC-721 SBT，唯一会员身份与等级更新。
- `FanoraCollectibles`：ERC-1155，演唱会纪念卡、自定义徽章和任务限定 Badge。

目标合约的函数、角色、事件、幂等和测试要求见 `PRODUCT_REQUIREMENTS.md` 第 7 节。实现完成前，不要把旧的 `BADGE_CONTRACT_ADDRESS` 解释为两个新合约地址。

## 7. Pinata 与 NFT metadata

### 7.1 当前状态

当前代码和 `.env.example` 尚未接入 Pinata。Pinata 是 v1.3 目标能力，不应在前端直接试接密钥。

### 7.2 目标服务端配置

具体变量名以实现时的 Settings 模型为准，至少需要表达：

```text
PINATA_JWT
PINATA_GATEWAY_BASE_URL
PINATA_GATEWAY_TOKEN            # 仅私有 Gateway 需要
NFT_MAX_UPLOAD_BYTES
NFT_ALLOWED_IMAGE_TYPES
NFT_STAGING_STORAGE_BUCKET
```

要求：

- Pinata JWT 只能存在后端密钥环境。
- 未审核图片先进入受控临时存储，不直接上传公开 IPFS。
- 后端先上传图片，再生成引用图片 CID 的 metadata JSON。
- 合约保存 `ipfs://metadataCid`，Gateway URL 只用于展示。
- Pinata 上传成功不等于链上铸造成功，两者分别记录状态。

## 8. 测试与检查

### 8.1 前端

```bash
cd frontend
npm run lint
npm run typecheck
npm run build
```

专项测试：

```bash
npm run test:api-timeout
npm run test:avatar
npm run test:header
npm run test:hero-animation
npm run test:fan-token
npm run test:membership
npm run test:official-membership
npm run test:video-sound
npm run test:key-export
```

### 8.2 后端

```bash
cd backend
make check
```

等价拆分命令：

```bash
make lint
make typecheck
make test
```

### 8.3 合约

```bash
cd contracts
npm run compile
npm test
```

新双合约实现后，至少补充 ERC-721 SBT、operationId、ERC-1155 供应量、钱包限额、时间窗、claimKey、metadata 冻结和恶意 receiver 测试。

## 9. 常见问题

### 数据库连接等待时间长

- 确认本地 PostgreSQL 已启动：`make db-status`。
- 检查 `.env.local` 是否仍指向不可达的远程数据库。
- 本项目数据库和前端 API 超时统一按 60 秒配置，不能用缩短客户端超时掩盖数据库问题。

### 前端显示后端不可用

- 检查 `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1`。
- 访问健康检查确认 FastAPI 已运行。
- 查看浏览器请求是否被 CORS 或认证状态拦截。

### 入会按钮无法发送交易

- 确认 `MEMBERSHIP_TREASURY_ADDRESS` 已配置。
- 确认钱包处于 Monad Testnet。
- 确认钱包具有测试 MON。

### 合约地址为空

当前目标双合约尚未部署是正常状态。不得使用虚构地址或前端 mock 冒充 Monad Testnet 部署证据。

## 10. 相关文档

- [文档中心](./README.md)
- [产品与开发需求](./PRODUCT_REQUIREMENTS.md)
- [技术架构](./ARCHITECTURE.md)
- [MVP 路线图](./MVP_ROADMAP.md)
