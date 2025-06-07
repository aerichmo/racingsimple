#!/usr/bin/env python3
"""
Live odds scheduler - runs every minute during racing hours
Checks for races within 5 minutes of post time and fetches live odds
"""

import os
import sys
from datetime import datetime, time
import logging
from odds_scraper import OddsScraper
import pytz

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def is_racing_hours():
    """Check if current time is during racing hours (Wed-Sat, 11am-7pm ET)"""
    eastern = pytz.timezone('US/Eastern')
    now = datetime.now(eastern)
    
    # Check if it's Wed-Sat (2-5)
    if now.weekday() not in [2, 3, 4, 5]:
        return False
    
    # Check if it's between 11am and 7pm ET
    current_time = now.time()
    start_time = time(11, 0)  # 11:00 AM
    end_time = time(19, 0)    # 7:00 PM
    
    return start_time <= current_time <= end_time


def main():
    """Main function for live odds scheduler"""
    logger.info("Starting live odds check")
    
    # Only run during racing hours
    if not is_racing_hours():
        logger.info("Outside of racing hours, skipping")
        return
    
    # Get database URL
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        logger.error("DATABASE_URL environment variable not set")
        sys.exit(1)
    
    try:
        # Run live odds check
        scraper = OddsScraper(db_url)
        scraper.run_live_odds_check()
        
        logger.info("Live odds check completed")
        
    except Exception as e:
        logger.error(f"Live odds check failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()