import os
import requests
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class HorseRacingUSAAPI:
    """
    Integration with Horse Racing USA API from RapidAPI
    """
    
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get('RAPIDAPI_KEY', '1c6ef83f5bmshae8b269821b23dep1c77dbjsn9ed69f94d9fa')
        self.host = 'horse-racing-usa.p.rapidapi.com'
        self.base_url = f'https://{self.host}'
        self.headers = {
            'x-rapidapi-host': self.host,
            'x-rapidapi-key': self.api_key
        }
    
    def get_race_data(self, race_id):
        """
        Get data for a specific race by ID
        
        Args:
            race_id: The race ID from the API
            
        Returns:
            dict: Race data including horses, odds, results
        """
        try:
            url = f"{self.base_url}/race/{race_id}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            return self._parse_race_data(data)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching race {race_id}: {e}")
            return None
    
    def _parse_race_data(self, raw_data):
        """
        Parse raw API data into format compatible with STALL10N database
        """
        if not raw_data:
            return None
            
        # Parse date from API format
        race_date_str = raw_data.get('date', '').split(' ')[0]
        try:
            race_date = datetime.strptime(race_date_str, '%Y-%m-%d').date()
        except:
            race_date = datetime.now().date()
        
        parsed_data = {
            'track': raw_data.get('course', '').replace(' (USA)', ''),
            'date': race_date.isoformat(),
            'race_id': raw_data.get('id_race'),
            'distance': raw_data.get('distance'),
            'finished': raw_data.get('finished') == '1',
            'horses': []
        }
        
        # Parse horse data
        for horse in raw_data.get('horses', []):
            if horse.get('non_runner') == '1':
                continue
                
            horse_data = {
                'horse_name': horse.get('horse', ''),
                'program_number': horse.get('number', ''),
                'jockey': horse.get('jockey', ''),
                'trainer': horse.get('trainer', ''),
                'weight': horse.get('weight', ''),
                'form': horse.get('form', ''),
                'position': horse.get('position', ''),
                'morning_line_odds': None,  # Not provided by this API
                'real_time_odds': self._extract_odds(horse.get('odds', {})),
                'win_probability': None  # Would need to calculate from odds
            }
            
            parsed_data['horses'].append(horse_data)
        
        return parsed_data
    
    def _extract_odds(self, odds_data):
        """
        Extract the latest odds from the odds structure
        """
        # The API returns empty arrays in the test data
        # In production, this would extract the latest odds
        winner_odds = odds_data.get('winner', [])
        if winner_odds and len(winner_odds) > 0:
            # Return the latest odds
            return winner_odds[-1]
        return None
    
    def search_races(self, date=None, track=None):
        """
        Search for races by date and/or track
        Note: This endpoint structure needs to be discovered from API docs
        """
        # Placeholder - actual endpoint structure needs to be determined
        logger.warning("Search functionality not yet implemented - API endpoint structure unknown")
        return []


class OddsService:
    """
    Service to manage odds data from multiple sources
    """
    
    def __init__(self):
        self.api = HorseRacingUSAAPI()
        self._cache = {}
    
    def get_race_odds(self, race_id):
        """
        Get odds for a race, with caching
        """
        cache_key = f"race_{race_id}"
        
        # Check cache first (5 minute TTL)
        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if (datetime.now() - timestamp).seconds < 300:
                logger.info(f"Returning cached data for race {race_id}")
                return cached_data
        
        # Fetch fresh data
        logger.info(f"Fetching fresh data for race {race_id}")
        data = self.api.get_race_data(race_id)
        
        if data:
            self._cache[cache_key] = (data, datetime.now())
        
        return data
    
    def update_database_odds(self, race_data):
        """
        Update STALL10N database with latest odds
        This would integrate with your existing database structure
        """
        if not race_data:
            return False
            
        # This would update your PostgreSQL database
        # Example structure matching your existing schema:
        updates = []
        for horse in race_data.get('horses', []):
            update = {
                'date': race_data['date'],
                'race_number': race_data.get('race_id'),
                'horse_name': horse['horse_name'],
                'real_time_odds': horse.get('real_time_odds')
            }
            updates.append(update)
        
        # TODO: Implement actual database update logic
        logger.info(f"Would update {len(updates)} horses with new odds")
        return True


# Example usage
if __name__ == "__main__":
    # Test the service
    service = OddsService()
    
    # Test with the race ID from your curl command
    race_data = service.get_race_odds(39302)
    
    if race_data:
        print(f"Race at {race_data['track']} on {race_data['date']}")
        print(f"Found {len(race_data['horses'])} horses")
        for horse in race_data['horses'][:3]:  # Show first 3
            print(f"  - {horse['horse_name']} (#{horse['program_number']})")