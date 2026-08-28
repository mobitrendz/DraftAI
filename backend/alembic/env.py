from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

from alembic import context
from app.core.config import settings
from app.models.activity import UserActivity  # noqa: F401
from app.models.ai_agent_config import AIAgentConfig  # noqa: F401
from app.models.ai_catalog import AIModelRow, AIProviderRow  # noqa: F401
from app.models.content import (  # noqa: F401
    ContentDraft,
    CoverImage,
    DevtoArticle,
    LinkedinPost,
    PublishJob,
)
from app.models.platform_config import PlatformConfig  # noqa: F401
from app.models.system_log import SystemLog  # noqa: F401
from app.models.user import User  # noqa: F401

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
assert config.config_file_name is not None  # noqa: S101
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
# target_metadata = None


target_metadata = SQLModel.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_url():
    return str(settings.SQLALCHEMY_DATABASE_URI)


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_url()
    print(f"Running migrations offline with URL: {url}")
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True, compare_type=True
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    print(f"Running migrations online with URL: {get_url()}")

    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()  # ty:ignore[invalid-assignment]
    connectable = engine_from_config(
        configuration,  # ty:ignore[invalid-argument-type]
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, compare_type=True
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
