"""
出库单 API — 选做任务A

并发安全方案：原子条件 UPDATE（SQLite 友好）。
「检查库存是否充足」与「扣减」合并为一条 UPDATE：
    UPDATE inventory SET quantity = quantity - :n
    WHERE product_id=:p AND location_code=:l AND quantity >= :n
rowcount == 0 即失败（库存不足或行不存在），从数据库层面杜绝超卖。
SQLite 为单写者数据库，写事务天然串行；本方案无需 version 字段、无需重试。
整个出库单与全部明细扣减在同一事务内，任一失败 db.rollback() 整体回滚。
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Inventory, Location, OutboundOrder, OutboundOrderItem, Product
from app.schemas import OutboundOrderCreate

router = APIRouter(tags=["出库单"])

# 出库单号格式 OUT-YYYYMMDD-XXX，XXX 为当日递增序号
ORDER_NO_PREFIX = "OUT"
# 并发下单号唯一约束冲突时的最大重试次数（递增序号后重试）
MAX_ORDER_NO_RETRY = 3


def _next_order_seq(db: Session) -> int:
    """取当日最大出库单号的序号，返回下一序号（无单则从 1 开始）"""
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"{ORDER_NO_PREFIX}-{today}-"
    last = (
        db.query(OutboundOrder.order_no)
        .filter(OutboundOrder.order_no.like(f"{prefix}%"))
        .order_by(OutboundOrder.order_no.desc())
        .first()
    )
    if not last:
        return 1
    return int(last[0].rsplit("-", 1)[1]) + 1


def _build_order_data(order: OutboundOrder) -> dict:
    """构造出库单响应数据（字段对齐接口文档 API_SPEC.md，camelCase）"""
    return {
        "id": order.id,
        "orderNo": order.order_no,
        "customerName": order.customer_name,
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


@router.post("/api/outbound-orders", status_code=201)
def create_outbound_order(req: OutboundOrderCreate, db: Session = Depends(get_db)):
    """
    创建出库单 — 选做任务A（并发安全：原子条件 UPDATE）

    要求：
    1. 校验商品、库位是否存在
    2. 生成出库单号 OUT-YYYYMMDD-XXX
    3. 逐条明细原子扣减库存（quantity >= 出库数 才扣，防止超卖）
    4. 整个流程单事务：全部成功 commit，任一失败 rollback
    """
    # 校验商品、库位是否存在（失败抛 400，事务未开始无需回滚）
    for item in req.items:
        if not db.query(Product).filter(Product.id == item.product_id).first():
            raise HTTPException(status_code=400, detail=f"商品不存在: {item.product_id}")
        if not db.query(Location).filter(Location.code == item.location_code).first():
            raise HTTPException(status_code=400, detail=f"库位不存在: {item.location_code}")

    seq = _next_order_seq(db)
    for _ in range(MAX_ORDER_NO_RETRY):
        try:
            order = OutboundOrder(
                order_no=f"{ORDER_NO_PREFIX}-{datetime.now().strftime('%Y%m%d')}-{seq:03d}",
                customer_name=req.customer_name,
                status="COMPLETED",
            )
            db.add(order)
            db.flush()  # 先拿到 order.id，再写明细

            # 逐条创建明细 + 原子条件扣减库存
            for item in req.items:
                db.add(
                    OutboundOrderItem(
                        order_id=order.id,
                        product_id=item.product_id,
                        quantity=item.quantity,
                        location_code=item.location_code,
                    )
                )
                # 「检查 + 扣减」在同一条原子 UPDATE 内：quantity >= n 才扣，防超卖
                stmt = (
                    update(Inventory)
                    .where(
                        Inventory.product_id == item.product_id,
                        Inventory.location_code == item.location_code,
                        Inventory.quantity >= item.quantity,
                    )
                    .values(
                        quantity=Inventory.quantity - item.quantity,
                        updated_at=datetime.now(),
                    )
                )
                if db.execute(stmt).rowcount == 0:
                    # rowcount==0 无法区分「库存不足」与「库位无库存」，再查一次行是否存在
                    inv = (
                        db.query(Inventory)
                        .filter(
                            Inventory.product_id == item.product_id,
                            Inventory.location_code == item.location_code,
                        )
                        .first()
                    )
                    if inv is None:
                        raise HTTPException(
                            status_code=400,
                            detail=f"该商品在该库位无库存: {item.product_id}@{item.location_code}",
                        )
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"库存不足: 商品{item.product_id}@{item.location_code} "
                            f"剩余{inv.quantity}"
                        ),
                    )

            db.commit()
            db.refresh(order)
            return {
                "code": 201,
                "message": "出库单创建成功",
                "data": _build_order_data(order),
            }
        except HTTPException:
            # 业务失败（库存不足等）：回滚全部，不产生部分扣减，再抛出给 FastAPI
            db.rollback()
            raise
        except IntegrityError:
            # 并发下 order_no 唯一约束冲突：回滚后递增序号重试
            db.rollback()
            seq += 1

    raise HTTPException(status_code=500, detail="出库单号生成失败，请重试")
