# Fanora 阶段开发汇总与 Week 3 角色

> 更新日期：2026-07-17
> 当前结论：已经完成可运行的技术骨架和产品展示 Demo，但“登录 → 任务 → 积分 → Agent 画像 → Monad Badge”端到端 MVP 尚未打通。

## 1. 我想做什么

Fanora 是一个 AI Agent 驱动的 Web3 粉丝身份与互动协议。我希望把粉丝的签到、活动参与、内容贡献和链上行为转化为可解释的身份积分与粉丝画像，并最终在 Monad 上铸造成不可转让、可公开验证的 Proof of Fandom Badge。

目标闭环是：

```text
快捷登录或钱包登录
  → 参与并完成粉丝任务
  → 后端验证并发放积分
  → LangGraph 更新粉丝画像
  → 确定性规则判断 Badge 资格
  → Monad 铸造或升级不可转让 Badge
```

项目采用 Next.js 前端、FastAPI + LangGraph 后端、PostgreSQL/Supabase 数据层，以及 Solidity + Hardhat 合约。AI 只负责画像分析、解释、推荐和 Badge 草案，不直接修改积分、授予权限或控制合约私钥。

## 2. 我实际做到了哪一步

### 总体进度

| 模块 | 当前状态 | 已完成 | 尚未完成 |
| --- | --- | --- | --- |
| Dev Plan | 已完成 | PRD、技术架构、MVP 路线、本地开发说明、Agent 权限边界和钱包身份方案 | 根据联调结果持续细化接口与验收项 |
| 前端 Demo | 可运行 | 将原 NFT 模板收敛为 Fanora 单主页；展示 Eason Fans Club、任务、积分、粉丝画像和 Badge 等级；保留 RainbowKit/wagmi/viem 钱包基础 | 页面数据仍以静态 Demo 为主；加入社区、任务和积分操作尚未连接后端 |
| 后端 | 可运行的基础版本 | FastAPI、LangGraph 画像工作流、确定性评分降级、结构化输出、健康检查、配置、日志、限流、指标、缓存、数据库模型和 Alembic 迁移 | 登录、任务、积分、等级、画像持久化、链上写入等业务服务尚未形成完整闭环 |
| 智能合约 | 本地可编译测试 | ERC-1155 Badge、角色权限、铸造、升级、URI 更新和禁止用户转让 | 尚未部署 Monad Testnet；升级、越权、重复铸造等测试覆盖仍需补齐 |
| 前后端与链上联调 | 未完成 | 已预留 API、合约地址、ABI 和 Badge 查询 Hook | 尚无真实任务数据、真实用户会话、测试网合约地址和完整铸造交易证据 |

### 代码与 Demo 入口

- 前端主页：`frontend/app/page.tsx`，本地访问 `http://localhost:3000`。
- Fanora 展示数据：`frontend/data/fanora.ts`。
- 钱包与 Badge 读取基础：`frontend/components/web3/WalletButton.tsx`、`frontend/hooks/useBadgeBalance.ts`。
- 后端入口：`backend/app/main.py`，API 文档位于 `http://localhost:8000/docs`。
- 粉丝画像 Agent：`backend/app/agents/fan_profile.py`。
- Agent API：`POST /api/v1/agent/fan-profile/analyze`。
- Badge 合约：`contracts/contracts/ProofOfFandomBadge.sol`。

### README 与开发文档

- `README.md`：项目定位、目录结构与推荐启动顺序。
- `docs/PRODUCT_REQUIREMENTS.md`：带编号和验收标准的产品/开发需求。
- `docs/ARCHITECTURE.md`：前端、后端、Agent、数据库和合约架构。
- `docs/MVP_ROADMAP.md`：最小闭环、Proof of Fandom 和创作者能力的开发顺序。
- `docs/DEVELOPMENT.md`：前端、后端和合约本地启动方式。
- `frontend/README.md`、`backend/README.md`、`contracts/README.md`：各模块说明。

### 运行证据（2026-07-17 本地复验）

| 验证项 | 结果 | 证据摘要 |
| --- | --- | --- |
| 前端 lint | 通过 | `eslint .` 无报错 |
| 前端类型检查 | 通过 | `tsc --noEmit` 无报错 |
| 前端生产构建 | 通过 | Next.js 15.5.20 编译成功；`/`、`/home-4`、`/_not-found` 生成成功 |
| 后端 lint | 通过 | Ruff：`All checks passed!` |
| 后端类型检查 | 通过 | Pyright：`0 errors, 0 warnings` |
| 后端测试 | 通过 | Pytest：`6 passed`；存在 1 条 Starlette TestClient 弃用提示 |
| 后端健康接口 | 通过 | SQLite Demo 环境返回 `status: healthy`，数据库 healthy，Agent ready |
| Agent 分析接口 | 通过 | 示例输入返回总分 `91/100`、`core_contributor`、规则降级来源和 Badge 草案 |
| 合约编译 | 通过 | Hardhat：无需重新编译且无错误 |
| 合约测试 | 通过 | `2 passing`：授权铸造成功、用户间转让被 Soulbound 规则拒绝 |

