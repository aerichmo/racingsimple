#!/usr/bin/env python3
"""
Cron job for automated race data pulling
Run this every 5 minutes to check for races needing data

Crontab entry:
*/5 * * * * /usr/bin/python3 /path/to/STALL10N/cron_scheduler.py >> /path/to/STALL10N/cron.log 2>&1
"""

import os
import sys
from datetime import datetime
from race_data_puller import run_scheduled_pull
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """
    Main cron job function
    """
    logger.info("=" * 50)
    logger.info(f"Starting cron job at {datetime.now()}")
    
    try:
        # Run the scheduled pull
        run_scheduled_pull()
        
        logger.info("Cron job completed successfully")
        
    except Exception as e:
        logger.error(f"Cron job failed: {e}")
        sys.exit(1)
    
    logger.info("=" * 50)

if __name__ == "__main__":
    main()