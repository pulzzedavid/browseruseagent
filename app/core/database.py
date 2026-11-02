"""
Database configuration and connection management
"""

import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from app.core.config import settings

logger = logging.getLogger(__name__)

# Create async engine
engine = None
async_session_maker = None

# Base class for models
Base = declarative_base()


async def init_db():
    """Initialize database connection"""
    global engine, async_session_maker
    
    try:
        # Convert PostgreSQL URL to async format
        if settings.database_url.startswith("postgresql://"):
            async_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        else:
            async_url = settings.database_url
        
        # Create async engine
        engine = create_async_engine(
            async_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            echo=settings.debug,
            pool_pre_ping=True,
        )
        
        # Create session maker
        async_session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        # Test connection
        async with engine.begin() as conn:
            await conn.run_sync(lambda _: None)
        
        logger.info("Database connection established successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def close_db():
    """Close database connection"""
    global engine
    
    if engine:
        await engine.dispose()
        logger.info("Database connection closed")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session"""
    if not async_session_maker:
        raise RuntimeError("Database not initialized")
    
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables():
    """Create all tables"""
    if not engine:
        raise RuntimeError("Database not initialized")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database tables created successfully")


async def drop_tables():
    """Drop all tables"""
    if not engine:
        raise RuntimeError("Database not initialized")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    logger.info("Database tables dropped successfully")
