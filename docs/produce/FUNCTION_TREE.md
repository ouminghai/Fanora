# Fanora 功能树

本文从用户可见功能向下映射页面、后端能力与外部系统，用于演示导航、测试覆盖和开发定位。

## 1. 总体功能树

```text
Fanora
├── 1. 身份与会员
│   ├── 钱包连接与网络切换
│   ├── Challenge / Signature 登录
│   ├── 正式会员激活与支付验证
│   ├── ERC-721 SBT 会员身份
│   └── 动态会员卡与等级同步
├── 2. 社区与内容
│   ├── 官方社区加入
│   ├── Post 发布、详情与图片
│   ├── 回复、二级回复与图片
│   ├── 点赞、收藏与回复点赞
│   └── 公开粉丝主页
├── 3. 任务、签到与 FAN
│   ├── 每日签到与连续天数
│   ├── 任务列表、领取、提交和完成
│   ├── 内容审核与任务审计
│   ├── FAN 余额、终身累计与流水
│   ├── 会员等级同步
│   └── FAN 排行榜
├── 4. AI NFT Studio
│   ├── 多轮故事访谈
│   ├── NFT 名称、描述、Prompt 与属性优化
│   ├── 数据库视觉模板库
│   ├── 从 Post、NFT 或上传图片建立模板
│   ├── 视觉风格与多模态参考图
│   ├── 模板推荐与另存 Tool
│   └── 条件式图片生成与 COS 预览
├── 5. Memory Forge
│   ├── AI 五维分析与 RareScore
│   ├── 数量、价格和模式建议
│   ├── 成功率计算
│   ├── FAN / Credit 结算
│   ├── 可审计成功或失败判定
│   └── Memory Fragment 与兑换
├── 6. NFT 发行与市场
│   ├── COS URL 规范化
│   ├── Pinata 图片与 Metadata 固定
│   ├── ERC-1155 Token Type 创建
│   ├── 创作者首枚 Mint
│   ├── Gallery 展示、点赞与收藏
│   ├── FAN 购买与买家 Mint
│   └── Collection 与头像设置
└── 7. 平台基础设施
    ├── PostgreSQL 与 Alembic
    ├── LangGraph Checkpoint
    ├── COS / Pinata / Monad Adapter
    ├── 结构化日志与 Request ID
    ├── Prometheus 与可选 Langfuse
    └── 限流、幂等、降级与退款
```

## 2. 页面导航

| 页面 | 主要用户 | 核心功能 |
| --- | --- | --- |
| `/` | 访客、粉丝 | 产品入口、Web3 身份路径、Agent 创作介绍、热门任务 |
| `/login` | 访客 | 钱包连接、签名登录、Monad 网络引导 |
| `/membership/join` | 登录用户 | 正式会员激活、激活状态与链上结果 |
| `/community` | 粉丝 | 社区 Feed、发帖、图片、互动与收藏 |
| `/community/posts/[postId]` | 粉丝 | 帖子详情、回复、二级回复与点赞 |
| `/community/tasks` | 正式会员 | 任务浏览、领取、提交、完成与奖励 |
| `/community/leaderboard` | 所有用户 | FAN 终身累计排行榜 |
| `/community/creations` | 粉丝 | 社区创作内容聚合 |
| `/collections` | 所有用户 | NFT Gallery、筛选、点赞、收藏与购买 |
| `/collections/create` | 正式会员 | Agent 共创、模板、参考图、Forge 与发布 |
| `/collection` | 登录用户 | 我的会员身份、NFT、Badge 与创作 |
| `/collection/[id]` | 所有用户 | 指定 Collection 详情 |
| `/item/[id]` | 所有用户 | NFT 详情与购买 |
| `/profile` | 登录用户 | 个人资料、会员与成长数据 |
| `/users/[userId]` | 所有用户 | 公开粉丝画像和收藏 |

## 3. 功能与 API 映射

所有路径默认带 `/api/v1` 前缀。

### 3.1 身份与会员

