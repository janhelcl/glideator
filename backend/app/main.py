import logging
import time
from kombu import Connection
from kombu.exceptions import OperationalError

from fastapi import FastAPI
from .database import engine, Base, SessionLocal
from .routers import sites
from fastapi.middleware.cors import CORSMiddleware

from .services.sites_loader import load_sites_from_csv
from .services.flight_stats_loader import load_flight_stats_from_csv
from .services.spots_loader import load_spots_from_csv
from .services.sites_info_loader import load_sites_info_from_jsonl
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
def setup_database():
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")

setup_database()

app = FastAPI(
    title="Glideator API",
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
def startup_db_client():
    logger.info("Starting up...")
    db = SessionLocal()
    try:
        logger.info("Loading sites data...")
        load_sites_from_csv(db, 'sites.csv')
        
        logger.info("Loading flight stats data...")
        load_flight_stats_from_csv(db)
        
        logger.info("Loading spots data...")
        load_spots_from_csv(db)
        
        logger.info("Loading sites info data...")
        load_sites_info_from_jsonl(db)
        
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
        
        logger.info("Data loading completed successfully")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
    finally:
        db.close()
        logger.info("Database session closed.")
