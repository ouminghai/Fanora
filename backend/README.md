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
├── adapters/         # 后续外部系统 Adapter
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
- 健康检查：`http://localhost:8000/health`
- Prometheus 指标：`http://localhost:8000/metrics`

如果尚未配置模型 API，粉丝画像工作流会使用确定性规则结果，不影响启动和测试。

## Docker 启动

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
  "points": 600,
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
