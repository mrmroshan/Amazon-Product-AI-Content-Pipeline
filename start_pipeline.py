import os
import sqlite3
import logging
from agents.orchestrator import build_content_crew
from tools.video_generator import VideoGenerator
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DB_NAME = os.getenv("DB_NAME", "jobs.db")
ASIN_LIST_FILE = os.getenv("ASIN_LIST_FILE", "asins.txt")

def start_pipeline():
    """
    Main entry point for starting the Content Generation pipeline.
    Reads ASINs from queue, respects idempotency, triggers AI Agents,
    and queues videos up for worker.py to process.
    """
    if not os.path.exists(ASIN_LIST_FILE):
        logging.error(f"Cannot find ASIN list at {ASIN_LIST_FILE}")
        return

    with open(ASIN_LIST_FILE, 'r') as f:
        asins = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    video_gen = VideoGenerator()

    for asin in asins:
        # Idempotency Check
        cursor.execute("SELECT status FROM jobs WHERE asin = ?", (asin,))
        row = cursor.fetchone()
        
        if row:
            current_status = row[0]
            if current_status in ['QUEUED', 'RESEARCHING', 'SCRIPTING', 'RENDERING', 'COMPLETED', 'QA_PASSED']:
                logging.info(f"Skipping ASIN {asin} - already in DB with status: {current_status}")
                continue

        # Insert new job or overwrite failed job
        cursor.execute(
            "INSERT OR REPLACE INTO jobs (asin, status) VALUES (?, ?)", 
            (asin, 'RESEARCHING')
        )
        conn.commit()
        
        logging.info(f"Triggering CrewAI for ASIN {asin}...")
        
        try:
            # Update to SCRIPTING automatically handled by Orchestrator internally in a larger setup
            cursor.execute("UPDATE jobs SET status = 'SCRIPTING' WHERE asin = ?", (asin,))
            conn.commit()
            
            # Step 1: Run CrewAI (Agent A & B)
            crew = build_content_crew(asin)
            script_result = crew.kickoff()
            
            # Step 2: Trigger Video Rendering (Agent C Mock)
            cursor.execute("UPDATE jobs SET status = 'RENDERING' WHERE asin = ?", (asin,))
            conn.commit()
            
            job_id = video_gen.start_render_job(asin, {"script": str(script_result)})
            
            cursor.execute(
                "UPDATE jobs SET rapidapi_job_id = ?, updated_at = CURRENT_TIMESTAMP WHERE asin = ?", 
                (job_id, asin)
            )
            conn.commit()
            
            logging.info(f"ASIN {asin} pipeline submitted. Handed over to worker.py")

        except Exception as e:
            logging.error(f"Pipeline error for ASIN {asin}: {e}")
            cursor.execute("UPDATE jobs SET status = 'FAILED' WHERE asin = ?", (asin,))
            conn.commit()

    conn.close()
    logging.info("Pipeline sweep finished.")

if __name__ == "__main__":
    start_pipeline()
