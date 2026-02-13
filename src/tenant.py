"""
Multi-Tenant Architecture Models

Implements tenant management with data isolation and tenant-specific authentication.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional
import uuid


@dataclass
class TenantAuthKey:
    """Tenant-specific authentication key with expiration"""
    key: str
    created_at: datetime
    expires_at: datetime
    active: bool = True

    @classmethod
    def create(cls, expiration_days: int = 365) -> "TenantAuthKey":
        """
        Create a new authentication key

        Args:
            expiration_days: Number of days until key expires

        Returns:
            New TenantAuthKey instance
        """
        created_at = datetime.utcnow()
        expires_at = created_at + timedelta(days=expiration_days)
        key = str(uuid.uuid4())
        return cls(key=key, created_at=created_at, expires_at=expires_at)

    def is_valid(self) -> bool:
        """Check if the authentication key is valid and not expired"""
        return self.active and datetime.utcnow() < self.expires_at

    def revoke(self) -> None:
        """Revoke this authentication key"""
        self.active = False


@dataclass
class Tenant:
    """Tenant model representing an organization"""
    id: str
    name: str
    domain: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    auth_keys: List[TenantAuthKey] = field(default_factory=list)
    active: bool = True
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        """Initialize tenant with default auth key if not provided"""
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.auth_keys:
            self.auth_keys = [TenantAuthKey.create()]

    @classmethod
    def create(cls, name: str, domain: str, metadata: Optional[dict] = None) -> "Tenant":
        """
        Create a new tenant

        Args:
            name: Tenant organization name
            domain: Tenant's domain name (for request routing)
            metadata: Optional metadata about the tenant

        Returns:
            New Tenant instance
        """
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            domain=domain,
            metadata=metadata or {}
        )

    def get_valid_auth_key(self) -> Optional[TenantAuthKey]:
        """Get a valid authentication key for this tenant"""
        for key in self.auth_keys:
            if key.is_valid():
                return key
        return None

    def generate_new_auth_key(self, expiration_days: int = 365) -> TenantAuthKey:
        """
        Generate a new authentication key

        Args:
            expiration_days: Number of days until key expires

        Returns:
            New TenantAuthKey instance
        """
        new_key = TenantAuthKey.create(expiration_days=expiration_days)
        self.auth_keys.append(new_key)
        return new_key

    def revoke_auth_key(self, key: str) -> bool:
        """
        Revoke a specific authentication key

        Args:
            key: The key to revoke

        Returns:
            True if key was found and revoked, False otherwise
        """
        for auth_key in self.auth_keys:
            if auth_key.key == key:
                auth_key.revoke()
                return True
        return False

    def deactivate(self) -> None:
        """Deactivate this tenant"""
        self.active = False
        for key in self.auth_keys:
            key.revoke()

    def reactivate(self) -> None:
        """Reactivate this tenant"""
        if not self.active:
            self.active = True
            if not self.get_valid_auth_key():
                self.generate_new_auth_key()


@dataclass
class TenantContext:
    """Context for current tenant in a request"""
    tenant_id: str
    tenant: Tenant

    def is_valid(self) -> bool:
        """Check if the tenant context is valid"""
        return self.tenant.active


class TenantStore:
    """In-memory storage for multi-tenant data"""

    def __init__(self):
        """Initialize the tenant store"""
        self.tenants: dict = {}  # tenant_id -> Tenant
        self.auth_key_to_tenant: dict = {}  # auth_key -> tenant_id

    def create_tenant(self, name: str, domain: str, metadata: Optional[dict] = None) -> Tenant:
        """Create and store a new tenant"""
        tenant = Tenant.create(name, domain, metadata)
        self.tenants[tenant.id] = tenant

        # Map auth keys to tenant
        for key in tenant.auth_keys:
            self.auth_key_to_tenant[key.key] = tenant.id

        return tenant

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Get a tenant by ID"""
        return self.tenants.get(tenant_id)

    def get_tenant_by_auth_key(self, auth_key: str) -> Optional[Tenant]:
        """Get a tenant by its authentication key"""
        tenant_id = self.auth_key_to_tenant.get(auth_key)
        if tenant_id:
            tenant = self.get_tenant(tenant_id)
            if tenant and tenant.get_valid_auth_key() and tenant.get_valid_auth_key().key == auth_key:
                return tenant
        return None

    def get_tenant_by_domain(self, domain: str) -> Optional[Tenant]:
        """Get a tenant by its domain"""
        for tenant in self.tenants.values():
            if tenant.domain == domain and tenant.active:
                return tenant
        return None

    def list_tenants(self) -> List[Tenant]:
        """List all active tenants"""
        return [t for t in self.tenants.values() if t.active]

    def deactivate_tenant(self, tenant_id: str) -> bool:
        """Deactivate a tenant"""
        tenant = self.get_tenant(tenant_id)
        if tenant:
            tenant.deactivate()
            return True
        return False

    def reactivate_tenant(self, tenant_id: str) -> bool:
        """Reactivate a tenant"""
        tenant = self.get_tenant(tenant_id)
        if tenant:
            tenant.reactivate()
            # Update auth key mapping
            for key in tenant.auth_keys:
                if key.is_valid():
                    self.auth_key_to_tenant[key.key] = tenant_id
            return True
        return False
