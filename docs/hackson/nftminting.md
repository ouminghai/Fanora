# Fanora AI 共创 NFT 游戏策划方案

> 文档版本：v2.1
>
> 更新日期：2026-08-01
>
> 适用范围：Fanora Hackathon Demo 与后续游戏化迭代
>
> 当前网络：Monad Testnet
>
> 核心原则：游戏博弈发生在“生成可发布 NFT 草稿”阶段；IPFS 上传、链上发布和真实 NFT Mint 均为确定性操作，不参与随机判定。

## 1. 项目概述

### 1.1 产品名称

**Fanora Memory Forge：AI 粉丝记忆铸造工坊**

### 1.2 一句话玩法

粉丝通过社区任务积累 FAN，在 AI Agent 引导下完善故事并获得 AI 稀有度评分，再选择 FAN 投入与锻造策略进行一次站内生成博弈；成功后获得可编辑、可发布的 NFT 草稿，失败则获得 Fragment 并继续积累，最终由用户确认后确定性发布到 Monad。

### 1.3 核心体验

Fanora 不是一个单独的 NFT 抽奖工具，而是一套连接粉丝成长与创作的游戏化循环：

```text
参与社区与任务
    ↓
获得 FAN、等级与身份
    ↓
AI 分析故事与素材
    ↓
选择投入并进行站内 Forge
    ↓
成功获得 NFT 草稿 / 失败获得 Fragment
    ↓
确认后发布为 Monad 限量 NFT
    ↓
被点赞、收藏和购买，继续成长
```

### 1.4 玩家获得的价值

- 普通粉丝：参与任务、收藏作品、证明自己支持过什么。
- 活跃粉丝：积累 FAN、提升等级、进入排行榜、获得限定 Badge。
- 深度粉丝：将真实记忆变成可展示、可验证的链上收藏品。
- 同人创作者与应援站：降低创作门槛，发布限量作品，并从收藏行为中获得 FAN。
- 创作者或艺人运营方：识别核心粉丝，以等级、Badge 和作品设计后续权益。

## 2. 策划目标与边界

### 2.1 Hackathon 目标

在 3 分钟内让评委看懂并看到一条完整链路：

1. 粉丝连接钱包并成为正式会员。
2. 粉丝通过任务和互动获得 FAN。
3. 粉丝进入 AI 共创工作台，选择模板与风格并讲述故事。
4. AI Vision 与 LLM 输出五维评分、RareScore、等级和推荐发行参数。
5. 玩家设置供应量、价格和 Forge 投入，查看成功率并选择锻造策略。
6. 点击“开始生成”，后端进行站内随机判定。
7. 成功或超级成功后调用 AI 生图并生成可编辑 NFT 草稿；失败获得 Fragment，不发生任何链上操作。
8. 用户确认草稿、发行参数与版权声明后，系统确定性上传 IPFS 并发布 Monad ERC-1155。
9. 作品进入 Gallery，其他粉丝用 FAN 收藏，NFT 发放到钱包。

### 2.2 设计原则

- **故事优先**：AI 评分和属性应解释作品的故事与贡献，不判断未来价格。
- **有风险但不伤链上资产**：随机结果只决定本次能否获得可发布草稿及其附加稀有属性。
- **结果可控**：即使 Forge 成功，名称、描述、图片、价格和供应量仍必须由用户确认。
- **边界清楚**：站内 Forge Game 负责概率和 Fragment；发布服务负责 FAN 账本、IPFS 与链上交易。
- **收藏友好**：正式购买采用保证铸造；失败时退款，不让粉丝无回报地损失 FAN。
- **贡献驱动**：FAN 来源于签到、任务、发布、回复等真实参与，不强调 Token 投机。
- **链上有边界**：重要身份和收藏品上链；高频积分、任务状态和审核记录保留在 PostgreSQL。
- **移动优先**：桌面端使用三栏工作台，移动端使用“选择 → 对话 → 预览 → 发布”分步流程。

### 2.3 本阶段不做

- 不发行可自由交易的 ERC-20 FAN Token。
- 不做 NFT 地板价、投资回报率和价格预测。
- 不做二级市场撮合、质押、借贷或收益承诺。
- 不做多社区、多艺人和复杂创作者后台。
- 不让 AI 模型直接执行扣费、随机判定或上链操作。
- 不让真实链上 Mint 随机失败，不在智能合约中实现概率游戏。
- 不把 Fragment、RareScore 或站内 Forge 结果包装为有现金价值的金融资产。

## 3. 系统现状与策划依据

以下内容以当前代码和项目文档为准。

| 能力 | 当前状态 | 游戏中的作用 |
| --- | --- | --- |
| RainbowKit 钱包连接与签名登录 | 已实现 | 玩家账号与链上身份入口 |
| Gateway 会费与正式会员 | 已实现 | 进入任务和创作体系的会员门槛 |
| FAN 可用余额与终身累计 | 已实现 | 消费货币与成长经验分离 |
| 签到、任务、发帖、回复、点赞、收藏 | 已实现 | FAN 的主要产出与社区循环 |
| 排行榜与会员等级 | 已实现 | 即时反馈、长期成长与核心粉识别 |
| ERC-721 会员身份 | 已实现 | 稳定 tokenId 的链上会员凭证 |
| ERC-1155 收藏品 | 已实现并部署 | 限量 NFT、任务 Badge、纪念卡 |
| AI NFT 对话工作台 | 已实现 | 收集故事、整理 Brief、生成与迭代作品 |
| 视觉模板、风格和参考图 | 已实现 | 控制作品风格、素材来源与版权边界 |
| AI 图片、名称、描述和属性草稿 | 已实现 | 降低深度粉丝的创作门槛 |
| IPFS metadata 与 Monad 发布 | 已实现 | 确认后创建真实链上资产 |
| Gallery 点赞、收藏、购买 | 已实现 | 内容传播和 FAN 流转 |
| 购买失败退款 | 已实现 | 保护玩家资产与购买体验 |
| AI 稀有度评分 | 未实现，MVP 待开发 | 为 Forge 成功率与推荐参数提供输入 |
| 站内 Forge 随机判定 | 未实现，MVP 待开发 | 玩家点击生成时的核心博弈 |
| Perfect Forge 与 Fragment | 未实现，MVP 待开发 | 成功惊喜、失败积累和再次尝试 |
| 链上随机 Mint | 不开发 | 链上发布保持确定性 |

