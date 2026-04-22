import sqlite3
import shutil
import time

DB_NAME = 'jobs.db'
BACKUP_DB = 'jobs_backup.db'

print(f"Creating backup of {DB_NAME} to {BACKUP_DB}...")
shutil.copy2(DB_NAME, BACKUP_DB)

print("Running schema migration to update strict status enum constraints...")
conn = sqlite3.connect(DB_NAME, timeout=10)
cursor = conn.cursor()

# 1. Disable constraints
conn.execute('PRAGMA foreign_keys=off;')

# 2. Create the exact same table with new constraints
conn.execute('''
CREATE TABLE IF NOT EXISTS jobs_v2 (
    asin TEXT PRIMARY KEY,
    status TEXT CHECK(status IN ('QUEUED', 'RESEARCHING', 'SCRIPTING', 'GENERATING_IMAGES', 'AWAITING_REVIEW', 'RENDERING', 'COMPLETED', 'QA_PASSED', 'QA_FAILED', 'FAILED')),
    rapidapi_job_id TEXT,
    video_url TEXT,
    local_video_path TEXT,
    research_data JSON,
    script_data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    script_text TEXT,
    error_log TEXT,
    product_image_url TEXT,
    scenes_json TEXT
)
''')

# 3. Pull older column mapping explicitly to map from the older format
cursor.execute('PRAGMA table_info(jobs)')
cols = [row[1] for row in cursor.fetchall()]

# Map overlapping columns dynamically so data migrates perfectly
col_str = ', '.join(cols)
conn.execute(f'INSERT INTO jobs_v2 ({col_str}) SELECT {col_str} FROM jobs')

# 4. Drop the old heavily-constrained table and swap
conn.execute('DROP TABLE jobs')
conn.execute('ALTER TABLE jobs_v2 RENAME TO jobs')

# 5. Bring keys back online
conn.execute('PRAGMA foreign_keys=on;')
conn.commit()
conn.close()

print("Schema migration completely successful! Your data is preserved with updated constraints.")
