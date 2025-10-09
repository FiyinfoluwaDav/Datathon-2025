from sqlalchemy import Column, Integer, String, Text, ARRAY, DateTime
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
    
