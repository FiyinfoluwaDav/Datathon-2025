from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from schemas import PHCAccount, PHCLogin
from database import get_db
from models import PHCUser
from hashing import Hash

router = APIRouter(prefix="/phc", tags=["PHC Authentication"])


@router.post("/sign-up")
def create_phc_account(request: PHCAccount, db: Session = Depends(get_db)):
    existing = db.query(PHCUser).filter(
        (PHCUser.phc_id == request.phc_id) | (PHCUser.phc_name == request.phc_name)
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="PHC already registered")

    new_phc = PHCUser(
        phc_id=request.phc_id,
        phc_name=request.phc_name,
        password=Hash.hashing(request.password)
    )
    db.add(new_phc)
    db.commit()
    db.refresh(new_phc)
    return {"message": "PHC account created successfully", "phc_name": new_phc.phc_name}


@router.post("/sign-in")
def phc_sign_in(request: PHCLogin, db: Session = Depends(get_db)):
    phc_user = db.query(PHCUser).filter(PHCUser.phc_id == request.phc_id).first()

    if not phc_user:
        raise HTTPException(status_code=404, detail="PHC not found")

    if not Hash.verifying(request.password, phc_user.password):
        raise HTTPException(status_code=401, detail="Incorrect password")

    return {"message": "Login successful", "phc_name": phc_user.phc_name}