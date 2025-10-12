from sqlalchemy import Column, Integer, String, Text, ARRAY, DateTime, Float, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import ENUM
import enum
from database import Base


# ---------- ENUM DEFINITIONS ----------
class Sex(enum.Enum):
    Male = "Male"
    Female = "Female"

class VisitType(enum.Enum):
    Emergency = "Emergency"
    Acute = "Acute"
    Routine = "Routine"
    FollowUp = "Follow-up"

SexEnum = ENUM(Sex, name="sex_enum", create_type=True)
VisitTypeEnum = ENUM(VisitType, name="visit_type_enum", create_type=True)


# ---------- PHC USERS ----------
class PHCUser(Base):
    __tablename__ = "phc_users"

    id = Column(Integer, primary_key=True, index=True)
    phc_id = Column(String, unique=True, index=True)
    phc_name = Column(String, unique=True, index=True)
    password = Column(String)

    capacity = Column(Integer, default=100)
    consecutive_overload_days = Column(Integer, default=0)
    latitude = Column(Float)
    longitude = Column(Float)
    lga_admin_email = Column(String, nullable=True)  # <-- uncommented, needed for alerting


# ---------- PATIENTS ----------
class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    age = Column(Integer, nullable=False)
    sex = Column(SexEnum, nullable=False)
    symptoms = Column(ARRAY(String), nullable=False)
    visit_type = Column(VisitTypeEnum, nullable=False)
    vitals = Column(Text, nullable=True)
    medical_history = Column(ARRAY(String), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


# ---------- INVENTORY ----------
class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    phc_id = Column(Integer, ForeignKey("phc_users.id", ondelete="CASCADE"), nullable=False)
    phc_name = Column(String, nullable=False)
    item_name = Column(String, nullable=False)
    item_type = Column(String, nullable=False)
    current_stock = Column(Integer, nullable=False)
    unit = Column(String, nullable=False)
    daily_consumption_rate = Column(Float, nullable=False)
    days_remaining = Column(Float, nullable=True)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ---------- RESTOCK REQUEST ----------
class RestockRequest(Base):
    __tablename__ = "restock_requests"

    id = Column(Integer, primary_key=True, index=True)
    item_name = Column(String, nullable=False)
    quantity_needed = Column(Integer, nullable=False)
    phc_id = Column(Integer, ForeignKey("phc_users.id", ondelete="CASCADE"), nullable=False)
    phc_name = Column(String, nullable=False)
    request_date = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String, default="pending")
    comments = Column(String, nullable=True)

    days_remaining = Column(Float, nullable=True)
    priority_level = Column(String, nullable=True)  # High / Medium / Low


# ---------- PHC WORKLOAD ----------
class PHCWorkloadLog(Base):
    __tablename__ = "phc_workload_logs"

    id = Column(Integer, primary_key=True, index=True)
    phc_id = Column(Integer, ForeignKey("phc_users.id", ondelete="CASCADE"), nullable=False)
    date = Column(DateTime(timezone=True), server_default=func.now())

    current_queue_count = Column(Integer, nullable=False)
    avg_wait_time = Column(Float, nullable=False)
    completed_visits_today = Column(Integer, nullable=False)
    forecast_next_day = Column(Integer, nullable=True)
    alert_sent = Column(Boolean, default=False)



class PHCFeedback(Base):
    __tablename__ = "phc_feedback"

    id = Column(Integer, primary_key=True, index=True)
    phc_id = Column(Integer, ForeignKey("phc_users.id", ondelete="CASCADE"))
    phc_name = Column(String, nullable=False)
    category = Column(String, nullable=False)  # e.g., "Power", "Water", "Equipment"
    message = Column(Text, nullable=False)
    status = Column(String, default="pending")  # pending / resolved / in-progress
    created_at = Column(DateTime(timezone=True), server_default=func.now())
