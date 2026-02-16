"""
Database configuration and models for the High School Management System
"""

from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base as async_declarative_base
import os

# Database URL - using SQLite for simplicity
DATABASE_URL = "sqlite+aiosqlite:///./school_activities.db"

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=True, future=True)

# Create async session
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = async_declarative_base()


class Activity(Base):
    """Activity model representing an extracurricular activity"""
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)
    schedule = Column(String(200), nullable=False)
    max_participants = Column(Integer, nullable=False)

    # Relationship to participants
    participants = relationship("Participant", back_populates="activity", cascade="all, delete-orphan")


class Participant(Base):
    """Participant model representing a student enrolled in an activity"""
    __tablename__ = "participants"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), nullable=False, index=True)
    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=False)

    # Relationship to activity
    activity = relationship("Activity", back_populates="participants")


async def init_db():
    """Initialize the database and create tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    """Dependency to get database session"""
    async with async_session() as session:
        yield session


async def seed_initial_data():
    """Seed the database with initial activity data"""
    async with async_session() as session:
        # Check if data already exists
        from sqlalchemy import select
        result = await session.execute(select(Activity))
        existing = result.scalars().first()
        
        if existing:
            return  # Data already seeded
        
        # Initial activities data
        initial_activities = [
            {
                "name": "Chess Club",
                "description": "Learn strategies and compete in chess tournaments",
                "schedule": "Fridays, 3:30 PM - 5:00 PM",
                "max_participants": 12,
                "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
            },
            {
                "name": "Programming Class",
                "description": "Learn programming fundamentals and build software projects",
                "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
                "max_participants": 20,
                "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
            },
            {
                "name": "Gym Class",
                "description": "Physical education and sports activities",
                "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
                "max_participants": 30,
                "participants": ["john@mergington.edu", "olivia@mergington.edu"]
            },
            {
                "name": "Soccer Team",
                "description": "Join the school soccer team and compete in matches",
                "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
                "max_participants": 22,
                "participants": ["liam@mergington.edu", "noah@mergington.edu"]
            },
            {
                "name": "Basketball Team",
                "description": "Practice and play basketball with the school team",
                "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
                "max_participants": 15,
                "participants": ["ava@mergington.edu", "mia@mergington.edu"]
            },
            {
                "name": "Art Club",
                "description": "Explore your creativity through painting and drawing",
                "schedule": "Thursdays, 3:30 PM - 5:00 PM",
                "max_participants": 15,
                "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
            },
            {
                "name": "Drama Club",
                "description": "Act, direct, and produce plays and performances",
                "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
                "max_participants": 20,
                "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
            },
            {
                "name": "Math Club",
                "description": "Solve challenging problems and participate in math competitions",
                "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
                "max_participants": 10,
                "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
            },
            {
                "name": "Debate Team",
                "description": "Develop public speaking and argumentation skills",
                "schedule": "Fridays, 4:00 PM - 5:30 PM",
                "max_participants": 12,
                "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
            }
        ]
        
        # Add activities and participants
        for activity_data in initial_activities:
            participants_list = activity_data.pop("participants")
            activity = Activity(**activity_data)
            session.add(activity)
            await session.flush()  # Get the activity ID
            
            # Add participants
            for email in participants_list:
                participant = Participant(email=email, activity_id=activity.id)
                session.add(participant)
        
        await session.commit()