## 4. 玩家角色

### 4.1 收藏型粉丝

主要行为：签到、完成任务、浏览 Gallery、点赞、收藏和购买 NFT。

核心动机：获得纪念品、支持喜欢的创作者、展示自己的粉丝身份。

### 4.2 成长型粉丝

主要行为：连续参与社区、积累终身 FAN、提升会员等级、冲击排行榜。

核心动机：获得身份认可、限定 Badge 和未来粉丝权益。

### 4.3 创作型粉丝

主要行为：用 Agent 整理故事、生成作品、发布限量 NFT、维护个人作品集。

核心动机：表达情感、降低创作成本、获得社区认可和 FAN 回报。

### 4.4 官方运营方

主要行为：配置任务与奖励、提供授权素材模板、观察高价值粉丝、设计等级权益。

核心动机：降低运营和审核成本，形成可持续的粉丝关系。

## 5. 核心游戏循环

### 5.1 日常循环

```text
签到/任务/互动 → 获得 FAN → 查看等级和排行榜 → 解锁创作或收藏机会
```

日常循环负责让普通粉丝持续回来，并为创作和收藏准备 FAN。

### 5.2 创作者循环

```text
选择模板 → 与 Agent 对话 → AI 评分 → 设置发行参数与 Forge 投入
→ 站内概率生成 → 成功获得草稿 / 失败获得 Fragment
→ 确认并支付发布费 → 获得创作者首枚 NFT → 作品进入 Gallery
→ 获得点赞、收藏、购买与 FAN 收入
```

### 5.3 收藏者循环

```text
发现作品 → 阅读粉丝故事 → 查看属性与剩余供应
→ 使用 FAN 购买 → 后端铸造 ERC-1155 → Collection 展示
→ 设置收藏品头像/分享链上记录
```

### 5.4 长期循环

```text
终身 FAN 累计 → 会员等级提升 → ERC-721 身份更新
→ 解锁限定任务、素材包、Badge、创作权限或线下权益
```

长期循环不能只提供数值增长，应逐步绑定真实粉丝权益，例如优先购票、限定内容、限定周边和活动资格。

## 6. AI 共创玩法

### 6.1 创作工作台结构

桌面端延续当前三栏工作台：

| 区域 | 内容 | 玩家感受 |
| --- | --- | --- |
| 左侧：灵感配置 | 视觉模板、视觉风格、参考图、自定义模板 | 先确定创作边界 |
| 中间：Story & Art Agent | 每轮询问一个问题，整理故事状态并建议下一步 | 像与创作伙伴共同打磨记忆 |
| 右侧：NFT 展厅 | 图片版本、名称、描述、属性、发行量、价格 | 随时看到最终作品会是什么 |

### 6.2 Agent 职责

Agent 可以：

- 从对话中提取主题、人物、事件、情绪和视觉元素。
- 判断信息是否足够生成，并提示缺失字段。
- 检索并应用当前用户可用的视觉模板。
- 生成或修改名称、描述、图片提示词和公开属性。
- 在用户明确确认后调用图片生成工具。
- 保留每轮图片版本，支持继续迭代。
- 在模型不可用时返回规则生成的可编辑草稿。

Agent 不可以：

- 自动决定发行量和价格。
- 自动扣除 FAN、发布或铸造 NFT。
- 编造故事中没有出现的演唱会、人物经历或授权关系。
- 绕过版权声明、会员资格或供应量校验。
- 将市场潜力或未来收益包装成确定结论。

### 6.3 推荐对话步骤

1. “你想记录哪一段粉丝记忆？”
2. “这段记忆里最重要的情绪是什么？”
3. “有哪些必须保留的颜色、物件或画面？”
4. “是否使用官方素材模板或自己的参考图？”
5. Agent 汇总故事状态，展示仍缺少的信息。
6. Agent 完成分析，展示 RareScore、推荐供应量、推荐价格和基础成功率。
7. 玩家调整发行参数并选择 Forge 模式。
8. 玩家确认 FAN 消耗后点击“开始生成 NFT”。
9. 后端先完成站内概率判定；成功后才调用图片生成工具。
10. 玩家可以继续修改文字或再次进行 Forge，最后选择满意版本进入发布确认。

### 6.4 两阶段生成

为了控制模型成本并让游戏结果可信，生成拆为两个阶段：

1. **Analyze**：分析故事、参考图和发行策略，只生成评分、推荐参数和结构化 Prompt，不生成最终图片。
2. **Forge**：玩家确认投入后，服务端扣除 FAN 并完成随机判定。成功才调用生图模型；失败不调用生图，返回 Fragment。

这样“失败”表示本次创作锻造未完成，不是区块链交易失败，也不是已经生成的 NFT 被销毁。

## 7. 站内 NFT Forge Game（MVP 核心）

### 7.1 游戏对象

Forge Game 的结果是一个**可发布 NFT 草稿**，不是链上 NFT。

草稿包含：

- 最终图片或图片版本。
- NFT 名称与故事描述。
- RareScore 和稀有等级。
- 五维 AI 分析。
- 公开属性标签。
- 推荐供应量和推荐 FAN 价格。
- Forge 结果和本次随机记录。

只有用户在成功后点击“确认发布”，系统才进入 IPFS 和 Monad 流程。

### 7.2 玩家输入

```json
{
  "title": "FEAR AND DREAMS",
  "story": "Concert Memory",
  "referenceImages": ["https://..."],
  "supply": 100,
  "priceFanTokens": 20,
  "forgeMode": "FOCUSED"
}
```

玩家可以调整：

- `supply`：计划发行数量。
- `priceFanTokens`：计划单枚售价。
- `forgeMode`：本次 FAN 投入、成功率和可获得稀有结果的上限。

