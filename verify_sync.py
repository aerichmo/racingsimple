#!/usr/bin/env python3
"""
Verification and sync script for Racing Simple
Compares website data with database and performs initial sync
"""

import os
import sys
from datetime import datetime
import requests
import json
from database import Database
from scraper import EquibaseScraper
from odds_scraper import OddsScraper
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RacingVerifier:
    def __init__(self):
        self.db = Database(os.environ.get('DATABASE_URL'))
        self.base_url = 'https://stall10n.onrender.com'
        
    def perform_initial_sync(self):
        """Run initial data sync"""
        logger.info("=" * 50)
        logger.info("Starting initial sync...")
        
        try:
            # Step 1: Create tables
            logger.info("Creating database tables...")
            self.db.create_tables()
            
            # Step 2: Run race data scraper
            logger.info("Fetching race entries...")
            scraper = EquibaseScraper(self.db.db_url)
            scraper.run_daily_sync()
            
            # Step 3: Run morning line odds scraper
            logger.info("Fetching morning line odds...")
            odds_scraper = OddsScraper(self.db.db_url)
            odds_scraper.save_morning_line_odds(datetime.now())
            
            logger.info("Initial sync completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Error during initial sync: {e}")
            return False
    
    def fetch_web_data(self, date):
        """Fetch data from the web API"""
        try:
            url = f"{self.base_url}/api/races/{date}"
            logger.info(f"Fetching from: {url}")
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if data.get('success'):
                return data.get('races', [])
            else:
                logger.error(f"API error: {data.get('error')}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch web data: {e}")
            return []
    
    def verify_data(self, date=None):
        """Compare database data with website data"""
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"\n{'=' * 50}")
        logger.info(f"Verifying data for {date}")
        logger.info("=" * 50)
        
        # Get database data
        logger.info("\nFetching from database...")
        db_races = self.db.get_races_by_date(date)
        logger.info(f"Database has {len(db_races)} races")
        
        # Get website data
        logger.info("\nFetching from website API...")
        web_races = self.fetch_web_data(date)
        logger.info(f"Website shows {len(web_races)} races")
        
        # Compare counts
        if len(db_races) != len(web_races):
            logger.warning(f"\n⚠️  Race count mismatch: DB={len(db_races)}, Web={len(web_races)}")
        else:
            logger.info(f"\n✅ Race counts match: {len(db_races)} races")
        
        # Detailed comparison
        logger.info("\n" + "=" * 50)
        logger.info("DETAILED COMPARISON")
        logger.info("=" * 50)
        
        for db_race in db_races:
            # Find matching web race
            web_race = next((wr for wr in web_races 
                           if wr.get('race_number') == db_race.get('race_number') 
                           and wr.get('track_name') == db_race.get('track_name')), None)
            
            if web_race:
                logger.info(f"\n✅ Race {db_race['race_number']} at {db_race['track_name']}")
                
                # Compare horse counts
                db_horses = db_race.get('horses', [])
                web_horses = web_race.get('horses', [])
                
                if len(db_horses) != len(web_horses):
                    logger.warning(f"   ⚠️  Horse count mismatch: DB={len(db_horses)}, Web={len(web_horses)}")
                else:
                    logger.info(f"   ✓ {len(db_horses)} horses")
                
                # Check for missing horses
                db_horse_names = {h['horse_name'] for h in db_horses if h}
                web_horse_names = {h['horse_name'] for h in web_horses if h}
                
                missing_on_web = db_horse_names - web_horse_names
                if missing_on_web:
                    logger.warning(f"   ⚠️  Missing on website: {', '.join(missing_on_web)}")
                
            else:
                logger.error(f"\n❌ Race {db_race['race_number']} at {db_race['track_name']} - NOT ON WEBSITE")
                horses = db_race.get('horses', [])
                logger.error(f"   Database has {len(horses)} horses for this race")
        
        # Check for races on web but not in DB
        for web_race in web_races:
            db_race = next((dr for dr in db_races 
                          if dr.get('race_number') == web_race.get('race_number') 
                          and dr.get('track_name') == web_race.get('track_name')), None)
            
            if not db_race:
                logger.error(f"\n❌ Race {web_race['race_number']} at {web_race['track_name']} - ON WEBSITE BUT NOT IN DB")
        
        # Check website health
        logger.info("\n" + "=" * 50)
        logger.info("WEBSITE HEALTH CHECK")
        logger.info("=" * 50)
        
        try:
            health_response = requests.get(f"{self.base_url}/health", timeout=10)
            if health_response.status_code == 200:
                health_data = health_response.json()
                logger.info(f"✅ Website status: {health_data.get('status', 'unknown')}")
                logger.info(f"   Timestamp: {health_data.get('timestamp', 'N/A')}")
            else:
                logger.error(f"❌ Health check failed: HTTP {health_response.status_code}")
        except Exception as e:
            logger.error(f"❌ Health check error: {e}")
        
        logger.info("\n" + "=" * 50)
        logger.info("Verification complete")
        logger.info("=" * 50 + "\n")


def main():
    """Main execution function"""
    verifier = RacingVerifier()
    
    args = sys.argv[1:]
    
    if '--sync' in args:
        # Perform initial sync
        success = verifier.perform_initial_sync()
        if not success:
            logger.error("Initial sync failed!")
            sys.exit(1)
        
        # Wait a moment for data to settle
        logger.info("\nWaiting 5 seconds for data to propagate...")
        import time
        time.sleep(5)
    
    # Run verification
    date = None
    for arg in args:
        if arg.count('-') == 2 and len(arg) == 10:  # Basic date format check
            date = arg
            break
    
    verifier.verify_data(date)


if __name__ == "__main__":
    main()