"""
Alternative data sources and methods for getting race data
"""
import os
import json
import logging
from datetime import datetime
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class AlternativeDataFetcher:
    """Try alternative sources for race data"""
    
    def __init__(self, db_url: str):
        self.db_url = db_url
        
    def fetch_from_drf(self, date: datetime):
        """Try Daily Racing Form as alternative"""
        logger.info("Trying Daily Racing Form...")
        
        try:
            # DRF entries URL pattern
            date_str = date.strftime("%Y-%m-%d")
            url = f"https://www.drf.com/entries-results/entries/{date_str}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return self._parse_drf_data(response.text, date)
                
        except Exception as e:
            logger.error(f"DRF error: {e}")
            
        return None
    
    def fetch_from_bloodhorse(self, date: datetime):
        """Try BloodHorse as alternative"""
        logger.info("Trying BloodHorse...")
        
        try:
            date_str = date.strftime("%Y/%m/%d")
            url = f"https://www.bloodhorse.com/horse-racing/entries/{date_str}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return self._parse_bloodhorse_data(response.text, date)
                
        except Exception as e:
            logger.error(f"BloodHorse error: {e}")
            
        return None
    
    def fetch_from_trackinfo(self, date: datetime):
        """Try track-specific websites"""
        logger.info("Trying track websites...")
        
        # Fonner Park specific
        fonner_races = self._fetch_fonner_park(date)
        if fonner_races:
            return fonner_races
            
        return None
    
    def _fetch_fonner_park(self, date: datetime):
        """Fetch from Fonner Park website"""
        try:
            # Fonner Park might have their own entries page
            url = "https://www.fonnerpark.com/racing/entries"
            
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Parse Fonner-specific format
                races = []
                
                # Look for race data
                race_divs = soup.find_all('div', class_=['race', 'race-card', 'entry'])
                
                for i, race_div in enumerate(race_divs, 1):
                    race = {
                        'date': date.date(),
                        'race_number': i,
                        'track_name': 'Fonner Park',
                        'horses': []
                    }
                    
                    # Extract horses
                    horse_rows = race_div.find_all(['tr', 'div'], class_=['horse', 'entry-row'])
                    for row in horse_rows:
                        horse_data = self._extract_horse_info(row)
                        if horse_data:
                            race['horses'].append(horse_data)
                    
                    if race['horses']:
                        races.append(race)
                
                return races if races else None
                
        except Exception as e:
            logger.error(f"Fonner Park error: {e}")
            
        return None
    
    def _extract_horse_info(self, element):
        """Extract horse information from various formats"""
        try:
            # Try different patterns
            text = element.get_text()
            
            # Pattern 1: Number Name (Jockey/Trainer)
            import re
            match = re.match(r'(\d+)\s+([^(]+)\s*\(([^)]+)\)', text)
            if match:
                return {
                    'program_number': match.group(1),
                    'horse_name': match.group(2).strip(),
                    'jockey': match.group(3).strip()
                }
            
            # Pattern 2: Table cells
            cells = element.find_all(['td', 'span'])
            if len(cells) >= 3:
                return {
                    'program_number': cells[0].get_text().strip(),
                    'horse_name': cells[1].get_text().strip(),
                    'jockey': cells[2].get_text().strip() if len(cells) > 2 else ''
                }
                
        except Exception as e:
            logger.debug(f"Extract error: {e}")
            
        return None
    
    def _parse_drf_data(self, html, date):
        """Parse DRF format"""
        soup = BeautifulSoup(html, 'html.parser')
        races = []
        # Implementation would depend on DRF's actual HTML structure
        return races
    
    def _parse_bloodhorse_data(self, html, date):
        """Parse BloodHorse format"""
        soup = BeautifulSoup(html, 'html.parser')
        races = []
        # Implementation would depend on BloodHorse's actual HTML structure
        return races
    
    def use_api_aggregators(self, date: datetime):
        """Try API aggregators that might have the data"""
        logger.info("Trying API aggregators...")
        
        # Some potential API services (would need API keys)
        aggregators = [
            {
                'name': 'Racing API',
                'url': 'https://api.racing-api.com/entries',
                'params': {'date': date.strftime('%Y-%m-%d'), 'track': 'fonner-park'}
            },
            {
                'name': 'Sports Data API',
                'url': 'https://api.sportsdata.io/v3/racing/entries',
                'params': {'date': date.strftime('%Y-%m-%d')}
            }
        ]
        
        for api in aggregators:
            try:
                # Would need actual API keys
                response = requests.get(api['url'], params=api['params'], timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data:
                        return self._parse_api_data(data, date)
            except Exception as e:
                logger.debug(f"{api['name']} error: {e}")
                
        return None
    
    def _parse_api_data(self, data, date):
        """Parse API response data"""
        races = []
        # Would parse based on API format
        return races


def fetch_from_alternatives(db_url: str, date: datetime):
    """Try all alternative sources"""
    fetcher = AlternativeDataFetcher(db_url)
    
    sources = [
        ('Daily Racing Form', fetcher.fetch_from_drf),
        ('BloodHorse', fetcher.fetch_from_bloodhorse),
        ('Track Websites', fetcher.fetch_from_trackinfo),
        ('API Aggregators', fetcher.use_api_aggregators),
    ]
    
    for source_name, fetch_method in sources:
        logger.info(f"Trying {source_name}...")
        try:
            races = fetch_method(date)
            if races:
                logger.info(f"Success with {source_name}!")
                return True, races, source_name
        except Exception as e:
            logger.error(f"{source_name} failed: {e}")
            
    return False, None, None