### 7.3 Forge 模式

MVP 建议使用三个清晰选项，避免玩家自己填写任意“铸造成本”导致规则难以理解。

| 模式 | 消耗 | 基础修正 | 可获得结果 | 适合玩家 |
| --- | ---: | ---: | --- | --- |
| Stable Forge | 10 FAN | +15% 成功率 | Normal / Special | 希望稳定生成 |
| Focused Forge | 20 FAN | 不修正 | Special / Rare | 平衡风险与稀有度 |
| Legendary Forge | 40 FAN | -15% 成功率 | Rare / Legendary | 愿意挑战高稀有结果 |

首次体验可以赠送一次免费的 `Stable Forge`，但仍需完整展示概率和结果动画。

### 7.4 成功率模型

先由 AI 与确定性规则计算基础参数：

```text
QualityFactor = 35 + RareScore × 0.45
StrategyFit = 发行量与建议区间的匹配修正，范围 -10 到 +10
PriceFit = 价格与建议区间的匹配修正，范围 -5 到 +5
LevelBonus = 玩家等级修正，范围 0 到 +8
ModeModifier = Stable +15 / Focused 0 / Legendary -15

SuccessRate = clamp(
  QualityFactor + StrategyFit + PriceFit + LevelBonus + ModeModifier,
  20,
  95
)
```

说明：

- `RareScore` 越高，作品基础完成度越高，生成成功率越高。
- 供应量和价格越接近 AI 推荐区间，策略修正越高。
- 盲目设置高价格或极大发行量不会提高成功率，反而降低匹配度。
- 等级只提供小幅加成，不能让高等级玩家达到 100%。
- 最终成功率必须在服务端计算，前端只负责展示。

示例：

```text
RareScore = 82
QualityFactor = 71.9
StrategyFit = +6
PriceFit = +3
LevelBonus = +4
ForgeMode = Legendary (-15)

SuccessRate = 69.9%，展示为 70%
```

### 7.5 Perfect Forge 概率

先判断是否成功，再在成功结果中判断是否触发 Perfect Forge：

```text
PerfectRate = clamp(
  5 + (RareScore - 60) × 0.25 + ModePerfectBonus,
  5,
  20
)
```

| 模式 | ModePerfectBonus |
| --- | ---: |
| Stable Forge | 0 |
| Focused Forge | +3 |
| Legendary Forge | +8 |

Perfect Forge 最高不超过 20%，并且是“成功结果中的条件概率”，页面必须分别展示成功率与 Perfect 概率，不能混为一个百分比。

### 7.6 Forge 结果

#### Perfect Forge

- 调用图片模型生成两个候选版本，玩家选择其一。
- 最终 RareScore 获得 `+5` 的 Forge Bonus，但总分不超过 100。
- 获得 `Perfect Forge` 站内属性。
- Legendary Forge 且最终分数达到 90 时，可获得 `Legendary` 等级。
- 获得 1 个站内 Perfect Forge 成就记录。

#### Normal Success

- 调用图片模型生成一个候选版本。
- 获得与最终分数和模式上限相符的稀有等级。
- 解锁编辑、再次生成和确认发布操作。

#### Failed Forge

- 不调用图片生成模型，不创建 IPFS 文件，不调用合约。
- 保留对话、故事摘要、AI 评分、Prompt 和发行参数。
- 消耗本次 Forge 对应 FAN。
- 获得 1 个 `Memory Fragment`。
- 玩家可以修改故事或策略后再次尝试。

### 7.7 Fragment 规则

Fragment 是 PostgreSQL 中的站内、不可交易道具，不是 ERC-1155，也不进入用户钱包。

| 行为 | 结果 |
| --- | --- |
| Forge 失败 | 获得 1 Fragment |
| 集齐 5 个 | 兑换一次免费 Stable Forge |
| 集齐 10 个 | 兑换一次免费 Focused Forge |
| 使用 Fragment 重试失败 | 仍获得 1 Fragment，避免完全清零 |

MVP 不开放 Fragment 转账、购买或出售。Fragment 只服务于失败积累和再次尝试。

### 7.8 FAN 扣费与异常处理

- Forge 开始前使用数据库事务预扣 FAN。
- 每个请求必须携带唯一 `idempotency_key`，重复点击只结算一次。
- 随机判定为正常失败时不退款，并发放 Fragment。
- AI、网络、超时或服务端异常不属于游戏失败，必须全额退款且不发 Fragment。
- 同一用户同时只能存在一个 `ANALYZING` 或 `FORGING` 任务。
- 每日 Forge 次数默认上限为 5 次，可由运营配置。

### 7.9 站内随机与可审计性

MVP 随机不进入智能合约，但不能由前端 `Math.random()` 决定。

后端应：

- 使用密码学安全随机源生成 `random_roll`。
- 保存规则版本、概率、随机值、结果和时间。
- 在判定前生成 `server_seed_hash`，结果后保存对应 seed，便于 Demo 审计。
- 禁止运营人员针对单个用户临时修改概率。
- 概率配置变更必须产生版本号，历史记录继续引用旧版本。

## 8. AI 稀有度分析（MVP）

### 8.1 RareScore

RareScore 用于游戏概率、结果分层和创作建议，不代表市场价格或投资价值。

```text
RareScore =
Originality × 25%
+ Visual Quality × 20%
+ Fan Emotion × 25%
+ Scarcity × 20%
+ Community Potential × 10%
```

| 维度 | 权重 | 分析内容 |
| --- | ---: | --- |
| Originality | 25% | 表达独特性、模板重复度、创意程度 |
| Visual Quality | 20% | 参考图质量、构图信息、色彩与视觉完整度 |
| Fan Emotion | 25% | 故事具体度、个人记忆、情感共鸣 |
| Scarcity | 20% | 内容独家性、私人故事、授权素材与发行策略 |
| Community Potential | 10% | 主题相关度、分享动力和社区讨论价值 |

