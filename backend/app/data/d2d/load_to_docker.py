#!/usr/bin/env python3
"""
Helper script to load TSV data into Docker postgres container.
Handles encoding properly and streams data.
"""

import sys
import subprocess
from pathlib import Path

def load_via_docker(jsonl_path, container_name="backend-postgres-1"):
    """Convert JSONL and pipe directly to Docker psql."""
    # Import our converter
    from jsonl_to_tsv import stream_convert
    
    # Set up docker exec command
    docker_cmd = [
        "docker", "exec", "-i", container_name,
        "psql", "-U", "postgres", "-d", "glideator",
        "-c", r"\copy scaled_features (site_id, date, features) FROM STDIN WITH (FORMAT text, DELIMITER E'\t', NULL 'NULL');"
    ]
    
    print(f"Starting conversion and load from {jsonl_path}...")
    print("This may take several minutes...")
    
    # Open subprocess for docker
    proc = subprocess.Popen(
        docker_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8',
        bufsize=8192
    )
    
    # Stream convert and write to docker stdin
    input_file = open(jsonl_path, "r", encoding="utf-8")
    line_count = 0
    
    try:
        from jsonl_to_tsv import to_pg_array
        import json
        
        for line_num, line in enumerate(input_file, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                obj = json.loads(line)
                site_id = int(obj["site_id"])
                date = str(obj["date"])
                feats = obj["features"]
                
                if not isinstance(feats, list):
                    continue
                
                pg_array = to_pg_array(feats)
                tsv_line = f"{site_id}\t{date}\t{pg_array}\n"
                
                proc.stdin.write(tsv_line)
                line_count += 1
                
                if line_count % 10000 == 0:
                    print(f"Processed {line_count} rows...", flush=True)
                    
            except Exception as e:
                print(f"Error on line {line_num}: {e}", file=sys.stderr)
                continue
        
        # Close stdin to signal EOF
        proc.stdin.close()
        
        # Wait for completion
        stdout, stderr = proc.communicate()
        
        if proc.returncode != 0:
            print(f"Error during load: {stderr}", file=sys.stderr)
            sys.exit(proc.returncode)
        
        print(f"\nSuccessfully loaded {line_count} rows!")
        if stdout:
            print(stdout)
            
    finally:
        input_file.close()

if __name__ == "__main__":
    jsonl_path = sys.argv[1] if len(sys.argv) > 1 else "../scaled_features.jsonl"
    jsonl_path = Path(jsonl_path).resolve()
    
    if not jsonl_path.exists():
        print(f"Error: JSONL file not found: {jsonl_path}", file=sys.stderr)
        sys.exit(1)
    
    load_via_docker(jsonl_path)

