import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import system_log as system_log_crud


@pytest.mark.asyncio
async def test_create_system_log(session: AsyncSession):
    log = await system_log_crud.create_system_log(
        session=session,
        level="ERROR",
        message="Test error",
        path="/test",
        method="GET",
        status_code=500,
        context={"test": "data"},
    )

    assert log.level == "ERROR"
    assert log.message == "Test error"
    assert log.path == "/test"
    assert log.method == "GET"
    assert log.status_code == 500
    assert log.context == {"test": "data"}
    assert log.id is not None
    assert log.created_at is not None


@pytest.mark.asyncio
async def test_get_system_logs(session: AsyncSession):
    # Create multiple logs
    for i in range(5):
        await system_log_crud.create_system_log(
            session=session, level="INFO" if i % 2 == 0 else "ERROR", message=f"Log {i}"
        )

    # Get all logs
    logs = await system_log_crud.get_system_logs(session=session)
    assert logs.count >= 5
    assert len(logs.data) >= 5

    # Filter by level
    error_logs = await system_log_crud.get_system_logs(session=session, level="ERROR")
    assert error_logs.count >= 2
    assert all(log.level == "ERROR" for log in error_logs.data)
