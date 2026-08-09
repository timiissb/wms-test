# 任务 2：库存查询

> 实现文件：`app/routers/inventory.py`（当前 `GET /api/inventory` 返回 501）
> 已就绪 schema：`InventoryResponse`（`app/schemas.py`），含 `product_id / product_name / sku / location_code / warehouse_name / quantity / updated_at`。

## 一、业务需求

仓库管理员查看各库位的实时库存，支持筛选和分页：

1. **后端 API** — 库存查询接口：
   - 支持按商品 SKU、仓库、库位编码筛选
   - 支持分页（page / pageSize）
   - 返回：商品名称、SKU、库位编码、库存数量、最后更新时间
   - 注意性能：数据量较大时避免全表扫描
2. **前端页面** — 库存列表（本仓库为纯后端，见文件末尾说明）：
   - 搜索栏（商品名称/SKU 模糊搜索 + 仓库下拉筛选）
   - 表格展示，支持分页；库存数量低于 10 的行高亮标记（红色）

**考核点：** SQL 查询是否合理使用索引；分页实现是否正确；前端状态管理是否清晰；搜索防抖处理。

## 二、接口规范

Base URL：`http://localhost:8000/api`，统一响应信封 `{"code", "message", "data"}`。

```
GET /api/inventory?keyword=&warehouseId=&page=1&pageSize=20
```

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| keyword | string | 否 | 商品名称或 SKU 模糊搜索 |
| warehouseId | int | 否 | 仓库 ID 筛选（注意：FastAPI 查询参数建议用 snake_case `warehouse_id`，见下方实现要求） |
| page | int | 否 | 页码，默认 1，最小 1 |
| pageSize | int | 否 | 每页条数，默认 20，最大 100 |

**Response (200)：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "list": [
      {
        "productId": 1,
        "productName": "蓝牙耳机",
        "sku": "SKU-001",
        "locationCode": "WH-A-01-01",
        "warehouseName": "广州主仓",
        "quantity": 100,
        "updatedAt": "2026-05-08T09:30:00"
      }
    ],
    "total": 50,
    "page": 1,
    "pageSize": 20
  }
}
```

## 三、涉及的数据库表结构

数据库为 SQLite（`wms.db`），表在 `app/main.py` 导入时由 `Base.metadata.create_all` 自动创建。
以下 DDL 与本仓库 `app/models.py` 一致。

```sql
-- 商品表（JOIN 取商品名称 / SKU）
CREATE TABLE products (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        VARCHAR(200) NOT NULL,
    sku         VARCHAR(50)  NOT NULL UNIQUE,
    unit        VARCHAR(20)  DEFAULT '个',
    created_at  DATETIME,
    updated_at  DATETIME
);

-- 仓库表（JOIN 取仓库名称）
CREATE TABLE warehouses (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL
);

-- 库位表（warehouse_id 关联仓库；code 全局唯一）
CREATE TABLE locations (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    warehouse_id INTEGER NOT NULL REFERENCES warehouses(id),
    code         VARCHAR(50) NOT NULL UNIQUE,
    status       VARCHAR(20) DEFAULT 'FREE'
);

-- 库存表（核心查询表）
CREATE TABLE inventory (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id    INTEGER NOT NULL REFERENCES products(id),
    location_code VARCHAR(50) NOT NULL REFERENCES locations(code),
    quantity      INTEGER NOT NULL DEFAULT 0,
    updated_at    DATETIME,
    CONSTRAINT uk_product_location UNIQUE (product_id, location_code)
);
```

**索引说明（性能考核点）：**
- 已有联合唯一索引 `uk_product_location (product_id, location_code)`，覆盖了按 `product_id`、按 `location_code` 的等值查找。
- `keyword` 对 `products.name / sku` 做 `contains`（LIKE `%kw%`）无法走普通索引；数据量大时可考虑 `FTS5` 或限制为前缀匹配。
- `warehouse_id` 筛选本质是 `locations.warehouse_id` 的等值条件，可为 `locations.warehouse_id` 加索引。

## 四、实现要点

1. **多表 JOIN**：`Inventory` → `Product`（取名称/SKU）、`Inventory.location_code → Location`（取 `warehouse_id`）→ `Location.warehouse_id → Warehouse`（取仓库名）。SQLAlchemy 已定义关系：
   - `Inventory.product`（`foreign_keys=[product_id]`）
   - `Inventory.location`（`foreign_keys=[location_code]`）
   - `Location.warehouse`（`relationship("Warehouse")`）
2. **条件筛选**（均为可选）：
   - `keyword`：`Product.name.contains(kw) | Product.sku.contains(kw)`
   - `warehouse_id`：通过 `Location.warehouse_id == warehouse_id` 过滤
3. **分页**：`query.offset((page-1)*page_size).limit(page_size)`；`total` 用 `query.count()` 单独统计（注意分页条件应用在 count 之前）。返回信封 `data` 含 `list / total / page / page_size`（对应 `schemas.PageResult`）。
4. **避免全表扫描**：尽量把过滤条件下推到 SQL 而非 Python 内存过滤；只 `SELECT` 需要的列（可选）。
5. **参数风格**：本仓库 FastAPI 路由用 snake_case（`page_size`、`warehouse_id`），与 `API_SPEC.md` 的 `pageSize` 为命名差异；若前端按 `camelCase` 对接，可自行约定或用别名映射。
6. **响应**：`InventoryResponse` 已有 `from_attributes=True`，可直接用 ORM 对象组装后返回。

## 五、验收标准

- [ ] `GET /api/inventory` 返回分页数据，字段齐全（商品名/SKU/库位/仓库名/数量/更新时间）
- [ ] `keyword` 支持按商品名称或 SKU 模糊搜索
- [ ] `warehouse_id` 可正确过滤出该仓库下的库存
- [ ] `page` / `page_size` 分页正确，`total` 与实际总数一致；`page_size` 超过 100 时被限制
- [ ] 空结果返回 `list: []`、`total: 0`，不报错
- [ ] 可在 `http://localhost:8000/docs` 调通接口
- [ ] （如有前端）库存 < 10 的行红色高亮、搜索防抖、分页切换正常

## 六、注意事项

本仓库为**纯后端（FastAPI）**，任务描述的「前端页面」对应 `frontend-vue` / `frontend-react` 目录，不在本仓库范围内；后端仅保证本接口可用、性能合理即可。
