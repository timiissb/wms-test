# 选做 C：前端性能优化

> 选做任务。库存列表页面在数据量大（500+ 条）时可能出现卡顿，请实施**至少一种**优化方案。
> 本仓库为**纯后端（FastAPI）**，本任务针对 `frontend-vue` / `frontend-react` 目录实现，此处给出方案与验收标准供前端仓库参考。

## 一、可选优化方案

| 方案 | 原理 | 适用场景 | 说明 |
|------|------|----------|------|
| **虚拟滚动** | 只渲染可视区域内的行，其余用占位高度 | 一次性渲染大量行 | 数据量上千、仍需整表可滚时首选；Element Plus `el-table-v2` / react-window 等库 |
| **防抖搜索** | 输入停止 N 毫秒后才发请求 | 搜索框高频输入 | 避免每次按键都请求后端；本仓库任务 2 的 `keyword` 接口已支持 |
| **后端分页** | 只请求当前页数据 | 数据量持续增长 | 本仓库任务 2 已实现 `page` / `pageSize` 分页，前端接上即可，是最省力且收益最稳的方案 |

> 三者可组合：后端分页（减请求量）+ 防抖（减请求频率）通常已能解决 500+ 条的卡顿；虚拟滚动用于仍有大量行需常驻渲染的场景。

## 二、前端优化要点（以 React / Vue 为例）

### 1. 后端分页对接

- 请求参数：`keyword`、`warehouse_id`、`page`、`page_size`（本仓库 FastAPI 为 snake_case，前端需与服务端约定映射）。
- 响应解析：`data.list`（当前页数据）、`data.total`（总数），用于渲染表格与分页器。
- 切换页码 / 修改筛选条件时重新请求，并将当前分页状态同步到 URL query（与任务 3 前端 Bug 修复思路一致，避免编辑返回丢失页码）。

### 2. 防抖搜索

```ts
// 输入防抖 300ms 后再发起查询，避免每次按键都请求
const debouncedKeyword = useDebounce(keyword, 300);
useEffect(() => { fetchInventory(); }, [debouncedKeyword]);
```

### 3. 虚拟滚动（如需）

- React：`react-window` / `@tanstack/react-virtual`
- Vue：`el-table-v2`（Element Plus 官方虚拟表格）或 `vue-virtual-scroller`

## 三、后端配合说明

本仓库任务 2（`GET /api/inventory`）已具备：
- `keyword` 模糊搜索、`warehouse_id` 筛选、`page` / `page_size` 分页（`page_size` 上限 100）
- 返回 `data.list` + `data.total`

前端优化落地前，请确保后端分页接口可用（见 [task-2-inventory-query.md](./task-2-inventory-query.md)）。

## 四、验收标准

- [ ] 实现至少一种优化方案（建议：后端分页 + 防抖搜索）
- [ ] 500+ 条数据下列表滚动/搜索不卡顿（可对比优化前后帧率或响应时间）
- [ ] 分页切换、搜索、筛选后状态正确且页码不回跳
- [ ] 在 `NOTES.md` 说明选择了哪种方案及理由
