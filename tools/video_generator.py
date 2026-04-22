import os
import time
import logging
from typing import Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class VideoGenerator:
    def __init__(self):
        self.google_key = os.getenv("GOOGLE_API_KEY")
        self.kling_key = os.getenv("KLING_API_KEY")
        
    def start_render_job(self, asin: str, script_payload: Dict[str, Any]) -> str:
        """
        Triggers the video generation. First tries Google Veo / Imagen. 
        If that fails, falls back to Kling AI.
        Returns a mock Job ID for the async worker to poll.
        """
        logging.info(f"Attempting to start video render for {asin} via Google Veo (Primary)...")
        # Ensure we have our Google Key
        if not self.google_key:
            logging.error("Google API key missing! Failing over to Kling...")
            return self._fallback_kling(asin, script_payload)
            
        try:
            # ----------------------------------------------------
            # MOCK VEO API CALL (Using the Nano Banana endpoints)
            # In production, this would be a requests.post() to the GCP endpoint
            # ----------------------------------------------------
            time.sleep(1) # Simulating network delay
            job_id = f"veo_job_{asin}_{int(time.time())}"
            logging.info(f"Successfully queued VEO render job: {job_id}")
            return job_id
            
        except Exception as e:
            logging.warning(f"Veo Render generation failed: {e}. Falling back to Kling...")
            return self._fallback_kling(asin, script_payload)

    def _fallback_kling(self, asin: str, script_payload: Dict[str, Any]) -> str:
        """
        Secondary fallback using Kling AI if the Google model errors out.
        """
        logging.info(f"Starting fallback Kling render for {asin}...")
        
        # ----------------------------------------------------
        # MOCK KLING API CALL 
        # ----------------------------------------------------
        time.sleep(1) # Simulating network delay
        job_id = f"kling_job_{asin}_{int(time.time())}"
        logging.info(f"Successfully queued KLING render job: {job_id}")
        return job_id
        
    def check_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Simulates checking the status of a rendering video job.
        In production, this queries the GCP/Veo or Kling API endpoint.
        """
        # For simulation purposes, we just return Success if it's over 10 seconds old
        job_timestamp_str = job_id.split('_')[-1]
        try:
            job_time = int(job_timestamp_str)
            if time.time() - job_time > 10:
                # Extract ASIN from job_id: f"veo_job_{asin}_{timestamp}"
                parts = job_id.split('_')
                asin_from_job = parts[-2] if len(parts) >= 2 else "UNKNOWN"
                return {
                    "status": "COMPLETED", 
                    "video_url": f"/preview/{asin_from_job}"
                }
            else:
                return {"status": "RENDERING"}
        except ValueError:
            return {"status": "FAILED", "error": "Invalid Job ID"}