在最终图片生成前，`Visual Quality` 评价的是参考图和视觉 Brief 完整度；Forge 成功生成图片后可进行一次复评，形成最终 RareScore。

### 8.2 Scarcity 规则

以下规则只能作为模型输入与解释标签，不能简单累加后突破 100 分：

| 内容特征 | 建议影响 |
| --- | ---: |
| 真实且已获授权的现场素材 | +15 |
| 具体私人故事 | +15 |
| 独家创作元素 | +10 |
| 供应量处于推荐区间 | +5 |
| 仅使用通用模板且没有个人故事 | -10 |
| AI 生成图片 | 不直接扣分，重点判断表达是否原创 |
| 版权来源不清楚 | 不进入 Forge，要求先补充声明 |

### 8.3 稀有等级与供应建议

| 最终分数 | 等级 | 推荐供应量 | 可用模式 |
| --- | --- | --- | --- |
| 90–100 | Legendary | 1–25 | Legendary Forge 成功或 Perfect Forge |
| 80–89 | Rare | 10–100 | Focused / Legendary |
| 65–79 | Special | 50–300 | 全部模式 |
| 40–64 | Normal | 100–500 | Stable / Focused |
| 0–39 | Draft | 建议继续完善 | 暂不允许 Legendary Forge |

用户可以修改供应量和价格，但系统应实时解释这会如何改变 `StrategyFit`、`PriceFit` 和最终成功率。

### 8.4 AI 输出结构

```json
{
  "rareScore": 82,
  "level": "Rare",
  "dimensions": {
    "originality": 85,
    "visualQuality": 78,
    "fanEmotion": 91,
    "scarcity": 76,
    "communityPotential": 73
  },
  "recommendSupply": {"min": 20, "max": 100, "default": 50},
  "recommendPrice": {"min": 10, "max": 40, "default": 20},
  "suggestions": ["补充这张照片发生的具体时间", "保留票根作为主要视觉元素"]
}
```

### 8.5 评分边界

- AI 输出必须通过 Pydantic 结构校验和数值截断。
- AI 不直接返回或执行随机结果。
- 价格建议只用于游戏策略匹配，不承诺市场接受度。
- 同一输入可因模型版本产生小幅差异，记录中必须保存评分版本。
- 内容审核或版权校验不通过时，不显示成功概率，也不能开始 Forge。

## 9. 确定性发布与真实 NFT Mint

### 9.1 边界定义

站内 Forge 成功只是获得“可发布草稿”。真正的 NFT 发布不再进行概率判定：

```text
Forge 成功
    ↓
用户编辑并确认最终草稿
    ↓
支付发布费
    ↓
图片与 metadata 上传 IPFS
    ↓
Monad 创建 ERC-1155 Token Type
    ↓
向创作者钱包 Mint 首枚 NFT
```

### 9.2 当前发布规则

| 参数 | 当前规则 |
| --- | --- |
| 发布资格 | Fanora 正式会员，并持有成功 Forge 草稿 |
| 发布费 | 默认 100 FAN，可配置 |
| 单枚价格 | 1–1,000,000 FAN |
| 发行数量 | 1–1,000 枚 |
| 资产标准 | ERC-1155 `FAN_LIMITED_NFT` |
| 存储 | Pinata IPFS |
| 网络 | Monad Testnet |
| 创作者首枚 | 发布成功后确定性 Mint 1 枚 |
| 购买失败 | 买家 FAN 自动退款，链上操作可重试 |

### 9.3 链上 metadata

链上 metadata 可以记录最终 RareScore、稀有等级和 Forge 结果，但必须明确它们来自 Fanora 站内游戏规则：

```json
{
  "name": "FEAR DREAMS",
  "description": "Fan Memory NFT",
  "image": "ipfs://...",
  "attributes": [
    {"trait_type": "Rare Score", "value": 87},
    {"trait_type": "Rarity Level", "value": "Rare"},
    {"trait_type": "Fan Emotion", "value": 95},
    {"trait_type": "Forge Result", "value": "Perfect"},
    {"trait_type": "Rules Version", "value": "forge-v1"}
  ]
}
```

### 9.4 合约原则

- 继续复用当前 `FanoraCollectibles` ERC-1155 合约。
- 不新增 `FanoraMintGame.sol`。
- 不在合约中保存 RareScore、随机数、Fragment 或 Forge 余额。
- 合约只负责供应量、单钱包限制、Mint 时间、幂等领取和资产归属。
- FAN 与 Fragment 继续以 PostgreSQL 为事实源，不新增 ERC-20 `FanToken.sol`。

## 10. FAN 经济系统

### 10.1 FAN 定位

FAN 是站内可审计的粉丝贡献单位，不是当前阶段的链上 ERC-20，也不承诺兑换现金。

系统必须继续区分：

- `fan_token_balance`：当前可消费余额。
- `fan_token_lifetime_earned`：终身累计贡献，用于等级成长，消费后不下降。

### 10.2 产出

- 每日签到。
- 完成指定帖子回复、发布创作或活动页任务。
- 内容通过 AI/规则审核。
- 社区发布、回复、点赞、收藏等有效互动。
- 特殊活动和运营奖励。

### 10.3 消耗

- Stable Forge：10 FAN。
- Focused Forge：20 FAN。
- Legendary Forge：40 FAN。
- 发布限量 NFT：当前默认 100 FAN。
- 购买 Gallery NFT：由创作者设置价格。
- Fragment 兑换免费 Forge 次数。
- P1 权益兑换：限定模板、Badge、活动资格或周边抽签资格。

### 10.4 流转与控制

- NFT 购买的 FAN 从买家转给创作者，形成创作者激励。
- 发布费作为系统消耗，用于控制垃圾作品和无限发行。
- Forge 费用作为系统消耗；正常游戏失败不退款，系统异常必须退款。
- 所有扣费必须使用幂等键，FAN 流水需区分 `forge-spend`、`publish-fee`、`purchase`、`sale` 和 `system-refund`。
- 运营应监控 FAN 产出/消耗比、头部集中度和异常互买行为。

## 11. 成长、成就与权益

### 11.1 会员等级

