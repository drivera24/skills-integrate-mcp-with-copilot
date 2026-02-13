"""
High School Management System API - Multi-Tenant Edition

A FastAPI application that allows students to view and sign up for extracurricular
activities with complete multi-tenant support and data isolation per tenant.

Features:
- Multi-tenant architecture with complete data isolation
- Tenant-specific authentication keys
- Role-based access control (RBAC)
- Tenant management endpoints
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from models import (
    Role, User, RoleAuthorization, OwnershipAuthorization
)
from auth import (
    AuthorizationMiddleware, get_current_user, set_current_user,
    check_authorization
)
from tenant import Tenant, TenantStore, TenantAuthKey
from tenant_middleware import (
    TenantMiddleware, get_current_tenant, get_current_tenant_id,
    get_tenant_store, filter_by_tenant, ensure_tenant_isolation
)

app = FastAPI(
    title="Mergington High School API - Multi-Tenant",
    description="API for viewing and signing up for extracurricular activities with multi-tenant support"
)

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# ============================================================================
# Multi-Tenant Setup
# ============================================================================

# Create and initialize tenant store
tenant_store = TenantStore()

# Create sample tenants
mergington_tenant = tenant_store.create_tenant(
    name="Mergington High School",
    domain="mergington.local",
    metadata={"country": "USA", "state": "California"}
)

riverside_tenant = tenant_store.create_tenant(
    name="Riverside Academy",
    domain="riverside.local",
    metadata={"country": "USA", "state": "Texas"}
)

print(f"Mergington Auth Key: {mergington_tenant.get_valid_auth_key().key}")
print(f"Riverside Auth Key: {riverside_tenant.get_valid_auth_key().key}")

# ============================================================================
# RBAC Setup - Define Roles
# ============================================================================

student_role = Role(
    name="student",
    label="Student",
    private=False,
    permissions={"view_activities", "signup_activity"}
)

teacher_role = Role(
    name="teacher",
    label="Teacher",
    private=False,
    permissions={"view_activities", "signup_activity", "unregister_student", "manage_activities"}
)

admin_role = Role(
    name="admin",
    label="Administrator",
    private=False,
    permissions={"view_activities", "signup_activity", "unregister_student", "manage_activities", "manage_users", "manage_roles"}
)

# In-memory storage for tenant data
# Structure: {tenant_id: {data_type: [items]}}
tenants_data = {
    mergington_tenant.id: {
        "users": {
            "teacher@mergington.edu": User(
                email="teacher@mergington.edu",
                name="Ms. Johnson",
                roles=[teacher_role]
            )
        },
        "activities": {
            "Chess Club": {
                "tenant_id": mergington_tenant.id,
                "description": "Learn strategies and compete in chess tournaments",
                "schedule": "Fridays 3:30 PM - 5:00 PM",
                "max_participants": 12,
                "participants": ["michael@mergington.edu"]
            },
            "Programming Class": {
                "tenant_id": mergington_tenant.id,
                "description": "Learn programming fundamentals",
                "schedule": "Tuesdays and Thursdays 3:30 PM - 4:30 PM",
                "max_participants": 20,
                "participants": ["emma@mergington.edu"]
            }
        }
    },
    riverside_tenant.id: {
        "users": {
            "teacher@riverside.edu": User(
                email="teacher@riverside.edu",
                name="Mr. Smith",
                roles=[teacher_role]
            )
        },
        "activities": {
            "Soccer Team": {
                "tenant_id": riverside_tenant.id,
                "description": "Join the school soccer team",
                "schedule": "Tuesdays and Thursdays 4:00 PM - 5:30 PM",
                "max_participants": 22,
                "participants": ["liam@riverside.edu"]
            },
            "Art Club": {
                "tenant_id": riverside_tenant.id,
                "description": "Explore creativity through painting and drawing",
                "schedule": "Thursdays 3:30 PM - 5:00 PM",
                "max_participants": 15,
                "participants": ["sarah@riverside.edu"]
            }
        }
    }
}

# ============================================================================
# Middleware Setup
# ============================================================================

# Add tenant middleware (must be before auth middleware)
app.add_middleware(TenantMiddleware, tenant_store=tenant_store)

# Add auth middleware
async def get_current_user_from_request(request: Request) -> Optional[User]:
    """Extract and return current user from request headers"""
    tenant_context = get_current_tenant()
    if not tenant_context:
        return None

    user_email = request.headers.get("X-User-Email")
    if user_email and tenant_context.tenant_id in tenants_data:
        users = tenants_data[tenant_context.tenant_id].get("users", {})
        if user_email in users:
            return users[user_email]
    return None

app.add_middleware(AuthorizationMiddleware, get_current_user_func=get_current_user_from_request)

# ============================================================================
# Routes
# ============================================================================

@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


# ============================================================================
# Tenant Management Endpoints
# ============================================================================

@app.get("/tenant")
def get_current_tenant_info():
    """Get current tenant information"""
    tenant_context = get_current_tenant()
    if not tenant_context:
        return {"error": "No tenant context"}

    tenant = tenant_context.tenant
    return {
        "id": tenant.id,
        "name": tenant.name,
        "domain": tenant.domain,
        "active": tenant.active,
        "created_at": tenant.created_at.isoformat(),
        "metadata": tenant.metadata
    }


@app.get("/tenant/auth-keys")
def get_tenant_auth_keys():
    """Get current tenant's authentication keys (admin only)"""
    tenant_context = get_current_tenant()
    if not tenant_context:
        raise HTTPException(status_code=403, detail="No tenant context")

    user = get_current_user()
    if not check_authorization(RoleAuthorization(["admin"]), user=user):
        raise HTTPException(status_code=403, detail="Only admins can view auth keys")

    tenant = tenant_context.tenant
    return {
        "tenant_id": tenant.id,
        "auth_keys": [
            {
                "key": key.key,
                "created_at": key.created_at.isoformat(),
                "expires_at": key.expires_at.isoformat(),
                "active": key.active,
                "valid": key.is_valid()
            }
            for key in tenant.auth_keys
        ]
    }


