# 选做 B：单元测试

> 选做任务。为以下模块编写单元测试（**至少 2 个测试用例**），运行命令 `pytest`。

## 一、测试范围

| 模块 | 说明 | 测试文件建议 |
|------|------|--------------|
| 后端：入库单创建的 Service 层 | 覆盖：正常创建 + 库存累加、商品/库位不存在报错、库存 upsert 累加 | `tests/test_inbound_order.py` |
| 前端：库存列表的筛选逻辑 | 覆盖：keyword 模糊筛选、仓库筛选、数量 <10 高亮判定 | 对应前端仓库的测试目录 |

> 本仓库为纯后端，前端测试在 `frontend-vue` / `frontend-react` 目录中完成。

## 二、测试环境说明

- 仓库使用 `uv` 管理依赖，dev 可选依赖含 `pytest` / `httpx` / `pytest-asyncio`：
  ```bash
  uv sync --extra dev
  pytest
  ```
- `pyproject.toml` 已配置 `asyncio_mode = "auto"`，异步测试无需手动 `@pytest.mark.asyncio`。
- 可使用 `httpx` 的 `TestClient`（FastAPI 自带依赖）直接对 app 发起请求：
  ```python
  from fastapi.testclient import TestClient
  from app.main import app

  client = TestClient(app)
  ```
- 注意：测试会操作真实的 `wms.db`（`app/database.py` 固定路径），**建议在测试中用独立的临时数据库**，或按 fixture 清理数据，避免污染开发数据。

## 三、后端测试用例设计（入库单创建 Service 层）

> 当前 `app/routers/inventory.py` 尚未实现，建议先按任务 1 实现后补测试；若想 TDD，可先写测试再实现。

### 用例 1：正常创建入库单并累加库存

```python
def test_create_inbound_order_increases_inventory(client, db_session):
    # 准备：商品 + 库位已存在，初始库存 quantity=0
    # 调用：POST /api/inbound-orders  {supplier_name, items:[{product_id, quantity, location_code}]}
    # 断言：HTTP 201；inbound_orders 有记录且 order_no 匹配 IN-YYYYMMDD-XXX
    # 断言：inventory.quantity == 新增数量
    ...
```

### 用例 2：同一 (product_id, location_code) 重复入库为累加

```python
def test_repeat_inbound_accumulates_quantity(client, db_session):
    # 第一次入库 10 → inventory.quantity == 10
    # 第二次入库 5  → inventory.quantity == 15（upsert，非覆盖）
    ...
```

### 用例 3：库位不存在时报错且事务回滚

```python
def test_create_inbound_order_with_missing_location_rolls_back(client, db_session):
    # items 里带一个不存在的 location_code
    # 断言：HTTP 400，message 包含「库位不存在」
    # 断言：inbound_orders 与 inventory 均无新增（事务回滚）
    ...
```

### 用例 4：商品不存在时报错

```python
def test_create_inbound_order_with_missing_product_fails(client, db_session):
    # items 里带一个不存在的 product_id
    # 断言：HTTP 400
    ...
```

## 四、前端测试用例设计（库存列表筛选逻辑）

- **用例 1：keyword 筛选** — 输入「蓝牙」只显示商品名/SKU 含「蓝牙」的行。
- **用例 2：仓库筛选** — 选择仓库后只显示该仓库下的行。
- **用例 3：低库存高亮** — `quantity < 10` 时行被标记红色（class 或样式断言）。

## 五、验收标准

- [ ] `uv sync --extra dev` 后 `pytest` 全部通过
- [ ] 后端入库单相关测试至少 2 个用例，覆盖正常 + 异常（含回滚）
- [ ] 测试使用独立数据库或清理数据，不污染 `wms.db`
- [ ] 测试断言具体业务行为（数量累加、报错信息），而非只测「不报错」
