# 🎬 Amazon Product AI Content Pipeline

An automated, multi-agent AI pipeline for generating, rendering, and QA-testing video content for Amazon Products based on ASINs. 

This project utilizes a robust architecture built on **CrewAI**, **FastAPI**, **Streamlit**, and **SQLite** to manage asynchronous tasks, track rendering jobs, and ensure strict content compliance using AI agents.

## 🚀 Features

- **Multi-Agent Orchestration**: Powered by CrewAI and Langchain to perform product research, write scripts, and perform final QA reviews.
- **Idempotent Job Tracking**: SQLite-backed state machine ensuring jobs aren't duplicated and gracefully resume if interrupted.
- **Asynchronous Rendering**: Background worker daemon (`worker.py`) that polls external rendering APIs to free up main execution threads.
- **Interactive QA Dashboard**: Streamlit-powered UI (`app.py`) for human-in-the-loop QA testing or triggering "Agent D" (QA Sentry) to automatically analyze compliance.
- **FastAPI Backend**: Standardized REST layer (`api.py`) for interacting with the pipeline programmatically.

---

## 🛠 Prerequisites

- Python 3.9+
- An OpenAI or Google Gemini API Key (for LLM Agents)
- Applicable API keys for Video Generation tools (via RapidAPI or similar, as defined in your `.env`)

---

## 📦 Setup & Installation

**1. Clone the repository**
```bash
git clone https://github.com/mrmroshan/Amazon-Product-AI-Content-Pipeline.git
cd Amazon-Product-AI-Content-Pipeline
```

**2. Create a Virtual Environment**
```bash
python -m venv venv

# On Windows:
.\venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate
```

**3. Install Dependencies**
```bash
pip install -r requirements.txt
```

**4. Environment Variables**
Create a `.env` file in the root directory and add your keys. It is explicitly ignored by `.gitignore` to prevent secret leakage:
```env
# Example .env file
DB_NAME="jobs.db"
ASIN_LIST_FILE="asins.txt"
# Add LLM Provider API Keys
GOOGLE_API_KEY="your_google_gemini_key_here"
# Add Video Render API Keys
RAPIDAPI_KEY="your_render_api_key_here"
```

**5. Initialize the Database**
```bash
python db_setup.py
# Or if upgrading schemas:
python migrate_schema.py
```

---

## 🚦 How to Run

The system is decoupled into three primary components to allow asynchronous processing.

### 1. The Dashboard (QA & Operations)
Launch the Streamlit interface to monitor the queue and run QA reviews on completed videos.
```bash
streamlit run app.py
```

### 2. The Rendering Worker
Start the background polling daemon that tracks the status of remote rendering operations.
```bash
python worker.py
```

### 3. Triggering the Pipeline
Add Amazon product ASINs (one per line) to `asins.txt`, and run the orchestrator to kick off the multi-agent CrewAI generation.
```bash
python start_pipeline.py
```

---

## 📂 Project Structure

```text
├── agents/             # CrewAI Agent definitions (Research, Scripting, QA Sentry)
├── tools/              # Custom Agent Tools (Video Generator API bindings, etc)
├── static/             # Static UI assets
├── generated_content/  # Local output storage for generated scripts and reports
├── api.py              # FastAPI endpoints for external webhooks/integrations
├── app.py              # Streamlit Web App Dashboard
├── start_pipeline.py   # Main entry point to ingest ASINs and trigger pipelines
├── worker.py           # Background daemon to poll rendering jobs
├── db_setup.py         # SQLite database initializer
├── migrate_schema.py   # Schema migration script
├── requirements.txt    # Python dependencies
└── asins.txt           # Input queue for product ASINs
```

## 🔒 Security
- Always ensure the `.env` file is never committed.
- This repository contains a pre-configured `.gitignore` to prevent sensitive credentials and large environment folders (`venv`) from being published.

## 👨‍💻 Author

**Roshan Ruzaik**
*This project was developed with the assistance of AI tools.*

## 📄 License
MIT License
