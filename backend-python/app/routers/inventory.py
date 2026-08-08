"""
============================================
 候选人需要实现以下接口：
============================================

POST /api/inbound-orders       — 创建入库单（任务1）
GET  /api/inbound-orders       — 入库单列表
GET  /api/inbound-orders/{id}  — 入库单详情
GET  /api/inventory            — 库存查询（任务2）

提示：
- 参考 routers/products.py 的实现风格
- 使用 SQLAlchemy 进行数据库操作
- 入库单创建需要使用事务（db.commit / db.rollback）
- 库存查询需要 JOIN 多表获取商品名、仓库名
- 注意 SQL 注入防护（使用参数化查询）
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import InboundOrder, InboundOrderItem, Inventory, Location, Product, Warehouse
from app.schemas import InboundOrderCreate

router = APIRouter(tags=["库存 & 入库"])

# 入库单号格式 IN-YYYYMMDD-XXX，XXX 为当日递增序号
ORDER_NO_PREFIX = "IN"
# 并发下单号唯一约束冲突时的最大重试次数（递增序号后重试）
MAX_ORDER_NO_RETRY = 3


def _next_order_seq(db: Session) -> int:
    """取当日最大入库单号的序号，返回下一序号（无单则从 1 开始）"""
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"{ORDER_NO_PREFIX}-{today}-"
    last = (
        db.query(InboundOrder.order_no)
        .filter(InboundOrder.order_no.like(f"{prefix}%"))
        .order_by(InboundOrder.order_no.desc())
        .first()
    )
    if not last:
        return 1
    return int(last[0].rsplit("-", 1)[1]) + 1


def _build_order_data(order: InboundOrder) -> dict:
    """构造入库单响应数据（字段对齐接口文档 API_SPEC.md，camelCase）"""
    return {
        "id": order.id,
        "orderNo": order.order_no,
        "supplierName": order.supplier_name,
        "status": order.status,
        "items": [
            {
                "productId": it.product_id,
                "productName": it.product.name if it.product else None,
                "quantity": it.quantity,
                "locationCode": it.location_code,
            }
            for it in order.items
        ],
        "createdAt": order.created_at,
    }


@router.post("/api/inbound-orders", status_code=201)
def create_inbound_order(req: InboundOrderCreate, db: Session = Depends(get_db)):
    """
    创建入库单 — 任务1

    要求：
    1. 生成入库单号 IN-YYYYMMDD-XXX
    2. 校验商品和库位是否存在
    3. 在事务中同时创建入库单 + 更新库存
    """
    # 校验商品、库位是否存在（失败直接抛 400，事务不提交）
    for item in req.items:
        if not db.query(Product).filter(Product.id == item.product_id).first():
            raise HTTPException(status_code=400, detail=f"商品不存在: {item.product_id}")
        if not db.query(Location).filter(Location.code == item.location_code).first():
            raise HTTPException(status_code=400, detail=f"库位不存在: {item.location_code}")

    seq = _next_order_seq(db)
    for _ in range(MAX_ORDER_NO_RETRY):
        try:
            order = InboundOrder(
                order_no=f"{ORDER_NO_PREFIX}-{datetime.now().strftime('%Y%m%d')}-{seq:03d}",
                supplier_name=req.supplier_name,
                status="COMPLETED",
            )
            db.add(order)
            db.flush()  # 先拿到 order.id，再写明细

            # 逐条创建明细 + 库存 upsert 累加
            for item in req.items:
                db.add(
                    InboundOrderItem(
                        order_id=order.id,
                        product_id=item.product_id,
                        quantity=item.quantity,
                        location_code=item.location_code,
                    )
                )
                inventory = (
                    db.query(Inventory)
                    .filter(
                        Inventory.product_id == item.product_id,
                        Inventory.location_code == item.location_code,
                    )
                    .first()
                )
                if inventory:
                    inventory.quantity += item.quantity
                else:
                    db.add(
                        Inventory(
                            product_id=item.product_id,
                            location_code=item.location_code,
                            quantity=item.quantity,
                        )
                    )

            db.commit()
            db.refresh(order)
            return {
                "code": 201,
                "message": "入库单创建成功",
                "data": _build_order_data(order),
            }
        except IntegrityError:
            # 并发下 order_no 唯一约束冲突：回滚后递增序号重试
            db.rollback()
            seq += 1

    raise HTTPException(status_code=500, detail="入库单号生成失败，请重试")


@router.get("/api/inbound-orders")
def list_inbound_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """入库单列表 — 分页"""
    query = db.query(InboundOrder).order_by(InboundOrder.id.desc())
    total = query.count()
    orders = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "code": 200,
        "message": "success",
        "data": {
            "list": [_build_order_data(o) for o in orders],
            "total": total,
            "page": page,
            "pageSize": page_size,
        },
    }


@router.get("/api/inbound-orders/{order_id}")
def get_inbound_order(order_id: int, db: Session = Depends(get_db)):
    """入库单详情"""
    order = db.query(InboundOrder).filter(InboundOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="入库单不存在")
    return {"code": 200, "message": "success", "data": _build_order_data(order)}


@router.get("/api/inventory")
def query_inventory(
    keyword: str | None = Query(default=None, description="商品名称/SKU 模糊搜索"),
    warehouseId: int | None = Query(default=None, description="仓库ID"),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    库存查询 — 任务2

    多表 JOIN（Inventory → Product / Location → Warehouse）取商品名、SKU、仓库名；
    条件全部下推到 SQL，只 SELECT 响应需要的列，避免全表扫描与 N+1 查询。
    """
    # 显式 JOIN 三表：inventory→products（取名称/SKU）、inventory→locations→warehouses（取仓库名）
    query = (
        db.query(
            Inventory.product_id,
            Product.name.label("product_name"),
            Product.sku.label("sku"),
            Inventory.location_code,
            Warehouse.name.label("warehouse_name"),
            Inventory.quantity,
            Inventory.updated_at,
        )
        .join(Product, Inventory.product_id == Product.id)
        .join(Location, Inventory.location_code == Location.code)
        .join(Warehouse, Location.warehouse_id == Warehouse.id)
    )

    # 可选条件筛选（keyword 走 LIKE 模糊，warehouseId 走 locations.warehouse_id 索引）
    if keyword:
        query = query.filter(
            (Product.name.contains(keyword)) | (Product.sku.contains(keyword))
        )
    if warehouseId is not None:
        query = query.filter(Location.warehouse_id == warehouseId)

    # total 在分页条件之前统计（count 在子查询上聚合，不触发全表取行）
    total = query.count()
    rows = (
        query.order_by(Inventory.id.desc())
        .offset((page - 1) * pageSize)
        .limit(pageSize)
        .all()
    )

    return {
        "code": 200,
        "message": "success",
        "data": {
            "list": [
                {
                    "productId": r.product_id,
                    "productName": r.product_name,
                    "sku": r.sku,
                    "locationCode": r.location_code,
                    "warehouseName": r.warehouse_name,
                    "quantity": r.quantity,
                    "updatedAt": r.updated_at,
                }
                for r in rows
            ],
            "total": total,
            "page": page,
            "pageSize": pageSize,
        },
    }
