from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os


DATABASE_URL = "postgresql://medisense_51dz_user:7nxnjwawB90SgpSCEGOLpPPeZQIQgYag@dpg-d3m22mt6ubrc73efll7g-a.oregon-postgres.render.com/medisense_51dz"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



