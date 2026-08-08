"""
pytest 全局配置 — 选做任务B

让每个测试使用独立的临时 SQLite 库（pytest 的 tmp_path），
通过 app.dependency_overrides 把 get_db 依赖替换为临时库会话，
避免污染真实的 wms.db（见 CLAUDE.md「测试建议用独立临时数据库」）。
"""
import logging
import sys
from pathlib import Path

# 把项目根目录加入 sys.path，保证 `import app` 可用
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 屏蔽 app/database.py 里 engine echo=True 的 SQL 日志（导入 app.main 时 create_all 会连一次真实库）。
# echo=True 会把 sqlalchemy.engine.Engine 的级别强制为 DEBUG，仅 setLevel 无效，需直接禁用该 logger。
logging.getLogger("sqlalchemy.engine.Engine").disabled = True

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def db_engine(tmp_path):
    """独立临时数据库：每个测试一个临时文件，互不污染"""
    db_file = tmp_path / "test_wms.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    """直连临时库的会话，供测试内直接断言数据库状态"""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture()
def client(db_engine):
    """TestClient：把 get_db 依赖替换为临时库会话，请求与断言同一数据库"""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
