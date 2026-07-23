# Fanora Protocol 技术架构文档

> 文档版本：v1.6\
> 更新日期：2026-07-23\
> 需求基线：[PRODUCT_REQUIREMENTS.md](./PRODUCT_REQUIREMENTS.md)\
> MVP 网络：Monad Testnet

## 1. 架构结论

Fanora 采用“链下业务事实 + 链上公开凭证”的混合架构：

```text
登录与主钱包
  → 任务验证
  → PostgreSQL 积分与等级
  → LangGraph 粉丝画像
  → Pinata IPFS metadata
  → Monad ERC-721 会员身份 / ERC-1155 纪念资产
```

核心边界如下：

- PostgreSQL 是用户、任务、FAN 可用余额与终身累计、等级、NFT 市场和链上任务状态的业务事实源。
- ERC-721 保存唯一、不可转让的会员身份和当前公开等级，tokenId 在升级时保持不变。
- ERC-1155 保存演唱会纪念卡、粉丝限量 NFT、自定义纪念徽章和任务限定 Badge。
- Pinata 保存会员证、粉丝 NFT 图片与 metadata；合约保存 `ipfs://CID`。
- LangGraph 负责分析、解释、推荐和 metadata 草案，不修改积分、不决定发布资格或 ERC-721 等级。
- 当前用户触发的身份同步、会员证、发布和购买链路会在 HTTP 请求中等待链上确认；可靠后台重试、常驻事件监听和完整对账仍待实现。
- 早期 `ProofOfFandomBadge.sol` 原型已删除，正式架构使用付款 Gateway、ERC-721 身份与 ERC-1155 纪念资产合约。

## 2. 系统总体架构

```mermaid
flowchart TB
    USER["粉丝 / 创作者 / 管理员"]

    subgraph FRONTEND["Next.js Frontend"]
        WEB["页面与业务交互"]
        WALLET["RainbowKit / wagmi / viem"]
    end

    subgraph BACKEND["Fanora Backend"]
        API["FastAPI Routes"]
        AUTH["身份与会话"]
        TASK["任务与积分"]
        PROFILE["LangGraph 粉丝画像"]
        NFT["会员证与粉丝 NFT 市场"]
        CHAIN["Monad Adapter"]
        IPFS["Pinata Adapter"]
        WORKER["待完善：重试 / 事件对账"]
    end

    subgraph DATA["Data"]
        DB["PostgreSQL<br/>业务事实源"]
        MEDIA["校验后的上传内容"]
    end

    subgraph EXTERNAL["External Services"]
        WALLETS["MetaMask / WalletConnect / 外部钱包"]
        OPENAI["OpenAI Platform API"]
        PINATA["Pinata IPFS Platform"]
        RPC["Monad RPC"]
    end

    subgraph MONAD["Monad Testnet"]
        ERC721["FanoraMembershipIdentity<br/>ERC-721 SBT"]
        ERC1155["FanoraCollectibles<br/>ERC-1155"]
    end

    USER --> WEB
    WEB --> WALLET
    WALLET --> WALLETS
    WEB --> API
    API --> AUTH
    API --> TASK
    API --> PROFILE
    API --> NFT
    AUTH --> DB
    TASK --> DB
    PROFILE --> DB
    PROFILE --> OPENAI
    NFT --> DB
    NFT --> MEDIA
    NFT --> IPFS
    IPFS --> PINATA
    NFT --> CHAIN
    CHAIN --> RPC
    RPC --> ERC721
    RPC --> ERC1155
    ERC721 --> WORKER
    ERC1155 --> WORKER
    WORKER --> DB
```

## 3. 项目模块与职责

| 模块 | 当前技术 | 主要职责 |
| --- | --- | --- |
| `frontend` | Next.js 15、React 19、RainbowKit、wagmi、viem | 登录、资料、官方社区、任务、会员证、个人收藏和粉丝 NFT 市场 |
| `backend` | FastAPI、SQLModel、Alembic、LangGraph、web3.py | 认证、任务、FAN、终身等级、Agent、Pinata、会员证、NFT 发布/购买和链上编排 |
| `contracts` | Solidity、Hardhat、OpenZeppelin | ERC-721 会员身份与 ERC-1155 纪念资产 |
| `docs` | Markdown | 产品需求、架构、路线图、开发说明和历史证据 |

模块之间保持独立依赖和部署生命周期。前端不导入后端或 Hardhat 依赖，后端不直接依赖前端状态，合约不理解数据库或 Pinata API。

## 4. 领域边界

### 4.1 身份与钱包

