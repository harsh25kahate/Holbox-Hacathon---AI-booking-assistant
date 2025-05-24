from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from database.database import get_db, engine, Base
from database.models import User, ServiceProvider, Appointment, TimeSlot
from ui.interface import launch_ui
import uvicorn
import threading

# Create tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(title="AI Appointment Booking System")

# Add some sample data
def add_sample_data(db: Session):
    # Add sample service providers if none exist
    if db.query(ServiceProvider).count() == 0:
        providers = [
            ServiceProvider(
                name="Dr. Smith",
                service_type="General Physician",
                email="dr.smith@example.com",
                phone="123-456-7890"
            ),
            ServiceProvider(
                name="Dr. Johnson",
                service_type="Dentist",
                email="dr.johnson@example.com",
                phone="123-456-7891"
            ),
            ServiceProvider(
                name="Ms. Williams",
                service_type="Beauty Salon",
                email="williams@example.com",
                phone="123-456-7892"
            )
        ]
        for provider in providers:
            db.add(provider)
        db.commit()

# Initialize sample data
with Session(engine) as db:
    add_sample_data(db)

def run_fastapi():
    """Run the FastAPI server"""
    uvicorn.run(app, host="0.0.0.0", port=8000)

def main():
    # Start FastAPI in a separate thread
    api_thread = threading.Thread(target=run_fastapi, daemon=True)
    api_thread.start()
    
    # Launch Gradio UI
    launch_ui()

if __name__ == "__main__":
    main() 