等级继续由终身累计 FAN 的确定性阈值决定。等级提升时更新同一枚 ERC-721 会员身份的等级和 metadata，不销毁重铸。

### 11.2 创作者成就

建议新增不会影响资产价格的成就：

- First Memory：首次发布 NFT。
- First Forge：首次完成站内 Forge。
- Perfect Moment：首次触发 Perfect Forge。
- Never Give Up：累计使用 5 个 Fragment 完成免费重试。
- Storyteller：发布 3 个故事完整的作品。
- Community Favorite：单件作品获得指定收藏数。
- Supported Creator：首次售出 NFT。
- Memory Keeper：收藏 5 个不同创作者的作品。
- Monad Publisher：完成首次 Monad 链上发布。

成就优先以数据库记录和个人页展示实现；稀缺、限量或活动型成就再铸造成 ERC-1155 Badge。

### 11.3 后续权益解锁

| 条件 | 可解锁权益示例 |
| --- | --- |
| 正式会员 | 进入 AI 共创工作台、参与 Forge、发布 NFT |
| 活跃等级 | 小幅 LevelBonus、更多每日 Forge 次数、限定模板 |
| 核心粉等级 | 优先活动报名、限定内容、纪念 Badge |
| 创作者成就 | Gallery 推荐位、专题展厅、联名素材包申请 |

权益必须由运营方明确有效期和履约条件。链上 Badge 只能证明资格或历史，不代表权益永久有效。

## 12. 页面与交互方案

### 12.1 `/collections/create` AI 共创工作台

必须展示：

- 当前 FAN 余额、Fragment 数量和发布费。
- 当前模板、风格与参考图。
- Agent 对话与故事状态。
- AI 五维评分、RareScore、稀有等级和改进建议。
- 推荐供应量、推荐价格与玩家当前设置的匹配度。
- Stable、Focused、Legendary 三种 Forge 模式。
- 当前成功率、Perfect 概率、模式消耗和可能结果。
- Forge 动画、随机结果和本次记录编号。
- 图片版本柜和当前选中版本。
- 名称、描述、属性、供应量和 FAN 价格。
- 版权声明与发布确认。
- IPFS、创建 Token Type、创作者首枚 Mint 的进度。

Forge 确认弹窗必须明确：本次消耗多少 FAN、成功率、Perfect 概率、失败后获得 1 Fragment，以及“本步骤不会执行链上交易”。

发布前确认弹窗必须明确：发布费、发行数量、单枚价格、创作者会先获得 1 枚，以及“发布阶段不再进行随机判定”。

### 12.2 Forge Result 状态

#### Perfect Forge

- 使用高亮全屏结果动画，但不伪装成已经链上 Mint。
- 文案：`Perfect Forge! Legendary draft unlocked.`
- 展示两个候选图片版本、RareScore Bonus 和成就。
- 主按钮：`选择版本并继续编辑`。

#### Normal Success

- 文案：`Forge Success! NFT draft generated.`
- 展示生成图片、RareScore、等级和公开属性。
- 主按钮：`编辑并准备发布`。

#### Failed Forge

- 文案：`Forge Failed. Memory Fragment +1.`
- 展示距离免费重试还差多少 Fragment。
- 保留故事摘要与参数，不清空工作台。
- 主按钮：`调整策略并再次尝试`。

结果页禁止显示 tokenId、合约地址或 `NFT Minted`，因为此时尚未发布链上资产。

### 12.3 `/collections` Gallery

作品卡片重点展示：

- 图片、名称和创作者。
- FAN 价格。
- 已铸造/总供应量。
- 点赞与收藏数。
- 售罄状态。

不在列表页展示复杂投资指标或夸大的稀有度文案。

### 12.4 `/item/{id}` 作品详情

必须展示：

- 完整粉丝故事与附图。
- 公开属性。
- 创作者信息。
- 价格、剩余供应和购买按钮。
- IPFS metadata、合约地址、tokenId、链 ID 和浏览器链接。
- Mint 记录与购买者。
- 购买进度、成功结果或失败退款提示。

### 12.5 `/collection` 个人收藏

必须展示：

- ERC-721 会员身份和当前等级。
- 自己持有的 ERC-1155 NFT、Badge 与纪念卡。
- 自己发布的作品。
- 交易状态和 Monad 浏览器入口。
- 将已持有收藏品设置为头像的能力。

## 13. 数据与接口规划

### 13.1 当前核心数据

- `NftApplication`：作品名称、故事、主题、属性、价格、供应量、版权声明和发布状态。
- `NftMetadataVersion`：图片 CID、metadata CID、内容哈希和 metadata 版本。
- `CollectibleTokenType`：ERC-1155 tokenId、供应量、时间窗口、转让规则和链上状态。
- `CollectibleOwnership`：用户持有数量、钱包、领取键和 Mint 状态。
- `ChainOperation`：链上操作、幂等键、交易哈希、确认数和失败原因。
- `NftCreationReaction`：点赞和收藏。
- FAN 流水：发布扣费、购买扣费、销售收入和失败退款。

### 13.2 当前核心接口

| 接口 | 用途 |
| --- | --- |
| `GET /api/v1/nft/creations/agent/templates` | 获取视觉模板 |
| `GET /api/v1/nft/creations/agent/styles` | 获取视觉风格 |
| `POST /api/v1/nft/creations/agent/chat` | 推进一次 Agent 共创对话 |
| `POST /api/v1/nft/creations/ai-draft` | 生成可编辑草稿和可选图片 |
| `POST /api/v1/nft/creations` | 确认并发布限量 NFT |
| `GET /api/v1/nft/creations` | 获取 Gallery 作品 |
| `GET /api/v1/nft/creations/{id}` | 获取作品详情与 Mint 记录 |
| `POST /api/v1/nft/creations/{id}/like` | 点赞 |
| `POST /api/v1/nft/creations/{id}/favorite` | 收藏 |
| `POST /api/v1/nft/creations/{id}/buy` | 使用 FAN 购买并铸造 NFT |
| `GET /api/v1/nft/me` | 获取个人身份、收藏品与申请 |

