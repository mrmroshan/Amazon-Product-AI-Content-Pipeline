from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import sqlite3
import os
import threading

# Import our custom architecture
from worker import start_worker, stop_worker
# Define DB locally instead of importing start_pipeline to avoid crewai cascade
DB_NAME = os.getenv("DB_NAME", "jobs.db")
from agents.qa_sentry import QASentry
# We now use our custom pure-REST Agentic Orchestrator
from agents.orchestrator import build_content_crew
from tools.video_generator import VideoGenerator
from tools.scraper import AxessoScraper

app = FastAPI(title="Video Pipeline API")

# Startup event to trigger the worker thread
@app.on_event("startup")
def startup_event():
    start_worker()

@app.on_event("shutdown")
def shutdown_event():
    stop_worker()

class PipelineTrigger(BaseModel):
    asin: str

def run_agentic_pipeline(asin: str):
    """Background task to run CrewAI & Video Trigger without blocking API."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO jobs (asin, status) VALUES (?, ?)", (asin, 'RESEARCHING'))
        conn.commit()
        
        # Scrape Product Image immediately for the UI selection phase
        scraper = AxessoScraper()
        prod_data = scraper.get_product_details(asin)
        img_url = "https://via.placeholder.com/500?text=No+Image+Found"
        if prod_data and 'imageUrlList' in prod_data and len(prod_data['imageUrlList']) > 0:
            img_url = prod_data['imageUrlList'][0]
        
        cursor.execute("UPDATE jobs SET product_image_url = ? WHERE asin = ?", (img_url, asin))
        conn.commit()

        # Crew AI Processing
        cursor.execute("UPDATE jobs SET status = 'SCRIPTING' WHERE asin = ?", (asin,))
        conn.commit()
        crew = build_content_crew(asin)
        script_result = crew.kickoff()
        
        # Save the generated script text for the local HTML UI Preview 
        cursor.execute("UPDATE jobs SET script_text = ? WHERE asin = ?", (str(script_result), asin))
        conn.commit()
        
        # Image Generation Phase
        cursor.execute("UPDATE jobs SET status = 'GENERATING_IMAGES' WHERE asin = ?", (asin,))
        conn.commit()
        
        from tools.image_generator import ImageGenerator
        import json
        import re
        
        # Parse out JSON from markdown
        clean_text = str(script_result)
        match = re.search(r'```(?:json)?\s*(.*?)\s*```', clean_text, re.DOTALL | re.IGNORECASE)
        raw_json_str = match.group(1) if match else clean_text
        
        try:
            script_data = json.loads(raw_json_str)
            img_gen = ImageGenerator()
            scenes_payload = []
            
            if 'visuals' in script_data:
                for idx, visual in enumerate(script_data['visuals']):
                    if isinstance(visual, dict):
                        desc = visual.get('description', str(visual))
                    else:
                        desc = str(visual)
                        
                    variants = img_gen.generate_scene_placeholders(img_url, desc)
                    scenes_payload.append({
                        "scene_id": idx,
                        "description": desc,
                        "variants": variants,
                        "selected_variant": None
                    })
            
            # Save the generated variants to DB for the UI to pick up
            cursor.execute("UPDATE jobs SET scenes_json = ? WHERE asin = ?", (json.dumps(scenes_payload), asin))
            
            # Formally Pause the orchestration loop for Human Approval
            cursor.execute("UPDATE jobs SET status = 'AWAITING_REVIEW', updated_at = CURRENT_TIMESTAMP WHERE asin = ?", (asin,))
            conn.commit()
        except Exception as json_e:
            raise Exception(f"Failed to parse or generate images: {json_e}")
            
        conn.close()
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(f"Error in background pipeline for {asin}:\n{error_msg}")
        try:
            conn = sqlite3.connect(DB_NAME)
            conn.cursor().execute("UPDATE jobs SET status = 'FAILED', error_log = ? WHERE asin = ?", (error_msg, asin))
            conn.commit()
            conn.close()
        except:
            pass

@app.post("/api/start")
def start_pipeline_route(payload: PipelineTrigger, background_tasks: BackgroundTasks):
    """Triggers the Agentic pipeline for a single ASIN."""
    background_tasks.add_task(run_agentic_pipeline, payload.asin)
    return {"message": f"Pipeline started for ASIN {payload.asin}", "status": "QUEUED"}

@app.get("/api/jobs")
def get_jobs():
    """Fetches all jobs from the pipeline table."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT asin, status, video_url, error_log, updated_at, scenes_json, product_image_url FROM jobs ORDER BY updated_at DESC")
    jobs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"jobs": jobs}

from fastapi.responses import HTMLResponse

