import streamlit as st
import sqlite3
import pandas as pd
import os
from agents.qa_sentry import QASentry

DB_NAME = os.getenv("DB_NAME", "jobs.db")

st.set_page_config(page_title="Staging Dashboard | QA", layout="wide")
st.title("🎬 AI Video Pipeline: Staging Dashboard")
st.markdown("Monitor ASIN jobs, review completed videos, and execute final Agent D QA checks.")

# Connect to DB and fetch latest status
try:
    conn = sqlite3.connect(DB_NAME)
    query = "SELECT asin, status, rapidapi_job_id, video_url, updated_at FROM jobs ORDER BY updated_at DESC"
    df = pd.read_sql_query(query, conn)
    conn.close()
except Exception as e:
    st.error(f"Failed to connect to Database: {e}")
    df = pd.DataFrame()

if not df.empty:
    st.subheader("Current Job Queue")
    
    # Dashboard Metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Jobs", len(df))
    col2.metric("Rendering", len(df[df['status'] == 'RENDERING']))
    col3.metric("Awaiting QA", len(df[df['status'] == 'COMPLETED']))
    col4.metric("Approved", len(df[df['status'] == 'QA_PASSED']))
    
    st.dataframe(df, use_container_width=True)
    
    st.divider()
    st.subheader("🔍 Agent D (QA Sentry) Action Center")
    
    # Filter for jobs that are COMPLETED but not yet QA'd
    qa_pending = df[df['status'] == 'COMPLETED']['asin'].tolist()
    
    if qa_pending:
        selected_asin = st.selectbox("Select ASIN to review:", qa_pending)
        
        if selected_asin:
            job_row = df[df['asin'] == selected_asin].iloc[0]
            video_url = job_row['video_url']
            
            st.info(f"Video URL: {video_url}")
            # st.video(video_url) # In production when video is available
            
            if st.button("Trigger QA Sentry Review"):
                with st.spinner("Agent D is analyzing video compliance..."):
                    sentry = QASentry()
                    result = sentry.inspect_final_video(selected_asin, video_url)
                    
                    if result['status'] == 'QA_PASSED':
                        st.success(f"PASSED: {result['reason']} (Confidence: {result['confidence']})")
                        
                        # Update DB
                        conn = sqlite3.connect(DB_NAME)
                        crs = conn.cursor()
                        crs.execute("UPDATE jobs SET status = 'QA_PASSED' WHERE asin = ?", (selected_asin,))
                        conn.commit()
                        conn.close()
                        st.balloons()
                        
                        # In production, this would trigger an upload/posting to social channel
                    else:
                        st.error(f"REJECTED: {result['reason']}")
                        conn = sqlite3.connect(DB_NAME)
                        crs = conn.cursor()
                        crs.execute("UPDATE jobs SET status = 'QA_FAILED' WHERE asin = ?", (selected_asin,))
                        conn.commit()
                        conn.close()
    else:
        st.write("No videos are currently pending QA Review.")

else:
    st.warning("Database is empty or jobs table not found. Run db_setup.py and start_pipeline.py.")
