"""Alembic environment configuration for Syndicate."""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

from syndicate.config import settings
from syndicate.db.models import Base

# Alembic Config object — provides access to values in the .ini file.
config = context.config

# Override sqlalchemy.url from application settings so the connection string
# lives in one place (.env / environment variables) rather than alembic.ini.
# Replace the asyncpg driver with psycopg2 for Alembic's synchronous engine.
sync_url = settings.database_url.replace("+asyncpg", "+psycopg2")
config.set_main_option("sqlalchemy.url", sync_url)

# Set up Python logging from the config file.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# MetaData object for autogenerate support.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Configures the context with just a URL so that an Engine (and therefore
    a live DBAPI connection) is not required.  Calls to context.execute()
    emit the given SQL string to the script output.
    """
    url = config.get_main_option("sqlalchemy.url")
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

    Creates an Engine and associates a connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