- 用户通过 RainbowKit 连接已有外部钱包，并通过一次性 challenge 和钱包签名完成服务端认证。
- 业务模块只读取统一 `user_id` 与 `primary_wallet`，不判断具体登录提供商。
- Fanora 后端不生成、保存或记录用户钱包私钥。
- 主钱包切换属于高风险操作；不可转让身份 NFT 不自动迁移。

### 4.2 单一官方社区

- Fanora MVP 只启用一个固定的官方社区记录。
- 前端直接展示官方社区，不提供社区列表、搜索、分页、创建、删除或切换入口。
- `communities` 与 `community_members` 表继续使用，但只保存官方社区资料和用户加入关系。
- 任务、Fan Token、等级、会员身份和纪念资产使用平台全局配置，不按社区建立独立账户或命名空间。
- 创作者只维护官方社区资料和全局内容，不设计多社区所有权或多管理员权限系统。

### 4.3 正式会员、积分与等级

- 新用户默认为待入会。
- 后端验证 1 MON 交易的发送方、收款方、金额、chainId、交易状态和确认数后激活正式会员。
- Fan Token 是精度 0 的站内积分，不是 ERC-20。
- 积分通过追加式流水产生，等级由 PostgreSQL 中的版本化阈值规则计算。
- 积分变化可以异步触发 ERC-721 身份升级，但链上失败不回滚合法积分。

### 4.4 任务与奖励

- 任务领取、提交、验证、积分和 NFT 奖励分别记录状态。
- 服务端验证是奖励依据，前端提交结果不能直接视为完成。
- 同一用户、任务和奖励版本使用唯一业务幂等键。
- 任务可以同时奖励 Fan Token 和一个 ERC-1155 限定 Badge。

### 4.5 NFT 与 metadata

- ERC-721 会员身份：每个有效主钱包最多一个 token；升级更新同一 token 的 levelId 与 metadata。
- ERC-1155 纪念资产：类别为演唱会纪念卡、粉丝限量 NFT、自定义纪念徽章或任务限定 Badge。
- 粉丝限量 NFT 由正式会员直接发布；图片与 metadata 发布成功后固定到 Pinata。
- 图片 CID 先生成，metadata JSON 引用 `ipfs://imageCid` 后再上传得到 metadata CID。
- 合约只保存 URI、等级/类别和必要约束，不保存图片二进制、完整积分或私密数据。

### 4.6 AI Agent

LangGraph 的高层接口是“生成粉丝画像与推荐”，输入和输出必须结构化。

允许：

- 聚合任务、积分、活跃天数和公开链上摘要。
- 生成评分、粉丝类型、解释和推荐任务。
- 为已批准的 ERC-1155 纪念主题生成 metadata 草案。

禁止：

- 修改积分、等级、角色或任务状态。
- 决定粉丝 NFT 发布资格、价格、供应量或资金结算。
- 决定 ERC-721 会员等级。
- 持有 Pinata JWT、运营私钥或管理员私钥。
- 直接提交链上交易或处理交易重试。

## 5. 前端架构

### 5.1 当前职责

- 官网、登录、Profile、官方社区展示与加入、正式入会页面。
- 统一 Axios API 客户端与用户会话状态。
- RainbowKit 多钱包连接、签名和切链入口。
- 公开 Monad 读取、交易状态和区块浏览器链接。
- 钱包私钥、助记词和账户备份只由用户选择的钱包应用管理。

### 5.2 已落地页面

- `/profile`：资料、钱包、FAN、等级与社区身份。
- `/collection`：ERC-721 会员证、链上同步、会员证生成/刷新和 ERC-1155 个人收藏。
- `/collections`：粉丝 NFT 广场、主题筛选、点赞和收藏。
- `/collections/create`：正式会员发布限量 NFT。
- `/item/[id]`：NFT 详情、故事图片、铸造记录和 FAN 购买。
- `/collection/[id]`：创作者集合页。

### 5.3 前端不负责

- 不计算可信积分或等级。
- 不验证任务最终结果。
- 不保存 OpenAI Key、Pinata JWT、运营私钥或数据库凭证。
- 不允许用户指定可信 tokenId、levelId、合约地址、metadata URI 或任意铸造地址。
- 不直接调用带有合约运营角色的写方法。

## 6. 后端架构

后端继续采用模块化单体。HTTP、业务规则、数据库、Agent、IPFS 和链上适配器通过小接口连接，MVP 不拆分微服务。

