# Fanora Vercel + Railway 部署指南

> 适用范围：`frontend/` 部署到 Vercel，`backend/` 部署到 Railway，数据库使用 Railway PostgreSQL。

## 1. 部署顺序

1. 先部署 Railway 后端，拿到后端公网域名。
2. 再部署 Vercel 前端，把 `NEXT_PUBLIC_API_URL` 指向 Railway。
3. 回到 Railway，把 Vercel 正式域名加入 `FRONTEND_ORIGINS`。
4. 验证健康检查、钱包登录、会员等级、任务和 NFT 图片展示。

这样做的原因是前端构建时需要固定的后端 API 地址，而后端 CORS 也需要知道正式前端域名。

## 2. Railway 后端

### 2.1 创建服务

在 Railway 新建 Project 后，从 GitHub 导入当前仓库。

服务配置：

```text
Root Directory: backend
Builder: Dockerfile
Dockerfile Path: Dockerfile
Healthcheck Path: /api/v1/health
```

仓库内 `backend/railway.toml` 已经声明 Dockerfile、健康检查和失败重启策略。Railway 会注入 `PORT`，容器入口脚本会自动让 Uvicorn 使用该端口。

### 2.2 添加 PostgreSQL

在同一个 Railway Project 中添加 PostgreSQL，然后给后端服务设置：

```dotenv
DATABASE_URL=${{Postgres.DATABASE_URL}}
```

后端会自动把 Railway 常见的 `postgres://` 或 `postgresql://` 规范为 SQLAlchemy async driver 使用的 `postgresql+psycopg://`。

### 2.3 后端最低环境变量

```dotenv
ENVIRONMENT=production
DEBUG=false
AUTO_CREATE_SCHEMA=false
RUN_MIGRATIONS=true
MIGRATION_MAX_ATTEMPTS=12
MIGRATION_RETRY_DELAY_SECONDS=5
DATABASE_URL=${{Postgres.DATABASE_URL}}
INTERNAL_API_KEY=<用 openssl rand -hex 32 生成>

# 第一次部署时可以先填本地或临时域名，Vercel 正式域名出来后再替换
FRONTEND_ORIGINS=http://localhost:3000
FRONTEND_ORIGIN_REGEX=

# AI 能力；不填时部分 Agent 会降级，不影响 API 启动
OPENAI_API_KEY=
OPENAI_BASE_URL=
OPENAI_MODEL=
OPENAI_FALLBACK_MODELS=
OPENAI_IMAGE_MODEL=gpt-image-2

# 首次上线建议先关闭真实链上写入，验证基础流程后再打开
CHAIN_WRITES_ENABLED=false
MONAD_RPC_URL=https://testnet-rpc.monad.xyz
MONAD_CHAIN_ID=10143
MEMBERSHIP_PAYMENT_CONTRACT_ADDRESS=
MEMBERSHIP_IDENTITY_CONTRACT_ADDRESS=
COLLECTIBLES_CONTRACT_ADDRESS=
PINATA_JWT=
```

启用真实链上写入前，再补齐合约地址、Pinata JWT 和各角色运营钱包私钥。

### 2.4 后端验证

部署成功后访问：

```bash
curl -fsS https://<railway-domain>/api/v1/health
curl -fsS https://<railway-domain>/api/v1/membership-levels
```

健康接口应返回 `healthy`，会员等级接口应返回默认等级数据。Railway 日志中应看到迁移和数据库初始化完成。

## 3. Vercel 前端

### 3.1 创建项目

在 Vercel 导入同一个 GitHub 仓库。

项目配置：

```text
Framework Preset: Next.js
Root Directory: frontend
Install Command: npm ci
Build Command: npm run build
Output Directory: .next
Node.js: 20.x 或更新的 LTS
```

仓库内 `frontend/vercel.json` 已声明 Next.js、`npm ci` 和构建命令；`frontend/package.json` 也声明了 Node 20.11+。

### 3.2 前端环境变量

在 Vercel Project Settings -> Environment Variables 中配置：

