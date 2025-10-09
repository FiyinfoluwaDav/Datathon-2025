from pydantic import BaseModel, Field
from typing import Optional, List
import enum
from datetime import datetime


class Sex(str, enum.Enum):
    """Enumeration for patient biological sex."""
    Male = "Male"
    Female = "Female"

class VisitType(str, enum.Enum):
    """Enumeration for the immediate triage/queue category."""
    Emergency = "Emergency"
    Acute = "Acute"
    Routine = "Routine"
    FollowUp = "Follow-up"


class PatientBase(BaseModel):
    """
    Base schema defining the shared fields for Patient creation and reading.
    Fields correspond directly to the database columns (excluding DB-managed fields).
    """
    name: str = Field(..., max_length=255, description="Patient's full name.")
    age: int = Field(..., gt=0, description="Patient's age in years.")
    sex: Sex = Field(..., description="Biological sex (Male or Female).")
    
    # Note: Pydantic handles the List[str] conversion from JSON array input,
    # which maps to ARRAY(String) in PostgreSQL/SQLAlchemy.
    symptoms: List[str] = Field(..., description="List of raw symptoms reported by the patient.")
    visit_type: VisitType = Field(..., description="Triage category/intent for the visit.")

    # Vitals is stored as a JSON string in the DB (Text), so we validate it as a string here.
    # In a more advanced setup, this could be a nested Pydantic model (e.g., VitalsModel).
    vitals: Optional[str] = Field(None, description="Vitals data, stored as a JSON string (e.g., '{\"temp\": 37.0}').")
    
    medical_history: Optional[List[str]] = Field(None, description="List of known past medical conditions.")

# --- 3. Schemas for API Operations ---

class PatientCreate(PatientBase):
    """Schema used when creating a new patient record (input validation)."""
    # Inherits all required fields from PatientBase
    pass

class PatientUpdate(BaseModel):
    """
    Schema used when updating an existing patient record.
    All fields are Optional, as an update might only change one attribute.
    """
    name: Optional[str] = Field(None, max_length=255)
    age: Optional[int] = Field(None, gt=0)
    sex: Optional[Sex] = None
    symptoms: Optional[List[str]] = None
    visit_type: Optional[VisitType] = None
    vitals: Optional[str] = None
    medical_history: Optional[List[str]] = None

class PatientRead(PatientBase):
    """
    Schema used when reading or returning patient data (output serialization).
    Includes database-managed fields like ID and timestamps.
    """
    id: int = Field(..., description="Database primary key ID.")
    created_at: datetime = Field(..., description="Timestamp of record creation.")
    updated_at: datetime = Field(..., description="Timestamp of last update.")

    class Config:
        # This is essential for compatibility with SQLAlchemy ORM objects.
        # It tells Pydantic to read data from ORM attributes instead of just dictionary keys.
        from_attributes = True