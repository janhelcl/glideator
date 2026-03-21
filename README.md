<p align="center">
  <img src="https://github.com/janhelcl/glideator/blob/main/parra-glideator.png" alt="Parra-Glideator Mascot" width="260" />
</p>

# Parra-Glideator – Your AI-powered Paragliding Companion

Parra-Glideator is an innovative web application designed to help paraglider pilots find the perfect place and time to fly. Leveraging sophisticated machine learning and generative AI models, it recommends the best flying spots based on weather forecasts and historical flight conditions.

Meet **Parra-Glideator**, our charming, paragliding gladiator parrot who traded natural flight for a paraglider. Like him, every pilot faces uncertainty—weather conditions, location choice, or flight planning can become a daunting battle. Parra-Glideator is here to ensure you have the odds on your side.

🌤️ **Fly smarter, safer, and with more confidence!**

The project is currently in **public beta** and available at [parra-glideator.com](https://www.parra-glideator.com/). Try it out, plan your next flight adventure, and help us refine this pilot-friendly tool!


---

## Table of Contents

1. [Repository Structure](#repository-structure)
2. [Quick Start](#quick-start)
3. [Key Components](#key-components)
4. [Model Training Pipeline](#model-training-pipeline)

---

## Repository Structure

```
agents/      Autonomous LangGraph agents (e.g. Site Researcher)
analytics/   Notebooks, datasets, training pipeline
art/         Brand assets (Parra-Glideator!)
backend/     FastAPI API, MCP server, Celery workers, Docker
db/          dbt project building the analytics warehouse
frontend/    React + Leaflet single-page app
gfs/         Library for downloading & flattening NOAA GFS data
net/         PyTorch models + preprocessing (Glideator-Net)
scrapers/    Scrapy spiders for XContest & Paragliding Map
```

---

## Quick Start

> **Deployment note:** production runs on **Render** and Render is the source of truth for production configuration. The Docker Compose setup under `backend/docker-compose.dev.yml` is for local development only.

### All-in-one (Docker Compose)

```bash
# clone & launch everything (API + DB + Worker + Web)
$ git clone https://github.com/janhelcl/glideator.git
$ cd glideator
$ docker-compose -f backend/docker-compose.dev.yml up --build
```

* API docs: <http://localhost:8000/docs>  
* Frontend: <http://localhost:3000>
* MCP Server <http://localhost:8000/mcp>

### Individual Services

Each core component can be run on its own. Follow the dedicated README in the corresponding folder for setup & usage details:

* [`backend/README.md`](backend/README.md) — FastAPI API, Celery worker, local dev stack, and Render deployment notes
* [`frontend/README.md`](frontend/README.md) — React single-page application
* [`db/README.md`](db/README.md) — dbt analytics warehouse
* [`scrapers/README.md`](scrapers/README.md) — Scrapy project for flight & site data
* [`gfs/README.md`](gfs/README.md) — GFS data downloader & utilities
* [`net/README.md`](net/README.md) — PyTorch model library
* [`analytics/training/README.md`](analytics/training/README.md) — End-to-end training pipeline
* [`agents/site_researcher/README.md`](agents/site_researcher/README.md) — Autonomous Site Researcher agent

---

## Key Components

* **Backend** (`backend/`) – FastAPI, MCP server, PostgreSQL, Celery, Redis, deployed on Render in production.
* **Frontend** (`frontend/`) – React 18, Material-UI, React-Leaflet, D3.
* **Warehouse** (`db/`) – Postgres + dbt (staging & mart models).
* **ML Library** (`net/`) – Neural Networks implemented in PyTorch.
* **Training** (`analytics/training/`) – WebDataset loaders, notebooks.
* **Weather** (`gfs/`) – Fetches & processes NOAA GFS GRIB2 files.
* **Scrapers** (`scrapers/`) – Flight & site data collection with Scrapy.
* **Agents** (`agents/site_researcher/`) – LangGraph agent enriching site metadata.
* **MCP Integration** – Model Context Protocol server enabling AI assistants to access paragliding data through structured tools for site information, weather forecasts, trip planning, and more.

---

## Model Training Pipeline

1. Scrapers write raw flights & sites → Postgres.
2. `dbt` transforms them into clean mart tables.
3. Training notebooks export WebDataset shards.
4. PyTorch models are trained & the best checkpoint is shipped to the API.

For the full deep-dive (maths included!) see [`analytics/training/README.md`](analytics/training/README.md).