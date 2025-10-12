# routers/auth.py
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field
from pydantic.error_wrappers import ValidationError
from passlib.context import CryptContext
from datetime import datetime, timedelta
import jwt
import os
import psycopg2
import psycopg2.extras
from psycopg2 import OperationalError, DatabaseError

router = APIRouter(prefix="/auth", tags=["Auth"])

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Use DATABASE_URL env var if provided; otherwise fall back to the project's Postgres URI
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:200428@127.0.0.1:5432/hackhealth")
SECRET_KEY = os.getenv("SECRET_KEY", "hackhealthsecret")
ALGORITHM = "HS256"

# Signup schema
class SignupRequest(BaseModel):
    full_name: str
    email: str
    password: str = Field(..., min_length=3, max_length=72)
    role: str

# normalize roles
def _normalize_role(r: str) -> str:
    if not r:
        return ""
    rr = r.strip().lower()
    if rr in ("phc", "phc_user", "phcuser", "frontline", "frontline_worker"):
        return "phc"
    if rr in (
        "health", "health_admin", "healthadmin", "admin", "health-admin",
        "healthcare_admin", "healthcareadmin", "healthcare", "health care", "health-care",
    ):
        return "health_admin"
    return rr

# helper: get a new Postgres connection (caller should close)
def _get_conn():
    try:
        # add a short connect_timeout to fail fast when Postgres is unreachable
        return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.DictCursor, connect_timeout=5)
    except OperationalError as e:
        print("Postgres connection error (OperationalError):", e)
        # re-raise so callers can convert to an HTTP error quickly
        raise
    except Exception as e:
        print("Postgres connection error:", e)
        raise

def db_fetchone(query: str, params: tuple = ()):
    conn = None
    cur = None
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(query, params)
        row = cur.fetchone()
        return dict(row) if row is not None else None
    except (OperationalError, DatabaseError) as e:
        # surface DB connectivity problems as a service-unavailable error
        print("DB error during fetchone:", e)
        raise HTTPException(status_code=503, detail="Database unavailable")
    finally:
        if cur is not None:
            try:
                cur.close()
            except Exception:
                pass
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass

def db_execute(query: str, params: tuple = ()):
    conn = None
    cur = None
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
    except (OperationalError, DatabaseError) as e:
        print("DB error during execute:", e)
        raise HTTPException(status_code=503, detail="Database unavailable")
    finally:
        if cur is not None:
            try:
                cur.close()
            except Exception:
                pass
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass

# ensure users table exists (Postgres only)
def _init_db():
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL
            );
        """)
        conn.commit()
    except Exception as e:
        print("Postgres init failed:", e)
        # raise so the process fails early and you can fix DB credentials
        raise
    finally:
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

# initialize on import - will raise if Postgres is unreachable / credentials invalid
_init_db()

@router.post("/signup")
async def signup(request: Request):
    """
    Accepts JSON or form signup payload and stores user in Postgres.
    """
    try:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            payload = await request.json()
        else:
            form = await request.form()
            payload = {
                "full_name": form.get("full_name") or form.get("name") or "",
                "email": form.get("email") or "",
                "password": form.get("password") or "",
                "role": form.get("role") or form.get("user_role") or ""
            }

        data = SignupRequest(**payload)
    except ValidationError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signup payload")

    email = data.email.strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    role = _normalize_role(data.role)
    if role not in ("phc", "health_admin"):
        raise HTTPException(status_code=400, detail="Invalid role. Allowed: 'phc' or 'health_admin'")

    password = data.password[:72]
    hashed_pw = pwd_context.hash(password)

    # check existing user and insert
    try:
        existing = db_fetchone("SELECT 1 FROM users WHERE email = %s", (email,))
        if existing:
            raise HTTPException(status_code=400, detail="Email already exists")

        db_execute(
            "INSERT INTO users (email, full_name, password, role, created_at) VALUES (%s, %s, %s, %s, %s)",
            (email, data.full_name, hashed_pw, role, datetime.utcnow())
        )
    except HTTPException:
        raise
    except Exception as e:
        print("DB error on signup:", e)
        raise HTTPException(status_code=500, detail=f"Failed to create user: {e}")

    return {"message": "User registered successfully!", "role": role}


@router.post("/login")
async def login(request: Request):
    """
    Accepts form or JSON credentials, verifies against Postgres, returns JWT and redirect hint.
    """
    try:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            body = await request.json()
            username = (body.get("username") or body.get("email") or "").strip().lower()
            password = body.get("password") or ""
        else:
            form = await request.form()
            username = (form.get("username") or form.get("email") or "").strip().lower()
            password = form.get("password") or ""
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid login payload")

    if not username or not password:
        raise HTTPException(status_code=401, detail="Missing credentials")

    try:
        row = db_fetchone("SELECT email, full_name, password, role FROM users WHERE email = %s", (username,))
    except Exception as e:
        print("DB error on login:", e)
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

    if not row:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    stored_pw = row.get("password")
    role = row.get("role")

    if not pwd_context.verify(password[:72], stored_pw):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Generate JWT token
    token_data = {
        "sub": username,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=12),
    }
    token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

    # redirect mapping: health_admin -> /admin.html, phc -> /frontline.html
    redirect_to = "/frontline.html" if role == "phc" else "/admin.html"

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": role,
        "redirect_to": redirect_to,
    }
