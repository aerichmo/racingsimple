#!/usr/bin/env python3
"""Apply the betting schema to the database"""
import os
import psycopg2
import logging
from database import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def apply_schema():
    """Apply the betting schema to the database"""
    # Get database URL
    db_url = os.environ.get('DATABASE_URL', 'postgresql://localhost/racingsimple')
    
    logger.info(f"Connecting to database...")
    
    try:
        # Connect to database
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        # Read schema file
        with open('betting_schema.sql', 'r') as f:
            schema_sql = f.read()
        
        logger.info("Applying betting schema...")
        
        # Execute schema
        cur.execute(schema_sql)
        conn.commit()
        
        # Verify tables were created
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('analysis_sessions', 'races', 'race_entries', 'betting_recommendations')
            ORDER BY table_name
        """)
        
        tables = [row[0] for row in cur.fetchall()]
        logger.info(f"Created tables: {', '.join(tables)}")
        
        cur.close()
        conn.close()
        
        logger.info("Betting schema applied successfully!")
        
    except Exception as e:
        logger.error(f"Error applying schema: {e}")
        raise

if __name__ == "__main__":
    apply_schema()