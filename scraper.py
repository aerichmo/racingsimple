import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from typing import List, Dict, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EquibaseScraper:
    def __init__(self, db_url: str):
        self.base_url = "https://www.equibase.com/static/entry/"
        self.db_url = db_url
        self.season_end = datetime(2025, 7, 20)
    
    def get_db_connection(self):
        """Create database connection"""
        return psycopg2.connect(self.db_url)
    
    def is_racing_day(self, date: datetime) -> bool:
        """Check if date is a racing day (Wed-Sat) and before season end"""
        weekday = date.weekday()
        # Wednesday = 2, Saturday = 5
        return 2 <= weekday <= 5 and date <= self.season_end
    
    def generate_url(self, date: datetime) -> str:
        """Generate Equibase URL for given date"""
        date_str = date.strftime("%m%d%y")
        return f"{self.base_url}FMT{date_str}USA-EQB.html"
    
    def parse_race_data(self, html: str, date: datetime) -> List[Dict]:
        """Parse HTML and extract race data"""
        soup = BeautifulSoup(html, 'html.parser')
        races = []
        
        # TODO: Update these selectors based on actual Equibase HTML structure
        # This is a template - you'll need to inspect the actual HTML
        
        # Example structure (needs to be updated):
        race_blocks = soup.find_all('div', class_='race-block')
        
        for race_block in race_blocks:
            try:
                race_data = {
                    'date': date.date(),
                    'race_number': race_block.find('span', class_='race-num').text.strip(),
                    'track_name': race_block.find('span', class_='track').text.strip(),
                    'post_time': race_block.find('span', class_='post-time').text.strip(),
                    'purse': race_block.find('span', class_='purse').text.strip(),
                    'distance': race_block.find('span', class_='distance').text.strip(),
                    'surface': race_block.find('span', class_='surface').text.strip(),
                    'race_type': race_block.find('span', class_='race-type').text.strip(),
                    'horses': []
                }
                
                # Parse horses in this race
                horse_rows = race_block.find_all('tr', class_='horse-row')
                for horse_row in horse_rows:
                    horse = {
                        'program_number': horse_row.find('td', class_='pgm').text.strip(),
                        'horse_name': horse_row.find('td', class_='horse').text.strip(),
                        'jockey': horse_row.find('td', class_='jockey').text.strip(),
                        'trainer': horse_row.find('td', class_='trainer').text.strip(),
                        'morning_line_odds': horse_row.find('td', class_='ml').text.strip(),
                        'weight': horse_row.find('td', class_='weight').text.strip(),
                    }
                    race_data['horses'].append(horse)
                
                races.append(race_data)
                
            except AttributeError as e:
                logger.warning(f"Error parsing race block: {e}")
                continue
        
        return races
    
    def fetch_daily_data(self, date: Optional[datetime] = None) -> Optional[List[Dict]]:
        """Fetch and parse data for a specific date"""
        if date is None:
            date = datetime.now()
        
        if not self.is_racing_day(date):
            logger.info(f"{date.strftime('%Y-%m-%d')} is not a racing day")
            return None
        
        url = self.generate_url(date)
        logger.info(f"Fetching data from: {url}")
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            races = self.parse_race_data(response.text, date)
            logger.info(f"Successfully parsed {len(races)} races")
            return races
            
        except requests.RequestException as e:
            logger.error(f"Error fetching data from {url}: {e}")
            return None
    
    def save_to_database(self, races: List[Dict]) -> None:
        """Save race data to PostgreSQL database"""
        conn = self.get_db_connection()
        cur = conn.cursor()
        
        try:
            for race in races:
                # Insert or update race
                cur.execute("""
                    INSERT INTO races (date, race_number, track_name, post_time, 
                                     purse, distance, surface, race_type)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (date, race_number, track_name) 
                    DO UPDATE SET 
                        post_time = EXCLUDED.post_time,
                        purse = EXCLUDED.purse,
                        distance = EXCLUDED.distance,
                        surface = EXCLUDED.surface,
                        race_type = EXCLUDED.race_type
                    RETURNING id
                """, (
                    race['date'], race['race_number'], race['track_name'],
                    race['post_time'], race['purse'], race['distance'],
                    race['surface'], race['race_type']
                ))
                
                race_id = cur.fetchone()[0]
                
                # Delete existing horses for this race
                cur.execute("DELETE FROM horses WHERE race_id = %s", (race_id,))
                
                # Insert horses
                for horse in race['horses']:
                    cur.execute("""
                        INSERT INTO horses (race_id, program_number, horse_name, 
                                          jockey, trainer, morning_line_odds, weight)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        race_id, horse['program_number'], horse['horse_name'],
                        horse['jockey'], horse['trainer'], horse['morning_line_odds'],
                        horse['weight']
                    ))
            
            conn.commit()
            logger.info(f"Successfully saved {len(races)} races to database")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            cur.close()
            conn.close()
    
    def run_daily_sync(self) -> None:
        """Main method to run the daily sync"""
        logger.info("Starting daily sync...")
        races = self.fetch_daily_data()
        
        if races:
            self.save_to_database(races)
            logger.info("Daily sync completed successfully")
        else:
            logger.info("No races to sync today")


def main():
    """Main function for manual testing"""
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        logger.error("DATABASE_URL environment variable not set")
        return
    
    scraper = EquibaseScraper(db_url)
    scraper.run_daily_sync()


if __name__ == "__main__":
    main()