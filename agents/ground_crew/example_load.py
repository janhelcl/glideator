"""Example script showing how to use load_extraction_run."""

import json
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

from ground_crew.io import load_extraction_run

# Load environment variables
load_dotenv()

# Create database engine
connection_string = "postgresql://{user}:{password}@{host}:{port}/{db}".format(
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    host=os.getenv('DB_HOST'),
    port=os.getenv('DB_PORT'),
    db=os.getenv('DB_NAME')
)
engine = create_engine(connection_string)

# Example 1: Load a single extraction run from JSONL file
print("Example 1: Load first line from JSONL")
with open("outputs/candidate_retrieval_results.jsonl", "r", encoding="utf-8") as f:
    first_line = f.readline()
    data = json.loads(first_line)
    
    run_id = load_extraction_run(data, engine)
    
    print(f"✓ Loaded extraction run with run_id={run_id}")
    print(f"  Site: {data['site_name']} (site_id={data['site_id']})")
    print(f"  Agent: {data['agent']}")
    print(f"  Model: {list(data['result']['usage_stats']['by_model'].keys())[0]}")
    print(f"  Candidates: {len(data['result']['structured_output']['candidate_websites'])}")

print("\n" + "="*60 + "\n")

# Example 2: Load all extraction runs from JSONL file
print("Example 2: Load all extraction runs")
with open("outputs/candidate_retrieval_results.jsonl", "r", encoding="utf-8") as f:
    loaded_count = 0
    for i, line in enumerate(f, 1):
        data = json.loads(line)
        run_id = load_extraction_run(data, engine)
        loaded_count += 1
        if i % 10 == 0:
            print(f"  Loaded {i} runs...")
    
    print(f"✓ Successfully loaded {loaded_count} extraction runs!")

print("\n" + "="*60 + "\n")

# Example 3: Query the loaded data
print("Example 3: Query loaded data")
from sqlalchemy import text

with engine.connect() as conn:
    # Count total runs
    result = conn.execute(text("""
        SELECT COUNT(*) as total_runs,
               COUNT(DISTINCT site_id) as unique_sites,
               SUM(candidate_count) as total_candidates
        FROM glideator_ground_crew.extraction_runs
    """))
    stats = result.fetchone()
    print(f"  Total runs: {stats.total_runs}")
    print(f"  Unique sites: {stats.unique_sites}")
    print(f"  Total candidates: {stats.total_candidates}")
    
    # Show latest runs
    result = conn.execute(text("""
        SELECT run_id, site_id, extracted_at, candidate_count
        FROM glideator_ground_crew.extraction_runs
        ORDER BY extracted_at DESC
        LIMIT 5
    """))
    print("\n  Latest 5 runs:")
    for row in result:
        print(f"    run_id={row.run_id}, site_id={row.site_id}, "
              f"extracted_at={row.extracted_at}, candidates={row.candidate_count}")

