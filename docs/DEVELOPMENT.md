# 本地开发说明

## 前端

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

默认地址：`http://localhost:3000`。

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

也可以使用 Docker 启动 FastAPI、PostgreSQL 和 Valkey：

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
