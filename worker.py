import sqlite3
import time
import logging
import os
import threading
from tools.video_generator import VideoGenerator
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DB_NAME = os.getenv("DB_NAME", "jobs.db")
_worker_thread = None
_stop_event = threading.Event()

def poll_rendering_jobs():
    """ Async State Machine Polling Loop. """
    video_gen = VideoGenerator()
    logging.info("Worker daemon started polling...")
    
    while not _stop_event.is_set():
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT asin, rapidapi_job_id FROM jobs WHERE status = 'RENDERING'")
            jobs = cursor.fetchall()
            
            for asin, job_id in jobs:
                if not job_id:
                    continue
                status_response = video_gen.check_job_status(job_id)
                new_status = status_response.get("status")
                
                if new_status == "COMPLETED":
                    video_url = status_response.get("video_url")
                    logging.info(f"[{asin}] Render COMPLETE! URL: {video_url}")
                    cursor.execute(
                        "UPDATE jobs SET status = 'COMPLETED', video_url = ?, updated_at = CURRENT_TIMESTAMP WHERE asin = ?",
                        (video_url, asin)
                    )
                elif new_status == "FAILED":
                    logging.error(f"[{asin}] Render FAILED.")
                    cursor.execute("UPDATE jobs SET status = 'FAILED', updated_at = CURRENT_TIMESTAMP WHERE asin = ?", (asin,))
            
            conn.commit()
            conn.close()
            
        except sqlite3.OperationalError:
            pass # Database might be locked, just skip a beat
        except Exception as e:
            logging.error(f"Worker Database Polling Error: {e}")
            
        # Poll every 5 seconds for Web UI snappiness
        _stop_event.wait(5.0)

def start_worker():
    global _worker_thread
    if _worker_thread is None or not _worker_thread.is_alive():
        _stop_event.clear()
        _worker_thread = threading.Thread(target=poll_rendering_jobs, daemon=True)
        _worker_thread.start()
        logging.info("Worker thread initialized.")

def stop_worker():
    global _worker_thread
    if _worker_thread is not None:
        _stop_event.set()
        _worker_thread.join()
        _worker_thread = None

if __name__ == "__main__":
    start_worker()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_worker()
