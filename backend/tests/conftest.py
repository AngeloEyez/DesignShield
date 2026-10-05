"""
Pytest 測試環境通用 Fixture 配置 (Pytest Test Fixtures)

建立檔案式 SQLite 測試資料庫 Session 與 DBOS 實例，確保測試間狀態完全隔離且多連線/執行緒完全相容。
"""

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dbos import DBOS, DBOSConfig

TEST_DB_FILE = "./test_app.db"
TEST_DBOS_FILE = "./test_dbos.db"
TEST_DB_URL = f"sqlite:///{TEST_DB_FILE}"
TEST_DBOS_URL = f"sqlite:///{TEST_DBOS_FILE}"

# 設定測試環境變數
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["DBOS_SYSTEM_DATABASE_URL"] = TEST_DBOS_URL

from backend.app.core.config import settings
settings.DATABASE_URL = TEST_DB_URL
settings.DBOS_SYSTEM_DATABASE_URL = TEST_DBOS_URL

from backend.app.db.session import Base, get_db
import backend.app.db.session as session_module
import backend.app.workflows.drc_workflow as workflow_module
import backend.app.api.v1.endpoints.tasks as tasks_module
import backend.app.workflows.dbos_app as dbos_app_module
from backend.app.main import app

# 測試環境下避免 TestClient 的 lifespan 每次 exit 時 destroy 掉 session-scoped DBOS
dbos_app_module.shutdown_dbos = lambda: None

# 建立全域測試用 Engine 與 SessionMaker
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# 覆蓋 session 模組中的 engine 與 SessionLocal
session_module.engine = test_engine
session_module.SessionLocal = TestingSessionLocal
workflow_module.SessionLocal = TestingSessionLocal
tasks_module.SessionLocal = TestingSessionLocal


@pytest.fixture(scope="session", autouse=True)
def setup_dbos_for_testing():
    """在測試 Session 期間初始化並啟動 DBOS"""
    if os.path.exists(TEST_DBOS_FILE):
        try:
            os.remove(TEST_DBOS_FILE)
        except OSError:
            pass

    config = DBOSConfig(name="test_drc_app", system_database_url=TEST_DBOS_URL)
    dbos = DBOS(config=config)
    try:
        DBOS.launch()
    except Exception as e:
        print("DBOS Launch Notice in test:", e)
    
    yield dbos
    
    try:
        DBOS.destroy()
    except Exception:
        pass
    if os.path.exists(TEST_DBOS_FILE):
        try:
            os.remove(TEST_DBOS_FILE)
        except OSError:
            pass


@pytest.fixture(scope="function")
def db_session():
    """為每個測試案例提供獨立清空的資料庫 Session"""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    """提供覆蓋 get_db 依賴之 FastAPI TestClient"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
