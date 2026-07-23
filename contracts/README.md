# Fanora Contracts

该模块存放 Fanora 在 Monad 上的三个正式 Solidity 合约：

- `FanoraMembershipGateway`：读取和收取动态正式会员会费，防止 paymentId 重放，托管并允许资金管理员提现。
- `FanoraMembershipIdentity`：不可转让 ERC-721 SBT；每个钱包最多一个会员身份，等级与会员证 metadata 更新时 tokenId 不变。
- `FanoraCollectibles`：ERC-1155 演唱会纪念卡、粉丝限量 NFT、自定义纪念徽章和任务限定 Badge，约束供应量、单钱包上限、时间窗、claimKey、转让策略和 metadata 冻结。

早期单 ERC-1155 `ProofOfFandomBadge` 原型已删除，不再作为当前架构。

## 常用命令

```bash
npm install
npm run compile
npm test
npm run release:testnet
```

当前 Hardhat 测试为 19 项。Monad Testnet 部署信息保存于 `deployments/monadTestnet.json`，同步后的公开 ABI 与地址位于 `../shared/contracts`。

## 权限

- Gateway：管理员、资金管理员与暂停角色。
- MembershipIdentity：管理员、铸造、等级、URI 与暂停角色。
- Collectibles：管理员、类型管理、铸造、URI 与暂停角色。

测试网可以暂时共用部署钱包，生产环境必须拆分最小权限账户，并将 `DEFAULT_ADMIN_ROLE` 迁移至多签或同等级安全钱包。任何部署或运营私钥都不得进入前端环境变量或 Git。
