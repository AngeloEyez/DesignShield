"""
Alembic 資料庫遷移環境配置 (Alembic Migration Environment)
"""

from logging.config import fileConfig
import os
import sys

from sqlalchemy import engine_from_config, pool
from alembic import context

# 將專案根目錄加入 sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.app.core.config import settings
from backend.app.db.session import Base
# 匯入所有模型以註冊至 Base.metadata
import backend.app.models

# Alembic 設定物件
config = context.config

# 設定日誌
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 目標資料庫中繼資料
target_metadata = Base.metadata


def get_url() -> str:
    """取得資料庫連線字串"""
    return settings.DATABASE_URL


def run_migrations_offline() -> None:
    """離線執行遷移"""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """線上執行遷移"""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()

    # 針對 SQLite 避免連線參數問題
    if get_url().startswith("sqlite"):
        connectable = engine_from_config(
            configuration,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
    else:
        connectable = engine_from_config(
            configuration,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