### 13.3 MVP 新增数据

#### `nft_forge_session`

- `id`
- `user_id`
- `conversation_id`
- `status`: `COLLECTING / ANALYZED / FORGING / SUCCESS / PERFECT / FAILED / ERROR / PUBLISHED`
- `story_summary`
- `reference_image_urls`
- `supply`
- `price_fan_tokens`
- `forge_mode`
- `rules_version`
- `created_at / updated_at`

#### `nft_ai_analysis`

- `id`
- `forge_session_id`
- `rare_score`
- `rarity_level`
- `originality`
- `visual_quality`
- `fan_emotion`
- `scarcity`
- `community_potential`
- `recommend_supply_min / max / default`
- `recommend_price_min / max / default`
- `suggestions`
- `model_name / prompt_version`

#### `nft_forge_attempt`

- `id`
- `forge_session_id`
- `user_id`
- `idempotency_key`
- `forge_mode`
- `fan_cost`
- `success_rate`
- `perfect_rate`
- `random_roll`
- `perfect_roll`
- `server_seed_hash`
- `server_seed_reveal`
- `result`: `PERFECT / SUCCESS / FAILED / ERROR`
- `refund_status`
- `rules_version`
- `created_at`

#### `user_fragment_balance` 与 `fragment_ledger`

- 当前 Fragment 余额。
- 获得、兑换和调整流水。
- 来源 Forge attempt。
- 幂等键和创建时间。

#### `nft_generation_job`

- 只在 Forge 成功后创建。
- 保存图片生成状态、模型、Prompt、输出版本、错误与耗时。
- 生成服务失败时将 Forge attempt 标记为 `ERROR` 并触发 FAN 退款。

### 13.4 MVP 新增接口

| 接口 | 用途 |
| --- | --- |
| `POST /api/v1/nft/forge/analyze` | 分析故事和参考图，返回 RareScore 与推荐参数 |
| `PATCH /api/v1/nft/forge/{sessionId}/strategy` | 更新供应量、价格和模式，重新计算成功率 |
| `POST /api/v1/nft/forge/{sessionId}/start` | 预扣 FAN、完成随机判定并在成功时启动生图 |
| `GET /api/v1/nft/forge/{sessionId}` | 查询分析、Forge 和生成状态 |
| `POST /api/v1/nft/forge/{sessionId}/retry` | 使用 FAN 或 Fragment 再次 Forge |
| `POST /api/v1/nft/forge/{sessionId}/select-version` | 选择成功生成的图片版本 |
| `GET /api/v1/nft/fragments/me` | 查询 Fragment 余额和流水 |
| `POST /api/v1/nft/fragments/redeem` | 兑换免费 Forge 次数 |

现有 `POST /api/v1/nft/creations` 需要增加 `forge_session_id`，后端只接受属于当前用户且状态为 `SUCCESS` 或 `PERFECT` 的会话。

### 13.5 后续数据

- `creator_achievement`：成就类型、进度、解锁时间和 Badge 关联。
- `nft_impression`：曝光、详情访问和来源，用于漏斗分析。

## 14. 风控、版权与公平性

### 14.1 版权

- 发布者必须勾选并提交版权声明。
- 官方模板要记录授权素材、允许用途和禁止元素。
- Agent 不应生成真实艺人的可识别肖像，除非素材与授权规则明确允许。
- 用户上传参考图时应提示其确认拥有使用权。
- 争议作品必须支持下架展示和停用继续 Mint；链上历史无法被平台删除，应在发布前明确提示。

### 14.2 内容安全

- AI 草稿和用户最终文本都应经过内容审核。
- Agent 的审核结论不能越权执行扣费或链上操作。
- 审核失败应保留可修改草稿，不直接销毁用户内容。

### 14.3 经济与刷量风险

- Forge、发布、购买和奖励都使用幂等键。
- 限制同一用户分析、Forge 和生成频率以及并发任务。
- 服务端保存概率输入和随机结果，禁止前端提交 `success=true` 一类结果字段。
- 游戏失败与系统错误必须使用不同状态；只有系统错误退款。
- Fragment 兑换必须写流水并防止并发重复消费。
- 概率规则更新使用新版本，不能修改历史 attempt 的计算结果。
- 监控同一批账户之间的循环购买和异常 FAN 转移。
- 排行榜应基于贡献规则，不把购买金额直接等同于粉丝忠诚度。
- 价格和供应量必须有后端硬限制，不能只依赖前端。

## 15. Demo 演示脚本

### 15.1 两分钟主线

1. 在 Community 展示玩家通过任务获得 FAN。
2. 进入 AI 共创工作台，选择“演唱会纪念系列”模板和视觉风格。
3. 向 Agent 讲述一段粉丝故事，展示 Agent 整理故事状态。
4. 展示 AI 五维评分、RareScore、推荐供应量和推荐价格。
5. 切换 Stable、Focused、Legendary 模式，展示投入、成功率和 Perfect 概率变化。
6. 点击“开始生成 NFT”，播放 Forge 动画并展示成功、Perfect 或 Fragment 结果。
7. 成功后展示 AI 生成图片、版本柜、名称、描述和属性。
8. 明确说明刚才全部是站内游戏，尚未发生链上交易。
9. 确认版权与发行参数后发布，展示 IPFS、ERC-1155 创建和创作者首枚 Mint。
10. 进入 Gallery 或详情页，使用另一个账号购买并展示双方 Collection/FAN 变化。

### 15.2 评委应记住的表达

**Fanora 先用 AI 理解粉丝故事，再让玩家用 FAN 和发行策略完成一次站内创作博弈；成功作品由用户确认后，才真正发布为可验证的链上收藏品。**

### 15.3 异常备用方案

- AI 分析不可用：展示已准备的评分会话，不执行随机 Forge。
- 图片生成失败：展示系统错误退款，不把它表现为游戏失败。
- Forge 随机结果不适合现场演示：使用预置 Demo 账号的历史 Perfect attempt，并展示完整审计字段。
- IPFS 或 Monad 延迟：展示交易进度、历史成功作品和浏览器链接。
- 钱包网络异常：使用已登录账号和已铸造收藏品继续演示。
- 购买失败：展示自动退款和可重试状态，说明资产安全设计。

