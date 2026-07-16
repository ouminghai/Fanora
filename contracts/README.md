# Fanora Contracts

该模块存放 Monad 上的 Solidity 合约。第一版使用 ERC-1155 表达多个 Badge 等级，并禁止用户之间转让，使其具备 SBT 身份凭证特征。

## 权限

- `DEFAULT_ADMIN_ROLE`：管理其他角色，建议部署后交给安全钱包。
- `MINTER_ROLE`：后端运营账户验证任务后铸造或升级 Badge。
- `URI_MANAGER_ROLE`：更新 metadata 基础地址。

管理员和部署私钥永远不能放进前端环境变量。

