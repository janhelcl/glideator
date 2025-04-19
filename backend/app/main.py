import logging
import time
from kombu import Connection
from kombu.exceptions import OperationalError

from fastapi import FastAPI, HTTPException
from .database import engine, Base, SessionLocal
from .routers import sites
from fastapi.middleware.cors import CORSMiddleware

from .services.sites_loader import load_sites_from_csv
from .services.flight_stats_loader import load_flight_stats_from_csv
from .services.spots_loader import load_spots_from_csv
from .services.sites_info_loader import load_sites_info_from_jsonl
from .celery_app import celery, simple_test_task

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
        
        # Wait for Broker (Redis) to be ready
        retry_count = 0
        connected_to_broker = False # Flag to track connection status
        while retry_count < 5:  # Try 5 times
            try:
                # Uses celery.conf.broker_url which should be your Redis URL from env vars
                conn = Connection(celery.conf.broker_url) 
                conn.connect()
                conn.close()
                logger.info("Successfully connected to broker.") # Add success log
                connected_to_broker = True 
                # If connection successful, break the loop
                break
            except OperationalError as e: # Catch specific error
                logger.warning(f"Waiting for Broker... Attempt {retry_count + 1}/5. Error: {e}")
                time.sleep(2)
                retry_count += 1
        
        if not connected_to_broker:
             logger.error("Failed to connect to broker after multiple retries. Tasks might not be sent.")
             # Depending on requirements, you might want to raise an exception here
             # or simply proceed knowing tasks might not be sent immediately.

        # Clean up old data
        try:
            logger.info("Attempting to send task: cleanup_old_data")
            celery.send_task('app.celery_app.cleanup_old_data')
            logger.info("Task 'cleanup_old_data' sent successfully.")
        except Exception as e:
            logger.error(f"Failed to send task 'cleanup_old_data': {e}")

        # Generate and store predictions
        try:
            logger.info("Attempting to send task: check_and_trigger_forecast_processing")
            celery.send_task('app.celery_app.check_and_trigger_forecast_processing')
            logger.info("Task 'check_and_trigger_forecast_processing' sent successfully.")
        except Exception as e:
            logger.error(f"Failed to send task 'check_and_trigger_forecast_processing': {e}")
        
        logger.info("Data loading and task submission sequence completed.") # Modified log
    except Exception as e:
        logger.error(f"Error during startup sequence: {str(e)}", exc_info=True) # Add traceback logging
    finally:
        db.close()
        logger.info("Database session closed.")

# Test endpoint for Celery
@app.get("/test-celery/{message}")
async def test_celery_task_endpoint(message: str):
    logger.info(f"WEB SERVICE: Received request for /test-celery/{message}")
    try:
        logger.info(f"WEB SERVICE: Attempting to send simple_test_task with message: {message}")
        task_result = simple_test_task.delay(message)
        logger.info(f"WEB SERVICE: simple_test_task sent. Task ID: {task_result.id}")
        return {"message": "Test task sent", "task_id": task_result.id}
    except Exception as e:
         logger.error(f"WEB SERVICE: Failed to send simple_test_task: {e}", exc_info=True)
         raise HTTPException(status_code=500, detail="Failed to send test task")
