# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目背景

这是 **WMS（仓库管理系统）线上测试题**的 React 18 + Ant Design 前端模板。仓库根目录（`wms-test/`）还包含 `backend-python/`（FastAPI，已选技术栈，vite 代理指向其 8000 端口）、`backend-java/`、`frontend-vue/`，业务需求相同，本目录只负责 React 前端。

候选人的任务拆解在 `../TASKS.md`，权威接口规范在 `../docs/API_SPEC.md`。

**当前实现状态：**
- ✅ 已实现（参考风格）：商品管理页 `ProductsPage.tsx`
- ❌ 待实现：入库管理页 `InboundPage.tsx`（任务1）、库存查询页 `InventoryPage.tsx`（任务2）
- 🐞 已预埋 Bug：`ProductsPage.tsx` 编辑商品返回列表后页码重置为第1页（任务3，见该文件行 71-72 注释）

## 常用命令

```bash
npm install          # 安装依赖
npm run dev          # 启动开发服务器 → http://localhost:5173（/api 代理到 http://localhost:8000）
npm run build        # tsc 类型检查 + vite 构建（package.json 中 tsc && vite build）
npm run preview      # 预览构建产物
```

- **无 lint / 测试脚本**（package.json 中只有 dev/build/preview），验证手段是 `npm run build` 的类型检查 + 浏览器手测
- 后端启动需在 `../backend-python`：`uv run uvicorn app.main:app --reload`，否则前端 `/api` 请求 502

## 架构

Vite + React 18 + TypeScript + Ant Design 5，`@` 别名指向 `src/`（vite.config.ts 与 tsconfig.json 均已配置）。

- **`src/main.tsx`** — 入口，`ConfigProvider locale={zhCN}`（AntD 中文）+ `RouterProvider`
- **`src/App.tsx`** — 布局壳：顶部 `Menu` 导航 + `Outlet`，菜单项与路由 path 一一对应，新增页面需在此加菜单项
- **`src/router.tsx`** — `createBrowserRouter` 定义路由，`/` 重定向到 `/products`；新增页面在此注册
- **`src/api/client.ts`** — 单例 axios 实例：`baseURL: '/api'`，**响应拦截器返回 `res.data`**（即把 HTTP 响应解包成统一信封对象）
- **`src/api/index.ts`** — 按业务分组的 API 函数 + TS 接口（Product / Warehouse / Location / InventoryItem / InboundItemRequest），页面对接数据的唯一入口
- **`src/pages/*.tsx`** — 每个路由对应一个页面组件，参考 `ProductsPage.tsx` 的实现风格

### 必须遵守的约定

- **统一响应信封**：后端所有接口返回 `{code, message, data}`。因为拦截器已返回 `res.data`，所以 `const res = await getProducts()` 得到的 `res` 就是信封对象，取值写 `res.data`（即 `res.data` 是实际负载列表）
- **错误处理**：axios 拦截器 `reject` 原始 error，页面里用 `catch (e) { e.response?.data?.message || e.message }` 取中文错误信息，参考 `ProductsPage.tsx:34-36`
- **API 封装**：`api/index.ts` 中新增接口函数时，用泛型标注信封类型，如 `api.get<any, { code: number; data: Xxx[] }>('...', { params })`
- **查询参数命名**：前端传 snake_case（`page_size`、`warehouse_id`），与 FastAPI 后端一致；`API_SPEC.md` 里的 camelCase（`pageSize`）是已知命名差异，不要混用
- **级联数据流**：商品下拉用 `getProducts(keyword)` 搜索；仓库→库位级联先 `getWarehouses()` 再 `getLocations(warehouseId)`
- **UI 文案、注释、错误提示均为中文**；组件用 AntD 5 组件（Table / Form / Modal / Select 等），沿用参考页写法

### 关键注意点

- **分页状态**：参考实现 `ProductsPage.tsx` 是前端分页（`useMemo` 切片，`pagination.current/onChange` 控制 `currentPage`）。任务3 要求修复「编辑后页码重置」Bug，修复思路是编辑/删除后回到**当前页**而非 `setCurrentPage(1)`，必要时删除末页最后一条后回退页码
- **库存页性能（选做C）**：`InventoryPage.tsx` 调 `getInventory` 走**后端分页**（返回 `{list, total, page, pageSize}`），与商品页前端分页不同；搜索可用 `Select` 仓库 + keyword 输入，低库存（<10）高亮建议用 `rowClassName` 判断 `record.quantity`
- **入库表单**：多行明细用 `items` state 数组渲染（参考 `InboundPage.tsx` 已给的骨架），提交组装 `{supplierName, items: [{productId, quantity, locationCode}]}` 调 `createInboundOrder`
- 依赖已锁定在 `package-lock.json`，装包用 `npm install` 不要加 `--legacy-peer-deps` 等覆盖参数

## 参考文档

- 任务详情：`../TASKS.md`
- 接口规范：`../docs/API_SPEC.md`（含出库单、表结构）
- 后端说明：`../backend-python/CLAUDE.md`
- 业务背景：`../README.md`、`../AI_USAGE_GUIDE.md`
