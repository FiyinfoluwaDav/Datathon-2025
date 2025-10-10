from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional
import os
import json
import logging

# Assuming these models/schemas are defined in their respective files
# NOTE: Ensure PatientCreate, PatientRead, PatientUpdate are imported from schemas.py
# and Patient (SQLAlchemy model) is imported from models.py
from schemas import PatientCreate, PatientRead, PatientUpdate # Import Pydantic schemas
from models import Patient, Sex, VisitType # Import SQLAlchemy model and enums
from database import get_db

# Imports for Gemini API Integration (lazy import, don't fail at module import)
try:
    import google.generativeai as genai  # type: ignore
    GEMINI_AVAILABLE = True
except Exception:
    genai = None  # type: ignore
    GEMINI_AVAILABLE = False

# Initialize the router with a prefix
router = APIRouter(prefix="/patients", tags=["patients"])

# --- Response Schema for Triage Output (Defined Locally for this Router) ---
class TriageResponse(BaseModel):
    """Structured response schema for the AI triage result."""
    patient_id: int = Field(..., description="ID of the patient triaged.")
    urgency_level: str = Field(..., description="AI's assigned urgency (e.g., Mild, Moderate, Severe, Critical).")
    recommended_actions: List[str] = Field(..., description="AI's suggested actions (e.g., Wait for GP, Refer to hospital, Order tests).")
    reasoning: str = Field(..., description="Brief justification for the recommendation.")


# --- 1. Patient Registration (POST /patients) ---
@router.post("/", response_model=PatientRead, status_code=status.HTTP_201_CREATED)
def register_patient(patient_data: PatientCreate, db: Session = Depends(get_db)):
    """
    Create and persist a new Patient row.
    Simple, synchronous implementation so the endpoint responds and can be tested from the frontend.
    """
    # convert string values into Python Enum members expected by models (if necessary)
    try:
        sex_val = Sex(patient_data.sex) if isinstance(patient_data.sex, str) else patient_data.sex
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid sex value")

    try:
        visit_val = VisitType(patient_data.visit_type) if isinstance(patient_data.visit_type, str) else patient_data.visit_type
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid visit_type value")

    db_patient = Patient(
        name=patient_data.name,
        age=patient_data.age,
        sex=sex_val,
        symptoms=patient_data.symptoms or [],
        visit_type=visit_val,
        vitals=patient_data.vitals,
        medical_history=patient_data.medical_history or []
    )
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return db_patient


# --- Helper: call Gemini (if available) ---
def _call_gemini_tts(prompt: str) -> Optional[str]:
    """
    Call Gemini via google.generativeai client and return unparsed text output.
    Returns None on any failure so caller can fallback.
    """
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not GEMINI_AVAILABLE or not api_key:
        return None

    try:
        # configure client lazily
        genai.configure(api_key=api_key)  # safe to call repeatedly
        # Compose a chat-style request. Implementation may differ across genai versions;
        # we attempt a commonly used API surface but guard with try/except.
        try:
            resp = genai.chat.create(
                model=os.getenv("GEMINI_MODEL", "gemini-1.0"),
                messages=[
                    {"role": "system", "content": "You are a concise medical triage assistant. Return only a JSON object with keys: urgency_level (string), recommended_actions (array of strings), reasoning (string)."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
            )
            # Try a few common response shapes
            text = None
            if hasattr(resp, "candidates") and resp.candidates:
                # candidate might hold content as text or message
                cand = resp.candidates[0]
                if isinstance(cand, dict) and "content" in cand:
                    text = cand["content"]
                elif hasattr(cand, "content"):
                    text = getattr(cand, "content")
            if not text and hasattr(resp, "output") and resp.output:
                # some versions use resp.output[0].content
                try:
                    text = resp.output[0].content[0].text
                except Exception:
                    text = None
            # fallback to string conversion
            if not text:
                text = str(resp)
            return text
        except Exception as e:
            logging.exception("Gemini chat call failed: %s", e)
            return None
    except Exception as e:
        logging.exception("Gemini configuration/call error: %s", e)
        return None


def _extract_json_from_text(text: str) -> Optional[dict]:
    """
    Attempt to find the first JSON object in text and parse it.
    Returns dict on success, else None.
    """
    if not text:
        return None
    # find first '{' and last '}' and try to load
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    snippet = text[start:end+1]
    try:
        return json.loads(snippet)
    except Exception:
        # try to be lenient: replace single quotes with double quotes
        try:
            snippet2 = snippet.replace("'", '"')
            return json.loads(snippet2)
        except Exception:
            logging.exception("Failed to parse JSON from model output")
            return None


# --- 2. Patient Triage (POST /patients/triage/{patient_id}) ---
@router.post("/triage/{patient_id}", response_model=TriageResponse)
async def triage_patient(patient_id: int, db: Session = Depends(get_db)):
    """
    LLM-backed triage: try Gemini first (if configured), otherwise fall back to a simple rule-based triage.
    """
    # 1. Fetch patient from database
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    # Build a compact prompt describing the patient
    prompt_lines = [
        f"Patient ID: {patient.id}",
        f"Name: {patient.name}",
        f"Age: {patient.age}",
        f"Sex: {getattr(patient.sex,'value', patient.sex)}",
        f"Visit type: {getattr(patient.visit_type,'value', patient.visit_type)}",
        f"Vitals: {patient.vitals or ''}",
        f"Medical history: {', '.join(patient.medical_history or [])}",
        f"Symptoms: {', '.join(patient.symptoms or [])}",
        "",
        "Provide a JSON object with keys: urgency_level (one of Critical/Severe/Moderate/Mild), recommended_actions (array of short action strings), reasoning (one sentence).",
        "Keep the JSON minimal and valid."
    ]
    prompt = "\n".join(prompt_lines)

    # 2. Try LLM (Gemini) if available
    model_text = _call_gemini_tts(prompt)
    if model_text:
        parsed = _extract_json_from_text(model_text)
        if parsed:
            # normalize response keys
            urgency = parsed.get("urgency_level") or parsed.get("urgency") or parsed.get("level") or "Moderate"
            actions = parsed.get("recommended_actions") or parsed.get("actions") or []
            if isinstance(actions, str):
                actions = [actions]
            reasoning = parsed.get("reasoning") or parsed.get("explanation") or ""
            return {
                "patient_id": patient.id,
                "urgency_level": urgency,
                "recommended_actions": actions,
                "reasoning": reasoning
            }
        else:
            logging.warning("Gemini returned text but JSON parsing failed. Text: %s", model_text)

    # 3. Fallback: simple rule-based triage
    symptoms = [s.lower() for s in (patient.symptoms or [])]
    joined = " ".join(symptoms)
    if any(k in joined for k in ("chest pain", "severe bleeding", "unconscious")):
        urgency = "Critical"
        actions = ["Refer to hospital", "Call emergency services"]
    elif patient.age is not None and patient.age >= 65:
        urgency = "Severe"
        actions = ["See clinician within 15 minutes"]
    elif "fever" in joined and "difficulty breathing" in joined:
        urgency = "Severe"
        actions = ["Order oxygen, refer as needed"]
    elif "fever" in joined:
        urgency = "Moderate"
        actions = ["Provide symptomatic care", "Consider malaria RDT or malaria treatment as per local guidelines"]
    else:
        urgency = "Mild"
        actions = ["Wait for GP", "Provide symptomatic care"]

    return {
        "patient_id": patient.id,
        "urgency_level": urgency,
        "recommended_actions": actions,
        "reasoning": f"Based on symptoms: {', '.join(patient.symptoms or [])} and age {patient.age}"
    }