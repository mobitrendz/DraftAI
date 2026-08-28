import logging
import sys
from typing import Any

import structlog
from rich.console import Console
from rich.logging import RichHandler

from app.core.config import settings


def setup_logging() -> None:
    processors: list[Any] = [
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.ENVIRONMENT == "local" and "pytest" not in sys.modules:
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        wrapper_class=structlog.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Re-direct standard library logging to structlog/rich
    root_logger = logging.getLogger()

    if settings.ENVIRONMENT == "local" and "pytest" not in sys.modules:
        # Use RichHandler for beautiful local console output
        rich_handler = RichHandler(
            console=Console(force_terminal=True),
            rich_tracebacks=True,
            markup=True,
        )
        root_logger.addHandler(rich_handler)
        root_logger.setLevel(logging.INFO)
    else:
        handler = logging.StreamHandler(sys.stdout)
        formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer()
        )
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)
