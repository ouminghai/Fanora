# Fanora AI Agents

> 更新日期：2026-07-23
> 代码目录：`backend/app/agents`
> 适用基线：Fanora V1

## 1. 运行边界与事实源

Fanora 当前有三个 LangGraph Agent：

| Agent | 代码 | 主要用途 | 是否直接改 FAN 或写链 |
| --- | --- | --- | --- |
| 粉丝画像 Agent | `backend/app/agents/fan_profile.py` | 读取已验证行为，生成画像、分数、解释和任务推荐 | 否 |
| 内容审核 Agent | `backend/app/agents/content_review.py` | 判定社区发布和任务提交是否相关、真实且非垃圾内容 | 否 |
| 粉丝 NFT 草稿 Agent | `backend/app/agents/nft_creation.py` | 生成可编辑 metadata、图片提示词和可选 NFT 图片 | 否 |

Agent 只输出结构化分析、审核结论或草稿。以下事实始终由确定性后端或链上回执决定：

- FAN 发放、消费、余额和终身累计值。
- 任务状态、奖励幂等和审核记录持久化。
- 会员等级和正式会员权限。
- Pinata 上传结果、CID 与 metadata 版本。
- Monad 交易提交、确认、token id 和资产所有权。

运行原则：

- 模型不可用时必须有确定性降级，不得让核心页面永久等待。
- 前端“AI 正在处理”只代表请求尚未完成，不能伪造审核、IPFS 或链上成功。
- LLM、图片模型、Langfuse、Pinata 或 RPC 的异常必须转换为可展示错误，并释放页面交互锁。

## 2. 粉丝画像 Agent

### 2.1 入口

```http
GET /api/v1/profile/me
GET /api/v1/profile/users/{user_id}
POST /api/v1/agent/fan-profile/analyze
```

### 2.2 工作流

```text
prepare_data
  → calculate_scores
  → classify_fan
  → enrich_with_llm
  → recommend_tasks
  → persist_result
```

数据来源包括 FAN、任务、签到、发帖、回复、审核记录、链上操作、收藏品和当前可参与任务。规则节点计算 `activity`、`loyalty`、`influence`、`contribution`、`total`；LLM 只改善摘要和 Badge 草稿表达，不改变规则分数。

持久化：

- 每次完整分析写入 `fan_profile_runs`。
- 同步更新 `user_profiles.fan_type`。
- 公开主页优先读取最近一次持久化画像；没有历史记录时使用快速规则画像，不因访客打开页面而重复调用 LLM。

降级：

- 未配置 LLM 或模型调用失败时，返回规则分数、规则分类和规则摘要。
- 降级结果通过 `analysis_source` 与 `degraded` 明确标识。

## 3. 社区发布审核与 Quest 任务判定

### 3.1 两条业务链必须分开

| 场景 | 调用链 | 目的 | 是否发任务奖励 |
| --- | --- | --- | --- |
| 社区发帖/回复 | `community.py` → `community_moderation.py` | 判断内容是否允许进入社区 | 否 |
| 已领取任务提交 | `task_completion.py` → `content_review_agent` | 判断内容是否真实参与指定任务 | 通过后由 service 发放 |

两条业务链复用审核图，但输入上下文、最低长度和副作用不同。社区发布不能因为用户没有领取任务而改变审核标准；任务判定也不能把文采、专业度或长篇表达当作完成条件。

### 3.2 工作流

```text
normalize_content
  → deterministic_checks
  → llm_review
  → validate_decision
```

兼容任务类型：

- `content_publish`
- `post_reply`
- `page_action`

社区发布类型：

- `post`
- `reply`

### 3.3 审核原则

应通过：

- 内容与社区或任务主题相关，并体现真实参与、观点、感受或粉丝互动。
- 简短、普通、情绪化、语言不丰富或有轻微 AI 感的表达。
- 使用常见粉丝话术，或与其他用户措辞相似，但确实回应当前主题。

只在以下情况拒绝：

- 明显无关内容。
- 大量无意义字符、占位文本或低信息量重复内容。
- 与当前主题无关的复制粘贴。
- 广告、垃圾信息、引流或基础安全规则命中。
- 明显只为刷任务而生成、没有主题参与信息的空洞内容。

审核信号包括 required tag、去除 URL/Markdown 后的有效长度、重复字符、垃圾词、主题关键词和语义主题。缺少 tag 只是弱信号；`quality_score` 用于审计和观察，不是文采评分，也不能单独决定拒绝。

### 3.4 结果与副作用

| 决策 | 业务含义 |
| --- | --- |
| `approved` | 社区内容可发布；任务 service 可继续执行幂等奖励 |
| `rejected` | 不发布或不发奖励，并返回可修改原因 |
| `manual_review` | 暂不发奖励，保留人工确认语义 |

任务审核写入 `task_content_reviews`，保存 decision、quality score、signals、reasons、source、model id、rule/prompt version 和 degraded。Agent 不直接修改 `task_participations`，也不调用 FAN/NFT 服务。

### 3.5 HTTP 与前端约定

