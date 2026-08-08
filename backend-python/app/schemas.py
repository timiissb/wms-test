from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ============ 通用 ============

class ApiResponse(BaseModel):
    """统一响应格式"""
    code: int = 200
    message: str = "success"
    data: object = None


class PageResult(BaseModel):
    """分页结果"""
    list: list
    total: int
    page: int
    page_size: int


# ============ 商品（参考实现） ============

class ProductCreate(BaseModel):
    """创建商品请求"""
    name: str = Field(..., min_length=1, max_length=200, description="商品名称")
    sku: str = Field(..., min_length=1, max_length=50, description="SKU编码")
    unit: str = Field(default="个", max_length=20)


class ProductUpdate(BaseModel):
    """更新商品请求"""
    name: str = Field(..., min_length=1, max_length=200)
    unit: str | None = Field(default=None, max_length=20)


class ProductResponse(BaseModel):
    """商品响应"""
    id: int
    name: str
    sku: str
    unit: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ 入库单（候选人实现） ============

class InboundItemRequest(BaseModel):
    """入库明细请求（接口文档字段为 camelCase，见 API_SPEC.md）"""
    model_config = ConfigDict(populate_by_name=True)

    product_id: int = Field(..., gt=0, alias="productId", description="商品ID")
    quantity: int = Field(..., gt=0, description="入库数量")
    location_code: str = Field(
        ..., min_length=1, max_length=50, alias="locationCode", description="目标库位编码"
    )


class InboundOrderCreate(BaseModel):
    """创建入库单请求（接口文档字段为 camelCase，见 API_SPEC.md）"""
    model_config = ConfigDict(populate_by_name=True)

    supplier_name: str = Field(
        ..., min_length=1, max_length=200, alias="supplierName", description="供应商名称"
    )
    items: list[InboundItemRequest] = Field(..., min_length=1, description="入库明细")


# ============ 库存查询（候选人实现） ============

class InventoryResponse(BaseModel):
    """库存查询响应"""
    product_id: int
    product_name: str
    sku: str
    location_code: str
    warehouse_name: str | None = None
    quantity: int
    updated_at: datetime

    class Config:
        from_attributes = True