```dotenv
NEXT_PUBLIC_APP_NAME=Fanora Protocol
NEXT_PUBLIC_APP_URL=https://<vercel-production-domain>
NEXT_PUBLIC_API_URL=https://<railway-domain>/api/v1
NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=<WalletConnect Cloud Project ID>

NEXT_PUBLIC_MONAD_TESTNET_RPC_URL=https://testnet-rpc.monad.xyz
NEXT_PUBLIC_MONAD_RPC_URL=https://rpc.monad.xyz
NEXT_PUBLIC_MEMBERSHIP_PAYMENT_CONTRACT_ADDRESS_MONAD_TESTNET=<Gateway 合约地址>
NEXT_PUBLIC_MEMBERSHIP_IDENTITY_CONTRACT_ADDRESS_MONAD_TESTNET=<Identity 合约地址>
NEXT_PUBLIC_COLLECTIBLES_CONTRACT_ADDRESS_MONAD_TESTNET=<Collectibles 合约地址>
```

所有 `NEXT_PUBLIC_` 变量都会进入浏览器，只能放公开配置，不能放私钥、服务端 Key、Pinata JWT 或数据库地址。

### 3.3 Vercel 构建验证

本地先在 `frontend/` 运行：

```bash
npm ci
npm run typecheck
npm run build
```

Vercel 首次部署成功后，打开正式域名检查首页、钱包按钮和需要后端数据的模块。

## 4. 回填 CORS

拿到 Vercel 正式域名后，回到 Railway 后端服务，把 CORS 改为正式域名：

```dotenv
FRONTEND_ORIGINS=https://<vercel-production-domain>
```

如果需要 Vercel Preview Deployments 也能访问后端，可以额外配置正则：

```dotenv
FRONTEND_ORIGIN_REGEX=https://fanora-git-.*-<vercel-team-or-user>\.vercel\.app
```

生产主域名仍放在 `FRONTEND_ORIGINS` 中，preview 域名再用 `FRONTEND_ORIGIN_REGEX` 放行。

## 5. 上线检查清单

- Railway `/api/v1/health` 返回 `healthy`。
- Vercel 的 `NEXT_PUBLIC_API_URL` 以 `/api/v1` 结尾，且没有多余斜杠。
- Railway 的 `FRONTEND_ORIGINS` 包含 Vercel 正式域名。
- Vercel 构建日志没有 TypeScript、ESLint 或图片域名错误。
- 浏览器 Network 中没有 CORS 错误。
- 钱包登录可以完成 challenge、签名和会话恢复。
- 会员等级、社区任务、个人主页和 NFT 图片可以正常加载。
- 真实链上写入开启前，确认合约地址、Pinata JWT、运营钱包私钥和测试网 RPC 都已配置。

## 6. 常见问题

### 前端请求被 CORS 拦截

确认 Railway：

```dotenv
FRONTEND_ORIGINS=https://<当前打开的 Vercel 域名>
```

如果打开的是 Vercel preview 域名，还需要配置 `FRONTEND_ORIGIN_REGEX` 或把该 preview 域名临时加入 `FRONTEND_ORIGINS`。

### Vercel 页面调用了 localhost

确认 Vercel 中配置了：

```dotenv
NEXT_PUBLIC_API_URL=https://<railway-domain>/api/v1
```

修改环境变量后需要重新部署一次前端。

### Railway 启动后数据库不健康

确认后端服务已经绑定 PostgreSQL，并且：

```dotenv
DATABASE_URL=${{Postgres.DATABASE_URL}}
AUTO_CREATE_SCHEMA=false
RUN_MIGRATIONS=true
```

查看 Railway 日志中 `Applying Fanora database migrations` 后面的 Alembic 错误。

### 图片在 Vercel 上不显示

当前已允许 `gateway.pinata.cloud`、`*.mypinata.cloud` 和 `ipfs.io` 的 `/ipfs/**` 图片。若后端改用新的 CDN 或自定义网关，需要同步加入 `frontend/next.config.mjs` 的 `images.remotePatterns`。

## 7. 官方文档入口

- Vercel Project Configuration: https://vercel.com/docs/project-configuration
- Vercel Environment Variables: https://vercel.com/docs/environment-variables
- Railway Configuration as Code: https://docs.railway.com/reference/config-as-code
- Railway Variables: https://docs.railway.com/reference/variables
