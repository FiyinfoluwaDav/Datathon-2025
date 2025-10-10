# routers/auth.py
from fastapi import APIRouter, HTTPException, Form
from pydantic import BaseModel, Field
from passlib.context import CryptContext
from datetime import datetime, timedelta
import jwt

router = APIRouter(prefix="/auth", tags=["Auth"])

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Dummy in-memory "database"
users_db = {}

SECRET_KEY = "hackhealthsecret"
ALGORITHM = "HS256"


# ✅ Signup schema with password length validation
class SignupRequest(BaseModel):
    full_name: str
    email: str
    password: str = Field(..., min_length=3, max_length=72)
    role: str


@router.post("/signup")
async def signup(data: SignupRequest):
    if data.email in users_db:
        raise HTTPException(status_code=400, detail="Email already exists")

    # ✅ Ensure password length is within bcrypt limit
    password = data.password[:72]

    hashed_pw = pwd_context.hash(password)
    users_db[data.email] = {
        "full_name": data.full_name,
        "email": data.email,
        "password": hashed_pw,
        "role": data.role,
    }

    return {"message": "User registered successfully!"}


# ✅ Login endpoint
@router.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    user = users_db.get(username)
    if not user or not pwd_context.verify(password[:72], user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Generate JWT token
    token_data = {
        "sub": username,
        "role": user["role"],
        "exp": datetime.utcnow() + timedelta(hours=12),
    }
    token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user["role"],
    }
