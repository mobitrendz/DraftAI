import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.crud.activity import create_activity
from app.db import database
from app.models.user import User

logger = structlog.get_logger(__name__)


class ActivityLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Process the request
        response = await call_next(request)

        # Log activity asynchronously after response is ready
        try:
            # Extract details
            method = request.method
            path = request.url.path
            status_code = response.status_code
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")

            # Check for user in request state (set by get_current_user dependency)
            user: User | None = getattr(request.state, "user", None)
            user_id = user.id if user else None

            # Create a new session for logging to avoid conflicts with request session
            async with database.async_session_maker() as session:
                await create_activity(
                    session=session,
                    user_id=user_id,
                    method=method,
                    path=path,
                    status_code=status_code,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
        except Exception as e:
            # We don't want activity logging to break the main request
            logger.error("Failed to log user activity", error=str(e))

        return response