```mermaid
flowchart LR
    ROUTES["Routes"] --> SERVICES["Domain Services"]
    SERVICES --> REPOS["Repository Interfaces"]
    SERVICES --> AGENT_IF["Fan Profile Interface"]
    SERVICES --> PINATA_IF["IPFS Interface"]
    SERVICES --> CHAIN_IF["Blockchain Interface"]
    SERVICES --> VERIFY_IF["Task Verifier Interface"]

    REPOS --> POSTGRES["PostgreSQL Adapter"]
    AGENT_IF --> GRAPH["LangGraph"]
    PINATA_IF --> PINATA["Pinata Adapter"]
    CHAIN_IF --> MONAD["web3.py Monad Adapter"]
    VERIFY_IF --> INTERNAL["内部行为验证器"]
    VERIFY_IF --> ONCHAIN["链上验证器"]
```

建议领域服务：

- `IdentityService`：统一用户、登录身份、钱包和会话。
- `MembershipService`：1 MON 正式入会与会员状态。
- `TaskService`：任务状态、领取、提交和验证。
- `PointService`：积分流水、余额和等级计算。
- `FanProfileService`：LangGraph 高层接口与运行记录。
- `NftService`：会员身份、会员证、粉丝限量 NFT 发布、购买、收藏和头像设置。
- `MetadataService`：图片、JSON、CID 和版本。
- `NftOrchestrator`：资格判断后创建链上 operationId/claimKey。
- `BlockchainAdapter`：交易构建、提交、回执和事件解析。
- `ReconciliationWorker`：确认数、链重组和数据库/链上对账。

## 7. 数据架构

### 7.1 数据归属

| 数据 | 事实源 | 说明 |
| --- | --- | --- |
| 用户、钱包、会话、官方社区 | PostgreSQL | 强一致业务关系和权限；社区固定为单一记录 |
| 任务、领取、验证、积分流水 | PostgreSQL | 高频写入、幂等和审计 |
| 当前积分与等级 | PostgreSQL | 不写入链上完整流水 |
| Agent 输入摘要、输出、版本 | PostgreSQL | 可追踪与重新计算 |
| 粉丝 NFT 原始图片 Data URL | PostgreSQL `nft_applications.image_data` | 当前原型保留发布记录；生产环境应迁移对象存储并缩减数据库负载 |
| 发布后的图片与 metadata | Pinata IPFS | 校验通过后固定，使用 CID 内容寻址和公开读取 |
| ERC-721 身份状态 | Monad | 公开验证唯一身份与当前等级 |
| ERC-1155 类型、余额与事件 | Monad | 公开验证纪念资产和发行约束 |
| 交易提交、确认和对账状态 | PostgreSQL | 支持失败重试与恢复 |

### 7.2 当前已存在的核心表

- `users`、`user_profiles`
- `auth_identities`、`wallets`
- `login_challenges`、`user_sessions`
- `communities`、`community_members`（MVP 仅一条官方社区及其成员关系）
- `membership_levels`、`fan_token_rules`、`fan_token_config`
- `official_membership_payments`
- `fan_profile_runs`

### 7.3 目标新增表

- `tasks`、`task_claims`、`point_ledger`（全局数据，不增加社区分区）
- `fan_profiles`
- `membership_identity_nfts`
- `nft_token_types`、`nft_claims`
- `nft_applications`、`nft_metadata_versions`
- `ipfs_pins`、受控申请文件记录
- `nft_transactions`、状态历史与 `audit_logs`

### 7.4 一致性原则

- 数据库事务先记录合法业务结果，再异步创建链上操作。
- 每个身份铸造/升级使用唯一 operationId，每次 ERC-1155 领取使用唯一 claimKey。
- 数据库唯一约束与合约防重同时存在，不能只依赖其中一侧。
- 链上确认失败不删除任务完成或积分流水，只更新 NFT 同步状态。
- Worker 通过合约事件和交易回执修复漏记或状态不一致。

## 8. 智能合约架构

### 8.1 FanoraMembershipIdentity

目标标准：ERC-721 + metadata + AccessControl + Pausable，会员身份为 SBT。

职责：

- 每个主钱包最多一个有效身份 token。
- 记录 tokenId、当前 levelId、metadata URI 和必要版本。
- 通过 `mintIdentity` 创建身份，通过 `updateMembershipLevel` 更新同一 token。
- 阻止普通转让和授权绕过。
- 使用 operationId 防止重复铸造或升级。
- 发出身份铸造、等级变化、metadata 更新和撤销事件。

不保存：

- 实时 Fan Token 余额和完整积分流水。
- 任务明细、邮箱、社交原始数据或 Agent 原始输出。

