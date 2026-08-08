"""
入库单创建接口（POST /api/inbound-orders）单元测试 — 选做任务B

覆盖：
1. 正常创建入库单 + 库存累加、单号格式 IN-YYYYMMDD-XXX
2. 同一 (product_id, location_code) 重复入库为 upsert 累加（非覆盖）
3. 库位不存在 → 400 且事务回滚（无脏数据）
4. 商品不存在 → 400 且无脏数据

所有请求与断言都走 conftest 提供的独立临时数据库，不污染 wms.db。
pyproject.toml 已配置 addopts = "-s"，print 输出默认可见。
"""
import re

from app.models import InboundOrder, Inventory, Location, Product, Warehouse


def _setup_product_and_location(db):
    """准备测试数据：仓库 + 库位 + 商品，返回 (product, location_code)"""
    warehouse = Warehouse(code="WH-TEST", name="测试仓库")
    db.add(warehouse)
    db.flush()
    location = Location(code="WH-TEST-01", warehouse_id=warehouse.id)
    product = Product(name="蓝牙耳机", sku="BLUETOOTH-001", unit="个")
    db.add(location)
    db.add(product)
    db.commit()
    print(f"    [准备] 仓库={warehouse.code}, 库位={location.code}, "
          f"商品(id={product.id}, name={product.name}, sku={product.sku})")
    return product, location.code


def _create_order(client, product_id, quantity, location_code, supplier="供应商A"):
    """发 POST /api/inbound-orders（请求体用接口文档 camelCase 字段），并打印请求/响应"""
    body = {
        "supplierName": supplier,
        "items": [
            {
                "productId": product_id,
                "quantity": quantity,
                "locationCode": location_code,
            }
        ],
    }
    print(f"    [请求] POST /api/inbound-orders  body={body}")
    resp = client.post("/api/inbound-orders", json=body)
    print(f"    [响应] HTTP {resp.status_code}  {resp.json()}")
    return resp


def _get_inventory(db, product_id, location_code):
    """按 (product_id, location_code) 查库存（expire_all 保证读到已提交的最新值）"""
    db.expire_all()
    return (
        db.query(Inventory)
        .filter(
            Inventory.product_id == product_id,
            Inventory.location_code == location_code,
        )
        .first()
    )


def test_create_inbound_order_increases_inventory(client, db_session):
    """用例1：正常创建入库单，库存累加、单号符合 IN-YYYYMMDD-XXX"""
    print("\n==================== 用例1: 正常创建入库单 + 库存累加 ====================")
    product, loc_code = _setup_product_and_location(db_session)

    resp = _create_order(client, product.id, 10, loc_code)
    assert resp.status_code == 201, f"期望 201, 实际 {resp.status_code}"
    data = resp.json()["data"]

    # 单号格式 IN-YYYYMMDD-XXX
    assert re.match(r"^IN-\d{8}-\d{3}$", data["orderNo"]), f"单号格式异常: {data['orderNo']}"
    print(f"    [断言] 单号 {data['orderNo']} 匹配 IN-YYYYMMDD-XXX")
    assert data["supplierName"] == "供应商A"
    assert data["status"] == "COMPLETED"
    assert data["items"][0]["productId"] == product.id
    assert data["items"][0]["quantity"] == 10
    print(f"    [断言] 明细 productId={data['items'][0]['productId']}, "
          f"quantity={data['items'][0]['quantity']}")

    # 入库单已落库
    order = (
        db_session.query(InboundOrder)
        .filter(InboundOrder.order_no == data["orderNo"])
        .first()
    )
    assert order is not None, "入库单未写入数据库"
    print(f"    [断言] inbound_orders 表存在记录 order_no={order.order_no}")

    # 库存累加到 10
    inv = _get_inventory(db_session, product.id, loc_code)
    assert inv is not None, "库存未创建"
    assert inv.quantity == 10
    print(f"    [断言] 库存累加: {product.name}@{loc_code} quantity = {inv.quantity} (期望 10)")
    print("    >>> 用例1 PASS: 入库单创建成功且库存累加\n")


def test_repeat_inbound_accumulates_quantity(client, db_session):
    """用例2：同一 (product_id, location_code) 重复入库为累加（upsert 非覆盖）"""
    print("\n==================== 用例2: 重复入库 upsert 累加 ====================")
    product, loc_code = _setup_product_and_location(db_session)

    print("    [步骤] 第一次入库 10:")
    r1 = _create_order(client, product.id, 10, loc_code)
    assert r1.status_code == 201
    print("    [步骤] 第二次入库 5:")
    r2 = _create_order(client, product.id, 5, loc_code)
    assert r2.status_code == 201

    # 10 + 5 = 15（累加，不是被覆盖为 5）
    inv = _get_inventory(db_session, product.id, loc_code)
    assert inv.quantity == 15
    print(f"    [断言] 库存累加: 10 + 5 = {inv.quantity} (期望 15, upsert 非覆盖)")

    # 两张入库单是独立记录
    count = db_session.query(InboundOrder).count()
    assert count == 2
    print(f"    [断言] inbound_orders 表共 {count} 条记录 (期望 2, 两张单独立)")
    print("    >>> 用例2 PASS: 重复入库累加而非覆盖\n")


def test_create_inbound_order_with_missing_location_rolls_back(client, db_session):
    """用例3：库位不存在 → 400，且入库单与库存均无新增（事务回滚）"""
    print("\n==================== 用例3: 库位不存在 → 400 且事务回滚 ====================")
    product, _ = _setup_product_and_location(db_session)

    resp = _create_order(client, product.id, 5, "NO-SUCH-LOC")
    assert resp.status_code == 400, f"期望 400, 实际 {resp.status_code}"
    assert "库位不存在" in resp.json()["detail"]
    print(f"    [断言] HTTP 400 且错误信息含「库位不存在」: {resp.json()['detail']}")

    # 无脏数据：既没有入库单，也没有库存
    order_count = db_session.query(InboundOrder).count()
    inv_count = db_session.query(Inventory).count()
    assert order_count == 0
    assert inv_count == 0
    print(f"    [断言] 事务回滚: inbound_orders={order_count} 条, inventory={inv_count} 条 (均应为 0, 无脏数据)")
    print("    >>> 用例3 PASS: 报错且无部分写入\n")


def test_create_inbound_order_with_missing_product_fails(client, db_session):
    """用例4：商品不存在 → 400，且无脏数据"""
    print("\n==================== 用例4: 商品不存在 → 400 且无脏数据 ====================")
    _, loc_code = _setup_product_and_location(db_session)

    resp = _create_order(client, 99999, 5, loc_code)
    assert resp.status_code == 400, f"期望 400, 实际 {resp.status_code}"
    assert "商品不存在" in resp.json()["detail"]
    print(f"    [断言] HTTP 400 且错误信息含「商品不存在」: {resp.json()['detail']}")

    order_count = db_session.query(InboundOrder).count()
    inv_count = db_session.query(Inventory).count()
    assert order_count == 0
    assert inv_count == 0
    print(f"    [断言] 无脏数据: inbound_orders={order_count} 条, inventory={inv_count} 条 (均应为 0)")
    print("    >>> 用例4 PASS: 报错且无部分写入\n")
