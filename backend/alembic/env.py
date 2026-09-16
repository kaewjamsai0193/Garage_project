import os

from alembic import context
from sqlalchemy import create_engine

import app.models  # noqa: F401  (ลงทะเบียนตารางทั้งหมด)
from app.db import Base

engine = create_engine(os.environ["DATABASE_URL"])
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
