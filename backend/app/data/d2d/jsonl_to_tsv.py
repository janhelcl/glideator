#!/usr/bin/env python3
"""
Convert scaled_features.jsonl to TSV format for PostgreSQL COPY import.

Each line of the JSONL file should contain:
{
  "site_id": int,
  "date": "YYYY-MM-DD",
  "features": [float, ...]
}

Outputs TSV to stdout with columns: site_id, date, features
where features is a PostgreSQL array literal like {1.0,2.0,3.0}
"""

import sys
import json
from pathlib import Path


def to_pg_array(values):
    """
    Convert Python list[float|None] to Postgres array literal: {1.0,2.0,NULL}
    """
    parts = []
    for v in values:
        if v is None:
            parts.append("NULL")
        else:
            # Ensure it's a valid float representation
            parts.append(str(float(v)))
    return "{" + ",".join(parts) + "}"


def stream_convert(input_path):
    """
    Stream convert JSONL to TSV, writing to stdout.
    """
    input_file = sys.stdin if input_path == "-" else open(input_path, "r", encoding="utf-8")
    
    try:
        for line_num, line in enumerate(input_file, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                obj = json.loads(line)
                site_id = int(obj["site_id"])
                date = str(obj["date"])  # Already "YYYY-MM-DD"
                feats = obj["features"]
                
                if not isinstance(feats, list):
                    sys.stderr.write(f"Warning: line {line_num}: features is not a list, skipping\n")
                    continue
                
                pg_array = to_pg_array(feats)
                sys.stdout.write(f"{site_id}\t{date}\t{pg_array}\n")
                
            except (KeyError, ValueError, TypeError) as e:
                sys.stderr.write(f"Error on line {line_num}: {e}, skipping\n")
                continue
    finally:
        if input_file != sys.stdin:
            input_file.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        input_path = sys.argv[1]
    else:
        input_path = "-"
    
    stream_convert(input_path)

