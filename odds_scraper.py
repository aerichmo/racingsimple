import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, time
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
import pytz
from typing import List, Dict, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OddsScraper:
    def __init__(self, db_url: str):
        self.base_url = "https://www.equibase.com/static/entry/"
        self.db_url = db_url
        self.eastern = pytz.timezone('US/Eastern')
    
    def get_db_connection(self):
        """Create database connection"""
        return psycopg2.connect(self.db_url)
    
    def generate_url(self, date: datetime) -> str:
        """Generate Equibase URL for given date"""
        date_str = date.strftime("%m%d%y")
        return f"{self.base_url}FMT{date_str}USA-EQB.html"
    
    def parse_odds_data(self, html: str) -> Dict[str, Dict[str, str]]:
        """Parse HTML and extract odds data by race and horse"""
        soup = BeautifulSoup(html, 'html.parser')
        odds_data = {}
        
        # TODO: Update these selectors based on actual Equibase HTML
        race_blocks = soup.find_all('div', class_='race-block')
        
        for race_block in race_blocks:
            try:
                race_num = race_block.find('span', class_='race-num').text.strip()
                track = race_block.find('span', class_='track').text.strip()
                race_key = f"{track}_{race_num}"
                
                odds_data[race_key] = {}
                
                # Parse odds for each horse
                horse_rows = race_block.find_all('tr', class_='horse-row')
                for horse_row in horse_rows:
                    horse_name = horse_row.find('td', class_='horse').text.strip()
                    # Look for morning line or live odds
                    odds_cell = horse_row.find('td', class_='odds')
                    if odds_cell:
                        odds_data[race_key][horse_name] = odds_cell.text.strip()
                
            except AttributeError as e:
                logger.warning(f"Error parsing race block: {e}")
                continue
        
        return odds_data
    
    def save_morning_line_odds(self, date: datetime) -> None:
        """Fetch and save morning line odds for today's races"""
        logger.info(f"Fetching morning line odds for {date.strftime('%Y-%m-%d')}")
        
        url = self.generate_url(date)
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            odds_data = self.parse_odds_data(response.text)
            
            conn = self.get_db_connection()
            cur = conn.cursor()
            
            # Get today's races and horses
            cur.execute("""
                SELECT r.id as race_id, r.track_name, r.race_number, 
                       h.id as horse_id, h.horse_name
                FROM races r
                JOIN horses h ON h.race_id = r.id
                WHERE r.date = %s
            """, (date.date(),))
            
            races_horses = cur.fetchall()
            
            for race_id, track, race_num, horse_id, horse_name in races_horses:
                race_key = f"{track}_{race_num}"
                if race_key in odds_data and horse_name in odds_data[race_key]:
                    ml_odds = odds_data[race_key][horse_name]
                    
                    # Save morning line odds
                    cur.execute("""
                        INSERT INTO odds_history (race_id, horse_id, odds_type, odds_value)
                        VALUES (%s, %s, 'morning_line', %s)
                    """, (race_id, horse_id, ml_odds))
            
            conn.commit()
            logger.info("Morning line odds saved successfully")
            
        except Exception as e:
            logger.error(f"Error fetching morning line odds: {e}")
            if 'conn' in locals():
                conn.rollback()
            raise
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                conn.close()
    
    def get_races_near_post_time(self, minutes_before: int = 5) -> List[Dict]:
        """Get races that are within X minutes of post time"""
        conn = self.get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # Get current time in Eastern
            now = datetime.now(self.eastern)
            today = now.date()
            
            # Find races posting soon
            cur.execute("""
                SELECT id, track_name, race_number, post_time
                FROM races
                WHERE date = %s
                AND post_time IS NOT NULL
            """, (today,))
            
            races_near_post = []
            for race in cur.fetchall():
                # Combine date and time for comparison
                post_datetime = datetime.combine(today, race['post_time'])
                post_datetime = self.eastern.localize(post_datetime)
                
                # Calculate minutes until post
                minutes_to_post = (post_datetime - now).total_seconds() / 60
                
                if 0 <= minutes_to_post <= minutes_before:
                    race['minutes_to_post'] = int(minutes_to_post)
                    races_near_post.append(race)
            
            return races_near_post
            
        finally:
            cur.close()
            conn.close()
    
    def save_live_odds(self, race_id: int, minutes_to_post: int) -> None:
        """Fetch and save live odds for a specific race"""
        logger.info(f"Fetching live odds for race {race_id} ({minutes_to_post} mins to post)")
        
        conn = self.get_db_connection()
        cur = conn.cursor()
        
        try:
            # Get race details
            cur.execute("""
                SELECT date, track_name, race_number
                FROM races
                WHERE id = %s
            """, (race_id,))
            
            race = cur.fetchone()
            if not race:
                logger.error(f"Race {race_id} not found")
                return
            
            date, track, race_num = race
            
            # Fetch current odds page
            url = self.generate_url(datetime.combine(date, time()))
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            odds_data = self.parse_odds_data(response.text)
            race_key = f"{track}_{race_num}"
            
            if race_key not in odds_data:
                logger.warning(f"No odds found for {race_key}")
                return
            
            # Get horses for this race
            cur.execute("""
                SELECT id, horse_name
                FROM horses
                WHERE race_id = %s
            """, (race_id,))
            
            horses = cur.fetchall()
            
            for horse_id, horse_name in horses:
                if horse_name in odds_data[race_key]:
                    live_odds = odds_data[race_key][horse_name]
                    
                    # Save live odds
                    cur.execute("""
                        INSERT INTO odds_history 
                        (race_id, horse_id, odds_type, odds_value, minutes_to_post)
                        VALUES (%s, %s, 'live', %s, %s)
                    """, (race_id, horse_id, live_odds, minutes_to_post))
            
            conn.commit()
            logger.info(f"Live odds saved for race {race_id}")
            
        except Exception as e:
            logger.error(f"Error saving live odds for race {race_id}: {e}")
            conn.rollback()
        finally:
            cur.close()
            conn.close()
    
    def run_live_odds_check(self) -> None:
        """Check for races near post time and fetch live odds"""
        races = self.get_races_near_post_time(minutes_before=5)
        
        for race in races:
            self.save_live_odds(race['id'], race['minutes_to_post'])


def run_morning_odds_sync():
    """Run morning line odds sync (8am)"""
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        logger.error("DATABASE_URL not set")
        return
    
    scraper = OddsScraper(db_url)
    scraper.save_morning_line_odds(datetime.now())


def run_live_odds_sync():
    """Run live odds sync (every minute during racing hours)"""
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        logger.error("DATABASE_URL not set")
        return
    
    scraper = OddsScraper(db_url)
    scraper.run_live_odds_check()


if __name__ == "__main__":
    # Test morning line odds
    run_morning_odds_sync()