- 审核拒绝使用 HTTP `422`，`detail` 返回面向用户的原因。
- FastAPI 请求校验可能返回 `detail[]` 或 `errors[]`；前端 `apiErrorMessage()` 统一转换为多行文字。
- 发帖和回复期间显示 `GlobalProcessModal`。
- 成功或失败后必须释放 body scroll lock、`cursor-wait` 和全屏 pointer events。
- 错误统一使用 `GlobalInfoModal`；保留原页面背景，不使用背景模糊。

## 4. 粉丝 NFT 草稿 Agent

### 4.1 入口与工作流

```http
POST /api/v1/nft/creations/ai-draft
```

```text
prepare_brief
  → draft_metadata
  → generate_image
```

输入：

- `theme`
- `story`
- `visual_style`
- `preferred_name`
- `reference_notes`
- `reference_image_data_url`：可选 PNG/JPEG/WebP 参考图
- `generate_image`

输出：名称、描述、图片提示词、建议 attributes、可选 Base64 图片，以及 metadata/image source 和 degraded 状态。

### 4.2 图片模型

- 无参考图时调用图片生成接口。
- 有参考图时调用图片编辑接口，并使用 `input_fidelity=high`。
- 实际模型由 `OPENAI_IMAGE_MODEL` 决定，不复用 `OPENAI_MODEL`。
- 图片失败不影响 metadata 草稿；用户仍可上传自己的 NFT 图片。

### 4.3 前端确认边界

- “Agent 正在生成可编辑的 metadata 草稿与 NFT 图片…”显示在 AI 按钮正下方。
- 图片生成后必须由用户点击生成结果，才成为正式 NFT 图片。
- Agent 不填写或修改价格、发行数量和版权确认。
- Agent 不扣 FAN、不上传 Pinata、不创建 ERC-1155 token type，也不声称已经发布。

## 5. 模型配置

```dotenv
OPENAI_API_KEY=
OPENAI_BASE_URL=
OPENAI_MODEL=
OPENAI_FALLBACK_MODELS=
OPENAI_IMAGE_MODEL=gpt-image-2
OPENAI_IMAGE_SIZE=1024x1024
IMAGE_GENERATION_TIMEOUT_SECONDS=90
LLM_TEMPERATURE=0.2
LLM_MAX_TOKENS=1200
LLM_MAX_RETRIES=3
LLM_TOTAL_TIMEOUT_SECONDS=60
```

- `OPENAI_MODEL` / `OPENAI_FALLBACK_MODELS`：画像叙述、审核结构化输出和 metadata 文案。
- `OPENAI_IMAGE_MODEL`：NFT 图片生成或参考图编辑。
- `OPENAI_BASE_URL`：OpenAI 官方或兼容服务；必须确认服务支持所配置的文本和图片接口。
- `OPENAI_API_KEY` 不得提交到 Git，修改配置后必须重启后端。

## 6. 数据库与 V1 迁移

| 表 | 用途 |
| --- | --- |
| `fan_profile_runs` | 粉丝画像输入、输出和来源 |
| `task_content_reviews` | 社区/任务审核审计数据 |
| `task_nft_rewards` | 任务 NFT 奖励状态与幂等记录 |

新数据库使用：

```text
backend/alembic/versions/20260723_v1_baseline.py
```

V1 之前的 30 个迁移保存在 `backend/alembic/legacy_versions/`，只用于审计和已有数据库 adoption，不参与新 Railway 数据库的 `upgrade head`。部署说明见 [RAILWAY_DEPLOYMENT.md](./RAILWAY_DEPLOYMENT.md)。

## 7. 观测与排障

优先检查这些结构化日志：

- `content_review_llm_fallback`：文本模型失败，已退回规则审核。
- `fan_nft_metadata_draft_fallback`：metadata 模型失败，已退回规则草稿。
- `fan_nft_image_generation_failed`：图片生成或参考图编辑失败。
- `request_validation_failed`：请求体不符合 FastAPI schema，HTTP 422。
- `langfuse_callback_unavailable`：仅影响观测，不应阻断业务请求。

推荐顺序：确认 HTTP 状态与响应体 → 检查模型配置 → 检查 `source/degraded` → 检查数据库审核记录 → 最后检查 Pinata 或链上副作用。

## 8. 验证命令

```bash
cd backend
./.venv/bin/python -m pytest tests/test_content_review.py tests/test_community_tasks.py tests/test_nft.py -q
./.venv/bin/python -m pyright app/agents app/services/llm app/services/task_completion.py
./.venv/bin/python -m ruff check app/agents app/services/llm app/services/task_completion.py

cd ../frontend
npm run test:community
npm run test:api-error
npm run typecheck
```

## 9. 后续建议

- 建立固定 Quest 审核评测集，覆盖真实粉丝内容、缺 tag、灌水、跑题和可疑模板文本。
- 为模型调用增加成本、延迟和降级率看板。
- 将 `manual_review` 接入运营后台。
- 将任务 NFT 铸造改为后台队列，补齐重试、链重组对账和失败补偿。
