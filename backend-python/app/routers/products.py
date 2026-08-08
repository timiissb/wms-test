"""
商品管理 API — 参考实现

展示了：FastAPI 路由、Pydantic 校验、异常处理、CRUD 操作
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Inventory, Product
from app.schemas import ProductCreate, ProductUpdate, ProductResponse

router = APIRouter(prefix="/api/products", tags=["商品管理"])


@router.get("")
def list_products(keyword: str | None = None, db: Session = Depends(get_db)):
    """商品列表 — 支持模糊搜索"""
    query = db.query(Product)
    if keyword:
        query = query.filter(
            (Product.name.contains(keyword)) | (Product.sku.contains(keyword))
        )
    products = query.all()
    return {"code": 200, "message": "success", "data": products}


@router.get("/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):
    """商品详情"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    return {"code": 200, "message": "success", "data": product}


@router.post("", status_code=201)
def create_product(req: ProductCreate, db: Session = Depends(get_db)):
    """创建商品"""
    # 检查 SKU 是否已存在
    existing = db.query(Product).filter(Product.sku == req.sku).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"SKU已存在: {req.sku}")

    product = Product(name=req.name, sku=req.sku, unit=req.unit)
    db.add(product)
    db.commit()
    db.refresh(product)
    return {"code": 201, "message": "创建成功", "data": product}


@router.put("/{product_id}")
def update_product(product_id: int, req: ProductUpdate, db: Session = Depends(get_db)):
    """更新商品"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    product.name = req.name
    if req.unit is not None:
        product.unit = req.unit
    db.commit()
    db.refresh(product)
    return {"code": 200, "message": "更新成功", "data": product}


@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """删除商品"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    # 修复（任务3 Bug1）：删除前校验是否有关联库存，避免删除后库存数据孤立。
    # SQLite 默认未开启外键约束，不能依赖数据库外键兜底，必须在应用层校验。
    if db.query(Inventory).filter(Inventory.product_id == product_id).first():
        raise HTTPException(status_code=400, detail="该商品存在关联库存，无法删除")

    db.delete(product)
    db.commit()
    return {"code": 200, "message": "删除成功", "data": None}
