import sqlite3
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DB_NAME = os.getenv("DB_NAME", "jobs.db")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def setup_database():
    """Initializes the SQLite database with the jobs table for tracking the async state machine."""
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Create the core jobs table
    # Schema accommodates Queueing, Agentic processing, and multimodal tracking 
    create_table_query = '''
    CREATE TABLE IF NOT EXISTS jobs (
        asin TEXT PRIMARY KEY,
        status TEXT CHECK(status IN ('QUEUED', 'RESEARCHING', 'SCRIPTING', 'GENERATING_IMAGES', 'AWAITING_REVIEW', 'RENDERING', 'COMPLETED', 'QA_PASSED', 'QA_FAILED', 'FAILED')),
        rapidapi_job_id TEXT,
        video_url TEXT,
        local_video_path TEXT,
        research_data JSON,
        script_data JSON,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    '''
    
    cursor.execute(create_table_query)
    conn.commit()
    conn.close()
    
    logging.info(f"Database '{DB_NAME}' setup completed successfully.")

if __name__ == "__main__":
    setup_database()
