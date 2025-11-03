# Glideator Backend

A brief description of the backend service for the Glideator project, built with FastAPI.

## Prerequisites

- Docker
- Docker Compose
- Python 3.10
- Git

## Core Technologies

- **Framework:** FastAPI
- **MCP Server:** Model Context Protocol server (FastMCP)
- **Database:** PostgreSQL (using SQLAlchemy and psycopg2)
- **Background Tasks:** Celery (with RabbitMQ as broker)
- **Web Server:** Uvicorn
- **Containerization:** Docker

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url> # Replace with your repository URL
    cd glideator/backend
    ```
2.  **Local Python Setup (Optional - Only if NOT using Docker):**
    *   Create a virtual environment:
        ```bash
        python -m venv env-backend
        source env-backend/bin/activate  # On Windows use `env-backend\\Scripts\\activate`
        ```
    *   Install local packages first (if any updates outside Docker):
        ```bash
        pip install ./packages/*.whl
        ```
    *   Install dependencies:
        ```bash
        pip install -r requirements.txt
        ```

## Running the Application

### Using Docker Compose (Recommended)

This is the easiest way to run the application and all its dependencies (PostgreSQL, RabbitMQ, Celery).

#### Development Environment (with Hot-Reloading)

This uses `docker-compose.dev.yml`.

```bash
docker-compose -f docker-compose.dev.yml up --build
```

The API will be available at `http://localhost:8000`.

#### Production Environment

This uses `docker-compose.yml` (assuming it's configured for production).

```bash
docker-compose -f docker-compose.yml up --build -d
```

To stop the services:

```bash
docker-compose -f <your-chosen-compose-file.yml> down
```

### Running Locally (Without Docker)

Ensure PostgreSQL and RabbitMQ services are running and accessible. Set the environment variables listed below.

```bash
# Run the FastAPI application with hot-reloading
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run the Celery worker and beat (in separate terminals or using a process manager)
celery -A app.celery_app worker --loglevel=info
celery -A app.celery_app beat --loglevel=info
```

## Environment Variables

Environment variables are primarily configured within the `docker-compose.*.yml` files. For local development without Docker, you would need to set these in your environment (e.g., using a `.env` file and `python-dotenv`, although `python-dotenv` is not listed in requirements):

```plaintext
# Example values (adjust as needed, especially for local setup)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/glideator
CELERY_BROKER_URL=amqp://guest:guest@localhost:5672//
CELERY_RESULT_BACKEND=rpc:// # Or configure a persistent backend like Redis or DB if needed
```

## Celery Tasks

This project uses Celery (`app.celery_app`) for background tasks, with RabbitMQ as the message broker.
- The `docker-compose.dev.yml` runs a combined worker and beat service.
- The `celerybeat-schedule` file likely stores the periodic task schedule database (managed by Celery Beat).
- Forecast processing triggers notification evaluation once new predictions are stored.
- A dedicated `dispatch_notifications` task runs every 30 minutes to queue push notifications for users with matching rules.

## Notifications and Push Subscriptions

The backend exposes authenticated endpoints under `/users/me` for managing notification rules and Web Push subscriptions.

- `POST /users/me/notifications` creates a site-specific rule with metric, comparison operator, threshold, and optional lead time.
- `PATCH /users/me/notifications/{notification_id}` updates thresholds, comparison, lead time, or active status.
- `GET /users/me/notifications/{notification_id}/events` retrieves the most recent push payloads queued for that rule.
- `POST /users/me/push-subscriptions` registers or refreshes a Web Push endpoint (upsert on the endpoint URL).
- `DELETE /users/me/push-subscriptions/{subscription_id}` deactivates a subscription without removing its history.

When Celery processes new forecasts, or the scheduled `dispatch_notifications` task runs, matching rules generate notification events stored in the `notification_events` table. The worker immediately attempts Web Push delivery (using the VAPID keys described below), updating `delivery_status` to `sent`, `failed`, `config_missing`, or `skipped` based on the outcome.

### Push Delivery Configuration

To enable outbound Web Push delivery, set the following environment variables (typically on the Celery worker):

```plaintext
VAPID_PUBLIC_KEY=<your-public-key>
VAPID_PRIVATE_KEY=<your-private-key>
VAPID_SUBJECT=mailto:ops@example.com  # Optional, defaults to mailto:admin@example.com
```

If the keys are omitted, notifications are still logged but marked with `delivery_status=config_missing`.

## API Documentation

Since this project uses FastAPI, interactive API documentation (Swagger UI) is automatically available when the application is running. Access it at:

`http://localhost:8000/docs`

## Database Migrations (Alembic)

This project uses Alembic for schema migrations.

Common commands:

```bash
pip install -r requirements.txt

# Create the database and run migrations
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/glideator
alembic -c alembic.ini upgrade head

# Create a new revision (example)
alembic -c alembic.ini revision -m "add users and favorites"

# Apply latest migrations
alembic -c alembic.ini upgrade head
```

In production on Render, migrations are executed during deploy/startup.

## MCP Server

The backend includes a Model Context Protocol (MCP) server that enables AI assistants to interact with Glideator's paragliding data through structured tools. The MCP server provides access to:

- **Site Discovery**: List all available paragliding sites
- **Site Information**: Get detailed site descriptions, facilities, and safety information
- **Weather Forecasts**: Access ML-powered flying predictions based on weather forecasts
- **Historical Statistics**: Retrieve seasonal flying patterns and statistics
- **Takeoff/Landing Data**: Get coordinates and details for launch and landing spots
- **Trip Planning**: Find optimal sites for specific date ranges with customizable filters

`http://localhost:8000/mcp`
