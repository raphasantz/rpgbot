import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from contextlib import asynccontextmanager

load_dotenv()

# Use o driver aiosqlite para bancos SQLite locais ou asyncpg para PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///rpg_masmorra.db")

# 1. Ajuste de Segurança: Garantir que a URL use o driver asyncpg se for PostgreSQL
if DATABASE_URL and "postgresql" in DATABASE_URL and "+asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# 2. O motor agora é assíncrono com pool_pre_ping para conexões saudáveis
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True
)

# 3. A fábrica de sessões agora cria AsyncSessions
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# A 'Base' continua a mesma
Base = declarative_base()

# 4. O Context Manager agora é ASSÍNCRONO (async with)
@asynccontextmanager
async def get_async_db():
    """Gerenciador de contexto assíncrono para injeção de dependência do DB."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# Alias para compatibilidade com código legado - aponta para a versão assíncrona
get_db_session = get_async_db