| 功能 | API | 权限 / 结果 |
| --- | --- | --- |
| 创建登录挑战 | `POST /auth/challenge` | 公开；返回待签名消息 |
| 钱包签名登录 | `POST /auth/wallet` | 校验签名并创建会话 |
| 退出登录 | `POST /auth/logout` | 登录用户；失效当前会话 |
| 查询会员状态 | `GET /membership/me` | 登录用户 |
| 免费激活 | `POST /membership/activate-free` | 仅 `MEMBERSHIP_FEE_WEI=0`；执行链上激活 |
| 验证付费激活 | `POST /membership/verify` | 验证交易与支付事实 |
| 查询等级规则 | `GET /membership-levels` | 公开 |
| 同步链上身份 | `POST /nft/identity/sync` | 登录用户 |
| 生成 / 刷新会员卡 | `POST /nft/identity/card`、`/refresh` | 正式会员 |

### 3.2 社区、任务与 FAN

| 功能 | API |
| --- | --- |
| 官方社区 | `GET/PATCH /community`、`POST /community/join` |
| Post | `GET/POST /community/posts`、`GET /community/posts/{id}` |
| 回复 | `POST /community/posts/{id}/replies` |
| 内容互动 | `POST /community/posts/{id}/like`、`bookmark`、`POST /community/replies/{id}/like` |
| 任务 | `GET/POST /tasks`、`POST /tasks/{id}/claim`、`complete`、`status` |
| 签到 | `GET /check-ins/me`、`POST /check-ins` |
| FAN 流水 | `GET /fan-tokens/me/ledger` |
| 排行榜 | `GET /fan-tokens/leaderboard` |
| 图片上传 | `POST /media/images`；上传 COS，返回 URL |

### 3.3 AI Studio、Forge 与 NFT

| 功能 | API |
| --- | --- |
| Agent 对话 | `POST /nft/creations/agent/chat` |
| 模板列表 / 新建 | `GET/POST /nft/creations/agent/templates` |
| 风格列表 | `GET /nft/creations/agent/styles` |
| 上传图分析 | `POST /nft/creations/agent/analyze-upload` |
| Forge 分析 | `POST /nft/forge/analyze` |
| 修改发行策略 | `PATCH /nft/forge/{sessionId}/strategy` |
| 开始 / 重试 Forge | `POST /nft/forge/{sessionId}/start`、`retry` |
| 选择图片版本 | `POST /nft/forge/{sessionId}/select-version` |
| Fragment | `GET /nft/fragments/me`、`POST /nft/fragments/redeem` |
| 发布 NFT | `POST /nft/creations` |
| Gallery / 详情 | `GET /nft/creations`、`GET /nft/creations/{id}` |
| 点赞 / 收藏 | `POST /nft/creations/{id}/like`、`favorite` |
| FAN 购买 | `POST /nft/creations/{id}/buy` |
| 我的收藏 / 创作 | `GET /nft/me`、`GET /nft/me/creations` |

## 4. 角色与权限

| 角色 | 能力边界 |
| --- | --- |
| 访客 | 浏览首页、Gallery、公开社区内容、用户主页和等级规则 |
| 登录用户 | 管理会话、查看个人资料、加入社区、查看会员状态 |
| 正式会员 | 发帖回复、领取任务、签到、Agent 创作、Forge、发布与购买 |
| 社区运营者 / 管理员 | 创建和管理任务、社区配置、FAN 人工调整等受保护操作 |
| 后端 Operator | 使用服务端私钥执行会员、ERC-1155 创建和 Mint；私钥不进入浏览器 |

## 5. 关键业务约束

- 业务图片持久化到 COS，数据库保存 URL，不保存 Base64 正文。
- 最终链上 NFT 图片与 metadata 使用 Pinata IPFS；AI 临时预览不等于链上资产。
- LLM 不直接扣 FAN、不修改权限、不决定随机结果，也不直接持有合约私钥。
- NFT 发布必须关联当前用户的 `SUCCESS` Forge Session，且选中图片版本一致。
- FAN 支出只影响可用余额，不回退终身会员等级。
- 幂等键用于阻止重复奖励、重复扣款、重复 Fragment 和重复 Mint 编排。
