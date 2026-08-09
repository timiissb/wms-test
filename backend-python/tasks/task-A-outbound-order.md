# 选做 A：出库单 + 库存扣减（并发安全）

> 选做任务。核心难点是**库存扣减的并发安全**（防超卖），需在 `NOTES.md` 中说明你选择的并发控制方案及理由。

## 一、业务需求

实现出库单创建功能：

- 出库时需要检查库存是否充足（`quantity >= 出库数量`，不足则报错）
- 高并发下防止超卖
- 说明你选择的并发控制方案及理由（写入 `NOTES.md`）

## 二、接口规范

Base URL：`http://localhost:8000/api`，统一响应信封 `{"code", "message", "data"}`。

```
POST /api/outbound-orders
```

**Request Body：**

```json
{
  "customerName": "客户X",
  "items": [
    { "productId": 1, "quantity": 10, "locationCode": "WH-A-01-01" }
  ]
}
```

**Response (201)：**（参照入库单响应结构）

```json
{
  "code": 201,
  "message": "出库单创建成功",
  "data": {
    "id": 1,
    "orderNo": "OUT-20260508-001",
    "customerName": "客户X",
    "status": "COMPLETED",
    "items": [
      { "productId": 1, "productName": "商品A", "quantity": 10, "locationCode": "WH-A-01-01" }
    ],
    "createdAt": "2026-05-08T10:00:00"
  }
}
```

**错误响应：**

```json
{ "code": 400, "message": "库存不足: 商品1@WH-A-01-01 剩余5", "data": null }
```

## 三、涉及的数据库表结构

> **注意**：本仓库 `app/models.py` **尚未定义**出库单模型，需要候选人新增 `OutboundOrder` / `OutboundOrderItem` 两个模型（`Base.metadata.create_all` 会自动建表）。DDL 参考 `docs/API_SPEC.md`，转成 SQLAlchemy `Column` 风格即可。

```sql
-- 出库单主表
CREATE TABLE outbound_orders (
    id            BIGINT PRIMARY KEY AUTO_INCREMENT,
    order_no      VARCHAR(50) NOT NULL UNIQUE,
    customer_name VARCHAR(200),
    status        VARCHAR(20) DEFAULT 'DRAFT',
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 出库单明细表
CREATE TABLE outbound_order_items (
    id            BIGINT PRIMARY KEY AUTO_INCREMENT,
    order_id      BIGINT NOT NULL,
    product_id    BIGINT NOT NULL,
    quantity      INT NOT NULL,
    location_code VARCHAR(50) NOT NULL,
    FOREIGN KEY (order_id)   REFERENCES outbound_orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);
```

扣减的对象是**现有 `inventory` 表**（DDL 见任务 2，联合唯一约束 `uk_product_location (product_id, location_code)`）。

```sql
-- 库存表（扣减目标）
CREATE TABLE inventory (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id    INTEGER NOT NULL REFERENCES products(id),
    location_code VARCHAR(50) NOT NULL REFERENCES locations(code),
    quantity      INTEGER NOT NULL DEFAULT 0,
    updated_at    DATETIME,
    CONSTRAINT uk_product_location UNIQUE (product_id, location_code)
);
```

## 四、并发安全方案（选型参考）

| 方案 | 原理 | 优点 | 缺点 | 适用场景 |
|------|------|------|------|----------|
| **乐观锁（version 字段）** | 库存表加 `version`，`UPDATE ... SET quantity=quantity-N, version=version+1 WHERE version=old`，影响行数为 0 则冲突重试 | 读多写少时性能好、实现简单 | 高冲突时重试多 | 冲突概率低的场景 |
| **悲观锁（行锁 `SELECT ... FOR UPDATE`）** | 扣减前锁定库存行，阻塞其他事务直到提交 | 强一致、无重试 | 并发下吞吐下降、易死锁（需固定加锁顺序） | 扣减冲突高的场景；但 **SQLite 不支持 `SELECT FOR UPDATE`** |
| **原子条件更新（推荐 / SQLite 友好）** | `UPDATE inventory SET quantity = quantity - :n WHERE product_id=:p AND location_code=:l AND quantity >= :n`，`rowcount == 0` 即库存不足或行不存在 | 一步到位、天然防超卖、无需额外字段 | 需先确认行存在（区分「库存不足」与「库位无库存」） | SQLite / 单机事务内均可 |

**推荐做法（结合本仓库 SQLite）：**

```python
# 在事务内逐条原子扣减，数量不足时 rowcount 为 0
stmt = (
    update(Inventory)
    .where(Inventory.product_id == item.product_id,
           Inventory.location_code == item.location_code,
           Inventory.quantity >= item.quantity)
    .values(quantity=Inventory.quantity - item.quantity,
            updated_at=datetime.now())
)
rowcount = db.execute(stmt).rowcount
if rowcount == 0:
    raise HTTPException(status_code=400, detail=f"库存不足: {item.product_id}@{item.location_code}")
```

> 关键点：**「检查 + 扣减」必须是同一个原子 SQL（条件写），不能先 SELECT 判断再 UPDATE**，否则两个请求会同时通过检查导致超卖。整个出库单创建与所有明细扣减放在同一个事务内，任一条失败 `rollback()` 全部回滚。

## 五、实现要点

1. 新建 `OutboundOrder` / `OutboundOrderItem` 模型，风格对齐 `app/models.py` 的 `InboundOrder` / `InboundOrderItem`。
2. 出库单号自动生成（建议 `OUT-YYYYMMDD-XXX`），规则参考任务 1。
3. 逐条明细**原子扣减库存**（条件 `quantity >= n`），不足抛 400。
4. 校验商品、库位存在（同任务 1）。
5. 整个流程在单事务内：全部明细扣减成功 → `db.commit()`；任一失败 → `db.rollback()`，保证出库单与库存扣减一致。
6. 在 `NOTES.md` 说明方案选型及理由（为何不用乐观锁/悲观锁，SQLite 的约束等）。

## 六、验收标准

- [ ] `POST /api/outbound-orders` 成功创建出库单并扣减对应库存
- [ ] 库存不足时返回 400，且**不产生部分扣减**（事务回滚）
- [ ] 同一库位同一商品并发出库不超卖（可用并发脚本验证）
- [ ] 出库后 `inventory.quantity` 正确减少

## 七、注意事项

- SQLite 不支持 `SELECT ... FOR UPDATE`，悲观锁方案不适用，需改用原子条件更新或加锁排队。
- 若只做单进程单库，可结合「事务 + 原子 UPDATE」达到防超卖效果；多实例部署需考虑数据库级约束或队列。
