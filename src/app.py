"""
High School Management System API

A FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.

Now with Role-Based Access Control (RBAC) for authorization!
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
import os
from pathlib import Path
from typing import Optional

from models import (
    Role, User, RoleAuthorization, OwnershipAuthorization,
    LimitedAccessAuthorization, AuthorizationExclusion
)
from auth import (
    AuthorizationMiddleware, get_current_user, set_current_user,
    require_authorization, check_authorization
)

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities with RBAC")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# ============================================================================
# RBAC Setup - Define Roles
# ============================================================================

# Create roles
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

# Store roles in memory
roles_db = {
    "student": student_role,
    "teacher": teacher_role,
    "admin": admin_role
}

# In-memory user database with roles
users_db = {
    "teacher@mergington.edu": User(
        email="teacher@mergington.edu",
        name="Ms. Johnson",
        roles=[teacher_role]
    ),
    "admin@mergington.edu": User(
        email="admin@mergington.edu",
        name="Dr. Smith",
        roles=[admin_role]
    )
}

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"],
        "owner": "teacher@mergington.edu"
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"],
        "owner": "teacher@mergington.edu"
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"],
        "owner": "admin@mergington.edu"
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"],
        "owner": "teacher@mergington.edu"
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"],
        "owner": "teacher@mergington.edu"
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"],
        "owner": "admin@mergington.edu"
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"],
        "owner": "teacher@mergington.edu"
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"],
        "owner": "teacher@mergington.edu"
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"],
        "owner": "admin@mergington.edu"
    }
}

# ============================================================================
# Middleware Setup
# ============================================================================

# Async function to extract current user from request
async def get_current_user_from_request(request: Request) -> Optional[User]:
    """Extract and return current user from request headers"""
    # Check for user email in headers (simplified for this example)
    user_email = request.headers.get("X-User-Email")
    if user_email and user_email in users_db:
        return users_db[user_email]
    return None

# Add authorization middleware
app.add_middleware(AuthorizationMiddleware, get_current_user_func=get_current_user_from_request)

# ============================================================================
# Routes
# ============================================================================

@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    """Get all activities with their details"""
    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    # Check authorization
    user = get_current_user()

    # Allow signup if user has student role or is a teacher (managing on behalf of student)
    if not check_authorization(RoleAuthorization(["student", "teacher"]), user=user):
        raise HTTPException(
            status_code=403,
            detail="Only students and teachers can sign up for activities"
        )

    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Check capacity
    if len(activity["participants"]) >= activity["max_participants"]:
        raise HTTPException(
            status_code=400,
            detail="Activity is at maximum capacity"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity (teachers and admins only)"""
    # Check authorization
    user = get_current_user()

    # Only teachers and admins can unregister students
    if not check_authorization(RoleAuthorization(["teacher", "admin"]), user=user):
        raise HTTPException(
            status_code=403,
            detail="Only teachers and administrators can unregister students"
        )

    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}


@app.get("/user/roles")
def get_user_roles():
    """Get current user's roles and permissions"""
    user = get_current_user()

    if not user:
        return {
            "authenticated": False,
            "message": "No user authenticated. Include X-User-Email header to authenticate"
        }

    return {
        "authenticated": True,
        "email": user.email,
        "name": user.name,
        "roles": [role.name for role in user.roles],
        "permissions": list(set(perm for role in user.roles for perm in role.permissions))
    }


@app.get("/roles")
def get_all_roles():
    """Get all available roles (admin only)"""
    user = get_current_user()

    if not check_authorization(RoleAuthorization(["admin"]), user=user):
        raise HTTPException(
            status_code=403,
            detail="Only administrators can view roles"
        )

    return {
        role_name: {
            "label": role.label,
            "private": role.private,
            "permissions": list(role.permissions)
        }
        for role_name, role in roles_db.items()
    }
