# Fanora Backend

Python 后端负责钱包登录、任务验证、积分与等级、粉丝画像 Agent，以及受控的合约写入。

当前骨架只提供健康检查和 Agent 工作流示例。建议按 MVP 顺序逐步增加功能，不要一次建立全部数据表和接口。

LangGraph 的接口范围仅包含粉丝画像、身份评分解释、粉丝任务推荐和 Badge metadata 草案。角色管理、任务发布、积分修改、审计与链上交易管理由确定性业务模块完成，不交给 Agent。

```text
app/
├── api/            # HTTP 接口
├── agents/         # LangGraph 工作流
├── adapters/       # 区块链、社交平台、外部模型适配器
├── core/           # 配置和基础设施
├── models/         # 数据库模型
├── repositories/   # 数据持久化接口与实现
├── schemas/        # 请求和响应结构
└── services/       # 任务、积分、身份等业务模块
```
