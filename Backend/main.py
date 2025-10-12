from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.phc_auth import router as auth_router
from routers import patients, inventory, workload_monitor, feedback
from database import Base, engine

# Attempt to create DB tables but don't let failure prevent server startup
try:
	# Create all tables in the database (if they don't exist)
	Base.metadata.create_all(bind=engine)
except Exception as e:
	# Log and continue; per-request DB calls will report errors
	print("Warning: could not run Base.metadata.create_all at startup:", e)

app = FastAPI(
    title="Hack Health API",
    description="API for managing patients and AI-based triage in PHC settings",
    version="1.0.0"
)

# Add CORS so frontline.html (served from e.g. http://127.0.0.1:5500) can call the API
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
app.include_router(inventory.router)
app.include_router(workload_monitor.router)
app.include_router(feedback.router)
app.include_router(auth_router)


@app.get("/")
def root():
    return {"message": "Welcome to Hack Health API!"}

if __name__ == "__main__":
    # When developing, run: python main.py
    # or from project root: uvicorn Backend.main:app --reload --port 8000
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)











