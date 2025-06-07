#!/usr/bin/env python3
"""
Initialize database and run initial sync
Run this once to set up the database
"""

import os
import sys
from database import Database
from scraper import EquibaseScraper
from odds_scraper import OddsScraper
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        logger.error("DATABASE_URL environment variable not set!")
        sys.exit(1)
    
    logger.info("Initializing database...")
    
    # Create database instance and tables
    db = Database(db_url)
    try:
        db.create_tables()
        logger.info("✅ Database tables created successfully")
    except Exception as e:
        logger.error(f"❌ Error creating tables: {e}")
        sys.exit(1)
    
    # Run initial data sync
    logger.info("\nRunning initial data sync...")
    try:
        scraper = EquibaseScraper(db_url)
        scraper.run_daily_sync()
        logger.info("✅ Race data synced")
        
        # Also get morning line odds
        odds_scraper = OddsScraper(db_url)
        odds_scraper.save_morning_line_odds(datetime.now())
        logger.info("✅ Morning line odds synced")
        
    except Exception as e:
        logger.error(f"❌ Error during sync: {e}")
        logger.info("Note: The scraper needs to be updated with correct HTML selectors")
    
    logger.info("\nDatabase initialization complete!")

if __name__ == "__main__":
    main()