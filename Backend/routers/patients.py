from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional

# Assuming these models/schemas are defined in their respective files
# NOTE: Ensure PatientCreate, PatientRead, PatientUpdate are imported from schemas.py
# and Patient (SQLAlchemy model) is imported from models.py
from schemas import PatientCreate, PatientCreateResponse # Import Pydantic schemas
from models import Patient # Import SQLAlchemy model
from database import get_db

# Imports for Gemini API Integration
import os
from google import genai
from google.genai import types
import json

# Initialize the router with a prefix
router = APIRouter(prefix="/patients", tags=["patients"])


try:
    client = genai.Client(api_key="AIzaSyDUdAcNHyVpqR88dgbY_bsXCdAzCnv-No4")
    print("Gemini client initialized successfully.")
except Exception as e:
    print(f"Gemini client initialization failed: {e}")
    client = None

# --- Response Schema for Triage Output (Defined Locally for this Router) ---
class TriageResponse(BaseModel):
    """Structured response schema for the AI triage result."""
    patient_id: int = Field(..., description="ID of the patient triaged.")
    urgency_level: str = Field(..., description="AI's assigned urgency (e.g., Mild, Moderate, Severe, Critical).")
    recommended_actions: List[str] = Field(..., description="AI's suggested actions (e.g., Wait for GP, Refer to hospital, Order tests).")
    reasoning: str = Field(..., description="Brief justification for the recommendation.")


# --- 1. Patient Registration (POST /patients) ---

@router.post("/", response_model=PatientCreateResponse, status_code=status.HTTP_201_CREATED)
def register_patient(patient_data: PatientCreate, db: Session = Depends(get_db)):
    """
    Registers a new patient and their visit details in the database.
    """
    try:
        # Create SQLAlchemy model instance from Pydantic data
        db_patient = Patient(
            name=patient_data.name,
            age=patient_data.age,
            sex=patient_data.sex,
            symptoms=patient_data.symptoms,
            visit_type=patient_data.visit_type,
            # Handle optional fields (vitals, medical_history)
            vitals=patient_data.vitals,
            medical_history=patient_data.medical_history
        )
        
        db.add(db_patient)
        db.commit()
        db.refresh(db_patient)
        return PatientCreateResponse(
        id=db_patient.id,
        name=db_patient.name,
        age=db_patient.age,
        message="Patient registered successfully"
    )
        
    except Exception as e:
        db.rollback()
        # Log the error internally for debugging
        print(f"Database error during patient registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to register patient in the database."
        )


# --- 2. Patient Triage (POST /patients/triage/{patient_id}) ---

@router.post("/triage/{patient_id}", response_model=TriageResponse)
async def triage_patient(patient_id: int, db: Session = Depends(get_db)):
    """
    Retrieves patient data and uses the Gemini LLM to perform an automated triage.
    """
    if not client:
         raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail="AI Triage service is unavailable (API key not configured)."
        )

    # 1. Fetch patient from database
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    # 2. Prepare the detailed prompt for the LLM
    prompt = f"""
    You are a highly experienced Triage Nurse specializing in Primary Healthcare Center (PHC) settings in Nigeria.
    Your task is to provide an initial triage assessment and recommended course of action.

    PATIENT DATA:
    - Patient ID: {patient.id}
    - Age: {patient.age}
    - Sex: {patient.sex}
    - Triage Category (Intent): {patient.visit_type}
    - Reported Symptoms: {', '.join(patient.symptoms)}
    - Vitals (JSON/String): {patient.vitals or 'No vitals recorded.'}
    - Medical History: {', '.join(patient.medical_history) if patient.medical_history else 'None known.'}

    INSTRUCTIONS:
    1. URGENCY LEVEL: Assign one of the following levels: 'Critical' (Needs immediate referral/resuscitation), 'Severe' (Needs doctor/CHO within 15 mins), 'Moderate' (Needs assessment/tests within 30-60 mins), or 'Mild' (Routine care/can wait).
    2. RECOMMENDED ACTIONS: Choose one or more from: ['Wait for GP', 'Refer to hospital', 'Order tests', 'Administer first aid', 'Proceed to immunization station', 'Discharge'].
    3. REASONING: Provide a brief, clinical justification (1-2 sentences) for the decision.

    Your entire output MUST be a valid JSON object matching the provided schema.
    """

    try:
        # 3. Configure and call the Gemini API for structured JSON output
        config = types.GenerateContentConfig(
            # Requesting JSON output that matches the TriageResponse schema
            response_mime_type="application/json",
            response_schema=TriageResponse.model_json_schema(),
        )

        llm_response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=config,
        )

        # 4. Parse the structured JSON response
        # The response.text should be guaranteed to be valid JSON matching TriageResponse
        triage_data = TriageResponse.model_validate_json(llm_response.text)
        
        # Add the patient ID to the response before returning
        triage_data.patient_id = patient_id 
        
        return triage_data

    except genai.errors.APIError as e:
        # Handle specific API errors (e.g., key invalid, rate limit)
        print(f"Gemini API Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, 
            detail="AI Triage service failed to process the request due to an API error."
        )
    except Exception as e:
        # Handle parsing errors or unexpected issues
        print(f"Triage processing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="An unexpected error occurred during triage processing."
        )
    