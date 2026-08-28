import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session


@pytest.mark.asyncio
async def test_get_session():
    async for session in get_session():
        assert isinstance(session, AsyncSession)
