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
    Scraper for OffTrackBetting.com
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
    
    def get_race_details(self, meetno, track_name, race_number):
        """Try to get detailed race information including odds"""
        try:
            # OTB uses meetno in their URLs
            # Pattern from resultsUrl: /results/10/belmont-park.html
            # Possible patterns for entries/odds:
            # /entries/[meetno]/[track-slug]/[race]
            # /odds/[meetno]/[race]
            
            # Create URL-friendly track slug
            track_slug = track_name.lower().replace(' ', '-').replace('(', '%28').replace(')', '%29')
            
            urls_to_try = [
                f"https://www.offtrackbetting.com/entries/{meetno}/{track_slug}/{race_number}",
                f"https://www.offtrackbetting.com/odds/{meetno}/{race_number}",
                f"https://www.offtrackbetting.com/race/{meetno}/{race_number}",
                f"https://www.offtrackbetting.com/entries/{meetno}",
            ]
            
            for url in urls_to_try:
                try:
                    response = self.session.get(url, timeout=5)
                    if response.status_code == 200:
                        return self._parse_race_page(response.text)
                except:
                    continue
                    
            return None
            
        except Exception as e:
            logger.error(f"Error getting race details: {e}")
            return None
    
    def _parse_race_page(self, html):
        """Parse a race detail page for odds"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            race_data = {
                'horses': []
            }
            
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
    
    def scrape_all_available(self):
        """Main method to scrape all available data"""
        all_data = {
            'timestamp': datetime.now().isoformat(),
            'source': 'OffTrackBetting.com',
            'races': []
        }
        
        # First get the race schedule
        race_schedule = self.get_current_races()
        if not race_schedule:
            logger.error("Could not get race schedule")
            return all_data
        
        # Focus on major US tracks - match by name since there's no code field
        major_track_names = {
            'Belmont Park': 'BEL',
            'Saratoga': 'SAR', 
            'Aqueduct': 'AQU',
            'Gulfstream Park': 'GP',
            'Santa Anita': 'SA',
            'Churchill Downs': 'CD',
            'Keeneland': 'KEE',
            'Del Mar': 'DMR',
            'Oaklawn Park': 'OP',
            'Fair Grounds': 'FG'
        }
        
        tracks = race_schedule.get('tracks', [])
        for track in tracks:
            track_name = track.get('name', '')
            meetno = track.get('meetno', '')
            
            # Check if this is a major track
            track_code = None
            for major_name, code in major_track_names.items():
                if major_name.lower() in track_name.lower():
                    track_code = code
                    break
            
            if not track_code:
                continue
                
            logger.info(f"Checking {track_name} ({track_code})")
            
            # Try to get race details for first few races
            for race_num in range(1, 4):  # Check races 1-3
                race_details = self.get_race_details(meetno, track_name, race_num)
                if race_details:
                    race_details['track'] = track_name
                    race_details['track_code'] = track_code
                    race_details['race_number'] = str(race_num)
                    race_details['meetno'] = meetno
                    all_data['races'].append(race_details)
                
                time.sleep(1)  # Rate limiting
        
        logger.info(f"Found {len(all_data['races'])} races with data")
        return all_data


if __name__ == "__main__":
    scraper = OTBScraper()
    
    # Test getting race schedule
    logger.info("Testing OTB scraper...")
    
    # First just get the schedule
    schedule = scraper.get_current_races()
    if schedule:
        print(f"Got schedule for: {schedule.get('headline')}")
        print(f"Total tracks: {len(schedule.get('tracks', []))}")
        
        # Show first 5 tracks
        for track in schedule.get('tracks', [])[:5]:
            print(f"- {track.get('name')} ({track.get('code')}) - Race {track.get('currentRace')}")
        
        # Save full schedule
        with open('otb_schedule.json', 'w') as f:
            json.dump(schedule, f, indent=2)
    
    # Try full scraping
    data = scraper.scrape_all_available()
    
    # Save results
    with open('otb_scraped_data.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\nScraped {len(data['races'])} races from OTB")