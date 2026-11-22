
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings
from app.core.database_config import build_connect_args


class Base(DeclarativeBase):
    pass


# Load application settings
settings = get_settings()

# Database connection configuration
connect_args = build_connect_args(
    settings.database_url,
    settings.db_ssl_enabled,
    settings.db_ssl_ca_file,
)


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
