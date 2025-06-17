#!/usr/bin/env python3
"""
StatPal Horse Racing API Service
Updated to work with actual StatPal API structure
"""
import requests
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StatPalService:
    """Service for integrating with StatPal Horse Racing API"""
    
    def __init__(self, access_key: str = None):
        self.access_key = access_key or Config.get_horseapi_key()
        if not self.access_key:
            raise ValueError("StatPal access key not found. Please set HORSEAPI_ACCESS_KEY environment variable.")
        
        self.base_url = 'https://statpal.io/api/v1/horse-racing'
        
    def _make_request(self, endpoint: str, country: str = 'uk', use_bearer: bool = False) -> Optional[Dict]:
        """Make API request with proper authentication"""
        # Use 'usa' for US endpoints, not 'us'
        if country == 'us':
            country = 'usa'
            
        url = f"{self.base_url}/{endpoint}/{country}"
        
        try:
            # Both UK and USA work with access_key parameter
            params = {'access_key': self.access_key}
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            return None
    
    def get_live_races(self, country: str = 'uk') -> Optional[List[Dict]]:
        """Get current live races for a country"""
        data = self._make_request('live', country)
        
        if not data or 'scores' not in data:
            return None
        
        # Parse StatPal format into our format
        races = []
        if 'tournament' in data['scores']:
            for venue in data['scores']['tournament']:
                venue_name = venue.get('name', 'Unknown')
                venue_id = venue.get('id', '')
                going = venue.get('going', '')
                
                if 'race' in venue:
                    for race in venue['race']:
                        race_data = {
                            'id': race.get('id', ''),
                            'venue_name': venue_name,
                            'venue_id': venue_id,
                            'race_name': race.get('name', ''),
                            'race_number': int(race.get('name', '').split(' ')[1]) if 'Race' in race.get('name', '') else 0,
                            'post_time': race.get('time', ''),
                            'datetime': race.get('datetime', ''),
                            'distance': race.get('distance', ''),
                            'class': race.get('class', ''),
                            'going': going,
                            'status': race.get('status', ''),
                            'num_horses': len(race.get('runners', {}).get('horse', [])) if 'runners' in race else 0
                        }
                        races.append(race_data)
        
        return races
    
    def get_race_details(self, race_id: str, country: str = 'uk') -> Optional[Dict]:
        """Get detailed information about a specific race including runners"""
        # First get all live races
        data = self._make_request('live', country)
        
        if not data or 'scores' not in data:
            return None
        
        # Find the specific race
        if 'tournament' in data['scores']:
            for venue in data['scores']['tournament']:
                if 'race' in venue:
                    for race in venue['race']:
                        if race.get('id') == race_id:
                            # Parse runners/horses
                            horses = []
                            if 'runners' in race and 'horse' in race['runners']:
                                for horse in race['runners']['horse']:
                                    horse_data = {
                                        'id': horse.get('id', ''),
                                        'name': horse.get('name', ''),
                                        'number': horse.get('number', ''),
                                        'stall': horse.get('stall', ''),
                                        'jockey': horse.get('jockey', ''),
                                        'trainer': horse.get('trainer', ''),
                                        'age': horse.get('age', ''),
                                        'weight': horse.get('wgt', ''),
                                        'rating': horse.get('rating', ''),
                                        'form': self._parse_form(horse.get('recent_form', {}))
                                    }
                                    horses.append(horse_data)
                            
                            return {
                                'race_info': {
                                    'id': race.get('id', ''),
                                    'name': race.get('name', ''),
                                    'venue': venue.get('name', ''),
                                    'time': race.get('time', ''),
                                    'distance': race.get('distance', ''),
                                    'going': venue.get('going', ''),
                                    'class': race.get('class', '')
                                },
                                'horses': horses
                            }
        
        return None
    
    def _parse_form(self, form_data: Dict) -> Dict:
        """Parse horse form statistics"""
        form = {}
        if isinstance(form_data, dict) and 'section' in form_data:
            for section in form_data['section']:
                if isinstance(section, dict):
                    section_name = section.get('name', '')
                    if section_name and 'stat' in section:
                        form[section_name] = {}
                        stats = section['stat']
                        if isinstance(stats, list):
                            for stat in stats:
                                if isinstance(stat, dict):
                                    stat_name = stat.get('name', '')
                                    if stat_name:
                                        form[section_name][stat_name] = {
                                            'runs': stat.get('runs', '0'),
                                            'wins': stat.get('wins', '0'),
                                            'places': stat.get('places', '0'),
                                            'win_pct': stat.get('win_pct', '0%')
                                        }
        return form
    
    def test_connection(self) -> bool:
        """Test if the API connection is working"""
        try:
            data = self.get_live_races('uk')
            return data is not None
        except:
            return False


# Example usage
if __name__ == "__main__":
    service = StatPalService()
    
    # Test connection
    if service.test_connection():
        print("✅ API connection successful!")
        
        # Get live races
        races = service.get_live_races('uk')
        if races:
            print(f"\nFound {len(races)} live UK races:")
            for race in races[:5]:  # Show first 5
                print(f"  - {race['venue_name']} R{race['race_number']}: {race['race_name']} @ {race['post_time']}")
            
            # Get details for first race
            if races:
                first_race_id = races[0]['id']
                details = service.get_race_details(first_race_id)
                if details:
                    print(f"\nDetails for {details['race_info']['name']}:")
                    print(f"  Horses: {len(details['horses'])}")
                    for horse in details['horses'][:3]:  # Show first 3 horses
                        print(f"    #{horse['number']} {horse['name']} - Jockey: {horse['jockey']}")
    else:
        print("❌ API connection failed")