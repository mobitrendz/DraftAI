import uuid
from typing import Any, cast

from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from app.models.system_log import SystemLog, SystemLogsPublic


async def create_system_log(
    *,
    session: AsyncSession,
    level: str,
    message: str,
    stack_trace: str | None = None,
    path: str | None = None,
    method: str | None = None,
    status_code: int | None = None,
    user_id: uuid.UUID | None = None,
    context: dict[str, Any] | None = None,
) -> SystemLog:
    db_log = SystemLog(
        level=level,
        message=message,
        stack_trace=stack_trace,
        path=path,
        method=method,
        status_code=status_code,
        user_id=user_id,
        context=context,
    )
    session.add(db_log)
    await session.commit()
    await session.refresh(db_log)
    return db_log


async def get_system_logs(
    *, session: AsyncSession, limit: int = 50, level: str | None = None
) -> SystemLogsPublic:
    statement = (
        select(SystemLog).order_by(desc(cast(Any, SystemLog.created_at))).limit(limit)
    )
    if level:
        statement = statement.where(SystemLog.level == level)

    count_statement = select(func.count()).select_from(SystemLog)
    if level:
        count_statement = count_statement.where(SystemLog.level == level)

    result = await session.execute(statement)
    logs = result.scalars().all()

    count_result = await session.execute(count_statement)
    total_count = count_result.scalar() or 0

    return SystemLogsPublic(data=list(logs), count=total_count)
