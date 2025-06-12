import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleHorseRacingScraper:
    """
    A simpler scraper that can fetch odds from various sources
    """
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
    
    def scrape_drf_entries(self):
        """Try to scrape from DRF (Daily Racing Form) which has simpler access"""
        try:
            # DRF provides free PPs for some races
            url = "https://www.drf.com/race-entries"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                races_data = []
                
                # Look for race cards or entries
                race_cards = soup.find_all('div', class_=['race-card', 'entry-card', 'race-entry'])
                
                for card in race_cards[:10]:  # Limit to first 10
                    race_info = self._parse_drf_race(card)
                    if race_info:
                        races_data.append(race_info)
                
                return races_data
            else:
                logger.warning(f"DRF returned status: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error scraping DRF: {e}")
            return []
    
    def scrape_tvg_json(self):
        """Try to get data from TVG's JSON endpoints"""
        try:
            # TVG might have JSON endpoints for their race data
            headers = self.session.headers.copy()
            headers['Accept'] = 'application/json'
            headers['Referer'] = 'https://www.tvg.com'
            
            # Try various potential endpoints
            endpoints = [
                "https://www.tvg.com/api/racing/races/today",
                "https://api.tvg.com/racing/races",
                "https://www.tvg.com/races/api/entries"
            ]
            
            for endpoint in endpoints:
                try:
                    response = self.session.get(endpoint, headers=headers, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        logger.info(f"Found data at {endpoint}")
                        return self._parse_tvg_json(data)
                except:
                    continue
                    
            return []
            
        except Exception as e:
            logger.error(f"Error with TVG JSON: {e}")
            return []
    
    def scrape_twinspires(self):
        """Try TwinSpires which might have accessible data"""
        try:
            url = "https://www.twinspires.com/racing"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                # Look for JSON data in script tags
                soup = BeautifulSoup(response.text, 'html.parser')
                scripts = soup.find_all('script', type='application/json')
                
                for script in scripts:
                    try:
                        data = json.loads(script.string)
                        if 'races' in str(data) or 'entries' in str(data):
                            return self._parse_embedded_json(data)
                    except:
                        continue
                        
            return []
            
        except Exception as e:
            logger.error(f"Error with TwinSpires: {e}")
            return []
    
    def _parse_drf_race(self, card):
        """Parse DRF race card"""
        try:
            race_data = {
                'source': 'DRF',
                'horses': []
            }
            
            # Extract basic info
            race_num = card.find(['h3', 'h4'], text=re.compile(r'Race \d+'))
            if race_num:
                race_data['race_number'] = race_num.text.strip()
            
            # Find horse entries
            horses = card.find_all(['tr', 'div'], class_=re.compile(r'horse|entry|runner'))
            
            for horse in horses:
                horse_info = {
                    'horse_name': '',
                    'morning_line': '',
                    'jockey': '',
                    'trainer': ''
                }
                
                # Try to extract horse name
                name_elem = horse.find(['td', 'span'], class_=re.compile(r'horse|name'))
                if name_elem:
                    horse_info['horse_name'] = name_elem.text.strip()
                
                # Try to extract odds
                odds_elem = horse.find(['td', 'span'], class_=re.compile(r'odds|ml'))
                if odds_elem:
                    horse_info['morning_line'] = odds_elem.text.strip()
                
                if horse_info['horse_name']:
                    race_data['horses'].append(horse_info)
            
            return race_data if race_data['horses'] else None
            
        except Exception as e:
            logger.error(f"Error parsing DRF race: {e}")
            return None
    
    def _parse_tvg_json(self, data):
        """Parse TVG JSON data"""
        races = []
        try:
            # Handle different possible JSON structures
            if isinstance(data, dict):
                if 'races' in data:
                    data = data['races']
                elif 'data' in data:
                    data = data['data']
            
            if isinstance(data, list):
                for item in data:
                    race = {
                        'source': 'TVG',
                        'race_number': str(item.get('raceNumber', '')),
                        'horses': []
                    }
                    
                    entries = item.get('entries', item.get('horses', []))
                    for entry in entries:
                        horse = {
                            'horse_name': entry.get('horseName', entry.get('name', '')),
                            'morning_line': str(entry.get('morningLine', entry.get('odds', ''))),
                            'jockey': entry.get('jockey', ''),
                            'trainer': entry.get('trainer', '')
                        }
                        if horse['horse_name']:
                            race['horses'].append(horse)
                    
                    if race['horses']:
                        races.append(race)
            
            return races
            
        except Exception as e:
            logger.error(f"Error parsing TVG JSON: {e}")
            return []
    
    def _parse_embedded_json(self, data):
        """Parse embedded JSON from page"""
        races = []
        try:
            # Recursively search for race data
            if isinstance(data, dict):
                for key, value in data.items():
                    if 'race' in key.lower() or 'entries' in key.lower():
                        if isinstance(value, list):
                            for item in value:
                                race = self._extract_race_from_json(item)
                                if race:
                                    races.append(race)
                        elif isinstance(value, dict):
                            race = self._extract_race_from_json(value)
                            if race:
                                races.append(race)
            
            return races
            
        except Exception as e:
            logger.error(f"Error parsing embedded JSON: {e}")
            return []
    
    def _extract_race_from_json(self, data):
        """Extract race info from JSON object"""
        try:
            race = {
                'source': 'TwinSpires',
                'race_number': str(data.get('number', data.get('raceNumber', ''))),
                'horses': []
            }
            
            # Look for entries/horses
            entries = data.get('entries', data.get('horses', data.get('runners', [])))
            
            if isinstance(entries, list):
                for entry in entries:
                    horse = {
                        'horse_name': entry.get('name', entry.get('horseName', '')),
                        'morning_line': str(entry.get('odds', entry.get('morningLine', ''))),
                        'post_position': str(entry.get('post', entry.get('postPosition', ''))),
                        'jockey': entry.get('jockey', entry.get('jockeyName', '')),
                        'trainer': entry.get('trainer', entry.get('trainerName', ''))
                    }
                    if horse['horse_name']:
                        race['horses'].append(horse)
            
            return race if race['horses'] else None
            
        except:
            return None
    
    def scrape_all_sources(self):
        """Try all sources and combine results"""
        all_data = {
            'timestamp': datetime.now().isoformat(),
            'races': []
        }
        
        # Try each source
        logger.info("Trying DRF...")
        drf_races = self.scrape_drf_entries()
        all_data['races'].extend(drf_races)
        
        time.sleep(2)  # Rate limiting
        
        logger.info("Trying TVG JSON...")
        tvg_races = self.scrape_tvg_json()
        all_data['races'].extend(tvg_races)
        
        time.sleep(2)
        
        logger.info("Trying TwinSpires...")
        ts_races = self.scrape_twinspires()
        all_data['races'].extend(ts_races)
        
        logger.info(f"Total races found: {len(all_data['races'])}")
        
        return all_data


# Manual test data generator
def generate_test_data():
    """Generate test data with realistic odds"""
    test_data = {
        'timestamp': datetime.now().isoformat(),
        'races': [
            {
                'source': 'Test',
                'race_number': '1',
                'track': 'Belmont Park',
                'horses': [
                    {'horse_name': 'Thunder Strike', 'morning_line': '5-2', 'post_position': '1'},
                    {'horse_name': 'Lightning Bolt', 'morning_line': '3-1', 'post_position': '2'},
                    {'horse_name': 'Storm Chaser', 'morning_line': '7-2', 'post_position': '3'},
                    {'horse_name': 'Wind Walker', 'morning_line': '9-2', 'post_position': '4'},
                    {'horse_name': 'Rain Dancer', 'morning_line': '6-1', 'post_position': '5'}
                ]
            },
            {
                'source': 'Test',
                'race_number': '2',
                'track': 'Belmont Park',
                'horses': [
                    {'horse_name': 'Speed Demon', 'morning_line': '2-1', 'post_position': '1'},
                    {'horse_name': 'Fast Track', 'morning_line': '5-2', 'post_position': '2'},
                    {'horse_name': 'Quick Silver', 'morning_line': '4-1', 'post_position': '3'},
                    {'horse_name': 'Rapid Fire', 'morning_line': '8-1', 'post_position': '4'}
                ]
            }
        ]
    }
    return test_data


if __name__ == "__main__":
    # Test the scraper
    scraper = SimpleHorseRacingScraper()
    
    # Try real scraping
    data = scraper.scrape_all_sources()
    
    # If no real data found, use test data
    if not data['races']:
        logger.info("No real data found, using test data")
        data = generate_test_data()
    
    # Save data
    with open('scraped_odds_data.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Scraped {len(data['races'])} races with odds data")