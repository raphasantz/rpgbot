"""Database configuration for MezzaRPG Web - sync version using modelos_web."""
from modelos_web import SessionLocal, init_db, get_db, Base, engine, JogadorWeb, CampanhaWeb

# Export for backward compatibility
__all__ = ["SessionLocal", "init_db", "get_db", "Base", "engine", "JogadorWeb", "CampanhaWeb"]