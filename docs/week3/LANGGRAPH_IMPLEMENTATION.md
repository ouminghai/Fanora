# Fanora LangGraph 与 AI Quest 初步版本

> 更新时间：2026-07-23
> 状态：核心流程可运行；真实模型、IPFS 与 Monad 铸造依赖部署环境配置

## 1. 本次完成范围

本次按需求完成四条可演示链路：

1. 数据库驱动的粉丝画像工作流。
2. Quest 发布内容、回复和专属页面提交的 AI Agent 判定。
3. FEAR and DREAMS 任务审核通过后的 FAN 奖励与 ERC-1155 纪念票铸造编排。
4. 限量粉丝 NFT 的 metadata 草稿与用户图片生成工作流。

Agent 不持有用户私钥，不直接修改 FAN，不负责权限判断，也不直接调用合约。它只生成结构化画像、审核结论或创作草稿；奖励和链上写入仍由后端确定性服务执行。

## 2. 粉丝画像工作流

工作流：

```text
prepare_data
  → calculate_scores
  → classify_fan
  → enrich_with_llm
  → recommend_tasks
  → persist_result
```

### 数据来源

- 当前 FAN 可用余额。
- 已奖励任务数量。
- 签到、发帖和回复形成的活跃天数。
- 已确认链上操作与已拥有收藏品数量。
- 多次内容审核拒绝和链上失败形成的风险信号。
- 正式会员状态、官方社区加入状态及当前可参与任务。

### 输出与保存

- 活跃度、忠诚度、影响力、贡献度与总分，范围均为 0–100。
- 粉丝类型、标签、风险等级和解释摘要。
- 只包含当前用户有资格参加、处于有效时间窗且尚未参与的任务推荐，每条推荐包含原因。
- 每次运行写入 `fan_profile_runs`，并更新 `user_profiles.fan_type`。
- OpenAI 未配置或调用失败时返回可复现的规则结果，并明确标记来源或降级状态。

查看接口：

```http
GET /api/v1/profile/me
Authorization: Bearer <session-token>
```

前端 `/profile` 已展示画像分数、类型、摘要和推荐任务。

## 3. Quest 内容审核工作流

工作流：

```text
normalize_content
  → deterministic_checks
  → llm_review
  → validate_decision
```

当前接入三类任务：

- `content_publish`：发帖 Quest。
- `post_reply`：任务回复 Quest。
- `page_action`：FEAR and DREAMS 等专属页面任务。

### 审核信号

- 是否包含任务要求的 tag。
- 去除 Markdown 和 URL 后的有效内容长度。
- 重复字符、占位文本、低信息量和明显灌水。
- 内容与任务标题、说明和互动提示的主题相关性。
- 基础内容安全规则。
- 模型给出的 AI 生成可能性、质量分和原因。

### 审核结果

```text
approved       → 后端幂等发放任务 FAN；如配置 NFT 奖励则进入铸造编排
rejected       → 不发奖励，任务保持 claimed，可修改后重交
manual_review  → 不发奖励，任务保持 claimed，保留人工确认语义
```

每次审核写入 `task_content_reviews`，保存决定、质量分、信号、原因、规则版本、提示词版本、模型来源与降级状态。

没有配置 OpenAI 时仍会执行 tag、长度、灌水、相关性和安全硬规则。这是可真实使用的确定性降级，不会伪造模型调用；更细的语义和 AI 痕迹判断需要真实模型配置。

## 4. FEAR and DREAMS 纪念票

页面：`/community/tasks/fear-and-dreams`

完整流程：

```text
正式会员加入社区并领取任务
  → 提交至少 10 个字的现场记忆和可选图片
  → AI Agent 审核
  → approved 后幂等发放 500 FAN
  → 创建 task_nft_rewards 记录
  → 上传 eason-concert.webp 与 metadata 到 Pinata
  → 创建或复用 ERC-1155 token type
  → mint 到用户主钱包
  → 返回状态、交易哈希和 MonadVision 链接
```

纪念票使用固定素材：

```text
frontend/public/img/fanora/eason-concert.webp
```

任务奖励配置包含版本、类别、名称、说明、图片、最大供应量 `10000`、单钱包上限 `1`、领取窗口和不可转让策略。幂等键为：

```text
task-nft-mint:{task_id}:{user_id}:v{version}
```

同一任务、用户和奖励版本只会创建一条奖励记录。FAN 与 NFT 使用不同记录，便于展示“积分已发放、NFT 等待配置或处理中”的真实状态。

