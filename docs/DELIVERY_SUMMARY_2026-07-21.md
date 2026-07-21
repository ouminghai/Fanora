# Fanora 2026-07-21 交付总结

本次交付完成了社区体验、Fan Token 成长规则、Web3Auth/MetaMask 入会、会员身份与纪念资产合约、Pinata/NFT 后端编排，以及 Monad Testnet 发布与三端配置同步。

## 1. 用户与社区体验

- Web3Auth Modal 统一登录流程，支持 MetaMask 外部钱包和 Web3Auth 嵌入式身份。
- 入会付款只允许由当前登录主钱包通过 MetaMask 确认，前后端不读取用户私钥。
- 社区首页、任务中心和创作墙完成布局与动画调整，首页热门帖子和热门任务改为后端动态数据。
- 创作支持 Markdown、多图上传和 Swiper 浏览；评论支持文字、图片、两层回复、分页加载和 PhotoSwipe 大图预览。
- `content_publish` 任务领取后，发布内容自动注入以任务标题生成的 `#tag`，不再额外展示发布 Badge。
- 创作墙按每页 25 条进行接近底部加载，评论每次加载 10 条并支持“更多评论”。

## 2. Fan Token 与会员成长

- 发布帖子奖励 5 FAN，首次有效回复和首次点赞各奖励 1 FAN。
- 帖子被不同用户首次收藏时，作者获得 1 FAN，每篇最多奖励前 10 个有效收藏。
- 每日签到增加月历、连续签到、今日奖励和月度累计展示。
- Fan Token 流水使用幂等键，重复请求不会重复发放奖励。
- 普通会员等级由 `membership_levels` 的余额区间确定，数据库等级变化后可由用户主动同步链上身份。
- 生成并入库 50 条陈奕迅粉丝吸引力创作内容，图片来自本地 `resources` 目录。

## 3. 智能合约

早期 `ProofOfFandomBadge.sol` 已删除，当前使用三个正式合约：

- `FanoraMembershipGateway`：当前会费精确校验、付款 ID/钱包防重、资金托管、管理员改价与提现。
- `FanoraMembershipIdentity`：不可转移 ERC-721 SBT，一个钱包一个有效身份，等级升级保持 tokenId 不变。
- `FanoraCollectibles`：ERC-1155 多类型纪念资产，支持供应量、钱包限额、时间窗、领取键、转移策略和 metadata 冻结。

合约测试共 16 项，覆盖权限、重复付款、提现、会费修改、SBT 转移阻止、升级防降级、供应限制、claimKey、暂停、metadata 冻结和恶意 receiver 回调。

## 4. 后端链上与 Pinata 编排

- 新增 Monad 适配器，统一处理运营钱包签名、合约调用、交易确认和事件参数。
- 新增 Pinata 适配器，支持图片与 metadata 上传、有限重试、CID 和 Gateway URL。
- 会员付款后自动创建初始身份；后续等级达到条件后由用户主动申领升级。
- 身份图片读取 `membership_levels.badge_image_url`，图片与每个版本的 metadata 分别固定到 IPFS。
- 新增 metadata 版本、链上操作、身份 NFT、收藏品类型、持有记录和自定义 NFT 申请数据模型。
- 新增统一收藏接口、身份同步、自定义徽章申请/审核/处理，以及管理员会费和资金提现接口。
- 平台运营私钥仅存在后端环境，不进入前端、部署清单或接口响应。

## 5. Monad Testnet 部署

| 合约 | 地址 | 起始区块 |
| --- | --- | ---: |
| `FanoraMembershipGateway` | `0xd966Fb616cBFd6c54d317Fc1d87344455e1F7A93` | 46839663 |
| `FanoraMembershipIdentity` | `0x14bE25042ac73Eb984aa60b8f0b49D78c79FcfEf` | 46839671 |
| `FanoraCollectibles` | `0xb8Eea4B312c58E6Cb1d142c8705fF766F03eD19f` | 46839678 |

- Chain ID：`10143`
- 当前入会费：`1 MON`，可由 `TREASURY_MANAGER_ROLE` 修改。
- 已配置身份等级 rank：`1, 2, 3, 4, 5, 6, 100`。
- 部署清单：`contracts/deployments/monadTestnet.json`。
- 一键命令：`npm run release:testnet`，自动测试、编译、部署、导出 ABI、同步环境变量并复核链上状态。

## 6. 验证证据

- Solidity 编译成功，Hardhat：`16 passing`。
- 前端 TypeScript 检查和会员专项测试通过。
- 后端 Ruff 检查通过，NFT/会员专项测试代码已补充。
- 前端 `http://localhost:3000` 和后端 `http://localhost:8000` 已加载新合约配置并正常响应。
- 完整后端集成测试仍受缺失的 `resources/Eason-Concert-Horizontal-01-2-3c-2048x1025.webp` 测试种子资源影响，该问题与本次合约及 NFT 实现无关。

## 7. 后续工作

- 将当前共用部署钱包的管理员、资金、铸造、URI 和暂停角色拆分为独立运营钱包或多签。
- 增加可靠后台任务执行器、自动重试、链重组处理和常驻事件对账。
- 完成任务限定 Badge、演唱会纪念卡资格领取和 ERC-1155 公开类型管理闭环。
- 增加自定义 NFT 恶意内容检测、审核审计日志、临时文件清理和配额限制。
- 完成身份恢复/迁移提示、管理员恢复流程和第三方公开身份查询说明。
