import os
from logging.config import fileConfig
from typing import cast

from alembic import context
from sqlalchemy import engine_from_config, pool

# 1. Import your Pydantic/Config engine helper and your Declarative Base
# Assuming a standard src/config.py and src/database/base.py structure
from src.config import settings 
from src.models.base import Base  

# 2. CRITICAL: Import ALL models here so SQLAlchemy registers them onto Base.metadata
from src.models.court import Court
from src.models.court_case import CourtCase
from src.models.hearing import Hearing
from src.models.charge import Charge
from src.models.case_charge import CaseCharge

# This is the Alembic Config object, which provides access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate support
target_metadata = Base.metadata

def get_url() -> str:
    """Dynamically fetches the database URL from environment variables."""
    # Prioritize a direct ENV override, otherwise fall back to your app settings
    return os.getenv("DATABASE_URL", settings.DATABASE_URL)

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate a connection with the context.
    """
    # Create a configuration dictionary and inject the dynamic database URL
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()