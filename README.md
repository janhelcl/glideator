<p align="center">
  <img src="https://github.com/janhelcl/glideator/blob/main/parra-glideator.png" alt="Parra-Glideator Mascot" width="260" />
</p>

# Parra-Glideator – Your AI-powered Paragliding Companion

Parra-Glideator is an innovative web application designed to help paraglider pilots find the perfect place and time to fly. Leveraging sophisticated machine learning and generative AI models, it recommends the best flying spots based on weather forecasts and historical flight conditions.

Meet **Parra-Glideator**, our charming, paragliding gladiator parrot who traded natural flight for a paraglider. Like him, every pilot faces uncertainty—weather conditions, location choice, or flight planning can become a daunting battle. Parra-Glideator is here to ensure you have the odds on your side.

🌤️ **Fly smarter, safer, and with more confidence!**

The project is currently in **public beta** and available at [parra-glideator.com](https://www.parra-glideator.com/). Try it out, plan your next flight adventure, and help us refine this pilot-friendly tool!

🤖 **Now available in ChatGPT:** Parra-Glideator has been approved as a public ChatGPT plugin. Ask ChatGPT where and when to fly, compare sites and dates, inspect forecast-derived XC potential, check historical seasonality, or pull up launches, landings, and curated local resources using Glideator's live tools.

---

## Table of Contents

1. [Repository Structure](#repository-structure)
2. [Quick Start](#quick-start)
3. [Key Components](#key-components)
4. [Model Training Pipeline](#model-training-pipeline)

---

## Repository Structure

~~~
docker-compose.dev.yml   Local dev stack (API, Postgres, Redis, Celery, frontend)
agents/      Ground Crew (site discovery & resources), Chat assistant
analytics/   Notebooks, datasets, production training pipeline
art/         Brand assets (Parra-Glideator!)
backend/     FastAPI API, MCP server, Celery workers, Dockerfiles (web & worker)
db/          dbt project building the analytics warehouse
frontend/    React + Leaflet single-page app
gfs/         Library for downloading & flattening NOAA GFS data
ml/          Reproducible ML experimentation and model documentation
net/         PyTorch models + preprocessing (Glideator-Net)
scrapers/    Scrapy spiders for XContest & Paragliding Map
~~~

---

## Quick Start

> **Deployment note:** production runs on **Render** and Render is the source of truth for production configuration. The Docker Compose file docker-compose.dev.yml at the repository root is for local development only.

### All-in-one (Docker Compose)

~~~bash
# clone & launch everything (API + DB + Worker + Web)
$ git clone https://github.com/janhelcl/glideator.git
$ cd glideator
$ docker-compose -f docker-compose.dev.yml up --build
~~~

* API docs: <http://localhost:8000/docs>
* Frontend: <http://localhost:3000>
* MCP Server: <http://localhost:8000/mcp>

### Individual Services

Each core component can be run on its own. Follow the dedicated README in the corresponding folder for setup and usage details:

* [backend/README.md](backend/README.md) — FastAPI API, Celery worker, Docker Compose details, Render deployment notes
* [frontend/README.md](frontend/README.md) — React single-page application
* [db/README.md](db/README.md) — dbt analytics warehouse
* [scrapers/README.md](scrapers/README.md) — Scrapy project for flight and site data
* [gfs/README.md](gfs/README.md) — GFS data downloader and utilities
* [ml/README.md](ml/README.md) — ML experiment harness, benchmarks, model docs, and decision records
* [net/README.md](net/README.md) — PyTorch model library
* [analytics/training/README.md](analytics/training/README.md) — Production training pipeline
* [agents/ground_crew/README.md](agents/ground_crew/README.md) — Ground Crew: browser agents, validation, exports for site resources
* [agents/chat/README.md](agents/chat/README.md) — Parra-Glideator chat assistant

---

## Key Components

* **Backend** (backend/) – FastAPI, MCP server, PostgreSQL, Celery, Redis, deployed on Render in production.
* **Frontend** (frontend/) – React 18, Material-UI, React-Leaflet, D3.
* **Warehouse** (db/) – Postgres + dbt staging and mart models.
* **ML Experiments** (ml/) – Reproducible model comparison, evaluation, tracking, and research documentation.
* **ML Library** (net/) – Production neural networks implemented in PyTorch.
* **Training** (analytics/training/) – WebDataset loaders and production training notebooks.
* **Weather** (gfs/) – Fetches and processes NOAA GFS GRIB2 files.
* **Scrapers** (scrapers/) – Flight and site data collection with Scrapy.
* **Ground Crew** (agents/ground_crew/) – Browser-use pipelines that discover and validate local site and club links, extract webcam and meteostation URLs, and export data for the Glideator API.
* **Chat** (agents/chat/) – Conversational assistant for the product.
* **ChatGPT & MCP Integration** – The approved public Parra-Glideator ChatGPT plugin gives ChatGPT structured access to site discovery, forecasts, XC potential, trip planning, historical seasonality, launches and landings, and curated local resources. The same read-only tools remain available through the MCP server for other compatible assistants.

---

## Model Training Pipeline

1. Scrapers write raw flights and sites to Postgres.
2. dbt transforms them into clean mart tables.
3. The production pipeline prepares training data and trains deployable models.
4. The ml/ workspace provides reproducible benchmarks for comparing candidate models before promotion.
5. Promoted artifacts are integrated explicitly into the serving stack.

For production training details, see [analytics/training/README.md](analytics/training/README.md). For model experimentation and benchmark documentation, see [ml/README.md](ml/README.md).
