# Mergington High School Activities API

A FastAPI application that allows students to view and sign up for extracurricular activities with **Role-Based Access Control (RBAC)**.

## Features

- View all available extracurricular activities
- Sign up for activities
- **Role-Based Access Control** with multiple authorization strategies
- Teacher and admin management capabilities
- Granular permission checking

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

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Sign up for an activity                                             |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Unregister a student from an activity (teachers/admins only) |
| GET    | `/user/roles`                                                     | Get current user's roles and permissions                            |
| GET    | `/roles`                                                          | Get all available roles (admin only)                                |

## Role-Based Access Control (RBAC)

### Available Roles

1. **Student**
   - Permissions: `view_activities`, `signup_activity`
   - Can view activities and sign up for them

2. **Teacher**
   - Permissions: `view_activities`, `signup_activity`, `unregister_student`, `manage_activities`
   - Can manage student registrations and activities

3. **Administrator**
   - Permissions: `view_activities`, `signup_activity`, `unregister_student`, `manage_activities`, `manage_users`, `manage_roles`
   - Full system access

### Authorization Strategies

The RBAC system supports multiple authorization strategies:

#### 1. RoleAuthorization
Check if user has specific roles:
```python
from models import RoleAuthorization
auth = RoleAuthorization(["teacher", "admin"])
# Check if user has teacher or admin role
```

#### 2. OwnershipAuthorization
Check if user owns a resource:
```python
from models import OwnershipAuthorization
auth = OwnershipAuthorization()
# Check if user owns the resource
```

#### 3. LimitedAccessAuthorization
Restrict access to specific roles:
```python
from models import LimitedAccessAuthorization
auth = LimitedAccessAuthorization(["admin"])
# Only admins can access
```

#### 4. AuthorizationExclusion
Exclude specific roles from access:
```python
from models import AuthorizationExclusion
auth = AuthorizationExclusion(["guest"])
# Everyone except guests can access
```

### Authentication

To authenticate as a user, include the `X-User-Email` header in your request:

```bash
curl -H "X-User-Email: teacher@mergington.edu" http://localhost:8000/user/roles
```

#### Available Test Users

- `teacher@mergington.edu` - Teacher account
- `admin@mergington.edu` - Administrator account

## Data Model

The application uses in-memory storage with the following models:

1. **Role** - Authorization role with name, label, and permissions
   - Attributes: name, label, private, permissions (set of strings)

2. **User** - User account with role associations and resource ownership
   - Attributes: email, name, roles (list of Role objects), owner_of (set of resource IDs)

3. **Activities** - Extracurricular activities
   - Attributes: description, schedule, max_participants, participants (list of emails), owner

All data is stored in memory, which means data will be reset when the server restarts.

## Code Structure

- `app.py` - FastAPI application with routes and RBAC integration
- `models.py` - RBAC models (Role, User, Authorization classes)
- `auth.py` - Authorization middleware and utilities
- `static/` - Frontend assets (HTML, CSS, JavaScript)

## Example Usage

### View Activities (No authentication required)
```bash
curl http://localhost:8000/activities
```

### Sign up for Activity (Any user)
```bash
curl -X POST "http://localhost:8000/activities/Chess%20Club/signup?email=student@mergington.edu" \
  -H "X-User-Email: student@mergington.edu"
```

### Unregister Student (Teachers and Admins only)
```bash
curl -X DELETE "http://localhost:8000/activities/Chess%20Club/unregister?email=student@mergington.edu" \
  -H "X-User-Email: teacher@mergington.edu"
```

### Check User Roles
```bash
curl http://localhost:8000/user/roles \
  -H "X-User-Email: teacher@mergington.edu"
```

### View All Roles (Admin only)
```bash
curl http://localhost:8000/roles \
  -H "X-User-Email: admin@mergington.edu"
```
