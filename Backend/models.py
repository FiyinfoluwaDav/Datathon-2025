from sqlalchemy import Column, Integer, String, Text, ARRAY, DateTime, Float
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import ENUM
import enum
from database import Base

# Define Python Enum classes for dropdowns
class Sex(enum.Enum):
    Male = "Male"
    Female = "Female"

class VisitType(enum.Enum):
    Emergency = "Emergency"
    Acute = "Acute"
    Routine = "Routine"
    FollowUp = "Follow-up"

# Create SQLAlchemy ENUM types for PostgreSQL
SexEnum = ENUM(Sex, name="sex_enum", create_type=True)
VisitTypeEnum = ENUM(VisitType, name="visit_type_enum", create_type=True)


class PHCUser(Base):
    __tablename__ = "phc_users"

    id = Column(Integer, primary_key=True, index=True)
    phc_id = Column(String, unique=True, index=True)
    phc_name = Column(String, unique=True, index=True)
    password = Column(String)


class Patient(Base):
    """Registered Patients - Demographics and Clinical Data"""
    __tablename__ = "patients"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    age = Column(Integer, nullable=False)
    sex = Column(SexEnum, nullable=False)  # Dropdown: 'Male', 'Female'
    symptoms = Column(ARRAY(String), nullable=False)  # e.g., ['fever', 'cough']
    visit_type = Column(VisitTypeEnum, nullable=False)  # Dropdown: 'Emergency', 'Acute', 'Routine', 'Follow-up'
    vitals = Column(Text, nullable=True)  # JSON string, e.g., '{"temperature": 38.5, "heart_rate": 90}'
    medical_history = Column(ARRAY(String), nullable=True)  # e.g., ['diabetes', 'hypertension']
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    

class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    phc_id = Column(Integer, nullable=False)
    phc_name = Column(String, nullable=False)
    item_name = Column(String, nullable=False)
    item_type = Column(String, nullable=False)
    current_stock = Column(Integer, nullable=False)
    unit = Column(String, nullable=False)
    daily_consumption_rate = Column(Float, nullable=False)
    days_remaining = Column(Float, nullable=True)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class RestockRequest(Base):
    __tablename__ = "restock_requests"

    id = Column(Integer, primary_key=True, index=True)
    item_name = Column(String, nullable=False)
    quantity_needed = Column(Integer, nullable=False)
    phc_id = Column(Integer, nullable=False)
    phc_name = Column(String, nullable=False)
    request_date = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String, default="pending")
    comments = Column(String, nullable=True)

    # Newly added fields
    days_remaining = Column(Float, nullable=True)
    priority_level = Column(String, nullable=True)  # High / Medium / Low
    
