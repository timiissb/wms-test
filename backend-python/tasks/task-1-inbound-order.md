# 任务 1：入库单创建

> 实现文件：`app/routers/inventory.py`（当前 `POST /api/inbound-orders` 返回 501）
> 参考实现：`app/routers/products.py`（RESTful 风格、响应信封、依赖注入、异常处理）

## 一、业务需求

采购部门将商品入库到指定仓库的库位：

1. **后端 API** — 创建入库单，包含：
   - 入库单号（自动生成，格式 `IN-YYYYMMDD-XXX`，XXX 为当日递增序号，如 `IN-20260508-001`）
   - 供应商名称
   - 明细列表（商品 SKU、数量、目标库位编码）
   - 创建入库单时**自动累加对应库位的库存**
   - 使用**数据库事务**保证入库单和库存更新的一致性
2. **前端页面** — 入库单创建表单（本仓库为纯后端，见文件末尾说明）：
   - 选择商品（下拉搜索）、选择目标仓库 → 库位（级联选择）、输入数量、支持添加多行明细、提交按钮

**考核点：** API 设计是否 RESTful；事务处理是否正确；异常处理是否完善（如库位不存在、数量校验）；前端表单交互是否流畅。

## 二、接口规范

Base URL：`http://localhost:8000/api`，请求体 `application/json`，统一响应信封 `{"code", "message", "data"}`。

### 2.1 创建入库单（本次任务核心）

```
POST /api/inbound-orders
```

**Request Body：**

```json
{
  "supplierName": "供应商A",
  "items": [
    { "productId": 1, "quantity": 100, "locationCode": "WH-A-01-01" },
    { "productId": 2, "quantity": 50,  "locationCode": "WH-A-01-02" }
  ]
}
```

> 对应 Pydantic schema（`app/schemas.py`）：`InboundOrderCreate { supplier_name, items: list[InboundItemRequest] }`，
> `InboundItemRequest { product_id, quantity(>0), location_code }`。字段为 snake_case，FastAPI 自动映射 JSON。

**Response (201)：**

```json
{
  "code": 201,
  "message": "入库单创建成功",
  "data": {
    "id": 1,
    "orderNo": "IN-20260508-001",
    "supplierName": "供应商A",
    "status": "COMPLETED",
    "items": [
      { "productId": 1, "productName": "商品A", "quantity": 100, "locationCode": "WH-A-01-01" }
    ],
    "createdAt": "2026-05-08T10:00:00"
  }
}
```

**错误响应示例：**

```json
{ "code": 400, "message": "库位不存在: WH-A-01-01", "data": null }
{ "code": 400, "message": "商品不存在: 999", "data": null }
{ "code": 422, "message": "请求参数校验失败（Pydantic 自动）", "data": null }
```

### 2.2 入库单列表

```
GET /api/inbound-orders?page=1&pageSize=20
```

分页响应信封：

```json
{
  "code": 200,
  "message": "success",
  "data": { "list": [], "total": 100, "page": 1, "pageSize": 20 }
}
```

### 2.3 入库单详情

```
GET /api/inbound-orders/{id}
```

## 三、涉及的数据库表结构

数据库为 SQLite（`wms.db`），表在 `app/main.py` 导入时由 `Base.metadata.create_all` 自动创建。
以下 DDL 与本仓库 `app/models.py` 一致。

```sql
-- 商品表（已存在，只读引用）
CREATE TABLE products (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        VARCHAR(200) NOT NULL,
    sku         VARCHAR(50)  NOT NULL UNIQUE,
    unit        VARCHAR(20)  DEFAULT '个',
    created_at  DATETIME,
    updated_at  DATETIME
);

-- 库位表（已存在，只读引用；code 全局唯一）
CREATE TABLE locations (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    warehouse_id INTEGER NOT NULL REFERENCES warehouses(id),
    code         VARCHAR(50) NOT NULL UNIQUE,
    status       VARCHAR(20) DEFAULT 'FREE'
);

-- 库存表（入库时需 upsert 累加）
CREATE TABLE inventory (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id    INTEGER NOT NULL REFERENCES products(id),
    location_code VARCHAR(50) NOT NULL REFERENCES locations(code),
    quantity      INTEGER NOT NULL DEFAULT 0,
    updated_at    DATETIME,
    CONSTRAINT uk_product_location UNIQUE (product_id, location_code)
);

-- 入库单主表
CREATE TABLE inbound_orders (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    order_no      VARCHAR(50) NOT NULL UNIQUE,
    supplier_name VARCHAR(200),
    status        VARCHAR(20) DEFAULT 'DRAFT',
    created_at    DATETIME
);

-- 入库单明细表
CREATE TABLE inbound_order_items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id      INTEGER NOT NULL REFERENCES inbound_orders(id),
    product_id    INTEGER NOT NULL REFERENCES products(id),
    quantity      INTEGER NOT NULL,
    location_code VARCHAR(50) NOT NULL
);
```

## 四、实现要点

1. **入库单号生成**：`IN-YYYYMMDD-XXX`。当日第一条为 `IN-20260508-001`，可用「按日查询最大 `order_no` → 序号 +1」或 SQLite 当日计数，注意并发下加唯一约束兜底。
2. **事务一致性**：单请求内用同一个 `db` 会话，`db.add(...)` 后统一 `db.commit()`；任何一步失败 `db.rollback()`，避免出现「入库单已建但库存没加」或反之。
   - 推荐顺序：先创建 `InboundOrder` → `db.flush()` 拿到 id → 逐条创建 `InboundOrderItem` → 逐条 upsert `Inventory` → 全部成功后再 `commit()`。
3. **库存 upsert**：`inventory` 有联合唯一约束 `(product_id, location_code)`，存在则 `quantity += 新增数量`，不存在则插入新行。
4. **校验**：
   - 商品存在性：`db.query(Product).filter(Product.id == ...)`，不存在抛 400。
   - 库位存在性：`db.query(Location).filter(Location.code == ...)`，不存在抛 400。
   - 数量：`quantity > 0`（Pydantic `Field(gt=0)` 已保证，可自行再校验）。
   - 明细不能为空（Pydantic `min_length=1` 已保证）。
5. **SQL 注入防护**：使用 SQLAlchemy 参数化查询（`filter(Product.id == value)`），不要拼接字符串。
6. **响应**：遵循 `products.py` 风格，返回 `{"code": 201, "message": "入库单创建成功", "data": {...}}`，用 `status_code=201`。

## 五、验收标准

- [ ] `POST /api/inbound-orders` 创建成功后返回 201 与入库单号 `IN-YYYYMMDD-XXX`
- [ ] 入库后 `inventory.quantity` 正确累加；同 `(product_id, location_code)` 重复入库为累加而非覆盖
- [ ] 库位不存在 / 商品不存在 / 明细为空时返回明确错误，且不产生脏数据（事务回滚）
- [ ] 并发下订单号不重复（唯一约束兜底）
- [ ] 可在 `http://localhost:8000/docs` 调通接口
- [ ] （如有前端）表单级联选择仓库→库位，多行明细可提交

## 六、注意事项

本仓库为**纯后端（FastAPI）**，任务描述的「前端表单」对应 `frontend-vue` / `frontend-react` 目录，不在本仓库范围内；候选人按所选技术栈在对应前端仓库实现，后端仅保证本接口可用即可。
