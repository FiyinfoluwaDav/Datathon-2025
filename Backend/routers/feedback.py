from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import PHCFeedback
from schemas import FeedbackCreate, FeedbackRead, FeedbackUpdate
from typing import List

router = APIRouter(prefix="/feedback", tags=["Feedback & Issues"])

# ---------- 1️⃣ Submit Feedback ----------
@router.post("/", response_model=FeedbackRead)
def submit_feedback(feedback: FeedbackCreate, db: Session = Depends(get_db)):
    new_feedback = PHCFeedback(**feedback.dict())
    db.add(new_feedback)
    db.commit()
    db.refresh(new_feedback)
    return new_feedback


# ---------- 2️⃣ Get All Feedback for a PHC ----------
@router.get("/{phc_id}", response_model=List[FeedbackRead])
def get_feedback_by_phc(phc_id: int, db: Session = Depends(get_db)):
    feedbacks = db.query(PHCFeedback).filter(PHCFeedback.phc_id == phc_id).all()
    if not feedbacks:
        raise HTTPException(status_code=404, detail="No feedback found for this PHC")
    return feedbacks


# ---------- 3️⃣ Update Feedback Status ----------
@router.put("/{feedback_id}", response_model=FeedbackRead)
def update_feedback_status(feedback_id: int, update: FeedbackUpdate, db: Session = Depends(get_db)):
    feedback = db.query(PHCFeedback).filter(PHCFeedback.id == feedback_id).first()
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    feedback.status = update.status
    db.commit()
    db.refresh(feedback)
    return feedback