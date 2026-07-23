# Fanora Backend

Fanora 后端使用 FastAPI + LangGraph，负责统一身份接口、任务验证、积分与等级、粉丝画像、Badge 草案以及受控链上写入。

本模块已整合 `wassim249/fastapi-langgraph-agent-production-ready-template` 的生产基础能力，并将原模板的聊天机器人领域替换为 Fanora 粉丝身份领域。许可证说明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## 已整合能力

- 环境化 Pydantic Settings 配置。
- 结构化日志与请求关联 ID。
- SlowAPI 接口限流。
- Prometheus 指标和可选 Grafana 环境。
- Valkey/Redis 缓存，连接失败时降级到进程内缓存。
- SQLModel 异步数据库接口与 Alembic 迁移。
- 可选 PostgreSQL LangGraph checkpoint。
- OpenAI 及 OpenAI-compatible 第三方模型接口。
- 模型重试、fallback、总超时和结构化输出。
- Docker、Docker Compose、uv 和 GitHub Actions CI。

## 明确没有照搬

- 通用聊天机器人接口和聊天线程模型。
- 邮箱密码注册体系。
- Agent 会话自动命名。
- mem0 对话长期记忆。
- 让 LangGraph 参与后台权限和运营管理。

Fanora 的 LangGraph 接口只负责粉丝画像、身份评分解释、粉丝任务推荐和 Badge metadata 草案。积分、权限、任务发布、审计和合约交易仍由确定性业务模块控制。

## 项目结构

```text
app/
├── api/              # HTTP 路由
├── agents/           # Fanora LangGraph 工作流
├── adapters/         # Monad、Pinata 等外部系统 Adapter
├── core/             # 配置、数据库、缓存、日志、限流、指标
├── models/           # SQLModel 数据模型
├── repositories/     # 持久化 Interface 与实现
├── schemas/          # 结构化输入与输出
└── services/         # LLM 与统一身份 Interface
alembic/              # 数据库迁移
grafana/              # Grafana provisioning
prometheus/           # Prometheus 配置
```

## 本地启动

推荐 Python 3.13 和 uv：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
cp .env.example .env
make install
make migrate
make dev
```

访问：

- API 文档：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/api/v1/health`
- Prometheus 指标：`http://localhost:8000/metrics`

如果尚未配置模型 API，粉丝画像工作流会使用确定性规则结果，不影响启动和测试。

## Docker 启动

只启动本地 PostgreSQL，并继续用本机命令运行 FastAPI：

```bash
make db-up
make migrate
make dev
```

本地数据库连接地址为：

```env
DATABASE_URL=postgresql+psycopg://fanora:fanora-local-password@127.0.0.1:5432/fanora
```

推荐将该地址放在不会提交到 Git 的 `.env.local` 中。停止数据库使用 `make db-down`，查看状态使用 `make db-status`。删除 `.env.local` 后，后端会重新读取 `.env` 中的 Railway 或其他远程数据库连接。

启动包含 FastAPI、PostgreSQL 和 Valkey 的完整 Docker 开发环境：

```bash
cp .env.example .env
make docker-up
```

启动完整观测环境：

```bash
make stack-up
```

Grafana 使用 `http://localhost:3001`，避免与 Next.js 的 `3000` 端口冲突。

## Agent 接口

```http
POST /api/v1/agent/fan-profile/analyze
```

开发环境未配置 `INTERNAL_API_KEY` 时可以直接调用。生产环境必须配置，并通过 `X-Internal-API-Key` 请求头传递；后续统一身份登录完成后，这个临时保护会替换为用户会话权限。

示例请求：

```json
{
  "wallet_address": "0x0000000000000000000000000000000000000001",
  "community_id": "fanora",
  "fan_token_balance": 600,
  "completed_tasks": 8,
  "active_days": 15,
  "referrals": 2,
  "onchain_actions": 5
}
```

## 第三方模型 API

任何兼容 OpenAI Chat Completions 接口的服务都可以配置：

```env
OPENAI_API_KEY=your-key
OPENAI_BASE_URL=https://provider.example.com/v1
OPENAI_MODEL=provider/model-name
OPENAI_FALLBACK_MODELS=provider/fallback-model,provider/another-model
```

模型只能生成画像解释和 Badge 草案，不能直接修改积分、授予权限或调用合约。

## 钱包签名登录与用户资料

前端通过 RainbowKit 连接用户钱包，调用 `POST /api/v1/auth/challenge` 获取一次性消息并由当前钱包签名，再将 challenge、钱包地址和签名提交到 `POST /api/v1/auth/wallet`。后端校验签名、钱包地址、挑战有效期和一次性使用状态。

