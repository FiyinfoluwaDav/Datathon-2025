# routers/workload_monitor.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta
import numpy as np

from database import get_db
from models import PHCWorkloadLog, PHCUser
from schemas import WorkloadLogCreate, WorkloadForecastResponse, WorkloadLogResponse
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import func

router = APIRouter(prefix="/workload", tags=["Workload Monitor"])


# 1️⃣ Log PHC workload data (every 1–2 hours)
@router.post("/log", response_model=WorkloadLogResponse)
def record_workload(payload: WorkloadLogCreate, db: Session = Depends(get_db)):
    log = PHCWorkloadLog(**payload.dict())
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


# 2️⃣ Forecast tomorrow’s patient load + rerouting logic
@router.post("/forecast/{phc_id}", response_model=WorkloadForecastResponse)
def forecast_next_day(phc_id: int, db: Session = Depends(get_db)):
    logs = (
        db.query(PHCWorkloadLog)
        .filter(PHCWorkloadLog.phc_id == phc_id)
        .order_by(PHCWorkloadLog.date.desc())
        .limit(14)
        .all()
    )

    if len(logs) < 3:
        raise HTTPException(status_code=400, detail="Not enough data to forecast")

    X = np.arange(len(logs)).reshape(-1, 1)
    y = np.array([log.completed_visits_today for log in logs])
    model = LinearRegression().fit(X, y)
    forecast = float(model.predict([[len(logs) + 1]])[0])

    phc = db.query(PHCUser).filter(PHCUser.id == phc_id).first()
    if not phc:
        raise HTTPException(status_code=404, detail="PHC not found")

    # --- Threshold logic ---
    capacity = phc.capacity
    overload_days = phc.consecutive_overload_days or 0
    message = "Normal load expected tomorrow."

    if forecast > capacity:
        overload_days += 1
        message = (
            f"⚠️ Forecast ({forecast:.1f}) exceeds capacity ({capacity}). "
            "Suggest rerouting some patients to nearby PHCs."
        )

        # If overload persists for 3 consecutive days → notify LGA admin
        # if overload_days >= 3:
        #     message = (
        #         "🚨 PHC overloaded for 3 days! LGA Admin has been notified to consider adding staff."
        #     )
        #     # Stub for admin notification — can later be integrated with email or dashboard
        #     print(f"[ADMIN ALERT] PHC {phc.phc_name} is overwhelmed. Email: {phc.lga_admin_email}")
    else:
        overload_days = 0

    phc.consecutive_overload_days = overload_days
    db.commit()

    # --- Rerouting suggestion ---
    reroute_suggestions = []
    if forecast > capacity and phc.latitude and phc.longitude:
        nearby = (
            db.query(PHCUser)
            .filter(PHCUser.id != phc_id)
            .filter(PHCUser.latitude.isnot(None))
            .all()
        )
        for n in nearby:
            # simple distance calc (in degrees — approximate)
            distance = ((phc.latitude - n.latitude) ** 2 + (phc.longitude - n.longitude) ** 2) ** 0.5
            if distance < 0.15:  # roughly ~15 km
                reroute_suggestions.append({"phc_name": n.phc_name, "distance": round(distance * 111, 1)})

    return WorkloadForecastResponse(
        forecast_next_day=forecast,
        capacity=capacity,
        overload_days=overload_days,
        message=message + (
            f" Suggested nearby PHCs: {', '.join([r['phc_name'] for r in reroute_suggestions])}"
            if reroute_suggestions else ""
        )
    )


# 3️⃣ Daily reset task (runs automatically)
def reset_daily_workload(db: Session):
    today = datetime.utcnow().date()
    db.query(PHCWorkloadLog).filter(func.date(PHCWorkloadLog.date) < today).delete()
    db.commit()
    print("✅ Daily workload logs reset completed.")


# 4️⃣ Background scheduler (runs daily)
def start_scheduler(db_session_factory):
    scheduler = BackgroundScheduler(timezone="Africa/Lagos")

    scheduler.add_job(
        lambda: reset_daily_workload(db_session_factory()),
        "cron",
        hour=0,
        minute=0,
        id="daily_reset_job",
        replace_existing=True
    )

    scheduler.start()
    print("🕒 Scheduler started for daily workload resets.")