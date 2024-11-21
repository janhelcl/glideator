"""
This script parses KML or KMZ files containing paragliding spot data and converts them to CSV format.

The script extracts information about paragliding spots including:
- Name and full name of the spot
- Type of spot (takeoff, landing, training)
- Type of takeoff (mountain, coastal, winch) 
- Whether it's suitable for hang gliders (HG)
- Wind directions
- Altitude
- Coordinates (latitude/longitude)
- Full description

The KML/KMZ files are expected to follow a specific naming convention for spots:
- TO: Mountain takeoff
- TOC: Coastal takeoff  
- TOW: Winch takeoff
- LZ: Landing zone
- TH: Training hill

Spots can optionally include:
- -HG suffix to indicate hang glider suitability
- Wind directions in parentheses e.g. (N), (SSW-S)

Usage:
    python parse_paragliding_spots.py <input_kml_or_kmz_file> <output_csv_file>

Arguments:
    input_kml_or_kmz_file: Path to input KML or KMZ file containing paragliding spot data
    output_csv_file: Path where the output CSV file should be written

Example:
    python parse_paragliding_spots.py spots.kmz spots.csv
    python parse_paragliding_spots.py spots.kml spots.csv
"""

import sys
import csv
import re
import logging
import zipfile
import tempfile

from pykml import parser
from lxml import etree
from bs4 import BeautifulSoup


logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

