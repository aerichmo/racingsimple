import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EquibaseScraper:
    def __init__(self):
        self.base_url = "https://www.equibase.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def get_todays_tracks(self):
        """Get list of tracks with races today"""
        try:
            url = f"{self.base_url}/static/entry/index.html"
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            tracks = []
            
            # Parse track links
            track_links = soup.find_all('a', href=re.compile(r'/static/entry/.*\.html'))
            for link in track_links:
                track_code = link.get('href').split('/')[-1].replace('.html', '')
                track_name = link.text.strip()
                if track_code and track_name:
                    tracks.append({
                        'code': track_code,
                        'name': track_name,
                        'url': f"{self.base_url}{link.get('href')}"
                    })
            
            return tracks
        except Exception as e:
            logger.error(f"Error getting tracks: {e}")
            return []
    
    def get_race_entries(self, track_url):
        """Get entries for a specific track"""
        try:
            response = self.session.get(track_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            races = []
            
            # Find race tables
            race_tables = soup.find_all('table', class_='race-table')
            
            for race_table in race_tables:
                race_info = self._parse_race_table(race_table)
                if race_info:
                    races.append(race_info)
            
            return races
        except Exception as e:
            logger.error(f"Error getting race entries from {track_url}: {e}")
            return []
    
    def _parse_race_table(self, table):
        """Parse individual race table"""
        try:
            race_data = {
                'horses': []
            }
            
            # Extract race number and details
            race_header = table.find_previous('div', class_='race-header')
            if race_header:
                race_data['race_number'] = race_header.text.strip()
            
            # Parse horse entries
            rows = table.find_all('tr')[1:]  # Skip header
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 6:
                    horse_info = {
                        'post_position': cols[0].text.strip(),
                        'horse_name': cols[1].text.strip(),
                        'jockey': cols[2].text.strip() if len(cols) > 2 else '',
                        'trainer': cols[3].text.strip() if len(cols) > 3 else '',
                        'morning_line': cols[4].text.strip() if len(cols) > 4 else '',
                        'weight': cols[5].text.strip() if len(cols) > 5 else ''
                    }
                    race_data['horses'].append(horse_info)
            
            return race_data if race_data['horses'] else None
        except Exception as e:
            logger.error(f"Error parsing race table: {e}")
            return None
    
    def get_live_odds(self, track_code, race_number):
        """Attempt to get live odds for a specific race"""
        # Note: Live odds might require additional authentication or may not be freely available
        # This is a placeholder for potential live odds scraping
        try:
            url = f"{self.base_url}/static/chart/summary/index.html"
            params = {
                'track': track_code,
                'race': race_number,
                'date': datetime.now().strftime('%Y%m%d')
            }
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            # Parse odds if available
            odds_data = {}
            
            # Look for odds in the results
            odds_elements = soup.find_all('td', class_='odds')
            for i, odds in enumerate(odds_elements):
                odds_data[f'horse_{i+1}'] = odds.text.strip()
            
            return odds_data
        except Exception as e:
            logger.error(f"Error getting live odds: {e}")
            return {}
    
    def scrape_all_tracks(self):
        """Main method to scrape all available data"""
        all_data = {
            'timestamp': datetime.now().isoformat(),
            'tracks': []
        }
        
        tracks = self.get_todays_tracks()
        logger.info(f"Found {len(tracks)} tracks with races today")
        
        for track in tracks[:5]:  # Limit to 5 tracks to avoid rate limiting
            logger.info(f"Scraping {track['name']}")
            races = self.get_race_entries(track['url'])
            
            track_data = {
                'track_name': track['name'],
                'track_code': track['code'],
                'races': races
            }
            all_data['tracks'].append(track_data)
            
            # Rate limiting
            time.sleep(2)
        
        return all_data


# Alternative scraper for TVG/FanDuel if Equibase doesn't work well
class TVGScraper:
    def __init__(self):
        self.base_url = "https://www.tvg.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.tvg.com/'
        })
    
    def get_races_data(self):
        """Get races data from TVG API endpoints"""
        try:
            # TVG likely has JSON API endpoints
            # This would need to be discovered through network inspection
            url = f"{self.base_url}/api/races/today"
            response = self.session.get(url)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"TVG API returned status {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error fetching TVG data: {e}")
            return None


if __name__ == "__main__":
    # Test the scraper
    scraper = EquibaseScraper()
    data = scraper.scrape_all_tracks()
    
    # Save sample data
    with open('sample_scraped_data.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Scraped data from {len(data['tracks'])} tracks")