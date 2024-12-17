import logging
import time
from kombu import Connection
from kombu.exceptions import OperationalError

from fastapi import FastAPI
from .database import engine, Base, SessionLocal
from .routers import sites
from fastapi.middleware.cors import CORSMiddleware

from .services.sites_loader import load_sites_from_csv
from .celery_app import celery

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set the logging level
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Paragliding Site Recommendations API",
    description="API for recommending paragliding sites based on weather forecasts.",
    version="1.0.0",
)

# Include routers
app.include_router(sites.router)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Update with your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    try:
        # Load sites from CSV
        logger.info("Loading sites from CSV...")
        load_sites_from_csv(db, 'sites.csv')
        
        # Wait for RabbitMQ to be ready
        retry_count = 0
        while retry_count < 5:  # Try 5 times
            try:
                conn = Connection(celery.conf.broker_url)
                conn.connect()
                conn.close()
                # If connection successful, break the loop
                break
            except OperationalError:
                logger.info("Waiting for RabbitMQ to be ready...")
                time.sleep(2)
                retry_count += 1
        
        # Clean up old data
        logger.info("Cleaning up old data...")
        celery.send_task('app.celery_app.cleanup_old_data')
        
        # Generate and store predictions
        logger.info("Generating and storing predictions...")
        celery.send_task('app.celery_app.check_and_trigger_forecast_processing')
    except Exception as e:
        logger.error(f"An error occurred during startup: {e}")
    finally:
        db.close()
        logger.info("Database session closed.")
