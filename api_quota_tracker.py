"""
API Quota Tracker for Managing Race Data API Calls
Tracks API usage and prevents exceeding quota limits
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

class QuotaManagedOddsService:
    """
    Service to manage API quota and track usage
    """
    
    def __init__(self):
        self.quota_file = Path("api_quota_status.json")
        self.daily_limit = 100  # Adjust based on your API plan
        self.api_base_url = os.environ.get('RACE_API_URL', 'https://api.horseracing.com/v1')
        self.api_key = os.environ.get('RACE_API_KEY', '')
        self.load_quota_status()
    
    def load_quota_status(self):
        """
        Load quota status from file or create new
        """
        if self.quota_file.exists():
            try:
                with open(self.quota_file, 'r') as f:
                    self.quota_data = json.load(f)
                    # Reset if new day
                    last_reset = datetime.fromisoformat(self.quota_data.get('last_reset', '2025-01-01'))
                    if datetime.now().date() > last_reset.date():
                        self.reset_daily_quota()
            except Exception as e:
                logger.error(f"Error loading quota file: {e}")
                self.reset_daily_quota()
        else:
            self.reset_daily_quota()
    
    def reset_daily_quota(self):
        """
        Reset daily quota counter
        """
        self.quota_data = {
            'daily_limit': self.daily_limit,
            'used_today': 0,
            'last_reset': datetime.now().isoformat(),
            'api_calls': []
        }
        self.save_quota_status()
    
    def save_quota_status(self):
        """
        Save quota status to file
        """
        try:
            with open(self.quota_file, 'w') as f:
                json.dump(self.quota_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving quota file: {e}")
    
    def can_make_request(self, required_calls=1):
        """
        Check if we have quota for the required number of calls
        """
        remaining = self.quota_data['daily_limit'] - self.quota_data['used_today']
        return remaining >= required_calls
    
    def record_api_call(self, endpoint, success=True):
        """
        Record an API call
        """
        self.quota_data['used_today'] += 1
        self.quota_data['api_calls'].append({
            'timestamp': datetime.now().isoformat(),
            'endpoint': endpoint,
            'success': success
        })
        
        # Keep only last 100 calls in log
        if len(self.quota_data['api_calls']) > 100:
            self.quota_data['api_calls'] = self.quota_data['api_calls'][-100:]
        
        self.save_quota_status()
    
    def get_quota_status(self):
        """
        Get current quota status
        """
        self.load_quota_status()  # Reload to check for day change
        return {
            'daily_limit': self.quota_data['daily_limit'],
            'used_today': self.quota_data['used_today'],
            'remaining': self.quota_data['daily_limit'] - self.quota_data['used_today'],
            'last_reset': self.quota_data['last_reset']
        }
    
    def get_race_odds(self, race_id):
        """
        Get race odds with quota management
        """
        if not self.can_make_request():
            raise Exception("API quota exceeded for today")
        
        # Simulate API call - replace with actual API implementation
        endpoint = f"/races/{race_id}/odds"
        
        try:
            # This is a placeholder - implement actual API call here
            # response = requests.get(f"{self.api_base_url}{endpoint}", 
            #                       headers={'API-Key': self.api_key})
            
            # For now, return mock data
            self.record_api_call(endpoint, success=True)
            
            return {
                'data': {
                    'race_id': race_id,
                    'finished': False,
                    'horses': []  # Would contain actual horse data
                },
                'remaining_quota': self.get_quota_status()['remaining']
            }
            
        except Exception as e:
            self.record_api_call(endpoint, success=False)
            logger.error(f"API call failed: {e}")
            raise
    
    def get_track_races(self, track_code, date):
        """
        Get races for a track on a specific date
        """
        if not self.can_make_request():
            raise Exception("API quota exceeded for today")
        
        endpoint = f"/tracks/{track_code}/races/{date}"
        
        try:
            # Placeholder for actual API call
            self.record_api_call(endpoint, success=True)
            
            return {
                'data': {
                    'track': track_code,
                    'date': date,
                    'races': []  # Would contain race list
                },
                'remaining_quota': self.get_quota_status()['remaining']
            }
            
        except Exception as e:
            self.record_api_call(endpoint, success=False)
            logger.error(f"API call failed: {e}")
            raise


# Example usage
if __name__ == "__main__":
    service = QuotaManagedOddsService()
    
    # Check quota status
    status = service.get_quota_status()
    print(f"API Quota Status:")
    print(f"  Daily Limit: {status['daily_limit']}")
    print(f"  Used Today: {status['used_today']}")
    print(f"  Remaining: {status['remaining']}")
    print(f"  Last Reset: {status['last_reset']}")