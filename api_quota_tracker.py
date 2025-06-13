import json
import os
from datetime import datetime, date
from pathlib import Path

class APIQuotaTracker:
    """
    Track API usage to stay within RapidAPI limits
    Horse Racing USA API: 50 calls/day, allocated 40 for STALL10N
    """
    
    def __init__(self, quota_file='api_quota.json', daily_limit=40):
        self.quota_file = Path(quota_file)
        self.daily_limit = daily_limit
        self.data = self._load_data()
    
    def _load_data(self):
        """Load quota data from file"""
        if self.quota_file.exists():
            with open(self.quota_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_data(self):
        """Save quota data to file"""
        with open(self.quota_file, 'w') as f:
            json.dump(self.data, f, indent=2)
    
    def can_make_request(self):
        """Check if we can make another API request today"""
        today = str(date.today())
        calls_today = self.get_calls_today()
        return calls_today < self.daily_limit
    
    def get_calls_today(self):
        """Get number of API calls made today"""
        today = str(date.today())
        return len(self.data.get(today, []))
    
    def get_remaining_quota(self):
        """Get remaining API calls for today"""
        return self.daily_limit - self.get_calls_today()
    
    def record_call(self, endpoint, race_id=None):
        """Record an API call"""
        today = str(date.today())
        
        if today not in self.data:
            self.data[today] = []
        
        call_record = {
            'timestamp': datetime.now().isoformat(),
            'endpoint': endpoint,
            'race_id': race_id
        }
        
        self.data[today].append(call_record)
        self._save_data()
        
        remaining = self.get_remaining_quota()
        print(f"API call recorded. Remaining quota for today: {remaining}/{self.daily_limit}")
        
        if remaining <= 5:
            print(f"WARNING: Only {remaining} API calls remaining for today!")
        
        return remaining
    
    def get_usage_summary(self):
        """Get usage summary for the last 7 days"""
        summary = []
        today = date.today()
        
        for i in range(7):
            check_date = str(today - timedelta(days=i))
            calls = len(self.data.get(check_date, []))
            summary.append({
                'date': check_date,
                'calls': calls,
                'limit': self.daily_limit
            })
        
        return summary


# Enhanced OddsService with quota tracking
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class QuotaManagedOddsService:
    """
    Odds service with built-in quota management
    """
    
    def __init__(self):
        from odds_service import HorseRacingUSAAPI
        self.api = HorseRacingUSAAPI()
        self.quota_tracker = APIQuotaTracker(
            quota_file='api_quota.json',
            daily_limit=40  # STALL10N allocation
        )
        self._cache = {}
        self.cache_duration = 3600  # 1 hour cache to minimize API calls
    
    def get_race_odds(self, race_id, force_refresh=False):
        """
        Get odds with quota management and extended caching
        """
        cache_key = f"race_{race_id}"
        
        # Check cache first (1 hour TTL to preserve quota)
        if not force_refresh and cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if (datetime.now() - timestamp).seconds < self.cache_duration:
                logger.info(f"Returning cached data for race {race_id}")
                return {
                    'data': cached_data,
                    'cached': True,
                    'remaining_quota': self.quota_tracker.get_remaining_quota()
                }
        
        # Check quota before making request
        if not self.quota_tracker.can_make_request():
            logger.error("Daily API quota exceeded!")
            return {
                'error': 'Daily API quota exceeded',
                'remaining_quota': 0,
                'cached': False
            }
        
        # Make API request
        logger.info(f"Fetching fresh data for race {race_id}")
        try:
            data = self.api.get_race_data(race_id)
            
            if data:
                # Record the API call
                remaining = self.quota_tracker.record_call('get_race', race_id)
                
                # Cache the data
                self._cache[cache_key] = (data, datetime.now())
                
                return {
                    'data': data,
                    'cached': False,
                    'remaining_quota': remaining
                }
            else:
                return {
                    'error': 'Failed to fetch race data',
                    'remaining_quota': self.quota_tracker.get_remaining_quota()
                }
                
        except Exception as e:
            logger.error(f"API error: {e}")
            return {
                'error': str(e),
                'remaining_quota': self.quota_tracker.get_remaining_quota()
            }
    
    def get_quota_status(self):
        """Get current quota status"""
        return {
            'calls_today': self.quota_tracker.get_calls_today(),
            'remaining': self.quota_tracker.get_remaining_quota(),
            'daily_limit': self.quota_tracker.daily_limit,
            'usage_summary': self.quota_tracker.get_usage_summary()
        }


# Example usage with quota management
if __name__ == "__main__":
    service = QuotaManagedOddsService()
    
    # Check quota status
    status = service.get_quota_status()
    print(f"API Quota Status: {status['remaining']}/{status['daily_limit']} calls remaining")
    
    # Get race data (will use quota)
    result = service.get_race_odds(39302)
    
    if 'error' in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Got data for race (cached: {result['cached']})")
        print(f"Remaining quota: {result['remaining_quota']}")
    
    # Second call should use cache
    result2 = service.get_race_odds(39302)
    print(f"Second call used cache: {result2['cached']}")