import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from contextlib import asynccontextmanager

load_dotenv()

# Pegamos a URL do banco que você colocou no .env
DATABASE_URL = os.getenv("DATABASE_URL")

# 1. Ajuste de Segurança: Garantir que a URL use o driver asyncpg
if DATABASE_URL and "+asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# 2. O motor agora é assíncrono (echo=False em produção para não poluir logs)
engine = create_async_engine(DATABASE_URL, echo=False)

# 3. A fábrica de sessões agora cria AsyncSessions
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False # Importante: mantém os objetos acessíveis após o commit assíncrono
)

# A 'Base' continua a mesma
Base = declarative_base()

# 4. O Context Manager agora é ASSÍNCRONO (async with)
@asynccontextmanager
async def get_db_session():
    """Context manager assíncrono que abre, commita/rollback e fecha a sessão."""
    db = AsyncSessionLocal()
    try:
        yield db
        await db.commit()  # Commit assíncrono
    except Exception:
        await db.rollback()  # Rollback assíncrono
        raise
    finally:
        await db.close()  # Close assíncrono