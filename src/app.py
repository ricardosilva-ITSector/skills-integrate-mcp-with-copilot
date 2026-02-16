"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
import os
from pathlib import Path
from contextlib import asynccontextmanager

from database import init_db, get_session, seed_initial_data, Activity, Participant


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
    session: AsyncSession = Depends(get_session)
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
    session: AsyncSession = Depends(get_session)
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
    session: AsyncSession = Depends(get_session)
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

