import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OTBScraper:
    """
    Scraper for OffTrackBetting.com race results
    """
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://www.offtrackbetting.com/'
        })
    
    def get_current_races(self):
        """Get current races from OTB API"""
        try:
            url = "https://us-west-2.aws.data.mongodb-api.com/app/races-bwsnh/endpoint/current_races/v2"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Got race schedule data for {data.get('headline', 'today')}")
                
                # Debug: print structure
                if 'todaysraces' in data:
                    actual_data = data['todaysraces']
                    logger.info(f"Found todaysraces with {len(actual_data.get('tracks', []))} tracks")
                    return actual_data
                
                return data
            else:
                logger.error(f"API returned status: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching current races: {e}")
            return None
    
    def get_race_results(self, meetno, track_name, date=None):
        """Get race results for a specific track and date"""
        try:
            # Get results from the results page
            track_slug = track_name.lower().replace(' ', '-').replace('(', '%28').replace(')', '%29')
            
            if date:
                # Specific date results
                url = f"https://www.offtrackbetting.com/results/{meetno}/{track_slug}-{date}.html"
            else:
                # Today's results
                url = f"https://www.offtrackbetting.com/results/{meetno}/{track_slug}.html"
            
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                return self._parse_results_page(response.text, track_name)
            else:
                logger.warning(f"Results page returned status {response.status_code}")
                return None
            
        except Exception as e:
            logger.error(f"Error getting race details: {e}")
            return None
    
    def _parse_results_page(self, html, track_name):
        """Parse a results page for race outcomes"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            all_races = []
            
            # Look for common patterns in OTB pages
            # Odds might be in tables with class names like:
            # - odds-table, race-entries, program-table
            # - or in divs with data attributes
            
            # Try table-based layout
            tables = soup.find_all('table', class_=re.compile(r'odds|race|entries|program'))
            for table in tables:
                rows = table.find_all('tr')
                for row in rows[1:]:  # Skip header
                    horse_data = self._extract_horse_from_row(row)
                    if horse_data:
                        race_data['horses'].append(horse_data)
            
            # Try div-based layout
            if not race_data['horses']:
                horse_divs = soup.find_all('div', class_=re.compile(r'horse|runner|entry'))
                for div in horse_divs:
                    horse_data = self._extract_horse_from_div(div)
                    if horse_data:
                        race_data['horses'].append(horse_data)
            
            return race_data if race_data['horses'] else None
            
        except Exception as e:
            logger.error(f"Error parsing race page: {e}")
            return None
    
    def _extract_horse_from_row(self, row):
        """Extract horse info from table row"""
        try:
            cols = row.find_all(['td', 'th'])
            if len(cols) < 3:
                return None
                
            horse_info = {
                'program_number': '',
                'horse_name': '',
                'morning_line': '',
                'current_odds': ''
            }
            
            # Common column patterns:
            # Program# | Horse | ML | Odds
            # Number | Name | Morning Line | Live Odds
            
            for i, col in enumerate(cols):
                text = col.text.strip()
                
                # Program number (usually first column)
                if i == 0 and text.isdigit():
                    horse_info['program_number'] = text
                
                # Horse name (usually second column)
                elif i == 1:
                    horse_info['horse_name'] = text
                
                # Odds (look for patterns like "5-2", "3/1", "5.50")
                elif re.match(r'^\d+[-/]\d+$', text) or re.match(r'^\d+\.\d+$', text):
                    if 'ML' in col.get('class', []) or i == 2:
                        horse_info['morning_line'] = text
                    else:
                        horse_info['current_odds'] = text
            
            return horse_info if horse_info['horse_name'] else None
            
        except Exception as e:
            logger.error(f"Error extracting horse from row: {e}")
            return None
    
    def _extract_horse_from_div(self, div):
        """Extract horse info from div element"""
        try:
            horse_info = {
                'program_number': '',
                'horse_name': '',
                'morning_line': '',
                'current_odds': ''
            }
            
            # Look for program number
            prog_elem = div.find(class_=re.compile(r'program|number|post'))
            if prog_elem:
                horse_info['program_number'] = prog_elem.text.strip()
            
            # Look for horse name
            name_elem = div.find(class_=re.compile(r'horse|name|runner'))
            if name_elem:
                horse_info['horse_name'] = name_elem.text.strip()
            
            # Look for odds
            odds_elems = div.find_all(class_=re.compile(r'odds|ml|price'))
            for elem in odds_elems:
                text = elem.text.strip()
                if re.match(r'^\d+[-/]\d+$', text) or re.match(r'^\d+\.\d+$', text):
                    if 'ml' in elem.get('class', []):
                        horse_info['morning_line'] = text
                    else:
                        horse_info['current_odds'] = text
            
            return horse_info if horse_info['horse_name'] else None
            
        except Exception as e:
            logger.error(f"Error extracting horse from div: {e}")
            return None
    
    def get_completed_races(self):
        """Get results for completed races from major tracks"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'source': 'OffTrackBetting.com',
            'completed_races': []
        }
        
        # First get the race schedule
        race_schedule = self.get_current_races()
        if not race_schedule:
            logger.error("Could not get race schedule")
            return results
        
        # Focus on Fair Meadows and major US tracks
        major_track_names = {
            'Fair Meadows': ('FMT', None),  # Add Fair Meadows
            'Belmont Park': ('BEL', '10'),
            'Gulfstream Park': ('GP', '36'),
            'Santa Anita': ('SA', '80'),
            'Churchill Downs': ('CD', '17'),
            'Keeneland': ('KEE', '47'),
            'Del Mar': ('DMR', '19'),
            'Aqueduct': ('AQU', '4'),
            'Saratoga': ('SAR', '81')
        }
        
        tracks = race_schedule.get('tracks', [])
        for track in tracks:
            track_name = track.get('name', '')
            meetno = track.get('meetno', '')
            current_race = track.get('currentRace', '1')
            
            # Check if this is a major track
            for major_name, (code, expected_meetno) in major_track_names.items():
                if major_name.lower() in track_name.lower():
                    logger.info(f"Found {track_name} - Race {current_race} (meetno: {meetno})")
                    
                    # Only check if races have been completed
                    if int(current_race) > 1:
                        results['completed_races'].append({
                            'track': track_name,
                            'track_code': code,
                            'meetno': meetno,
                            'current_race': current_race,
                            'completed_races': int(current_race) - 1
                        })
                    break
        
        logger.info(f"Found {len(results['completed_races'])} tracks with completed races")
        return results


if __name__ == "__main__":
    scraper = OTBScraper()
    
    # Test getting completed races
    logger.info("Testing OTB results scraper...")
    
    results = scraper.get_completed_races()
    
    print(f"\nFound {len(results['completed_races'])} tracks with completed races:")
    for track in results['completed_races']:
        print(f"- {track['track']} ({track['track_code']}): {track['completed_races']} races completed")
    
    # Save results
    with open('otb_results.json', 'w') as f:
        json.dump(results, f, indent=2)