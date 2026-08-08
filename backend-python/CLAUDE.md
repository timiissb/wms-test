# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目背景

这是一个 **WMS（仓库管理系统）线上测试题**的 Python/FastAPI 后端模板。仓库根目录（`wms-test/`）还包含 `backend-java/`、`frontend-vue/`、`frontend-react/`，业务需求相同，本目录只负责 FastAPI 后端。

候选人需要完成的任务拆解在 `tasks/*.md`（已 gitignore，但保留在本地），权威接口规范在 `docs/API_SPEC.md`（仓库根目录）。

**当前实现状态：**
- ✅ 已实现（参考风格）：商品 CRUD、仓库 & 库位查询
- ❌ 待实现：`POST /api/inbound-orders`、`GET /api/inventory`（当前在 `app/routers/inventory.py` 中返回 501）
- 🐞 已预埋 Bug：`app/routers/products.py` 的删除商品接口未校验关联库存（任务 3）
- 选做任务（出库单、单元测试）需自行新增模型/测试文件

## 常用命令

```bash
uv sync                    # 安装依赖
uv sync --extra dev        # 安装开发依赖（pytest/httpx/pytest-asyncio）
uv run uvicorn app.main:app --reload   # 启动服务 → http://localhost:8000/docs
uv run pytest              # 运行全部测试
uv run python init_data.py # 初始化示例数据（商品/仓库/库位/库存）
```

- 依赖与 pytest 配置在 `pyproject.toml`，已设 `asyncio_mode = "auto"`，异步测试无需手动 `@pytest.mark.asyncio`
- 数据库是 SQLite 文件 `wms.db`（已 gitignore），表由 `app/main.py` 导入时 `Base.metadata.create_all(bind=engine)` 自动创建，**无 alembic 迁移**（虽然依赖里有 alembic）

## 架构

单目录扁平结构，`app/` 下四块职责清晰：

- **`app/models.py`** — SQLAlchemy 2.0 `DeclarativeBase` 模型：`Product` / `Warehouse` / `Location` / `Inventory` / `InboundOrder` / `InboundOrderItem`。注意 `Inventory` 有联合唯一约束 `(product_id, location_code)`，入库是 upsert 累加
- **`app/schemas.py`** — Pydantic v2 schema：统一响应信封 `ApiResponse`、分页 `PageResult`、各接口的 Create/Update/Response
- **`app/routers/*.py`** — 每个路由文件一个 APIRouter，通过 `app/main.py` 注册。`products.py` / `warehouses.py` 是参考实现
- **`app/database.py`** — engine / `SessionLocal` / `get_db` FastAPI 依赖（每个请求一个 session）

### 必须遵守的约定

- **统一响应信封**：所有接口返回 `{"code": <http状态码>, "message": "...", "data": ...}`；`data` 为 `None` 表示无数据
- **错误处理**：用 `HTTPException(status_code=4xx, detail="中文错误信息")`，不吞异常
- **路由风格**：路由函数用 `db: Session = Depends(get_db)` 注入会话；参考实现中 `products.py` 用 `prefix="/api/products"`，`warehouses.py` / `inventory.py` 直接写全路径
- **查询参数命名**：FastAPI 实现用 snake_case（`page_size`、`warehouse_id`），而 `docs/API_SPEC.md` 写的是 camelCase（`pageSize`、`warehouseId`）——这是已知命名差异，后端保持一致即可
- **SQL 注入防护**：始终用 SQLAlchemy 参数化查询（`.filter(Model.col == value)`），不拼接字符串
- 注释、错误消息、日志均为中文

### 关键注意点

- **SQLite 限制**：不支持 `SELECT ... FOR UPDATE`，出库扣减的并发安全要用「原子条件 UPDATE」（`UPDATE inventory SET quantity=quantity-N WHERE product_id=? AND location_code=? AND quantity>=N`，`rowcount==0` 即不足），见 `tasks/task-A-outbound-order.md`
- **入库单号**格式 `IN-YYYYMMDD-XXX`，当日递增序号，靠唯一约束兜底并发
- 入库/出库全程在一个事务内完成（单请求同一 `db` 会话，失败 `db.rollback()`），否则会出现「订单已建但库存没动」的脏数据
- 测试建议用独立临时数据库或 fixture 清理，避免污染 `wms.db`（见 `tasks/task-B-unit-tests.md`）

## 参考文档

- 任务详情：`tasks/task-{1,2,3,A,B,C}-*.md`
- 接口规范：`../docs/API_SPEC.md`
- 业务说明：`../TASKS.md`、`../README.md`、`../AI_USAGE_GUIDE.md`
