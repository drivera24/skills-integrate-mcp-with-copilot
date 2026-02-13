"""
Tenant Middleware and Context Management

Provides middleware for extracting and managing tenant context from requests,
ensuring complete data isolation per tenant.
"""

from typing import Optional, Callable
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from tenant import Tenant, TenantContext, TenantStore


# Global tenant store
_tenant_store: TenantStore = TenantStore()

# Global variable to store current tenant context in request
_current_tenant: Optional[TenantContext] = None


class TenantMiddleware(BaseHTTPMiddleware):
    """Middleware to extract and manage tenant context from requests"""

    def __init__(self, app, tenant_store: Optional[TenantStore] = None):
        """
        Initialize tenant middleware

        Args:
            app: FastAPI application
            tenant_store: Optional TenantStore instance (uses global if not provided)
        """
        super().__init__(app)
        self.tenant_store = tenant_store or _tenant_store

    async def dispatch(self, request: Request, call_next):
        """
        Process request and set tenant context

        Args:
            request: HTTP request
            call_next: Next middleware/handler

        Returns:
            Response with tenant context set

        Raises:
            HTTPException: If tenant cannot be identified or is inactive
        """
        global _current_tenant

        # Try to extract tenant from request
        tenant = await self._extract_tenant(request)

        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tenant authentication required. Provide X-Tenant-Key header or Host header"
            )

        if not tenant.active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant is inactive"
            )

        # Set tenant context
        _current_tenant = TenantContext(tenant_id=tenant.id, tenant=tenant)

        try:
            response = await call_next(request)
        finally:
            _current_tenant = None

        return response

    async def _extract_tenant(self, request: Request) -> Optional[Tenant]:
        """
        Extract tenant from request

        Priority:
        1. X-Tenant-Key header (auth key)
        2. Host/Domain header
        3. X-Tenant-ID header (for admin operations)

        Args:
            request: HTTP request

        Returns:
            Tenant instance if found, None otherwise
        """
        # Try auth key first (highest priority)
        auth_key = request.headers.get("X-Tenant-Key")
        if auth_key:
            tenant = self.tenant_store.get_tenant_by_auth_key(auth_key)
            if tenant:
                return tenant

        # Try domain/host
        host = request.headers.get("Host") or request.headers.get("X-Tenant-Domain")
        if host:
            # Extract domain without port
            domain = host.split(":")[0]
            tenant = self.tenant_store.get_tenant_by_domain(domain)
            if tenant:
                return tenant

        # Try tenant ID (for direct requests, requires auth key or other verification)
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            tenant = self.tenant_store.get_tenant(tenant_id)
            if tenant:
                return tenant

        return None


def get_current_tenant() -> Optional[TenantContext]:
    """Get the current tenant context from the request"""
    return _current_tenant


def get_current_tenant_id() -> Optional[str]:
    """Get the current tenant ID"""
    if _current_tenant:
        return _current_tenant.tenant_id
    return None


def set_tenant_store(tenant_store: TenantStore) -> None:
    """Set a new tenant store"""
    global _tenant_store
    _tenant_store = tenant_store


def get_tenant_store() -> TenantStore:
    """Get the current tenant store"""
    return _tenant_store


def require_tenant(func: Callable):
    """
    Decorator to ensure current request has a valid tenant

    Raises:
        HTTPException: If no tenant context is available

    Example:
        @app.get("/protected")
        @require_tenant
        def protected_route():
            return {"message": "Tenant authenticated"}
    """
    async def wrapper(*args, **kwargs):
        tenant_context = get_current_tenant()
        if not tenant_context or not tenant_context.is_valid():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid or missing tenant context"
            )
        return await func(*args, **kwargs)

    return wrapper


def filter_by_tenant(data: dict, tenant_id: Optional[str] = None) -> dict:
    """
    Add tenant_id to data dictionary for storage

    Args:
        data: Data dictionary
        tenant_id: Tenant ID (uses current context if not provided)

    Returns:
        Data dictionary with tenant_id added
    """
    if tenant_id is None:
        tenant_id = get_current_tenant_id()

    if tenant_id:
        data["tenant_id"] = tenant_id

    return data


def ensure_tenant_isolation(data_item: dict, tenant_id: Optional[str] = None) -> bool:
    """
    Check if data item belongs to the current tenant

    Args:
        data_item: Data item to check
        tenant_id: Expected tenant ID (uses current context if not provided)

    Returns:
        True if data item belongs to tenant, False otherwise
    """
    if tenant_id is None:
        tenant_id = get_current_tenant_id()

    return data_item.get("tenant_id") == tenant_id
