"""
Role-Based Access Control Models

Implements comprehensive authorization system with multiple authorization strategies.
"""

from dataclasses import dataclass, field
from typing import List, Set, Optional
from enum import Enum


class AuthorizationType(Enum):
    """Types of authorization strategies"""
    ROLE_BASED = "role_based"
    OWNERSHIP_BASED = "ownership_based"
    LIMITED_ACCESS = "limited_access"
    EXCLUSION = "exclusion"


@dataclass
class Role:
    """Role model with name, label, and privacy settings"""
    name: str
    label: str
    private: bool = False
    permissions: Set[str] = field(default_factory=set)

    def add_permission(self, permission: str) -> None:
        """Add a permission to this role"""
        self.permissions.add(permission)

    def remove_permission(self, permission: str) -> None:
        """Remove a permission from this role"""
        self.permissions.discard(permission)

    def has_permission(self, permission: str) -> bool:
        """Check if role has a specific permission"""
        return permission in self.permissions


@dataclass
class User:
    """User model with role associations"""
    email: str
    name: str
    roles: List[Role] = field(default_factory=list)
    owner_of: Set[str] = field(default_factory=set)  # Resource IDs owned by user

    def add_role(self, role: Role) -> None:
        """Add a role to the user"""
        if role not in self.roles:
            self.roles.append(role)

    def remove_role(self, role: Role) -> None:
        """Remove a role from the user"""
        if role in self.roles:
            self.roles.remove(role)

    def has_role(self, role_name: str) -> bool:
        """Check if user has a specific role"""
        return any(role.name == role_name for role in self.roles)

    def has_permission(self, permission: str) -> bool:
        """Check if user has a permission through any of their roles"""
        return any(role.has_permission(permission) for role in self.roles)

    def owns_resource(self, resource_id: str) -> bool:
        """Check if user owns a specific resource"""
        return resource_id in self.owner_of


class Authorization:
    """Base class for authorization strategies"""

    def authorize(self, user: Optional[User], **kwargs) -> bool:
        """
        Determine if user is authorized

        Args:
            user: The user to check authorization for
            **kwargs: Additional context for authorization

        Returns:
            True if authorized, False otherwise
        """
        raise NotImplementedError


class RoleAuthorization(Authorization):
    """Authorization based on user roles"""

    def __init__(self, required_roles: List[str]):
        """
        Initialize role-based authorization

        Args:
            required_roles: List of role names required for authorization
        """
        self.required_roles = required_roles

    def authorize(self, user: Optional[User], **kwargs) -> bool:
        """Check if user has any of the required roles"""
        if not user:
            return False
        return any(user.has_role(role_name) for role_name in self.required_roles)


class OwnershipAuthorization(Authorization):
    """Authorization based on resource ownership"""

    def __init__(self):
        """Initialize ownership-based authorization"""
        pass

    def authorize(self, user: Optional[User], resource_id: Optional[str] = None, **kwargs) -> bool:
        """Check if user owns the resource"""
        if not user or not resource_id:
            return False
        return user.owns_resource(resource_id)


class LimitedAccessAuthorization(Authorization):
    """Restrict access to specific roles"""

    def __init__(self, allowed_roles: List[str]):
        """
        Initialize limited access authorization

        Args:
            allowed_roles: List of role names allowed to access resource
        """
        self.allowed_roles = allowed_roles

    def authorize(self, user: Optional[User], **kwargs) -> bool:
        """Check if user has one of the allowed roles"""
        if not user:
            return False
        return any(user.has_role(role_name) for role_name in self.allowed_roles)


class AuthorizationExclusion(Authorization):
    """Exclude specific roles from access"""

    def __init__(self, excluded_roles: List[str]):
        """
        Initialize authorization exclusion

        Args:
            excluded_roles: List of role names to exclude from access
        """
        self.excluded_roles = excluded_roles

    def authorize(self, user: Optional[User], **kwargs) -> bool:
        """Check if user does NOT have any of the excluded roles"""
        if not user:
            return True
        return not any(user.has_role(role_name) for role_name in self.excluded_roles)


class AuthorizationContext:
    """Manages authorization checks across the application"""

    def __init__(self):
        """Initialize authorization context"""
        self.authorizations: List[Authorization] = []

    def add_authorization(self, authorization: Authorization) -> "AuthorizationContext":
        """Add an authorization strategy (fluent API)"""
        self.authorizations.append(authorization)
        return self

    def check(self, user: Optional[User], **kwargs) -> bool:
        """
        Check if user passes all authorization strategies

        Args:
            user: The user to check
            **kwargs: Additional authorization context

        Returns:
            True if all authorizations pass, False otherwise
        """
        return all(auth.authorize(user, **kwargs) for auth in self.authorizations)

    def check_any(self, user: Optional[User], **kwargs) -> bool:
        """
        Check if user passes any authorization strategy

        Args:
            user: The user to check
            **kwargs: Additional authorization context

        Returns:
            True if any authorization passes, False otherwise
        """
        if not self.authorizations:
            return True
        return any(auth.authorize(user, **kwargs) for auth in self.authorizations)