class KMLParserExtractor:
    def __init__(self, file_path):
        self.original_file_path = file_path
        self.kml_file_path = file_path  # This will point to the actual KML file
        self.namespaces = {
            'kml': 'http://www.opengis.net/kml/2.2',
            'gx': 'http://www.google.com/kml/ext/2.2',
            'atom': 'http://www.w3.org/2005/Atom'
        }
        # Define abbreviation mappings
        self.abbreviation_mapping = {
            'TO': {'spot_type': 'takeoff', 'takeoff_type': 'mountain'},
            'TOC': {'spot_type': 'takeoff', 'takeoff_type': 'coast'},
            'TOW': {'spot_type': 'takeoff', 'takeoff_type': 'winch'},
            'LZ': {'spot_type': 'landing', 'takeoff_type': None},
            'TH': {'spot_type': 'training', 'takeoff_type': None}
        }
        self.temp_dir = None  # To hold temporary directory for extracted KML

    def load_kml(self):
        """
        Loads the KML content from a KML or KMZ file.
        If the file is a KMZ, it extracts the KML file from it.
        """
        try:
            if self.original_file_path.lower().endswith('.kmz'):
                logging.info("KMZ file detected. Extracting KML from KMZ.")
                with zipfile.ZipFile(self.original_file_path, 'r') as kmz:
                    # Typically, the main KML file is named 'doc.kml'
                    kml_names = [name for name in kmz.namelist() if name.endswith('.kml')]
                    if not kml_names:
                        logging.error("No KML file found inside the KMZ archive.")
                        sys.exit(1)
                    # For simplicity, take the first KML file found
                    kml_name = kml_names[0]
                    logging.info(f"Extracting KML file: {kml_name}")
                    kml_data = kmz.read(kml_name)
                    
                    # Create a temporary file to hold the extracted KML
                    self.temp_dir = tempfile.TemporaryDirectory()
                    self.kml_file_path = f"{self.temp_dir.name}/extracted.kml"
                    with open(self.kml_file_path, 'wb') as temp_kml:
                        temp_kml.write(kml_data)
                logging.info("KML extracted successfully from KMZ.")
            else:
                logging.info("KML file detected. Proceeding with parsing.")

            with open(self.kml_file_path, 'rb') as f:
                self.root = parser.parse(f).getroot()
            logging.info("KML file loaded successfully.")
        except zipfile.BadZipFile:
            logging.error("The file does not appear to be a valid KMZ (ZIP) archive.")
            sys.exit(1)
        except FileNotFoundError:
            logging.error(f"The file {self.original_file_path} does not exist.")
            sys.exit(1)
        except Exception as e:
            logging.error(f"Error loading KML/KMZ file: {e}")
            sys.exit(1)

    def extract_spots(self):
        """
        Extracts spot information from the KML file.
        Returns a list of dictionaries, each representing a spot.
        """
        spots = []
        placemarks = self.root.findall('.//kml:Placemark', namespaces=self.namespaces)
        logging.info(f"Found {len(placemarks)} placemarks.")
        for placemark in placemarks:
            spot = {}
            # Extract Full Name
            name_elem = placemark.find('kml:name', namespaces=self.namespaces)
            full_name = name_elem.text.strip() if name_elem is not None else "N/A"
            spot['full_name'] = full_name

            # Parse Spot Attributes from Full Name
            name, spot_type, takeoff_type, hg, wind_direction = self.parse_spot_full_name(full_name)
            spot['name'] = name
            spot['spot_type'] = spot_type
            spot['takeoff_type'] = takeoff_type
            spot['hg'] = hg
            spot['wind_direction'] = wind_direction

            # Extract Description
            desc_elem = placemark.find('kml:description', namespaces=self.namespaces)
            cleaned_description = self._clean_description(desc_elem.text) if desc_elem is not None else "N/A"
            spot['Description'] = cleaned_description

            # Extract Altitude from Description
            altitude = self.parse_altitude(cleaned_description)
            spot['altitude'] = altitude

            # Extract Coordinates
            coord_elem = placemark.find('.//kml:coordinates', namespaces=self.namespaces)
            if coord_elem is not None and coord_elem.text:
                coords = coord_elem.text.strip().split(',')
                if len(coords) >= 2:
                    spot['Longitude'] = coords[0]
                    spot['Latitude'] = coords[1]
                else:
                    spot['Longitude'] = "N/A"
                    spot['Latitude'] = "N/A"
            else:
                spot['Longitude'] = "N/A"
                spot['Latitude'] = "N/A"

            spots.append(spot)
        return spots

    def parse_spot_full_name(self, full_name):
        """
        Parses the full spot name to extract the cleaned name, spot_type, takeoff_type, hg, and wind_direction.
        """
        # Regular expression to match the abbreviation and optional -HG and wind direction
        # Example: "TO (SSW-S) Gjeravicë" or "TOC -HG (NE) Coastal Spot"
        pattern = r'^(TOC?|TOW|LZ|TH)(-HG)?\s*(?:\(([^)]+)\))?\s+(.*)$'
        match = re.match(pattern, full_name)
        if match:
            abbrev = match.group(1)
            hg_suffix = match.group(2)
            wind_direction = match.group(3).strip() if match.group(3) else None
            remaining_name = match.group(4).strip()

            mapping = self.abbreviation_mapping.get(abbrev, {})
            spot_type = mapping.get('spot_type')
            takeoff_type = mapping.get('takeoff_type')
            hg = True if hg_suffix else False

            return remaining_name, spot_type, takeoff_type, hg, wind_direction
        else:
            # If pattern doesn't match, return original name and set new attributes to None
            return full_name, None, None, None, None

    def parse_altitude(self, description):
        """
        Extracts altitude from the description.
        Expected format: "H <number> m"
        """
        pattern = r'H\s+(\d+)\s*m'
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            return int(match.group(1))
        else:
            return None

    def _clean_description(self, description):
        """
        Cleans the HTML content in descriptions to plain text while preserving line breaks.
        """
        if not description:
            return "N/A"
        try:
            soup = BeautifulSoup(description, 'html.parser')
            # Replace <br> and <p> tags with newline characters
            for br in soup.find_all(['br', 'p']):
                br.replace_with('\n')
            text = soup.get_text(separator="\n").strip()
            return text
        except Exception as e:
            logging.warning(f"Error cleaning description: {e}")
            return description.strip()

    def save_to_csv(self, spots, output_file):
        """
        Saves the extracted spots to a CSV file.
        """
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['full_name', 'name', 'description', 'latitude', 'longitude', 'spot_type', 'takeoff_type', 'hg', 'wind_direction', 'altitude']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                for spot in spots:
                    writer.writerow({
                        'full_name': spot['full_name'],
                        'name': spot['name'],
                        'description': spot['Description'],
                        'latitude': spot['Latitude'],
                        'longitude': spot['Longitude'],
                        'spot_type': spot['spot_type'],
                        'takeoff_type': spot['takeoff_type'],
                        'hg': spot['hg'],
                        'wind_direction': spot['wind_direction'],
                        'altitude': spot['altitude']
                    })
            logging.info(f"Successfully wrote to {output_file}.")
        except Exception as e:
            logging.error(f"Error writing to CSV file: {e}")
            sys.exit(1)

    def _print_element(self, element, indent=0):
        """
        Recursive function to print XML elements.
        """
        prefix = "  " * indent
        tag = etree.QName(element).localname
        print(f"{prefix}<{tag}>")
        for child in element:
            self._print_element(child, indent + 1)
        print(f"{prefix}</{tag}>")

def main():
    """Main function to run the KML/KMZ parsing and CSV conversion."""
    if len(sys.argv) != 3:
        print("Usage: python parse_paragliding_spots.py <input_kml_or_kmz_file> <output_csv_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_csv = sys.argv[2]

    extractor = KMLParserExtractor(input_file)
    extractor.load_kml()
    spots = extractor.extract_spots()
    extractor.save_to_csv(spots, output_csv)
    logging.info(f"Extracted {len(spots)} spots to {output_csv}")

if __name__ == "__main__":
    main()