### 8.2 FanoraCollectibles

目标标准：ERC-1155 + AccessControl + Pausable。

每个 tokenId 配置：

- `category`
- `metadataUri`
- `maxSupply` 与累计 `mintedSupply`
- `perWalletLimit`
- `mintStart`、`mintEnd`
- `transferable`
- `metadataFrozen`、`active`

合约必须在链上校验供应量、累计钱包领取量、时间窗和 claimKey。自定义徽章默认供应量 1 且不可转让；任务限定 Badge 单钱包最多 1；演唱会纪念卡的转让策略在创建时确定。

### 8.3 原型迁移

`ProofOfFandomBadge` 已删除。正式合约拆分资金、会员身份和纪念资产职责，旧的 Badge 地址、ABI 与读取 Hook 不再使用。

## 9. 核心业务流

### 9.1 正式入会与 ERC-721 身份

```mermaid
sequenceDiagram
    participant U as 用户
    participant F as Next.js
    participant B as FastAPI
    participant D as PostgreSQL
    participant P as Pinata
    participant C as ERC-721

    U->>F: 提交 1 MON 交易哈希
    F->>B: 请求验证正式入会
    B->>B: 验证发送方、收款方、金额、chainId 与确认数
    B->>D: 激活正式会员并创建身份 operationId
    B->>P: 固定会员证图片与 metadata
    P-->>B: 返回 image CID 与 metadata CID
    B->>C: mintIdentity(primaryWallet, levelId, uri, operationId)
    C-->>B: IdentityMinted
    B->>D: 保存 tokenId、交易与确认状态
```

### 9.2 任务、积分与身份升级

```mermaid
sequenceDiagram
    participant U as 粉丝
    participant B as FastAPI
    participant V as 验证器
    participant D as PostgreSQL
    participant A as LangGraph
    participant P as Pinata
    participant C as ERC-721

    U->>B: 提交任务结果
    B->>V: 服务端验证
    V-->>B: 验证证据与结果
    B->>D: 幂等写入任务完成与积分流水
    D-->>B: 返回新余额与等级
    B->>A: 更新粉丝画像
    A-->>B: 评分、标签、解释与推荐
    alt 等级发生变化
        B->>P: 固定新等级 metadata
        B->>C: updateMembershipLevel(tokenId, levelId, uri, operationId)
        B->>D: 更新链上同步状态
    end
```

### 9.3 粉丝限量 NFT 发布与购买

```mermaid
sequenceDiagram
    participant U as 用户
    participant B as FastAPI
    participant P as Pinata
    participant D as PostgreSQL
    participant C as ERC-1155

    U->>B: 发布 NFT 图片、定价和限量
    B->>D: 校验正式会员与 100 FAN 发布费
    B->>P: 上传图片与 metadata
    P-->>B: 返回 CID
    B->>C: createTokenType(FAN_LIMITED_NFT, maxSupply)
    B->>D: 扣除 100 FAN 并发布上架
    U->>B: 购买 NFT
    B->>D: 扣买家 FAN
    B->>C: mintCollectible(buyer, tokenId, 1, claimKey)
    C-->>B: CollectibleMinted
    B->>D: 给创作者记入 FAN，更新库存
```

### 9.4 演唱会纪念卡与任务限定 Badge

- 创作者先创建资产草稿、发行约束和领取依据。
- 后端审核 metadata 并固定到 Pinata，再创建 ERC-1155 token 类型。
- 演唱会纪念卡通过已验证打卡任务或经审计领取名单发放。
- 任务限定 Badge 只在任务完成且领取时间窗有效时创建 claimKey。
- 前端不能提交任意铸造地址；后端始终使用当前用户经过验证的主钱包。

## 10. 部署架构

推荐 MVP 组合：

```text
Vercel
  └─ Next.js Frontend

Railway / Render / Fly.io / Cloud Run
  ├─ FastAPI
  ├─ LangGraph
  └─ Worker / Reconciliation

PostgreSQL / Supabase
  └─ 业务数据库与当前原型图片记录

Object Storage（生产目标）
  └─ 上传原图、配额与清理

Pinata
  └─ 校验通过的会员证、NFT 图片与 metadata

Monad Testnet
  ├─ FanoraMembershipGateway
  ├─ FanoraMembershipIdentity
  └─ FanoraCollectibles
```

Vercel Functions 可以用于短请求，但不适合依赖 HTTP 返回后继续执行的链上写入或常驻事件监听。链上交易、Pinata 重试和事件对账应在支持常驻进程或可靠任务队列的 Python 环境运行。

