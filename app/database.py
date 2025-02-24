from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import create_engine, MetaData
import os
# Testing Paths
# # Database URLs
POSTGRES_USER = "postgres"
POSTGRES_HOST = "localhost"
POSTGRES_PORT = "5433"
POSTGRES_DB = "multitenant_chatbot_db"
SYNC_DATABASE_URL = f"postgresql+psycopg2://{POSTGRES_USER}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
ASYNC_DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
# NEO_DATABASE_URL = "postgresql://neondb_owner:qLYxB2EwWTi1@ep-autumn-darkness-a55ku0kh.us-east-2.aws.neon.tech/neondb?sslmode=require"
# Production configuration
# POSTGRES_USER = "postgres"
# POSTGRES_PASSWORD = "secret"  # Replace with the actual password
# POSTGRES_HOST = "138.201.226.205"
# POSTGRES_PORT = "5434"
# POSTGRES_DB = "dpa_bot_prod"
#
# # Synchronous database URL
# SYNC_DATABASE_URL = (f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
#
# # Asynchronous database URL
# ASYNC_DATABASE_URL = (f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")


# neo_engine = create_engine(
#     NEO_DATABASE_URL,
#     echo=True,
#     pool_size=30,        # Increase the pool size for better connection handling
#     max_overflow=50,     # Allow up to 50 extra connections beyond the pool size
#     pool_timeout=60,     # Increase the timeout to 60 seconds for long-running jobs
#     pool_recycle=3600    # Recycle connections every 1 hour to prevent them from hanging too long
# )
# SessionLocalNeo = sessionmaker(autocommit=False, autoflush=False, bind=neo_engine)

# ------------------------------
# Synchronous Database Setup
# ------------------------------
engine = create_engine(
    SYNC_DATABASE_URL,
    echo=False,
    pool_size=300,        # Increase the pool size for better connection handling
    max_overflow=100,     # Allow up to 50 extra connections beyond the pool size
    pool_timeout=60,     # Increase the timeout to 60 seconds for long-running jobs
    pool_recycle=3600    # Recycle connections every 1 hour to prevent them from hanging too long
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    Dependency to get a synchronous database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ------------------------------
# Asynchronous Database Setup
# ------------------------------
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=False,
    pool_size=300,  # Increase the pool size for better connection handling
    max_overflow=100,  # Allow up to 50 extra connections beyond the pool size
    pool_timeout=60,  # Increase the timeout to 60 seconds for long-running jobs
    pool_recycle=3600  # Recycle connections every 1 hour to prevent them from hanging too long
)
AsyncSessionLocal = async_sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)

async def get_async_db():
    """
    Dependency to get an asynchronous database session.
    """
    async with AsyncSessionLocal() as session:
        yield session

# ------------------------------
# Declarative Base
# ------------------------------
metadata = MetaData()
Base = declarative_base()
