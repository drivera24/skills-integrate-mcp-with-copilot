"""
Authorization middleware and utilities

Provides middleware for request-level authorization context and decorators
for granular permission checking.
"""

from functools import wraps
from typing import Optional, Callable, List
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from models import User, Authorization, AuthorizationContext


# Global variable to store current user in request context
_current_user: Optional[User] = None


class AuthorizationMiddleware(BaseHTTPMiddleware):
    """Middleware to set authorization context from request"""

    def __init__(self, app, get_current_user_func: Optional[Callable] = None):
        """
        Initialize authorization middleware

        Args:
            app: FastAPI application
            get_current_user_func: Optional function to extract user from request
        """
        super().__init__(app)
        self.get_current_user_func = get_current_user_func

    async def dispatch(self, request: Request, call_next):
        """
        Process request and set authorization context

        Args:
            request: HTTP request
            call_next: Next middleware/handler

        Returns:
            Response with authorization context set
        """
        global _current_user

        # Extract user from request if getter function provided
        if self.get_current_user_func:
            _current_user = await self.get_current_user_func(request)
        else:
            _current_user = None

        try:
            response = await call_next(request)
        finally:
            _current_user = None

        return response


def get_current_user() -> Optional[User]:
    """Get the current user from the authorization context"""
    return _current_user


def set_current_user(user: Optional[User]) -> None:
    """Set the current user in the authorization context"""
    global _current_user
    _current_user = user


def require_authorization(authorization: Authorization):
    """
    Decorator to enforce authorization on a route

    Args:
        authorization: Authorization strategy to enforce

    Raises:
        HTTPException: If user is not authorized

    Example:
        @app.get("/admin")
        @require_authorization(RoleAuthorization(["admin"]))
        def admin_route():
            return {"message": "Admin only"}
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            user = get_current_user()
            if not authorization.authorize(user, **kwargs):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User is not authorized to perform this action"
                )
            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            user = get_current_user()
            if not authorization.authorize(user, **kwargs):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User is not authorized to perform this action"
                )
            return func(*args, **kwargs)

        # Return async or sync wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def require_authorizations(authorizations: List[Authorization], require_all: bool = True):
    """
    Decorator to enforce multiple authorization strategies

    Args:
        authorizations: List of authorization strategies
        require_all: If True, user must pass all authorizations
                     If False, user must pass at least one

    Raises:
        HTTPException: If user is not authorized

    Example:
        @app.post("/activity/{activity_id}/unregister")
        @require_authorizations([
            RoleAuthorization(["teacher"]),
            OwnershipAuthorization()
        ])
        def teacher_or_owner_only():
            return {"message": "Authorized"}
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            user = get_current_user()
            context = AuthorizationContext()

            for auth in authorizations:
                context.add_authorization(auth)

            is_authorized = context.check(user, **kwargs) if require_all else context.check_any(user, **kwargs)

            if not is_authorized:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User is not authorized to perform this action"
                )
            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            user = get_current_user()
            context = AuthorizationContext()

            for auth in authorizations:
                context.add_authorization(auth)

            is_authorized = context.check(user, **kwargs) if require_all else context.check_any(user, **kwargs)

            if not is_authorized:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User is not authorized to perform this action"
                )
            return func(*args, **kwargs)

        # Return async or sync wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def check_authorization(authorization: Authorization, **kwargs) -> bool:
    """
    Check authorization for current user

    Args:
        authorization: Authorization strategy to check
        **kwargs: Additional authorization context

    Returns:
        True if authorized, False otherwise

    Example:
        if check_authorization(RoleAuthorization(["teacher"]), user=current_user):
            # Allow action
    """
    user = get_current_user()
    return authorization.authorize(user, **kwargs)


def check_authorizations(authorizations: List[Authorization], require_all: bool = True, **kwargs) -> bool:
    """
    Check multiple authorization strategies

    Args:
        authorizations: List of authorization strategies
        require_all: If True, all must pass; if False, any can pass
        **kwargs: Additional authorization context

    Returns:
        True if authorized, False otherwise
    """
    user = get_current_user()
    context = AuthorizationContext()

    for auth in authorizations:
        context.add_authorization(auth)

    return context.check(user, **kwargs) if require_all else context.check_any(user, **kwargs)
