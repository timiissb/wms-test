from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.routers import products, warehouses, inventory, outbound

# 创建所有表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="WMS API",
    description="仓储管理系统 API",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(products.router)
app.include_router(warehouses.router)
app.include_router(inventory.router)
app.include_router(outbound.router)


@app.get("/")
def root():
    return {"message": "WMS API is running. Visit /docs for API documentation."}