首次验证成功会自动创建统一用户、钱包登录身份、唯一主钱包、用户资料和 `fan` 角色；再次验证会恢复同一个用户。后端只保存钱包地址，不生成、索取或保存用户私钥。

登录后使用 Bearer Token 调用：

- `GET /api/v1/users/me`
- `PATCH /api/v1/users/me`
- `POST /api/v1/auth/logout`
- `POST /api/v1/communities/{community_id}/join`

无需登录即可调用 `GET /api/v1/membership-levels`，按 `rank` 返回所有启用的会员等级、Fan Token 门槛、管理身份标记和 Badge 图片地址，供首页成长模块读取。

### 批量上传会员等级图片到 Pinata

配置 `backend/.env` 中的 `PINATA_JWT` 后执行：

```bash
cd backend
PYTHONPATH=. .venv/bin/python scripts/pin_membership_levels.py
```

脚本默认跳过已经存在 `badge_image_cid` 的等级，并将成功上传后的 CID、Pinata 文件 ID 和图片内容哈希写回 `membership_levels`。图片更新后可使用 `--force` 重新上传全部等级：

```bash
PYTHONPATH=. .venv/bin/python scripts/pin_membership_levels.py --force
```

需要同时更新所有已铸造会员身份的链上图片时，追加 `--refresh-identities`。脚本会为每位会员生成新版 metadata，并调用 `FanoraMembershipIdentity.updateIdentityMetadata()` 更新原 Token ID；Owner、会员等级和 Token ID 均不会变化：

```bash
PYTHONPATH=. .venv/bin/python scripts/pin_membership_levels.py --force --refresh-identities
```

注册用户默认为待入会状态，不会对外显示神经萌新等级。配置付款合约后，用户可通过 `GET /api/v1/membership/me` 获取链上当前会费（默认 1 MON），并向 `POST /api/v1/membership/verify` 提交交易哈希。后端会验证 Monad 链 ID、交易成功状态、确认数、发送主钱包、付款合约和 `MembershipPaid` 事件金额，再写入 `official_membership_payments` 并激活 `user_profiles.is_official_member`。签到和任务接口应使用 `require_official_member` 依赖。

创作者社区创建和编辑接口要求数据库中已有 `creator` 或 `admin` 角色，普通用户不能自行提升权限。

## 会员等级与积分规则

会员等级和 Fan Token 规则保存在 `membership_levels` 与 `fan_token_rules` 表中。`membership_levels.badge_image_url` 保存前端可访问的 Badge 图片地址。普通会员按 Fan Token 余额自动升级：新生儿（0–99）、轻度神经（100–499）、中度神经（500–1,499）、重度神经（1,500–3,999）、病入膏肓（4,000–9,999）、无药可救（10,000+）。神经领袖属于管理员或版主管理身份，不通过 Token 自动获得。

Fan Token 规则包含注册、资料完善、每日签到、连续签到、内容互动、活动打卡、社区共创、邀请和链上行为，并为高价值操作设置每日/月度上限或人工审核。违规内容、刷屏骚扰、任务作弊通过负 Token 规则处理。PostgreSQL 触发器会在 `user_profiles.fan_token_balance` 变化时自动重新计算普通会员等级。

系统统一使用 `Fan Token`，符号为 `FAN`，视觉上使用 ETH 菱形图标。`user_profiles.fan_token_balance` 是可消费余额，`user_profiles.fan_token_lifetime_earned` 是只累计正向奖励的历史成长值，会员等级由历史成长值决定且只升不降；兑换、消费和负数调整只减少可用余额。规则变化量字段为 `fan_token_rules.token_delta`。Token 配置保存在 `fan_token_config` 表中；当前 `is_onchain=false`、精度为 0，表示它仍是可审计的站内 Token 单位，而不是真实 ETH 或已发行 ERC-20。未来发行链上 Token 时可补充 `chain_id` 和 `contract_address`。

### 删除测试用户

只允许在非生产环境运行。命令会按外键依赖顺序删除用户的会话、角色、资料、钱包、登录身份、登录挑战、画像运行记录和社区成员关系：

```bash
uv run python -m app.cli.delete_user \
  --user-id "要删除的 users.id" \
  --confirm "要删除的 users.id"
```

如果用户拥有社区，命令默认停止，避免连带删除其他用户的成员关系。确认这些也是测试数据时才显式级联：

```bash
uv run python -m app.cli.delete_user \
  --user-id "要删除的 users.id" \
  --confirm "要删除的 users.id" \
  --delete-owned-communities
```

该工具读取当前 `DATABASE_URL`，执行前务必确认连接的是测试数据库。