Agent 运行示例的核心返回：

```json
{
  "scores": { "total": 91 },
  "fan_type": "core_contributor",
  "analysis_source": "rules",
  "badge_eligible": true,
  "badge_draft": { "name": "Core Contributor Badge" }
}
```

这证明 Agent API 和规则降级路径已经可运行，但不代表 Badge 已经上链。

### AI Collaboration Log

| 时间 | AI 协作内容 | 人工负责的判断与验证 |
| --- | --- | --- |
| 2026-07-16 | 将项目想法拆成 PRD、技术架构、MVP 路线和模块边界 | 确认产品目标、技术选型、优先级与暂不开发范围 |
| 2026-07-16 | 辅助收窄 LangGraph 范围，补充创作者后台和权限边界 | 决定 Agent 不参与积分、权限、审批和链上交易管理 |
| 2026-07-17 | 辅助设计“无感登录但钱包必备”的统一身份方案 | 确认嵌入式钱包与外部钱包双入口，以及主钱包约束 |
| 2026-07-17 | 辅助将生产型 FastAPI/LangGraph 模板适配到 Fanora 领域，并补充配置、测试和迁移可靠性 | 审核保留/移除的模板能力，运行测试并处理本地环境问题 |
| 2026-07-17 | 辅助清理前端模板、替换 Fanora Demo 内容，并汇总阶段证据 | 选择主页方案、确认产品表达，并执行 lint、类型检查、构建、API 与合约复验 |

AI 主要用于需求拆解、架构讨论、代码草拟、模板改造、测试补充和文档整理。最终范围判断、环境配置、运行验证和是否达到验收标准仍由开发者负责；未获得的测试网部署证据不会被写成已完成。

### Known Issues

1. 当前没有端到端业务闭环：前端任务和积分仍是静态展示，未连接真实后端服务。
2. 登录只有数据模型和统一接口设计，嵌入式钱包登录、nonce 签名登录和会话管理尚未实现。
3. Agent 已能评分与生成解释/Badge 草案，但分析结果尚未写入 `fan_profile_runs`，也未由真实任务事件触发。
4. 合约尚未部署到 Monad Testnet，前端合约地址为空，因此没有真实 Badge 余额与区块浏览器证据。
5. 合约测试目前只覆盖授权铸造和不可转让；升级、URI 权限、越权调用、重复铸造和边界条件需要补测。
6. WalletConnect Project ID、模型 API、数据库和运营钱包等外部配置仍需按环境提供。
7. 本机直接执行 `make check` 需要先把 `uv` 安装到 shell PATH；本次使用项目 `.venv` 完成了等价的 Ruff、Pyright 和 Pytest 验证。
8. 若本地 `DATABASE_URL` 指向未启动或不可达的 PostgreSQL，健康检查会等待连接超时；SQLite Demo 环境已验证可正常运行。

## 3. Week 3 我能继续承担什么开发角色

### 主要角色：AI Agent + Backend Integration Developer

我可以继续负责把当前技术骨架推进为可演示的最小闭环，重点承担：

- 实现统一身份与钱包绑定接口，先跑通一种快捷登录或外部钱包签名登录。
- 实现最小任务、领取/提交、幂等验证、积分流水和等级计算接口。
- 将任务与积分数据接入 LangGraph 粉丝画像，并持久化每次分析结果。
- 连接前端任务、积分、画像与 Badge 页面，替换静态 Demo 数据。
- 补齐合约升级和权限测试，协助完成 Monad Testnet 部署与地址同步。
- 维护 API 契约、自动化测试、README、运行证据和 Known Issues。

如果团队按角色拆分，我适合主责后端与 Agent 集成，同时承担前后端联调和合约接入；合约安全审计、产品视觉精修和外部钱包供应商接入可与对应成员协作完成。

### Week 3 建议交付目标

Week 3 不追求一次完成全部需求，优先交付一条真实可演示链路：

```text
测试用户进入 Fanora
  → 完成一个签到任务
  → 后端幂等发放积分
  → Agent 更新并保存粉丝画像
  → 前端展示最新积分与画像
  → 达到阈值后生成 Badge 资格记录
```

若测试网部署条件准备完成，再把最后一步扩展为真实 Monad Badge 铸造；否则明确保留为下一阶段，不用模拟交易冒充上链结果。
