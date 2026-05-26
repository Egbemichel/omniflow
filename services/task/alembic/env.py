import sys
from logging.config import fileConfig
from pathlib import Path

_APP_ROOT = Path(__file__).resolve().parent.parent / "app"
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT.parent))

from sqlalchemy import engine_from_config, pool, text  # noqa: E402
from alembic import context  # noqa: E402
import os  # noqa: E402
from app.models import Base  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url():
    return os.getenv("DATABASE_URL", "sqlite:///./task.db")


def run_migrations_offline() -> None:
    url = get_url()
    schema = os.getenv("DATABASE_SCHEMA", "task_schema")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema=schema if not url.startswith("sqlite") else None,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = get_url()
    schema = os.getenv("DATABASE_SCHEMA", "task_schema")
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = url
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        if not url.startswith("sqlite"):
            connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
            connection.execute(text(f"SET search_path TO {schema}"))
            connection.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=schema if not url.startswith("sqlite") else None,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
