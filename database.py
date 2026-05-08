import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import contextmanager

load_dotenv()

# Pegamos a URL do banco que você colocou no .env
DATABASE_URL = os.getenv("DATABASE_URL")

# O 'engine' é o motor que realmente faz o barulho de conexão
engine = create_engine(DATABASE_URL)

# A 'Session' é como uma conversa aberta com o banco
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# A 'Base' é a semente de onde todos os nossos modelos vão nascer
Base = declarative_base()

@contextmanager
def get_db_session():
    """Context manager que abre, commita/rollback e fecha a sessão automaticamente."""
    db = SessionLocal()
    try:
        yield db
        db.commit()  # Sucesso → confirma todas as alterações
    except Exception:
        db.rollback()  # Erro → desfaz qualquer alteração pendente
        raise  # Relança a exceção para o código que chamou
    finally:
        db.close()