# Fanora 文档中心

> 更新日期：2026-07-23
> 当前产品基线：v1.7，钱包登录 + 官方社区 + Agent 审核/画像/NFT 草稿 + 全局 FAN/终身等级 + ERC-721 会员证 + ERC-1155 粉丝 NFT + Pinata + Monad Testnet

## 1. 文档层级

| 文档 | 定位 | 是否作为当前基线 |
| --- | --- | --- |
| [PRODUCT_REQUIREMENTS.md](./PRODUCT_REQUIREMENTS.md) | 产品范围、编号需求、验收标准和 MVP 完成定义 | 是，需求事实源 |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 系统边界、数据归属、三合约、Pinata、部署和安全设计 | 是，技术架构事实源 |
| [AI_AGENTS.md](./AI_AGENTS.md) | LangGraph Agent 代码入口、职责边界、模型配置、数据表和验证命令 | 是，Agent 工程说明 |
| [MVP_ROADMAP.md](./MVP_ROADMAP.md) | 按依赖关系排列的实施阶段、交付物和退出条件 | 是，执行顺序基线 |
| [DEVELOPMENT.md](./DEVELOPMENT.md) | 当前代码可执行的本地启动、测试和配置说明 | 是，开发操作基线 |
| [CONTRACT_DEPLOYMENT.md](./CONTRACT_DEPLOYMENT.md) | Monad 合约编译、发布、角色配置和前后端参数同步 | 是，合约发布操作指南 |
| [RAILWAY_DEPLOYMENT.md](./RAILWAY_DEPLOYMENT.md) | Railway Docker、PostgreSQL、V1 Alembic 基线和上线检查 | 是，后端云部署指南 |
| [week3/README.md](./week3/README.md) | Week 3 初步版本交付、运行方式、真实功能、Mock 范围和问题清单 | 是，团队演示入口 |
| [week3/DEMO_GUIDE.md](./week3/DEMO_GUIDE.md) | 钱包、社区、会员证与 NFT 市场的演示脚本 | 是，演示操作指南 |
| [DELIVERY_SUMMARY_2026-07-23.md](./DELIVERY_SUMMARY_2026-07-23.md) | 钱包登录、终身等级、会员证与粉丝 NFT 市场的当前交付证据 | 是，当前交付证据 |
| [DELIVERY_SUMMARY_2026-07-21.md](./DELIVERY_SUMMARY_2026-07-21.md) | 社区、Fan Token、NFT、合约与 Testnet 发布完成摘要 | 否，历史快照 |
| [WEEK2_DELIVERY_SUMMARY.md](./WEEK2_DELIVERY_SUMMARY.md) | 2026-07-17 阶段交付证据和当时的 Known Issues | 否，历史快照 |

如果文档内容发生冲突，按以下优先级处理：

```text
PRODUCT_REQUIREMENTS
  → ARCHITECTURE
  → MVP_ROADMAP
  → DEVELOPMENT
  → 历史阶段总结
```

## 2. 当前核心架构决策

1. Fanora MVP 只运营一个固定的官方社区；不建设社区创建、列表搜索、独立积分/任务/等级/Badge 或多管理员体系。
2. Fanora 正式会员的核心身份使用不可转让 ERC-721，一个主钱包最多一个有效身份 token。
3. 每个用户只有一个全局 Fan Token 余额和一套全局等级阈值；积分达到阈值时更新同一个 ERC-721 token 的等级与 metadata，tokenId 不变。
4. 演唱会纪念卡、粉丝限量 NFT、自定义纪念徽章和任务限定 Badge 使用 ERC-1155。
5. ERC-1155 token 类型在链上约束类别、最大供应量、单钱包上限、领取时间窗、转让策略和 metadata 冻结状态。
6. NFT 图片与 metadata 由后端上传至 Pinata IPFS Platform，合约保存 `ipfs://CID`。
7. 正式会员发布粉丝限量 NFT 时由后端校验图片、FAN 余额、定价和供应量，随后直接固定图片与 metadata 到 Pinata；该市场流程不经过管理员审核。
8. LangGraph 只负责粉丝画像、解释、推荐和 ERC-1155 metadata 草案，不修改积分、不决定 ERC-721 等级、不持有合约权限。
9. 早期 `ProofOfFandomBadge.sol` 原型已删除，付款 Gateway、ERC-721 身份和 ERC-1155 纪念资产已部署至 Monad Testnet。
10. 当前测试网所有运营角色暂时共用部署钱包；正式环境必须拆分最小权限账户并将管理员迁移至多签。

## 3. 推荐阅读路径

### 产品或答辩

1. `PRODUCT_REQUIREMENTS.md` 的产品目标、核心闭环和 MVP 完成定义。
2. `ARCHITECTURE.md` 的系统图、数据归属和核心业务流。
3. `MVP_ROADMAP.md` 的实施阶段和风险控制。

### 开发实现

1. `DELIVERY_SUMMARY_2026-07-23.md` 了解当前已经交付的完整范围与剩余工作。
2. `DEVELOPMENT.md` 启动当前前端、后端、PostgreSQL 和正式合约。
3. `AI_AGENTS.md` 查看 LangGraph Agent 职责、模型配置和测试入口。
4. `PRODUCT_REQUIREMENTS.md` 查找需求编号与验收条件。
5. `ARCHITECTURE.md` 确认模块边界、数据库事实源、Pinata 和链上写入约束。
6. `CONTRACT_DEPLOYMENT.md` 执行测试网发布与三端配置同步。
7. `RAILWAY_DEPLOYMENT.md` 部署后端与 PostgreSQL。

### 了解历史进度

阅读 `WEEK2_DELIVERY_SUMMARY.md`，但其中的单 ERC-1155 身份方案和 2026-07-17 完成度只代表当时状态。

## 4. 文档维护规则

- 新功能先在 `PRODUCT_REQUIREMENTS.md` 增加唯一需求编号和验收标准，再更新架构与路线图。
- 已完成状态必须有代码、测试、部署或人工验收证据；不能仅因文档写完就标记 `[x]`。
- 当前实现与目标架构不同步时，必须分别写明“当前原型”和“目标方案”。
- 合约、数据库或 API 命名变化时，同时检查前端、后端、部署变量和开发说明。
- 阶段总结属于历史证据，不回写成当前事实；新的阶段证据应新增日期明确的总结。
- 不在文档中记录私钥、Pinata JWT、数据库密码、真实导出密钥或其他敏感值。