## 16. 核心指标

### 16.1 创作漏斗

- 进入工作台人数。
- 开始 Agent 对话比例。
- 完成 AI 分析比例。
- 各 Forge 模式选择占比。
- Forge 成功率、Perfect 率与规则理论值偏差。
- 失败后再次尝试比例与 Fragment 兑换率。
- Forge 成功后图片生成成功率。
- 生成后进入发布确认比例。
- 发布成功率与平均耗时。

### 16.2 收藏漏斗

- Gallery 曝光到详情点击率。
- 详情页点赞、收藏和购买转化率。
- 每件作品平均收藏人数。
- 售罄作品比例。
- 购买失败率与退款成功率。

### 16.3 生态健康

- FAN 日产出与日消耗。
- Forge 费、发布费与购买流转占比。
- 系统异常退款率与平均退款耗时。
- Stable、Focused、Legendary 模式的 FAN 消耗和留存差异。
- 创作者收入分布。
- 7 日任务留存和创作者复发率。
- 版权投诉、审核拒绝和异常互买比例。

## 17. 开发计划与实施顺序

### Phase 0：当前已完成闭环

- 钱包登录、正式会员和 FAN。
- 任务、签到、社区互动、等级和排行榜。
- AI 对话、模板、风格、参考图和图片生成。
- 用户确认名称、描述、属性、价格和供应量。
- IPFS 发布与 Monad ERC-1155 创建。
- 创作者首枚 Mint、Gallery、点赞、收藏和购买。
- 购买失败退款、Collection 展示和链上浏览器链接。

### Phase 1：数据模型与规则服务

- 新增 Forge session、AI analysis、Forge attempt、Fragment 余额与流水模型。
- 增加数据库迁移、唯一约束、索引和幂等键。
- 实现 `ForgeRulesService`，集中维护费用、模式、概率上下限和规则版本。
- 实现供应量/价格匹配算法、等级加成和成功率计算。
- 使用密码学安全随机源，保存 seed hash、roll 和结果。
- 为公式边界、概率计算、重复请求和 Fragment 并发消费增加单元测试。

### Phase 2：AI 分析与生成拆分

- 扩展现有 NFT Agent，新增结构化五维评分和发行建议。
- 将现有“一次调用直接生图”拆为 Analyze 与 Forge 后 Generate 两步。
- AI 分析不扣费；Forge 成功后才创建图片生成任务。
- 增加内容安全、版权声明和输入完整度检查。
- 保存模型名、Prompt 版本、原始结构化结果和降级来源。
- 覆盖 LLM 不可用、结构校验失败和模型超时的测试。

### Phase 3：FAN、Fragment 与状态机

- 实现 Forge FAN 预扣和 `forge-spend` 流水。
- 正常 Failed Forge 消耗 FAN 并发放 1 Fragment。
- 系统错误写入 `ERROR`，自动生成 `system-refund` 流水。
- 实现 5 个 Fragment 兑换 Stable、10 个兑换 Focused。
- 限制同一用户并发任务和每日 Forge 次数。
- 增加任务超时扫描与异常任务恢复机制。

### Phase 4：前端 Forge Game

- 在 `NftStudioWorkbench` 增加 AI 评分面板和 RPG 属性展示。
- 增加供应量、价格匹配提示与成功率实时预览。
- 增加三种 Forge 模式卡片、FAN 消耗和风险确认弹窗。
- 增加 Analyze、Forging、Perfect、Success、Failed、Error 动画状态。
- Failed 状态保留会话和参数，并展示 Fragment 进度。
- 成功状态接入现有图片版本柜与编辑表单。
- 移动端按“故事 → 分析 → 策略 → Forge → 编辑 → 发布”分步展示。

### Phase 5：确定性发布接入

- `POST /nft/creations` 增加 `forge_session_id`。
- 校验 session 所属用户、成功状态、已选图片版本和未重复发布。
- 将 RareScore、稀有等级、Forge 结果和规则版本写入 metadata attributes。
- 继续复用现有 Pinata、Monad、ERC-1155、首枚 Mint 和 100 FAN 发布费逻辑。
- 发布失败沿用现有错误恢复，不回滚已经结算的正常 Forge 结果。
- 页面清楚分开 Forge 进度和 Monad 发布进度。

### Phase 6：联调、测试与 Demo 数据

- 打通 Analyze → Strategy → Forge → Generate → Publish 全链路。
- 准备 Stable Success、Legendary Perfect、Failed Fragment 三套演示记录。
- 验证正常失败不调用图片模型、IPFS 或合约。
- 验证系统异常自动退款且不发 Fragment。
- 验证重复点击不会重复扣 FAN、发 Fragment 或生成图片。
- 验证发布阶段不重新随机，链上 Mint 只受真实服务错误影响。
- 完成前端类型检查、构建、后端测试和合约回归测试。

### Phase 7：后续成长

- 增加 Forge 历史、统计和 seed 审计展示。
- 增加 First Forge、Perfect Moment 等成就。
- 将限定模板、Forge 次数和活动资格绑定等级或 Badge。
- 增加 Gallery 推荐机制与限时 Forge 活动。
- 根据真实数据平衡三种模式的费用和概率。

### Phase 8：生态扩展

- 多艺人或多创作者素材包，但继续使用统一身份协议。
- 票务、周边和线下活动方读取公开 Badge 与身份摘要。
- 创作者专题展厅、联名活动和权益核验。
- 在合规与用户需求明确后再评估二级市场。

## 18. 工程改造清单

### 18.1 后端

