# 本地开发说明

## 前端

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

默认地址：`http://localhost:3000`。

Web3Auth 登录页：`http://localhost:3000/login`；用户资料页：`http://localhost:3000/profile`。前端业务请求统一通过 Axios 访问 `NEXT_PUBLIC_API_URL`。

Profile 的私钥导出只适用于 Web3Auth 嵌入式钱包。导出请求直接由浏览器调用钱包 Provider，不经过后端接口；开发和测试过程中禁止输出、截图或记录真实私钥。

## 后端

推荐 Python 3.13，并使用 uv 管理依赖。

```bash
cd backend
curl -LsSf https://astral.sh/uv/install.sh | sh
cp .env.example .env
make install
make migrate
make dev
```

健康检查：`http://localhost:8000/api/v1/health`。

本地联调推荐使用 Docker PostgreSQL，避免远程 Railway 数据库的网络延迟：

```bash
cd backend
make db-up
make migrate
make dev
```

项目使用被 Git 忽略的 `backend/.env.local` 覆盖远程配置：

```env
DATABASE_URL=postgresql+psycopg://fanora:fanora-local-password@127.0.0.1:5432/fanora
AUTO_CREATE_SCHEMA=false
```

停止数据库使用 `make db-down`。需要重新连接 Railway 时，删除或重命名 `.env.local` 即可恢复读取 `.env`。

认证和资料接口：

- `POST /api/v1/auth/challenge`：创建一次性钱包签名挑战。
- `POST /api/v1/auth/web3auth`：验证 Web3Auth 身份令牌和钱包签名，首次调用自动注册。
- `POST /api/v1/auth/logout`：撤销 Fanora 会话。
- `GET/PATCH /api/v1/users/me`：读取和维护当前用户资料。
- `GET /api/v1/communities`、`POST /api/v1/communities/{id}/join`：浏览和加入社区。

也可以使用 Docker 同时启动 FastAPI、PostgreSQL 和 Valkey：

```bash
make docker-up
```

## 合约

推荐 Node.js 20 或更高版本。

```bash
cd contracts
cp .env.example .env
npm install
npm run compile
npm test
```

准备好测试钱包私钥后再执行部署：

```bash
npm run deploy:testnet
```

私钥只能放在本地 `.env`，不能提交到代码仓库，也不能使用存有真实资产的主钱包。