@app.get("/preview/{asin}", response_class=HTMLResponse)
def preview_video_script(asin: str):
    """
    Since Video API isn't fully connected, this visually renders 
    the CrewAI generated script natively in HTML as a teleprompter, 
    and uses Web Speech API to read it!
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Check if script_text column exists natively over fetching
    try:
        cursor.execute("SELECT script_text FROM jobs WHERE asin = ?", (asin,))
        row = cursor.fetchone()
        script_text = row[0] if row and row[0] else None
    except:
        script_text = None
    conn.close()

    if not script_text:
        return f"<h1>Video Rendering or Script Text not found for {asin}</h1>"
    
    import json
    import re

    # Try to extract and format JSON if it's trapped in a markdown block
    clean_text = script_text or ""
    try:
        # Strip markdown json blocks
        match = re.search(r'```(?:json)?\s*(.*?)\s*```', clean_text, re.DOTALL | re.IGNORECASE)
        raw_json_str = match.group(1) if match else clean_text
        
        data = json.loads(raw_json_str)
        formatted_script = ""
        spoken_text = ""
        
        # Build beautiful readable output
        if 'voiceover' in data:
            formatted_script += "<h4 class='text-warning mt-3'>🔊 VOICEOVER</h4>"
            for item in data['voiceover']:
                if isinstance(item, dict):
                    v_text = item.get('text', item.get('script', str(item)))
                else:
                    v_text = str(item)
                spoken_text += v_text + " "
                formatted_script += f"<p class='mb-2'>&ldquo;{v_text}&rdquo;</p>"
                
        if 'visuals' in data:
            formatted_script += "<h4 class='text-info mt-4'>🎬 VISUALS</h4>"
            for item in data['visuals']:
                if isinstance(item, dict):
                    desc = item.get('description', str(item))
                else:
                    desc = str(item)
                formatted_script += f"<p class='mb-3' style='color: #94a3b8; font-size: 1.25rem; font-style: italic; border-left: 4px solid #0dcaf0; padding-left: 15px;'>[ {desc} ]</p>"
                
        display_html = formatted_script if formatted_script else clean_text
        # the spoken text for the Web Speech API
        safe_script = spoken_text.replace('`', '\\`').replace('\\', '\\\\').replace('"', '\\"') if spoken_text else clean_text.replace('`', '\\`').replace('\\', '\\\\').replace('"', '\\"')
    except:
        # Fallback if it's just raw text
        display_html = clean_text.replace('\n', '<br>')
        safe_script = clean_text.replace('`', '\\`').replace('\\', '\\\\').replace('"', '\\"')

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Video Preview - {asin}</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            :root {{
                --bg-color: #0b0f19;
                --text-color: #e2e8f0;
            }}
            body {{
                background-color: var(--bg-color);
                color: var(--text-color);
                font-family: 'Inter', sans-serif;
                height: 100vh;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                overflow: hidden;
            }}
            .teleprompter {{
                width: 80%;
                max-width: 800px;
                height: 60vh;
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 20px;
                padding: 40px;
                font-size: 1.6rem;
                line-height: 1.6;
                overflow-y: auto;
                text-align: left;
                backdrop-filter: blur(10px);
                box-shadow: 0 8px 32px 0 rgba(0,0,0,0.37);
                word-wrap: break-word;
            }}
            .highlight {{
                border-color: #20c997;
                box-shadow: 0 0 20px rgba(32, 201, 151, 0.4);
            }}
            .controls {{ margin-top: 30px; }}
        </style>
    </head>
    <body>
        <h2 class="mb-4 text-info"><i class="fas fa-video"></i> AI Video Preview: {asin}</h2>
        <div class="teleprompter" id="scriptBox">{display_html}</div>
        
        <div class="controls">
            <button class="btn btn-lg btn-success shadow-lg" onclick="playAudio()">
                <i class="fas fa-play"></i> Play Voiceover Audio
            </button>
        </div>

        <script>
            function playAudio() {{
                const text = `{safe_script}`;
                const utterance = new SpeechSynthesisUtterance(text);
                
                utterance.rate = 1.05;
                utterance.pitch = 0.9;
                
                const box = document.getElementById('scriptBox');
                box.classList.add('highlight');
                
                utterance.onend = () => {{
                    box.classList.remove('highlight');
                }};
                
                window.speechSynthesis.cancel(); 
                window.speechSynthesis.speak(utterance);
            }}
        </script>
    </body>
    </html>
    """
    return html_content

from pydantic import BaseModel

class ImageApprovalRequest(BaseModel):
    selected_images: dict

@app.post("/api/approve_images/{asin}")
def approve_images(asin: str, payload: ImageApprovalRequest):
    """Saves user image selections and kicks off video generation."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Update the scenes JSON with user selections
    cursor.execute("SELECT scenes_json FROM jobs WHERE asin = ?", (asin,))
    row = cursor.fetchone()
    if not row or not row[0]:
        conn.close()
        raise HTTPException(status_code=400, detail="Scenes data not found for this ASIN.")
        
    import json
    scenes_data = json.loads(row[0])
    for scene in scenes_data:
        scene_id = str(scene.get('scene_id'))
        if scene_id in payload.selected_images:
            scene['selected_variant'] = payload.selected_images[scene_id]
            
    cursor.execute("UPDATE jobs SET scenes_json = ? WHERE asin = ?", (json.dumps(scenes_data), asin))
    
    # 2. Trigger rendering simulation now that images are approved!
    cursor.execute("UPDATE jobs SET status = 'RENDERING' WHERE asin = ?", (asin,))
    conn.commit()
    
    # We pass the approved scenes payload to the video generator
    from tools.video_generator import VideoGenerator
    video_gen = VideoGenerator()
    job_id = video_gen.start_render_job(asin, {"approved_scenes": scenes_data})
    
    cursor.execute("UPDATE jobs SET rapidapi_job_id = ?, updated_at = CURRENT_TIMESTAMP WHERE asin = ?", (job_id, asin))
    conn.commit()
    conn.close()
    
    return {"message": "Images approved, rendering started!", "status": "RENDERING"}

@app.post("/api/qa/{asin}")
def trigger_qa(asin: str):
    """Triggers Agent D for a specific ASIN."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT video_url FROM jobs WHERE asin = ?", (asin,))
    row = cursor.fetchone()
    
    if not row or not row[0]:
        conn.close()
        raise HTTPException(status_code=400, detail="Video URL not found for this ASIN.")
        
    sentry = QASentry()
    result = sentry.inspect_final_video(asin, row[0])
    
    status = result['status']
    cursor.execute("UPDATE jobs SET status = ? WHERE asin = ?", (status, asin))
    conn.commit()
    conn.close()
    
    return result

# Serve static files for Frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def serve_home():
    # Because we mounted /static above, we serve index explicitly from root
    return FileResponse("static/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
