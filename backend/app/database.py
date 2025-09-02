from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
import os

# Convert postgresql:// to postgresql+asyncpg:// for async driver
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/glideator")
SYNC_DATABASE_URL = DATABASE_URL  # Keep sync URL for database setup

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Async engine and session for all operations  
SQL_ECHO = os.getenv("SQL_ECHO", "false").lower() == "true"
engine = create_async_engine(DATABASE_URL, echo=SQL_ECHO)
AsyncSessionLocal = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# Sync engine only for database table creation during setup
sync_engine = create_engine(SYNC_DATABASE_URL)

Base = declarative_base()