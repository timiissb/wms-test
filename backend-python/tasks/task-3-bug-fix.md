# 任务 3：Bug 修复

> 模板代码预埋了 2 个 Bug，请定位并修复，并在项目根目录 `NOTES.md` 中说明发现的 Bug 及修复方式。

## 一、Bug 清单

### Bug 1（后端）：删除商品未校验关联库存

- **位置**：`app/routers/products.py` 的 `DELETE /api/products/{product_id}`（`delete_product` 函数）。
- **现象**：商品存在关联库存（`inventory` 表有 `product_id` 指向该商品）时，仍可直接删除商品，导致删除后库存数据孤立（外键悬空 / 脏数据）。
- **代码线索**：该函数内有一行注释 `# BUG 预埋点：没有校验该商品是否有关联库存`，说明此处即为问题点。
- **修复思路**：删除前先查询 `inventory` 是否有 `product_id` 等于待删商品的行；若存在则返回 400 拒绝删除（如 `"该商品存在关联库存，无法删除"`）。注意 SQLite 默认未开启外键约束，不能依赖数据库外键兜底，必须在应用层校验。

### Bug 2（前端）：商品列表切换页码后编辑返回跳回第 1 页

- **位置**：`frontend-vue` / `frontend-react` 目录的商品列表页（本仓库为纯后端，见文件末尾说明）。
- **现象**：切换页码后，编辑某条商品，返回列表时跳回了第 1 页，丢失原页码。
- **修复思路**：编辑返回时保持当前分页状态 —— 将分页参数（`page` / `pageSize` / `keyword`）提升到路由 query 或全局状态管理，返回列表时从 query/state 恢复，而非重新初始化。

## 二、涉及的数据库表结构

Bug 1 涉及商品与库存的关联关系，以下 DDL 与本仓库 `app/models.py` 一致。

```sql
-- 商品表
CREATE TABLE products (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        VARCHAR(200) NOT NULL,
    sku         VARCHAR(50)  NOT NULL UNIQUE,
    unit        VARCHAR(20)  DEFAULT '个',
    created_at  DATETIME,
    updated_at  DATETIME
);

-- 库存表（product_id 引用商品；删除商品前必须确认此处无关联）
CREATE TABLE inventory (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id    INTEGER NOT NULL REFERENCES products(id),
    location_code VARCHAR(50) NOT NULL REFERENCES locations(code),
    quantity      INTEGER NOT NULL DEFAULT 0,
    updated_at    DATETIME,
    CONSTRAINT uk_product_location UNIQUE (product_id, location_code)
);
```

> 关联关系（SQLAlchemy）：`Inventory.product = relationship("Product", foreign_keys=[product_id])`。

## 三、接口规范（删除商品，现有接口）

```
DELETE /api/products/{product_id}
```

**成功 (200)：**

```json
{ "code": 200, "message": "删除成功", "data": null }
```

**修复后应新增的错误响应：**

```json
{ "code": 400, "message": "该商品存在关联库存，无法删除", "data": null }
```

## 四、修复要求

1. 保留现有 `products.py` 风格（响应信封、`HTTPException`）。
2. Bug 1 修复需新增对 `inventory` 的查询校验，别用 `try/except` 吞掉异常。
3. Bug 2 修复需保持分页状态（若做前端）。
4. 在项目根目录 `NOTES.md` 中记录：Bug 是什么、如何定位、如何修复、修复后如何验证。

## 五、验收标准

- [ ] 有关联库存的商品删除时返回 400，商品与库存均未被删除
- [ ] 无关联库存的商品仍可正常删除（不影响原功能）
- [ ] 全量跑通原有商品 CRUD，无回归
- [ ] `NOTES.md` 已说明两个 Bug 的定位与修复方式

## 六、注意事项

本仓库为**纯后端（FastAPI）**，Bug 2 位于 `frontend-vue` / `frontend-react` 目录，不在本仓库范围内；如未选择前端技术栈，可在 `NOTES.md` 说明修复思路或仅完成 Bug 1。
