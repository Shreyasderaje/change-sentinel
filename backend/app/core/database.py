
import ssl

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


# Load application settings
settings = get_settings()

# Database connection configuration
connect_args = {}

if settings.database_url.startswith("sqlite"):
    connect_args = {
        "check_same_thread": False
    }

elif settings.database_url.startswith("postgresql+pg8000"):
    # Enable verified SSL for Supabase PostgreSQL
    ssl_context = ssl.create_default_context(
        cafile=settings.db_ssl_ca_file
    )

    connect_args = {
        "ssl_context": ssl_context
    }


# Create SQLAlchemy database engine
engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)


# Database session factory
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


# FastAPI database dependency
def get_db():
    with SessionLocal() as session:
        yield session
