from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from models import Base
from config import settings

# Crear engine
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    """Crear todas las tablas"""
    Base.metadata.create_all(bind=engine)
    print("✅ Tablas creadas/verificadas")

@contextmanager
def get_db_session() -> Session:
    """Context manager para sesiones de base de datos"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"❌ Error en sesión de BD: {e}")
        raise
    finally:
        session.close()