| 模块 | 实施内容 |
| --- | --- |
| `backend/app/models/nft.py` | 新增 Forge session、analysis、attempt、Fragment 余额与流水模型 |
| `backend/app/schemas/nft_agent.py` | 新增评分、策略、Forge 结果和状态响应 Schema |
| `backend/app/agents/nft_studio.py` | 保留故事收集，增加 Analyze 节点；移除分析完成后自动生图 |
| `backend/app/agents/nft_creation.py` | 只在成功 Forge 后执行最终 metadata 与图片生成 |
| `backend/app/services/nft_forge.py` | 新增规则计算、FAN 结算、随机判定、Fragment 和状态机服务 |
| `backend/app/services/nft.py` | 发布时验证成功 Forge session，并写入 Forge metadata 属性 |
| `backend/app/api/routes/nft.py` | 增加 Analyze、Strategy、Start、Retry、Status 和 Fragment 接口 |
| `backend/app/core/config.py` | 增加三种模式费用、概率上下限、每日次数和 Fragment 兑换配置 |
| 数据库迁移 | 创建新表、索引、外键、唯一幂等键和状态约束 |

### 18.2 前端

| 模块 | 实施内容 |
| --- | --- |
| `frontend/components/nft/NftStudioWorkbench.tsx` | 接入评分、策略、Forge 状态机和发布校验 |
| `frontend/components/nft/NftStudioWorkbench.module.css` | 增加 RPG 属性面板、模式选择和结果动画样式 |
| `frontend/components/nft/ForgeStrategyPanel.tsx` | 新增三种模式、成功率和参数匹配控制 |
| `frontend/components/nft/ForgeResultModal.tsx` | 新增 Perfect、Success、Failed、Error 结果弹窗 |
| `frontend/components/common/FanTokenAmount.tsx` | 复用 FAN 展示，增加 Forge 扣费确认场景 |
| `frontend/lib/api/types.ts` | 增加 Forge session、analysis、attempt 和 Fragment 类型 |
| `/collections/create` | 保持现有入口，加入“分析 → 策略 → Forge → 编辑 → 发布”步骤 |

### 18.3 测试

| 测试类型 | 必须覆盖 |
| --- | --- |
| 公式单元测试 | RareScore 边界、三种模式、clamp、等级加成、参数匹配 |
| 账本测试 | 成功扣费、正常失败扣费、系统异常退款、重复请求幂等 |
| Fragment 测试 | 发放、5/10 个兑换、并发兑换、重复兑换 |
| 状态机测试 | 非法状态跳转、成功后生成、失败不生成、发布后不可重发 |
| API 集成测试 | Analyze、Strategy、Start、Retry、Status、Publish 全链路 |
| 前端测试 | 概率展示、确认弹窗、结果状态、失败保留数据、错误退款提示 |
| 回归测试 | 原有 NFT 发布、购买、退款、Collection 和 Monad 合约测试 |

### 18.4 实施依赖

```text
数据模型与迁移
    ↓
规则服务与账本事务
    ↓
AI Analyze 输出
    ↓
Forge API 与状态机
    ↓
前端策略面板与结果动画
    ↓
成功后图片生成
    ↓
发布接口校验与 metadata
    ↓
全链路测试和 Demo 数据
```

前端动画可以与后端规则服务并行开发，但最终联调前必须冻结 `forge-v1` 的费用、概率公式、状态枚举和接口字段。

## 19. MVP 验收标准

满足以下条件，才算“AI 共创 NFT 游戏闭环”可交付：

- [ ] 正式会员可以进入 `/collections/create`。
- [ ] 玩家可以选择模板、视觉风格和最多 6 张参考图。
- [ ] Agent 可以通过多轮对话整理故事并输出五维评分与 RareScore。
- [ ] 系统可以推荐供应量和价格，并实时计算策略匹配修正。
- [ ] 页面提供 Stable、Focused、Legendary 三种 Forge 模式。
- [ ] 页面分别展示成功率、Perfect 概率、FAN 消耗和失败 Fragment。
- [ ] Forge 随机由服务端执行并保存规则版本、概率和随机记录。
- [ ] Perfect、Success、Failed 三种游戏结果均可正确展示。
- [ ] 只有 Forge 成功后才调用最终图片生成，结果进入版本柜。
- [ ] Forge 正常失败扣除 FAN 并增加 1 Fragment。
- [ ] AI、网络或服务异常全额退款，不增加 Fragment。
- [ ] 集齐 5/10 个 Fragment 可以兑换对应免费 Forge。
- [ ] 用户可以编辑名称、描述、供应量和 FAN 价格。
- [ ] 页面明确展示发布费、当前 FAN 和版权声明。
- [ ] Forge 结果页面不显示 tokenId、合约地址或 `NFT Minted`。
- [ ] 发布接口只接受当前用户成功且未发布的 Forge session。
- [ ] 发布成功后图片与 metadata 可通过 IPFS 访问。
- [ ] Monad 上可查到 ERC-1155 tokenId、合约和创作者首枚 Mint。
- [ ] Gallery 能展示价格、供应量、点赞和收藏。
- [ ] 其他用户可以使用 FAN 购买并在 Collection 中看到 NFT。
- [ ] 创作者收到购买 FAN，买家失败时获得退款。
- [ ] Demo 不把站内 FAN 描述为可投资或保证升值的链上 Token。
- [ ] AI、IPFS 或链上服务异常时有降级方案，不阻断整场演示。

## 20. 最终产品表达

Fanora 的独特之处，是把“生成 NFT”从一次普通的 AI 按钮变成有评分、有投入、有策略、有成功与积累反馈的创作游戏，同时把站内游戏和真实链上资产操作清楚分开：

1. **贡献成长**：真实任务和互动产生 FAN、等级与排行榜。
2. **AI 分析**：Vision 与 LLM 理解故事，生成 RareScore 和发行建议。
3. **站内 Forge**：玩家选择投入与风险，成功生成草稿，失败积累 Fragment。
4. **确定性发布**：成功草稿经用户确认后，才写入 IPFS 并发布 Monad ERC-1155。
5. **社区经济**：作品被收藏和购买，FAN 在粉丝与创作者之间流转。

最终形成 Fanora 的核心游戏化系统：

> **参与获得 FAN，策略决定风险，Forge 生成作品，链上证明归属。**
