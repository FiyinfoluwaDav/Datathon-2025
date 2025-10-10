from fastapi import FastAPI
from routers import patients
from routers import auth
from database import Base, engine
import models

# Create all tables in the database (if they don't exist)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Hack Health API",
    description="API for managing patients and AI-based triage in PHC settings",
    version="1.0.0"
)

# Add CORS so frontline.html (served from e.g. http://127.0.0.1:5500) can call the API
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:5501", 
        "http://localhost:5501", 
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://127.0.0.1:8000",
        "http://localhost:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include your patient router
app.include_router(patients.router)
app.include_router(auth.router)

@app.get("/")
def root():
    return {"message": "Welcome to Hack Health API!"}