## 11. 配置边界

### 11.1 当前已有公开前端配置

- `NEXT_PUBLIC_API_URL`
- `NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID`
- `NEXT_PUBLIC_MONAD_TESTNET_RPC_URL`

当前以前端公开变量提供 Gateway、ERC-721 和 ERC-1155 地址。公开变量只能包含可公开链上配置，不能包含任何密钥。

### 11.2 当前已有服务端配置

- `DATABASE_URL`
- `MONAD_RPC_URL`、`MONAD_CHAIN_ID`
- 正式入会 Gateway、动态会费备用值、资金地址和确认数
- ERC-721、ERC-1155 地址、事件起始区块和最小权限运营签名配置
- Pinata JWT、上传地址、Gateway 地址、超时和重试配置
- `OPENAI_API_KEY`、模型与超时配置
- 历史原型变量 `BADGE_CONTRACT_ADDRESS`、`OPERATOR_PRIVATE_KEY` 已停用。

### 11.3 尚待生产化的配置

- 将测试网共用部署钱包拆分为独立运营账户或安全签名服务。
- 配置生产 Pinata JWT、对象存储、上传配额和文件清理策略。
- 配置后台任务队列、事件轮询间隔、链重组确认和告警渠道。

Pinata JWT、运营私钥、管理员私钥、数据库凭证和 OpenAI Key 只能存在服务端密钥环境。

## 12. 安全与可靠性

- 登录 challenge 一次性、限时并绑定域名、钱包地址和 chainId。
- 钱包登录签名由后端恢复签名地址，并校验 challenge 内容、有效期和一次性使用状态。
- FAN、任务、会员等级、NFT 发布约束和链上参数全部由服务端确定。
- 用户上传图片验证 MIME、文件签名、大小、尺寸和内容；MVP 不接受未经清洗的 SVG。
- 文件必须通过 MIME、签名、大小和尺寸校验后才能进入公开 IPFS。
- Pinata JWT 与链上运营签名权限分离。
- 合约按角色拆分管理员、铸造者、等级管理、类型管理、URI 管理和暂停权限。
- operationId/claimKey 在数据库与合约两侧防重。
- 链上任务保存提交、确认、失败、可重试和需要对账状态。
- metadata 更新产生新 CID；旧 CID 和版本保留。
- 已冻结 ERC-1155 metadata 不可再次更新，已铸造内容默认不自动 unpin。

## 13. 当前实现状态

### 13.1 已具备

- RainbowKit 多钱包连接、钱包签名挑战、统一会话和入会付款确认。
- 官方社区创作、Markdown、多图、评论回复、任务、签到日历和 Fan Token 幂等奖励闭环。
- 动态会费 Gateway、管理员提现与改价、付款事件验证和正式会员激活。
- ERC-721 SBT 会员身份、等级 metadata 版本、Pinata 固定和用户主动等级同步。
- ERC-1155 纪念资产合约、粉丝限量 NFT 发布/购买、点赞/收藏、创作者集合和统一收藏页。
- Monad/Pinata 适配器、链上操作和 NFT 数据模型，以及对应 FastAPI 接口。
- LangGraph 确定性评分、结构化画像、LLM 降级和分析记录持久化。
- 三个合约 Monad Testnet 部署、19 项合约测试、ABI 导出和前后端配置自动同步。

### 13.2 仍需完成

- 外部钱包关联、主钱包切换和 SBT 身份恢复/迁移管理。
- 可靠后台任务执行器、失败自动重试、链重组处理、常驻事件监听和完整对账。
- 任务限定 Badge 与演唱会纪念卡的资格领取、类型管理和前端闭环。
- Pinata pin 状态查询、独立对象存储、恶意内容检测、配额和清理策略。
- 粉丝 NFT 编辑/下架、退款或失败补偿、完整交易审计和管理员操作页面。
- 将 Testnet 共用运营钱包拆分为最小权限账户，并迁移 `DEFAULT_ADMIN_ROLE` 至多签。

## 14. 非目标

MVP 暂不实现：

- 多社区创建、搜索、切换和独立配置。
- 按社区拆分积分、任务、等级、Badge 或管理员权限。
- 多链和跨链身份聚合。
- 将完整积分、任务或粉丝画像写入链上。
- NFT 二级市场、拍卖、版税和跨平台交易聚合。
- DAO、协议代币或真实空投。
- 多 Agent 管理平台和 AI 自动审批。
- 未经安全评估的 Monad 主网部署。
