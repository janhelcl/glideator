"""
GFS Data Downloader

This script downloads Global Forecast System (GFS) data files from NOAA's THREDDS server
for a specified date range and geographical area. It supports downloading historical
reanalysis data at 0.25° resolution.

Example usage:
    python gfs_downloader.py --start-date 2024-01-01 --end-date 2024-01-03 --output gfs_data
"""

import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path
import sys
import time
from typing import Iterator, Optional

import requests
from requests.exceptions import RequestException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('gfs_downloader.log')
    ]
)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_VARIABLES = [
    'u-component_of_wind_height_above_ground',
    'v-component_of_wind_height_above_ground',
    'Temperature_height_above_ground',
    'Dewpoint_temperature_height_above_ground',
    'Geopotential_height_isobaric',
    'Relative_humidity_isobaric',
    'Temperature_isobaric',
    'u-component_of_wind_isobaric',
    'v-component_of_wind_isobaric',
    'Vertical_velocity_pressure_isobaric',
    'Cloud_mixing_ratio_isobaric',
    'Geopotential_height_surface',
    'Precipitable_water_entire_atmosphere_single_layer',
    'Pressure_surface',
    'Wind_speed_gust_surface',
    'Cloud_water_entire_atmosphere_single_layer',
]

def generate_gfs_urls(
    start_date: datetime,
    end_date: datetime,
    run: int = 0,
    delta: int = 0,
    north: float = 60,
    south: float = 35,
    west: float = -10,
    east: float = 23,
    variables: Optional[list] = None
) -> Iterator[str]:
    """
    Generate URLs for downloading GFS data within specified parameters.

    Args:
        start_date: Start date for data download
        end_date: End date for data download
        run: Model run hour (0, 6, 12, 18)
        delta: Forecast hour delta
        north: Northern boundary of the area (latitude)
        south: Southern boundary of the area (latitude)
        west: Western boundary of the area (longitude)
        east: Eastern boundary of the area (longitude)
        variables: List of GFS variables to download. If None, uses DEFAULT_VARIABLES

    Yields:
        str: URL for downloading GFS data
    """
    if variables is None:
        variables = DEFAULT_VARIABLES

    var_params = "&".join(f"var={var}" for var in variables)
    
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime("%Y%m%d")
        year_str = current_date.strftime("%Y")
        ref_time = current_date.replace(hour=run) + timedelta(hours=delta)
        
        url = (
            f"https://thredds.rda.ucar.edu/thredds/ncss/grid/files/g/d084001"
            f"/{year_str}/{date_str}/gfs.0p25.{date_str}{run:02d}.f{delta:03d}.grib2"
            f"?{var_params}"
            f"&north={north}&west={west}&east={east}&south={south}"
            f"&horizStride=1"
            f"&time_start={ref_time.isoformat()}Z"
            f"&time_end={ref_time.isoformat()}Z"
            f"&accept=netcdf3"
        )
        
        yield url
        current_date += timedelta(days=1)

def download_gfs_files(
    urls: Iterator[str],
    output_folder: str,
    max_retries: int = 3,
    retry_delay: int = 5
) -> None:
    """
    Downloads GFS files from provided URLs to specified output folder.
    
    Args:
        urls: Iterator of GFS data URLs
        output_folder: Path to folder where files should be saved
        max_retries: Maximum number of download attempts per file
        retry_delay: Delay in seconds between retry attempts
    """
    output_path = Path(output_folder)
    output_path.mkdir(parents=True, exist_ok=True)
    
    failed_urls = []
    consecutive_failures = 0
    
    for url in urls:
        filename = url.split('/')[-1].split('?')[0]
        file_path = output_path / filename
        
        if file_path.exists():
            logger.info(f"File {filename} already exists, skipping...")
            continue
            
        for attempt in range(max_retries):
            try:
                logger.info(f"Downloading {filename} (attempt {attempt + 1}/{max_retries})")
                response = requests.get(url, stream=True)
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                block_size = 8192
                downloaded = 0
                
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=block_size):
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Log download progress
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            logger.debug(f"Download progress: {progress:.1f}%")
                
                logger.info(f"Successfully downloaded {filename}")
                consecutive_failures = 0  # Reset consecutive failures on success
                break
                
            except RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Failed to download {filename} after {max_retries} attempts")
                    failed_urls.append(url)
                    consecutive_failures += 1
                    if consecutive_failures >= 3:
                        logger.error("Three consecutive URLs failed. Stopping download.")
                        break
                    else:
                        break

    if failed_urls:
        logger.error("The following URLs failed to download:")
        for failed_url in failed_urls:
            logger.error(failed_url)

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Download GFS data files for a specified date range and area."
    )
    
    parser.add_argument(
        "--start-date",
        type=lambda s: datetime.strptime(s, '%Y-%m-%d'),
        required=True,
        help="Start date in YYYY-MM-DD format"
    )
    
    parser.add_argument(
        "--end-date",
        type=lambda s: datetime.strptime(s, '%Y-%m-%d'),
        required=True,
        help="End date in YYYY-MM-DD format"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default="gfs_data",
        help="Output folder path (default: gfs_data)"
    )
    
    parser.add_argument(
        "--run",
        type=int,
        choices=[0, 6, 12, 18],
        default=0,
        help="Model run hour (default: 0)"
    )
    
    parser.add_argument(
        "--delta",
        type=int,
        default=0,
        help="Forecast hour delta (default: 0)"
    )
    
    parser.add_argument(
        "--north",
        type=float,
        default=60,
        help="Northern boundary latitude (default: 60)"
    )
    
    parser.add_argument(
        "--south",
        type=float,
        default=35,
        help="Southern boundary latitude (default: 35)"
    )
    
    parser.add_argument(
        "--west",
        type=float,
        default=-10,
        help="Western boundary longitude (default: -10)"
    )
    
    parser.add_argument(
        "--east",
        type=float,
        default=23,
        help="Eastern boundary longitude (default: 23)"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    return parser.parse_args()

def main() -> None:
    """Main execution function."""
    args = parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    logger.info(f"Starting GFS data download from {args.start_date.date()} to {args.end_date.date()}")
    
    try:
        urls = generate_gfs_urls(
            start_date=args.start_date,
            end_date=args.end_date,
            run=args.run,
            delta=args.delta,
            north=args.north,
            south=args.south,
            west=args.west,
            east=args.east
        )
        
        download_gfs_files(urls, args.output)
        logger.info("Download completed successfully")
        
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()