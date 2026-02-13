# Mergington High School Activities API - Multi-Tenant Edition

A FastAPI application that allows students to view and sign up for extracurricular activities with **Multi-Tenant Support** and complete data isolation per tenant.

## Features

- **Multi-Tenant Architecture** - Complete data isolation per organization
- View all available extracurricular activities for your tenant
- Sign up for activities
- Tenant-specific authentication keys with expiration
- Role-Based Access Control (RBAC)
- Teacher and admin management capabilities
- Tenant management endpoints

## Multi-Tenant Support

The platform supports multiple schools/organizations running on the same infrastructure with complete data isolation.

### Tenant Authentication

Every request must be authenticated with a tenant's authentication key. There are three ways to authenticate:

1. **X-Tenant-Key Header** (Recommended)
   ```bash
   curl -H "X-Tenant-Key: <auth-key>" http://localhost:8000/activities
   ```

2. **Host/Domain Header**
   ```bash
   curl -H "Host: mergington.local" http://localhost:8000/activities
   ```

3. **X-Tenant-ID Header**
   ```bash
   curl -H "X-Tenant-ID: <tenant-id>" http://localhost:8000/activities
   ```

### Sample Tenants

Two sample tenants are created on startup:

| Tenant | Domain | Auth Key | Credentials |
|--------|--------|----------|-------------|
| Mergington High School | mergington.local | `<generated>` | teacher@mergington.edu |
| Riverside Academy | riverside.local | `<generated>` | teacher@riverside.edu |

Auth keys are printed to console on startup.

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Run the application:

   ```
   python app.py
   ```

3. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

4. Note the printed auth keys for the sample tenants

## API Endpoints

### Tenant Management (Admin only)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/tenant` | Get current tenant information |
| GET | `/tenant/auth-keys` | List all auth keys for current tenant (admin) |
| POST | `/tenant/auth-keys/generate` | Generate new auth key for current tenant (admin) |

### Activity Management (Tenant-Isolated)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/activities` | Get all activities for current tenant |
| POST | `/activities/{activity_name}/signup?email=student@org.edu` | Sign up for activity |
| DELETE | `/activities/{activity_name}/unregister?email=student@org.edu` | Unregister (teachers/admins only) |

### User Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/user/roles` | Get current user's roles for current tenant |

## Data Isolation

All data is scoped to the tenant:

- ✅ Activities are isolated per tenant
- ✅ Users are isolated per tenant
- ✅ Queries automatically filter by `tenant_id`
- ✅ Cross-tenant data access is impossible
- ✅ Each tenant has its own authentication keys

## Architecture

```
┌─────────────────────────────────────────────────┐
│           FastAPI Application                    │
├─────────────────────────────────────────────────┤
│  TenantMiddleware (Extract tenant from request)  │
│         ↓                                         │
│  AuthorizationMiddleware (User authentication)   │
│         ↓                                         │
│  Routes (All requests have tenant context)       │
└─────────────────────────────────────────────────┘

Data Storage:
┌──────────────────────────────────────────┐
│  In-Memory Tenants Data                   │
├──────────────────────────────────────────┤
│  Tenant A:                                │
│    - Activities (isolated)                │
│    - Users (isolated)                     │
│    - Auth Keys                            │
├──────────────────────────────────────────┤
│  Tenant B:                                │
│    - Activities (isolated)                │
│    - Users (isolated)                     │
│    - Auth Keys                            │
└──────────────────────────────────────────┘
```

## Roles and Permissions

### Available Roles

1. **Student**
   - Permissions: `view_activities`, `signup_activity`

2. **Teacher**
   - Permissions: `view_activities`, `signup_activity`, `unregister_student`, `manage_activities`

3. **Administrator**
   - Permissions: All permissions

## Example Usage

### Get Mergington's Activities
```bash
# Using auth key
curl -H "X-Tenant-Key: <mergington-auth-key>" http://localhost:8000/activities

# Output shows only Mergington activities
```

### Get Riverside's Activities
```bash
# Using auth key
curl -H "X-Tenant-Key: <riverside-auth-key>" http://localhost:8000/activities

# Output shows only Riverside activities (different from Mergington)
```

### Sign Up Student (Using Host Header)
```bash
curl -X POST "http://localhost:8000/activities/Chess%20Club/signup?email=student@mergington.edu" \
  -H "Host: mergington.local" \
  -H "X-User-Email: teacher@mergington.edu"
```

### Generate New Auth Key (Admin Only)
```bash
curl -X POST http://localhost:8000/tenant/auth-keys/generate?expiration_days=90 \
  -H "X-Tenant-Key: <admin-auth-key>" \
  -H "X-User-Email: admin@org.edu"
```

### Check Current Tenant
```bash
curl http://localhost:8000/tenant \
  -H "X-Tenant-Key: <auth-key>"

# Returns:
# {
#   "id": "...",
#   "name": "Mergington High School",
#   "domain": "mergington.local",
#   "active": true,
#   "created_at": "2026-02-13T...",
#   "metadata": {...}
# }
```

## Authentication Flow

1. Client sends request with tenant authentication key
2. TenantMiddleware extracts and validates the key
3. Sets tenant context (`TenantContext`)
4. AuthorizationMiddleware extracts user information
5. All routes operate within the tenant context
6. Data is automatically scoped to current tenant

## Code Structure

- `app.py` - FastAPI application with multi-tenant support
- `models.py` - RBAC models (Role, User, Authorization)
- `auth.py` - Authorization middleware
- `tenant.py` - Tenant models (Tenant, TenantAuthKey, TenantStore)
- `tenant_middleware.py` - Tenant context management middleware
- `static/` - Frontend assets

## Multi-Tenant Security

- ✅ All queries filtered by `tenant_id`
- ✅ Auth keys expire automatically
- ✅ Invalid tenants cannot access data
- ✅ Cross-tenant data access is prevented
- ✅ Tenant context verified on every request
- ✅ Complete data isolation per tenant

## Data Model

All data entities include `tenant_id` field for isolation:

```python
Activity = {
    "tenant_id": "...",  # Scoped to tenant
    "name": "...",
    "description": "...",
    "participants": [...]
}
```

## Production Considerations

For production use:
- Replace in-memory storage with a database
- Add `tenant_id` index to all tables
- Use database-level row-level security
- Implement tenant quota management
- Add audit logging per tenant
- Use JWT tokens with tenant claims
- Implement rate limiting per tenant
