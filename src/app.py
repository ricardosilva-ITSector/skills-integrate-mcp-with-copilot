"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional

from database import init_db, get_session, seed_initial_data, Activity, Participant, User, UserRole


# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# Pydantic models for request/response
class ActivityCreate(BaseModel):
    name: str
    description: str
    schedule: str
    max_participants: int


class ActivityUpdate(BaseModel):
    description: str | None = None
    schedule: str | None = None
    max_participants: int | None = None


class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.STUDENT


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[UserRole] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: UserRole
    created_at: datetime

    class Config:
        from_attributes = True


# Authentication helper functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session)
) -> User:
    """Get the current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, role=UserRole(role) if role else None)
    except JWTError:
        raise credentials_exception
    
    # Get user from database
    result = await session.execute(
        select(User).where(User.username == token_data.username)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user


def require_role(*allowed_roles: UserRole):
    """Dependency to check if user has required role"""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
    return role_checker


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database
    await init_db()
    await seed_initial_data()
    yield
    # Shutdown: Clean up resources if needed


app = FastAPI(
    title="Mergington High School API",
    description="API for viewing and signing up for extracurricular activities",
    lifespan=lifespan
)

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


# Authentication endpoints

@app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    session: AsyncSession = Depends(get_session)
):
    """Register a new user"""
    # Check if username already exists
    result = await session.execute(
        select(User).where(User.username == user_data.username)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    result = await session.execute(
        select(User).where(User.email == user_data.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        role=user_data.role
    )
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    
    return new_user


@app.post("/auth/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session)
):
    """Login and receive JWT token"""
    # Find user by username
    result = await session.execute(
        select(User).where(User.username == form_data.username)
    )
    user = result.scalar_one_or_none()
    
    # Verify credentials
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role.value},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user information"""
    return current_user


@app.post("/auth/refresh", response_model=Token)
async def refresh_token(current_user: User = Depends(get_current_user)):
    """Refresh JWT token"""
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": current_user.username, "role": current_user.role.value},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/activities")
async def get_activities(session: AsyncSession = Depends(get_session)):
    """Get all activities with their participants"""
    result = await session.execute(select(Activity))
    activities = result.scalars().all()
    
    # Format response to match the original structure
    activities_dict = {}
    for activity in activities:
        activities_dict[activity.name] = {
            "description": activity.description,
            "schedule": activity.schedule,
            "max_participants": activity.max_participants,
            "participants": [p.email for p in activity.participants]
        }
    
    return activities_dict


@app.post("/activities/{activity_name}/signup")
async def signup_for_activity(
    activity_name: str, 
    email: str,
    session: AsyncSession = Depends(get_session)
):
    """Sign up a student for an activity"""
    # Find the activity
    result = await session.execute(
        select(Activity).where(Activity.name == activity_name)
    )
    activity = result.scalar_one_or_none()
    
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    # Check if student is already signed up
    result = await session.execute(
        select(Participant).where(
            Participant.activity_id == activity.id,
            Participant.email == email
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )
    
    # Check if activity is full
    participant_count = len(activity.participants)
    if participant_count >= activity.max_participants:
        raise HTTPException(
            status_code=400,
            detail="Activity is full"
        )
    
    # Add student
    new_participant = Participant(email=email, activity_id=activity.id)
    session.add(new_participant)
    await session.commit()
    
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
async def unregister_from_activity(
    activity_name: str,
    email: str,
    session: AsyncSession = Depends(get_session)
):
    """Unregister a student from an activity"""
    # Find the activity
    result = await session.execute(
        select(Activity).where(Activity.name == activity_name)
    )
    activity = result.scalar_one_or_none()
    
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    # Find the participant
    result = await session.execute(
        select(Participant).where(
            Participant.activity_id == activity.id,
            Participant.email == email
        )
    )
    participant = result.scalar_one_or_none()
    
    if not participant:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )
    
    # Remove student
    await session.delete(participant)
    await session.commit()
    
    return {"message": f"Unregistered {email} from {activity_name}"}


# Admin endpoints for CRUD operations

@app.post("/admin/activities")
async def create_activity(
    activity: ActivityCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.ACTIVITY_ADMIN))
):
    """Create a new activity (Admin only)"""
    # Check if activity already exists
    result = await session.execute(
        select(Activity).where(Activity.name == activity.name)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Activity with this name already exists"
        )
    
    # Create new activity
    new_activity = Activity(
        name=activity.name,
        description=activity.description,
        schedule=activity.schedule,
        max_participants=activity.max_participants
    )
    session.add(new_activity)
    await session.commit()
    await session.refresh(new_activity)
    
    return {
        "message": "Activity created successfully",
        "activity": {
            "name": new_activity.name,
            "description": new_activity.description,
            "schedule": new_activity.schedule,
            "max_participants": new_activity.max_participants
        }
    }


@app.put("/admin/activities/{activity_name}")
async def update_activity(
    activity_name: str,
    activity_update: ActivityUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.ACTIVITY_ADMIN))
):
    """Update an existing activity (Admin only)"""
    # Find the activity
    result = await session.execute(
        select(Activity).where(Activity.name == activity_name)
    )
    activity = result.scalar_one_or_none()
    
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    # Update fields if provided
    if activity_update.description is not None:
        activity.description = activity_update.description
    if activity_update.schedule is not None:
        activity.schedule = activity_update.schedule
    if activity_update.max_participants is not None:
        activity.max_participants = activity_update.max_participants
    
    await session.commit()
    await session.refresh(activity)
    
    return {
        "message": "Activity updated successfully",
        "activity": {
            "name": activity.name,
            "description": activity.description,
            "schedule": activity.schedule,
            "max_participants": activity.max_participants
        }
    }


@app.delete("/admin/activities/{activity_name}")
async def delete_activity(
    activity_name: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.ACTIVITY_ADMIN))
):
    """Delete an activity (Admin only)"""
    # Find the activity
    result = await session.execute(
        select(Activity).where(Activity.name == activity_name)
    )
    activity = result.scalar_one_or_none()
    
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    # Delete the activity (participants will be cascade deleted)
    await session.delete(activity)
    await session.commit()
    
    return {"message": f"Activity '{activity_name}' deleted successfully"}

