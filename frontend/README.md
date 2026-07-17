# Fanora Frontend

该模块由原 `xhibiter-ts` 模板整理而来，使用 Next.js、RainbowKit、wagmi 和 viem。

当前前端已经收敛到原始 `home-4` 设计，只保留 `/`、`/home-4` 和 404 路由。第一阶段保持模板的布局、视觉和交互不变，后续再逐步替换为 Fanora 文案与业务数据。原模板中的其他 Home、博客和独立商城页面已经移除。

后续需要新的组件或样式时，从仓库根目录的 `xhibiter-ts` 素材工程中按需复制，不重新把整套模板依赖引入 `frontend`。

`public/img` 只保留当前 `home-4` 页面、导航、页脚和样式实际引用的资源；后续复制新组件时，需要同步复制该组件依赖的图片。

## 启动

```bash
cp .env.example .env.local
npm install
npm run dev
```

浏览器访问 `http://localhost:3000`。

## 目录建议

- `app/`：主页、`home-4` 展示路由和 404。
- `components/homes/home-4/`：Hero 与动态 Badge Cover Flow。
- `components/homes/common/`：协议能力、Agent、工作流程和用户价值区块。
- `lib/web3/`：Monad 网络、合约地址和 ABI。
- `hooks/`：钱包与合约读取 hooks。
- `data/fanora.ts`：主页展示数据，后续逐步替换为后端接口。

## 质量检查

```bash
npm run lint
npm run typecheck
npm run build
```
