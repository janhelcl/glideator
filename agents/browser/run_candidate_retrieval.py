import asyncio
import json
import os
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import create_engine

from src import agents
from src import utils


async def run_candidate_retrieval_for_all_sites(output_file: str = "candidate_retrieval_results.jsonl"):
    """
    Run CandidateRetrievalAgent for all sites and write results to a JSONL file.
    
    Args:
        output_file: Path to the output JSONL file
    """
    # Load environment variables
    load_dotenv()
    
    # Set up database connection
    connection_string = (
        "postgresql://{user}:{password}@{host}:{port}/{db}".format(
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            db=os.getenv("DB_NAME"),
        )
    )
    engine = create_engine(connection_string)
    
    # Get all sites
    sites_df = utils.get_sites(engine)
    print(f"Found {len(sites_df)} sites to process")
    
    # Ensure output directory exists
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Process each site
    with open(output_file, 'w', encoding='utf-8') as f:
        for idx, row in sites_df.iterrows():
            site_id = row['site_id']
            site_name = row['name']
            country = row['country']
            
            print(f"\n{'='*80}")
            print(f"Processing site {idx + 1}/{len(sites_df)}: {site_name} ({country})")
            print(f"{'='*80}")
            
            try:
                # Format site details
                site_details = utils.format_site_details(site_name, country, engine)
                
                # Create and run agent
                retrieval_agent = agents.CandidateRetrievalAgent()
                retrieval_agent.set_task(site_details)
                
                print(f"Running agent for {site_name}...")
                start_time = datetime.now()
                result = await retrieval_agent.run()
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                # Prepare output record
                output_record = {
                    "site_id": int(site_id),
                    "site_name": site_name,
                    "country": country,
                    "timestamp": datetime.now().isoformat(),
                    "duration_seconds": duration,
                    "result": result
                }
                
                # Write to JSONL file
                f.write(json.dumps(output_record, ensure_ascii=False) + '\n')
                f.flush()  # Ensure data is written immediately
                
                # Print summary
                if result['is_successful']:
                    num_candidates = len(result['structured_output'].get('candidate_websites', []))
                    print(f"✅ Success! Found {num_candidates} candidate website(s)")
                    print(f"   Duration: {duration:.2f}s")
                    print(f"   Cost: ${result['usage_stats'].get('total_cost', 0):.4f}")
                else:
                    print(f"❌ Failed to retrieve candidates")
                    print(f"   Duration: {duration:.2f}s")
                
            except Exception as e:
                print(f"❌ Error processing {site_name}: {str(e)}")
                
                # Write error record
                error_record = {
                    "site_id": int(site_id),
                    "site_name": site_name,
                    "country": country,
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e),
                    "result": None
                }
                f.write(json.dumps(error_record, ensure_ascii=False) + '\n')
                f.flush()
                
                continue
    
    print(f"\n{'='*80}")
    print(f"✅ All sites processed. Results written to: {output_file}")
    print(f"{'='*80}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run CandidateRetrievalAgent for all paragliding sites"
    )
    parser.add_argument(
        "--output",
        "-o",
        default="candidate_retrieval_results.jsonl",
        help="Output JSONL file path (default: candidate_retrieval_results.jsonl)"
    )
    
    args = parser.parse_args()
    
    # Run the async function
    asyncio.run(run_candidate_retrieval_for_all_sites(args.output))


if __name__ == "__main__":
    main()

