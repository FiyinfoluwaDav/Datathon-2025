from fastapi import FastAPI
from routers import patients
from database import Base, engine
import models

# Create all tables in the database (if they don't exist)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Hack Health API",
    description="API for managing patients and AI-based triage in PHC settings",
    version="1.0.0"
)

# Include your patient router
app.include_router(patients.router)

@app.get("/")
def root():
    return {"message": "Welcome to Hack Health API!"}
