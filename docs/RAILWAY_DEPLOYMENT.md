# Fanora Backend Railway 部署

> 适用范围：`backend/` Docker 服务、Railway PostgreSQL、新数据库从 Fanora V1 基线开始。

## 1. 部署结论

- Railway 使用 `backend/Dockerfile` 构建。
- 容器读取 Railway 注入的 `PORT`，本地默认 `8000`。
- 容器启动前执行 `alembic upgrade head`；迁移失败时 API 不会启动。
- Railway 的 `postgres://` 或 `postgresql://` 会自动规范为 `postgresql+psycopg://`。
- 健康检查为 `/api/v1/health`。
- 生产环境设置 `AUTO_CREATE_SCHEMA=false`，schema 只由 Alembic 管理。

## 2. Railway 服务配置

创建服务时将 Root Directory 设置为：

```text
backend
```

添加 Railway PostgreSQL，并让后端引用数据库变量：

```dotenv
DATABASE_URL=${{Postgres.DATABASE_URL}}
```

仓库中的 `backend/railway.toml` 已声明 Dockerfile、健康检查和失败重启策略。

## 3. 最低环境变量

```dotenv
ENVIRONMENT=production
DEBUG=false
AUTO_CREATE_SCHEMA=false
RUN_MIGRATIONS=true
FRONTEND_ORIGINS=https://your-frontend.example
INTERNAL_API_KEY=<至少 32 字节随机值>
DATABASE_URL=${{Postgres.DATABASE_URL}}

OPENAI_API_KEY=
OPENAI_BASE_URL=
OPENAI_MODEL=
OPENAI_FALLBACK_MODELS=
OPENAI_IMAGE_MODEL=gpt-image-2

CHAIN_WRITES_ENABLED=false
```

首次只验证 API、数据库和 Agent 降级时，建议保持 `CHAIN_WRITES_ENABLED=false`。启用真实 Monad 写入前，再配置合约地址、Pinata JWT 和最小权限运营钱包。

## 4. V1 Alembic 基线

新 Railway PostgreSQL 执行：

```bash
alembic upgrade head
```

当前 head：

```text
20260723_v1
```

V1 migration 创建最终 schema，并在 PostgreSQL 创建基于 `fan_token_lifetime_earned` 的会员等级触发器。应用启动后以幂等方式补齐官方社区、默认帖子、任务、会员等级和当前业务使用的 FAN 规则。

### 已有数据库采用 V1 标记

不要在未核对 schema 时直接 stamp。已有数据库必须先备份，并确认结构已经等价于旧 `20260723_0030`：

```bash
alembic stamp 20260723_v1
```

旧迁移保存在 `backend/alembic/legacy_versions/`。如果数据库尚未到旧 head，应先使用发布前代码完成旧迁移，再升级代码并 stamp V1。

## 5. 部署验证

```bash
curl -fsS https://<railway-domain>/api/v1/health
curl -fsS https://<railway-domain>/api/v1/membership-levels
```

预期：健康接口为 `healthy`，会员等级接口返回 7 个默认等级。Railway 日志应依次出现：

```text
Applying Fanora database migrations
database_initialized
```

## 6. 上线前安全检查

- 不提交数据库密码、OpenAI Key、Pinata JWT 或运营钱包私钥。
- `FRONTEND_ORIGINS` 只填写真实前端域名。
- 链上写入钱包按角色拆分，不复用合约部署管理员。
- 首次启用真实链上写入前，在 staging 完成发布、购买、任务 NFT 和失败重试验证。
