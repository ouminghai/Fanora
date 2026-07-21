# Fanora 智能合约编译、发布与同步指南

本文适用于 Monad Testnet。发布脚本会部署三个合约、配置角色和会员等级、导出 ABI，并同步前后端运行参数。

## 1. 钱包职责

- `DEPLOYER_PRIVATE_KEY`：平台部署钱包私钥，只用于部署和初始化合约，不是用户私钥。
- `CONTRACT_ADMIN_ADDRESS`：合约最高管理员地址，正式环境建议使用多签钱包。
- `TREASURY_MANAGER_ADDRESS`：修改入会费、修改资金接收地址和提现的运营钱包。
- `IDENTITY_*_ADDRESS`：会员身份铸造、等级升级、metadata 和暂停角色。
- `COLLECTIBLE_*_ADDRESS`：收藏品类型、铸造、metadata 和暂停角色。
- `MEMBERSHIP_TREASURY_ADDRESS`：提现资金最终进入的钱包地址，不是私钥。

用户入会时始终由自己的 MetaMask 确认付款，平台不读取用户私钥。

## 2. contracts/.env 参数

```env
MONAD_RPC_URL=https://testnet-rpc.monad.xyz
MONAD_CHAIN_ID=10143
DEPLOYER_PRIVATE_KEY=0x...
MEMBERSHIP_FEE_WEI=1000000000000000000
MEMBERSHIP_LEVEL_RANKS=1,2,3,4,5,6,100
CONTRACT_ADMIN_ADDRESS=0x...
MEMBERSHIP_TREASURY_ADDRESS=0x...
TREASURY_MANAGER_ADDRESS=0x...
GATEWAY_PAUSER_ADDRESS=0x...
IDENTITY_MINTER_ADDRESS=0x...
IDENTITY_LEVEL_MANAGER_ADDRESS=0x...
IDENTITY_URI_MANAGER_ADDRESS=0x...
IDENTITY_PAUSER_ADDRESS=0x...
COLLECTIBLE_TYPE_MANAGER_ADDRESS=0x...
COLLECTIBLE_MINTER_ADDRESS=0x...
COLLECTIBLE_URI_MANAGER_ADDRESS=0x...
COLLECTIBLE_PAUSER_ADDRESS=0x...
```

`MEMBERSHIP_FEE_WEI` 默认是 1 MON。`MEMBERSHIP_LEVEL_RANKS` 必须与数据库 `membership_levels.rank` 对应，当前普通等级为 1–6，管理等级为 100。

测试阶段可以让所有角色地址都使用部署钱包。正式环境建议将管理员、资金管理、铸造和暂停权限拆分到不同钱包。

如果角色地址与部署钱包不同，发布脚本只能配置角色地址，不能获得该钱包私钥。对应运营私钥需要由管理员单独写入 `backend/.env`。

## 3. 一键发布

在 `contracts` 目录执行：

```bash
npm run release:testnet
```

命令依次执行：

1. 运行全部合约测试。
2. 编译 Solidity 并导出 ABI 到 `shared/contracts`。
3. 部署 Gateway、MembershipIdentity 和 Collectibles。
4. 设置当前入会费和等级 `rank`。
5. 分配管理员、资金、铸造、metadata 和暂停角色。
6. 将地址、起始区块和可复用的平台运营私钥同步到前后端环境文件。
7. 重新读取链上 bytecode、会费、等级和角色，确认发布完整。

发布结果保存在：

```text
contracts/deployments/monadTestnet.json
shared/contracts/monadTestnet.deployment.json
```

部署文件只包含公开地址、交易哈希、区块和角色，不包含私钥。

## 4. 自动同步内容

`backend/.env` 会更新：

```env
MEMBERSHIP_TREASURY_ADDRESS=...
MEMBERSHIP_FEE_WEI=...
MEMBERSHIP_PAYMENT_CONTRACT_ADDRESS=...
MEMBERSHIP_IDENTITY_CONTRACT_ADDRESS=...
COLLECTIBLES_CONTRACT_ADDRESS=...
MEMBERSHIP_IDENTITY_START_BLOCK=...
COLLECTIBLES_START_BLOCK=...
```

当运营角色地址等于部署钱包时，还会同步对应的平台运营私钥：

```env
MEMBERSHIP_TREASURY_MANAGER_PRIVATE_KEY=...
IDENTITY_MINTER_PRIVATE_KEY=...
IDENTITY_LEVEL_MANAGER_PRIVATE_KEY=...
IDENTITY_URI_MANAGER_PRIVATE_KEY=...
COLLECTIBLE_TYPE_MANAGER_PRIVATE_KEY=...
COLLECTIBLE_MINTER_PRIVATE_KEY=...
COLLECTIBLE_URI_MANAGER_PRIVATE_KEY=...
```

`frontend/.env` 或 `frontend/.env.local` 会更新三个 `NEXT_PUBLIC_*_CONTRACT_ADDRESS_MONAD_TESTNET` 地址。

## 5. 分步执行

```bash
npm run compile          # 编译并导出 ABI
npm run deploy:testnet   # 只部署和初始化
npm run sync:testnet     # 使用部署文件重新同步前后端
npm run verify:testnet   # 重新验证链上代码、会费、等级和角色
```

同步完成后需要重启 FastAPI。Next.js 修改环境变量后也应重启，浏览器才能使用新地址。

## 6. 发布后检查

- `/api/v1/membership/me` 返回 Gateway 当前链上会费和合约地址。
- 用户通过 MetaMask 调用 `join(paymentId)`，金额必须等于 `membershipFee`。
- 入会验证成功后，后端运营钱包调用 `mintIdentity()`。
- 用户积分达到更高等级并主动申领时，后端调用 `updateMembershipLevel()`。
- 管理员通过 `PUT /api/v1/membership/admin/fee` 修改后续入会费。
- 管理员通过 `/api/v1/membership/admin/treasury` 查看或提取 Gateway 余额。
