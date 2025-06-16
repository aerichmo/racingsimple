import requests
import json
import os
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Tuple
import threading
import time
from collections import defaultdict
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HorseAPIService:
    """Service for integrating with HorseAPI/StatPal for live odds data"""
    
    def __init__(self, access_key: str = None):
        self.access_key = access_key or Config.get_horseapi_key()
        if not self.access_key:
            raise ValueError("HorseAPI access key not found. Please set HORSEAPI_ACCESS_KEY environment variable.")
        
        self.base_url = 'https://statpal.io/api/v1/horse-racing'
        self.scheduled_pulls = defaultdict(list)  # race_id: [(pull_time, completed)]
        self.odds_cache = {}  # race_id: {timestamp: odds_data}
        self.rate_limit_remaining = 10  # 10 calls per hour
        self.rate_limit_reset = datetime.now() + timedelta(hours=1)
        
    def _check_rate_limit(self) -> bool:
        """Check if we have API calls remaining"""
        if datetime.now() > self.rate_limit_reset:
            self.rate_limit_remaining = 10
            self.rate_limit_reset = datetime.now() + timedelta(hours=1)
        return self.rate_limit_remaining > 0
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make API request with rate limiting and error handling"""
        if not self._check_rate_limit():
            logger.warning("Rate limit exceeded. Next reset at %s", self.rate_limit_reset)
            return None
            
        url = f"{self.base_url}/{endpoint}"
        params = params or {}
        params['access_key'] = self.access_key
        
        try:
            response = requests.get(url, params=params, timeout=10)
            self.rate_limit_remaining -= 1
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            return None
    
    def get_live_races(self, country: str = 'us') -> Optional[List[Dict]]:
        """Get current live races for a country"""
        data = self._make_request(f'live/{country}')
        return data.get('races', []) if data else None
    
    def get_race_schedule(self, country: str = 'us') -> Optional[List[Dict]]:
        """Get upcoming race schedule for a country"""
        data = self._make_request(f'schedule/{country}')
        return data.get('races', []) if data else None
    
    def get_race_odds(self, race_id: str) -> Optional[Dict]:
        """Get current odds for a specific race"""
        data = self._make_request(f'odds/{race_id}')
        if data:
            # Cache the odds with timestamp
            self.odds_cache[race_id] = {
                'timestamp': datetime.now(),
                'odds': data
            }
        return data
    
    def schedule_odds_pulls(self, race_id: str, post_time: datetime) -> List[Tuple[datetime, str]]:
        """Schedule odds pulls at specific intervals before post time
        
        Returns list of scheduled pull times: [(datetime, interval_name)]
        """
        intervals = [
            (10, "10min_before"),
            (5, "5min_before"),
            (2, "2min_before"),
            (1, "1min_before"),
            (0, "at_post")
        ]
        
        scheduled_times = []
        
        for minutes_before, interval_name in intervals:
            pull_time = post_time - timedelta(minutes=minutes_before)
            
            # Only schedule if time hasn't passed
            if pull_time > datetime.now():
                scheduled_times.append((pull_time, interval_name))
                self.scheduled_pulls[race_id].append({
                    'time': pull_time,
                    'interval': interval_name,
                    'completed': False
                })
        
        logger.info(f"Scheduled {len(scheduled_times)} odds pulls for race {race_id}")
        return scheduled_times
    
    def execute_scheduled_pull(self, race_id: str, interval_name: str) -> Optional[Dict]:
        """Execute a scheduled odds pull and store results"""
        logger.info(f"Executing {interval_name} odds pull for race {race_id}")
        
        odds_data = self.get_race_odds(race_id)
        
        if odds_data:
            # Store with interval identifier
            key = f"{race_id}_{interval_name}"
            self.odds_cache[key] = {
                'timestamp': datetime.now(),
                'interval': interval_name,
                'odds': odds_data
            }
            
            # Mark as completed
            for pull in self.scheduled_pulls[race_id]:
                if pull['interval'] == interval_name:
                    pull['completed'] = True
                    break
                    
            logger.info(f"Successfully pulled {interval_name} odds for race {race_id}")
            return odds_data
        else:
            logger.error(f"Failed to pull {interval_name} odds for race {race_id}")
            return None
    
    def get_odds_history(self, race_id: str) -> Dict[str, Dict]:
        """Get all cached odds for a race organized by interval"""
        history = {}
        
        for interval in ["10min_before", "5min_before", "2min_before", "1min_before", "at_post"]:
            key = f"{race_id}_{interval}"
            if key in self.odds_cache:
                history[interval] = self.odds_cache[key]
                
        return history
    
    def start_odds_scheduler(self):
        """Start background thread to monitor and execute scheduled pulls"""
        def scheduler_loop():
            while True:
                now = datetime.now()
                
                for race_id, pulls in self.scheduled_pulls.items():
                    for pull in pulls:
                        if not pull['completed'] and pull['time'] <= now:
                            # Execute pull in separate thread to avoid blocking
                            threading.Thread(
                                target=self.execute_scheduled_pull,
                                args=(race_id, pull['interval'])
                            ).start()
                
                time.sleep(30)  # Check every 30 seconds
        
        scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
        scheduler_thread.start()
        logger.info("Odds scheduler started")
    
    def get_upcoming_races_to_monitor(self, country: str = 'us', hours_ahead: int = 2) -> List[Dict]:
        """Get races starting in the next N hours that should be monitored"""
        schedule = self.get_race_schedule(country)
        
        if not schedule:
            return []
        
        upcoming = []
        cutoff_time = datetime.now() + timedelta(hours=hours_ahead)
        
        for race in schedule:
            # Parse post time from API response
            post_time_str = race.get('post_time')
            if post_time_str:
                try:
                    post_time = datetime.fromisoformat(post_time_str)
                    if datetime.now() < post_time <= cutoff_time:
                        race['post_time_parsed'] = post_time
                        upcoming.append(race)
                except:
                    logger.error(f"Failed to parse post time: {post_time_str}")
        
        return upcoming


# Example usage and integration
if __name__ == "__main__":
    # Initialize service
    service = HorseAPIService()
    
    # Start scheduler
    service.start_odds_scheduler()
    
    # Get upcoming races
    upcoming = service.get_upcoming_races_to_monitor(hours_ahead=3)
    
    # Schedule odds pulls for each race
    for race in upcoming:
        race_id = race.get('id')
        post_time = race.get('post_time_parsed')
        
        if race_id and post_time:
            scheduled = service.schedule_odds_pulls(race_id, post_time)
            print(f"Race {race_id} at {post_time}:")
            for pull_time, interval in scheduled:
                print(f"  - {interval}: {pull_time}")