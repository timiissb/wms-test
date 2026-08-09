# 任务目录

> 本目录将 `docs/TASKS.md` 中的每个任务拆分为独立文档，供候选人逐项实现。
> 每个任务文件都包含：**业务需求 / 涉及的数据库表结构 / 接口规范 / 实现要点 / 考核点与验收标准**。
> 表结构以本仓库 `app/models.py`（SQLAlchemy / SQLite）为准，接口规范以 `docs/API_SPEC.md` 为准。

## 必做任务

| 文件 | 任务 | 当前状态 |
|------|------|----------|
| [task-1-inbound-order.md](./task-1-inbound-order.md) | 任务 1：入库单创建 | `POST /api/inbound-orders` 返回 501 |
| [task-2-inventory-query.md](./task-2-inventory-query.md) | 任务 2：库存查询 | `GET /api/inventory` 返回 501 |
| [task-3-bug-fix.md](./task-3-bug-fix.md) | 任务 3：Bug 修复 | 后端 BUG 已预埋于 `app/routers/products.py` |

## 选做任务

| 文件 | 任务 |
|------|------|
| [task-A-outbound-order.md](./task-A-outbound-order.md) | 选做 A：出库单 + 库存扣减（并发安全） |
| [task-B-unit-tests.md](./task-B-unit-tests.md) | 选做 B：单元测试 |
| [task-C-frontend-performance.md](./task-C-frontend-performance.md) | 选做 C：前端性能优化 |

## 提交要求（摘自 TASKS.md）

- 所有必做任务功能正常运行
- 代码可以一键启动（`uv sync && uvicorn app.main:app --reload`）
- Git 提交记录清晰，建议小步提交、message 有意义
- 在项目根目录填写 `NOTES.md`（AI 使用说明、遇到的问题、选做任务说明）
