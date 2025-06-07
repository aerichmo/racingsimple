#!/usr/bin/env python3
"""
Morning cron job - runs at 8:00 AM daily
1. Fetches race entries and basic data
2. Fetches morning line odds
"""

import os
import sys
from datetime import datetime
import logging
from scraper import EquibaseScraper
from odds_scraper import OddsScraper

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def main():
    """Main morning cron job function"""
    logger.info("=" * 50)
    logger.info(f"Starting morning sync at {datetime.now()}")
    
    # Get database URL from environment
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        logger.error("DATABASE_URL environment variable not set")
        sys.exit(1)
    
    try:
        # Step 1: Fetch race entries
        logger.info("Step 1: Fetching race entries")
        scraper = EquibaseScraper(db_url)
        scraper.run_daily_sync()
        
        # Step 2: Fetch morning line odds
        logger.info("Step 2: Fetching morning line odds")
        odds_scraper = OddsScraper(db_url)
        odds_scraper.save_morning_line_odds(datetime.now())
        
        logger.info("Morning sync completed successfully")
        
    except Exception as e:
        logger.error(f"Morning sync failed: {e}", exc_info=True)
        sys.exit(1)
    
    logger.info("=" * 50)


if __name__ == "__main__":
    main()