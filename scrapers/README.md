# Glideator Scrapers

This directory contains the Scrapy project used to gather data for the Glideator flight recommender system. The scrapers are designed to extract flight information from various paragliding websites.

## Project Structure

- **`scrapy.cfg`**: The main configuration file for the Scrapy project.
- **`glideator/`**: The core directory of the Scrapy project.
  - **`spiders/`**: Contains the spider definitions, which are the classes that define how to scrape specific websites.
  - **`items.py`**: Defines the data structure (Scrapy Items) for the scraped data.
  - **`pipelines.py`**: Used for processing the scraped data (e.g., cleaning, validation, saving to a database).
  - **`settings.py`**: Contains the settings for the Scrapy project, such as user-agent strings, request delays, and pipeline configurations.
- **`requirements.txt`**: Lists the Python dependencies for this project.
- **`outputs/`**: The default directory where the scraped data is saved.

## Dependencies

- `scrapy`
- `scrapy-playwright`

## Usage

1.  **Install dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

2.  **Run a spider**:

    To run a specific spider, use the `scrapy crawl` command from within the `scrapers` directory:

    ```bash
    scrapy crawl <spider_name>
    ```

    Replace `<spider_name>` with the name of the spider you want to run.
