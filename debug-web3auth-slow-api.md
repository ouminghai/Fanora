# [HISTORICAL / RESOLVED] web3auth-slow-api

> 该记录描述 2026-07-22 之前的 Web3Auth 方案。当前前后端已删除 Web3Auth、Identity Token 和 JWKS 验证，统一使用 RainbowKit 钱包 challenge 签名登录；下文仅保留为历史诊断证据，不代表当前接口或配置。

## 背景

- 症状：`POST /api/v1/auth/web3auth` 请求明显过慢，用户反馈前端大约 30 秒停止请求，虽然 Axios 已设置 60 秒超时。
- 目标：定位慢点是否来自 Web3Auth `id_token` 验证、数据库、签名校验、HTTP 链路或其他外部依赖，并给出最小修复方案。

## 当前假设

1. `id_token` 验证过程中发生了耗时的外部网络请求。
2. 数据库读取或写入链路存在慢查询或连接等待。
3. 多个校验步骤串行执行导致总耗时过长。
4. 前端/浏览器实际超时与 Axios 配置不一致。
5. 缺少分阶段日志，无法快速确认瓶颈位置。

## 计划

1. 阅读认证接口与依赖代码，确认关键阶段。
2. 添加最小化分阶段调试日志，只收集运行时证据。
3. 复现请求并对比各阶段耗时。
4. 根据证据实施最小修复。
5. 再次验证并与修复前日志对比。

## 证据

- 静态检查确认 `Web3AuthService` 使用 `PyJWKClient(settings.web3auth_jwks_url, cache_keys=True)`，未显式设置 `timeout`，因此退回 PyJWT 默认 `30s`。
- 直接复现用户提供的 `/api/v1/auth/web3auth` 请求，返回 `401 Login challenge is invalid or expired`，总耗时约 `0.82s`，说明“challenge 已失效”的请求本身不是慢点。
- 独立测量 `PyJWKClient(..., timeout=30)` 访问 `https://api-auth.web3auth.io/jwks`，实际耗时约 `30.56s`，并抛出 `SSL handshake timeout`。
- 将服务端 `PyJWKClient` 超时改为 `5s` 后，同样的 JWKS 访问路径耗时降到约 `5.65s` 后失败返回，证明 30 秒等待来自 JWKS 网络握手而非数据库或签名恢复。

## 当前结论

- 已确认根因：Web3Auth JWKS 拉取在当前网络环境发生 TLS 握手超时，后端默认等待 `30s`，导致前端感知为“30 秒左右就卡住/断开”。
- 已实施最小修复：显式配置 `web3auth_jwks_timeout_seconds=5.0`，并显式配置 JWKS 缓存寿命 `web3auth_jwks_cache_lifespan_seconds=3600`。
- 预期效果：当 Web3Auth JWKS 不可达时，接口会在约 5 秒内快速失败而不是卡 30 秒；当 JWKS 可达且缓存命中时，后续登录仍可走缓存快速返回。

## 最终处置

- Web3Auth 登录与上述超时配置已从当前代码删除。
- 当前登录接口为 `POST /api/v1/auth/challenge` 与 `POST /api/v1/auth/wallet`。
- 钱包私钥与账户恢复完全由用户选择的钱包应用管理。