@app.post("/tenant/auth-keys/generate")
def generate_new_tenant_auth_key(expiration_days: int = 365):
    """Generate a new authentication key for current tenant (admin only)"""
    tenant_context = get_current_tenant()
    if not tenant_context:
        raise HTTPException(status_code=403, detail="No tenant context")

    user = get_current_user()
    if not check_authorization(RoleAuthorization(["admin"]), user=user):
        raise HTTPException(status_code=403, detail="Only admins can generate auth keys")

    tenant = tenant_context.tenant
    new_key = tenant.generate_new_auth_key(expiration_days)

    return {
        "key": new_key.key,
        "created_at": new_key.created_at.isoformat(),
        "expires_at": new_key.expires_at.isoformat(),
        "message": f"New auth key generated. Valid for {expiration_days} days"
    }


# ============================================================================
# Activity Endpoints (Tenant-Isolated)
# ============================================================================

@app.get("/activities")
def get_activities():
    """Get all activities for current tenant"""
    tenant_context = get_current_tenant()
    if not tenant_context:
        raise HTTPException(status_code=403, detail="No tenant context")

    tenant_id = tenant_context.tenant_id
    if tenant_id in tenants_data:
        activities = tenants_data[tenant_id].get("activities", {})
        # Return only activities for this tenant
        return {
            name: activity for name, activity in activities.items()
            if ensure_tenant_isolation(activity, tenant_id)
        }
    return {}


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity (tenant-isolated)"""
    tenant_context = get_current_tenant()
    if not tenant_context:
        raise HTTPException(status_code=403, detail="No tenant context")

    tenant_id = tenant_context.tenant_id
    user = get_current_user()

    # Check authorization
    if not check_authorization(RoleAuthorization(["student", "teacher"]), user=user):
        raise HTTPException(status_code=403, detail="Only students and teachers can sign up")

    # Get tenant's activities
    if tenant_id not in tenants_data:
        raise HTTPException(status_code=400, detail="Tenant has no activities")

    activities = tenants_data[tenant_id]["activities"]

    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    activity = activities[activity_name]

    # Verify activity belongs to this tenant
    if not ensure_tenant_isolation(activity, tenant_id):
        raise HTTPException(status_code=403, detail="Access denied")

    # Check if already signed up
    if email in activity["participants"]:
        raise HTTPException(status_code=400, detail="Student already signed up")

    # Check capacity
    if len(activity["participants"]) >= activity["max_participants"]:
        raise HTTPException(status_code=400, detail="Activity is at capacity")

    # Add student
    activity["participants"].append(email)
    return {
        "message": f"Signed up {email} for {activity_name}",
        "tenant": tenant_context.tenant.name
    }


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity (teachers/admins only, tenant-isolated)"""
    tenant_context = get_current_tenant()
    if not tenant_context:
        raise HTTPException(status_code=403, detail="No tenant context")

    tenant_id = tenant_context.tenant_id
    user = get_current_user()

    # Check authorization
    if not check_authorization(RoleAuthorization(["teacher", "admin"]), user=user):
        raise HTTPException(status_code=403, detail="Only teachers/admins can unregister")

    # Get tenant's activities
    if tenant_id not in tenants_data:
        raise HTTPException(status_code=400, detail="Tenant has no activities")

    activities = tenants_data[tenant_id]["activities"]

    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    activity = activities[activity_name]

    # Verify activity belongs to this tenant
    if not ensure_tenant_isolation(activity, tenant_id):
        raise HTTPException(status_code=403, detail="Access denied")

    # Check if student is signed up
    if email not in activity["participants"]:
        raise HTTPException(status_code=400, detail="Student not signed up")

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}


@app.get("/user/roles")
def get_user_roles():
    """Get current user's roles and permissions (tenant-aware)"""
    tenant_context = get_current_tenant()
    user = get_current_user()

    if not user:
        return {
            "authenticated": False,
            "tenant": tenant_context.tenant.name if tenant_context else None,
            "message": "No user authenticated. Include X-User-Email header"
        }

    return {
        "authenticated": True,
        "email": user.email,
        "name": user.name,
        "tenant": tenant_context.tenant.name if tenant_context else None,
        "roles": [role.name for role in user.roles],
        "permissions": list(set(perm for role in user.roles for perm in role.permissions))
    }