若 Pinata、Monad 合约地址或运营钱包未配置，奖励记录进入 `WAITING_CONFIGURATION`，页面会明确显示等待配置，不会返回虚假交易成功。

## 5. 限量粉丝 NFT 的 AI 草稿与图片

工作流：

```text
prepare_brief → draft_metadata → generate_image
```

接口：

```http
POST /api/v1/nft/creations/ai-draft
Authorization: Bearer <session-token>
Content-Type: application/json

{
  "theme": "演唱会散场后的蓝色灯海",
  "story": "描述粉丝故事与纪念意义",
  "visual_style": "电影感拼贴",
  "preferred_name": "可选名称",
  "reference_notes": "可选视觉参考说明",
  "generate_image": true
}
```

返回名称、描述、图片提示词、建议属性和可选 Base64 图片。前端 NFT 发布弹窗中的“AI 生成草稿与图片”会把结果填回可编辑表单。

边界：

- Agent 不决定 FAN 价格和发行量。
- Agent 不自动扣发布费、不上传 Pinata、不发布或铸造。
- 创作者必须检查并确认草稿，再主动走原有发布流程。
- 未配置图片模型时 metadata 仍有规则草稿，图片返回不可用状态，用户可以自行上传图片。

## 6. 部署配置

### 数据库迁移

部署新版本后先执行：

```bash
cd backend
uv run alembic upgrade head
```

迁移 `20260723_0028_agent_quest_reviews_and_nft_rewards.py` 会创建内容审核和任务 NFT 奖励表。

### 模型配置

```dotenv
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5-mini
OPENAI_IMAGE_MODEL=gpt-image-2
OPENAI_IMAGE_SIZE=1024x1024
IMAGE_GENERATION_TIMEOUT_SECONDS=90
```

### FEAR and DREAMS 真实铸造配置

```dotenv
CHAIN_WRITES_ENABLED=true
MONAD_RPC_URL=https://testnet-rpc.monad.xyz
MONAD_CHAIN_ID=10143
COLLECTIBLES_CONTRACT_ADDRESS=
COLLECTIBLE_TYPE_MANAGER_PRIVATE_KEY=
COLLECTIBLE_MINTER_PRIVATE_KEY=
PINATA_JWT=
```

`CHAIN_WRITES_ENABLED=false` 适用于自动化测试或只演示数据库状态的环境。生产环境如需真实铸造必须显式配置合约、Pinata 和最小权限运营钱包；任何密钥都不得提交到 Git。

## 7. 真实可用、配置依赖与未完成项

### 已真实连接数据库和业务服务

- 粉丝画像数据聚合、评分、推荐、运行记录保存和用户类型更新。
- Quest tag、长度、灌水、相关性、安全检查与结构化审核记录。
- 审核结果控制 FAN 是否发放，重复请求不重复奖励。
- FEAR and DREAMS 独立任务页、固定纪念图、奖励状态和幂等记录。
- NFT metadata 草稿接口及前端可编辑回填。

### 依赖外部配置

- OpenAI 文本模型：增强画像解释、语义审核和 metadata 文案。
- OpenAI 图片模型：生成 Base64 粉丝 NFT 图片草稿。
- Pinata 与 Monad：上传纪念票素材和 metadata、创建 ERC-1155 类型并 mint。

### 暂未完成

- `manual_review` 的运营审核界面；当前只保留状态与审计数据。
- Agent 离线评测集、成本/延迟仪表盘和批量画像更新调度。
- 链上写入后台队列、自动重试、链重组对账与失败补偿。
- 无法仅凭文本可靠断言内容是否由 AI 生成；当前该项只是审核信号，不作为单独拒绝依据。

## 8. 验证说明

- 后端测试覆盖规则画像、画像图节点、内容审核、NFT 草稿、Quest 审核和任务 NFT 幂等编排。
- 测试环境显式设置 `CHAIN_WRITES_ENABLED=false`，避免读取本地 `.env` 后意外发送真实链上交易。
- 前端类型检查、生产构建和 FEAR and DREAMS 页面交互已验证。
- 全新 SQLite 从最早 Alembic 版本迁移仍受历史 PostgreSQL 专用 `ALTER` 语句影响；新增 `0028` 迁移本身不是该失败来源，生产迁移应在 PostgreSQL 备份或临时数据库先验证。
