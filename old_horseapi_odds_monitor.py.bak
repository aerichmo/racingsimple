#!/usr/bin/env python3
"""
HorseAPI Odds Monitor
Monitors races and pulls odds at specific intervals before post time
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import schedule

from horseapi_service import HorseAPIService
from horseapi_db_integration import HorseAPIOddsDB

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OddsMonitor:
    """Main monitor that coordinates odds pulling"""
    
    def __init__(self):
        self.api_service = HorseAPIService()
        self.db = HorseAPIOddsDB()
        self.active_monitors = {}  # race_id: scheduled_jobs
        
    def pull_odds_for_race(self, race_info: dict, interval_name: str):
        """Pull odds for a specific race and interval"""
        race_id = race_info['id']
        horse_api_race_id = race_info['horse_api_race_id']
        
        logger.info(f"Pulling {interval_name} odds for race {race_id} (API: {horse_api_race_id})")
        
        # Get odds from API
        odds_data = self.api_service.get_race_odds(horse_api_race_id)
        
        if odds_data:
            # Save to database
            success = self.db.save_odds_snapshot(
                race_id=race_id,
                horse_api_race_id=horse_api_race_id,
                interval_name=interval_name,
                odds_data=odds_data
            )
            
            if success:
                logger.info(f"Successfully saved {interval_name} odds for race {race_id}")
            else:
                logger.error(f"Failed to save {interval_name} odds for race {race_id}")
        else:
            logger.error(f"Failed to get odds from API for race {race_id}")
    
    def schedule_race_monitoring(self, race_info: dict):
        """Schedule odds pulls for a single race"""
        race_id = race_info['id']
        post_time = race_info['post_time']
        
        # Skip if already monitoring
        if race_id in self.active_monitors:
            logger.info(f"Already monitoring race {race_id}")
            return
        
        intervals = [
            (10, "10min_before"),
            (5, "5min_before"),
            (2, "2min_before"),
            (1, "1min_before"),
            (0, "at_post")
        ]
        
        scheduled_jobs = []
        now = datetime.now()
        
        for minutes_before, interval_name in intervals:
            pull_time = post_time - timedelta(minutes=minutes_before)
            
            # Only schedule if time hasn't passed
            if pull_time > now:
                # Calculate seconds until pull
                seconds_until = (pull_time - now).total_seconds()
                
                # Schedule the job
                job = schedule.every(seconds_until).seconds.do(
                    self.pull_odds_for_race, 
                    race_info=race_info, 
                    interval_name=interval_name
                ).tag(f"race_{race_id}")
                
                scheduled_jobs.append({
                    'job': job,
                    'pull_time': pull_time,
                    'interval': interval_name
                })
                
                logger.info(f"Scheduled {interval_name} pull for race {race_id} at {pull_time}")
        
        if scheduled_jobs:
            self.active_monitors[race_id] = scheduled_jobs
            logger.info(f"Monitoring race {race_id} with {len(scheduled_jobs)} scheduled pulls")
    
    def update_monitored_races(self):
        """Check for new races to monitor and schedule them"""
        logger.info("Checking for races to monitor...")
        
        # Get races from database that need monitoring
        races = self.db.get_races_for_monitoring()
        
        logger.info(f"Found {len(races)} races eligible for monitoring")
        
        for race in races:
            self.schedule_race_monitoring(race)
        
        # Clean up completed races
        self.cleanup_completed_races()
    
    def cleanup_completed_races(self):
        """Remove monitoring for races that have passed"""
        current_time = datetime.now()
        races_to_remove = []
        
        for race_id, jobs in self.active_monitors.items():
            # Check if all jobs are past their scheduled time
            all_complete = all(
                job['pull_time'] < current_time 
                for job in jobs
            )
            
            if all_complete:
                races_to_remove.append(race_id)
                # Cancel any remaining scheduled jobs
                schedule.clear(f"race_{race_id}")
        
        for race_id in races_to_remove:
            del self.active_monitors[race_id]
            logger.info(f"Removed monitoring for completed race {race_id}")
    
    def run_monitor(self):
        """Main monitoring loop"""
        logger.info("Starting HorseAPI Odds Monitor")
        
        # Initial setup
        self.db.create_odds_tables()
        
        # Schedule periodic checks for new races
        schedule.every(5).minutes.do(self.update_monitored_races)
        
        # Initial race check
        self.update_monitored_races()
        
        # Main loop
        while True:
            try:
                schedule.run_pending()
                time.sleep(10)  # Check every 10 seconds
            except KeyboardInterrupt:
                logger.info("Shutting down monitor...")
                break
            except Exception as e:
                logger.error(f"Error in monitor loop: {str(e)}")
                time.sleep(60)  # Wait a minute before retrying
    
    def get_monitor_status(self) -> dict:
        """Get current monitoring status"""
        status = {
            'active_races': len(self.active_monitors),
            'races': []
        }
        
        for race_id, jobs in self.active_monitors.items():
            pending_pulls = [
                {
                    'interval': job['interval'],
                    'scheduled_time': job['pull_time'].isoformat()
                }
                for job in jobs
                if job['pull_time'] > datetime.now()
            ]
            
            status['races'].append({
                'race_id': race_id,
                'pending_pulls': pending_pulls
            })
        
        return status


# Flask integration endpoints
def add_monitoring_endpoints(app):
    """Add monitoring endpoints to Flask app"""
    monitor = OddsMonitor()
    
    @app.route('/api/horseapi/monitor/status')
    def monitor_status():
        """Get current monitoring status"""
        return monitor.get_monitor_status()
    
    @app.route('/api/horseapi/monitor/race/<int:race_id>', methods=['POST'])
    def enable_race_monitoring(race_id):
        """Enable monitoring for a specific race"""
        from flask import request, jsonify
        
        data = request.json
        horse_api_race_id = data.get('horse_api_race_id')
        post_time_str = data.get('post_time')
        
        if not horse_api_race_id or not post_time_str:
            return jsonify({'error': 'Missing required fields'}), 400
        
        try:
            post_time = datetime.fromisoformat(post_time_str)
        except:
            return jsonify({'error': 'Invalid post_time format'}), 400
        
        # Enable in database
        success = monitor.db.enable_race_monitoring(
            race_id=race_id,
            horse_api_race_id=horse_api_race_id,
            post_time=post_time
        )
        
        if success:
            # Schedule monitoring
            race_info = {
                'id': race_id,
                'horse_api_race_id': horse_api_race_id,
                'post_time': post_time
            }
            monitor.schedule_race_monitoring(race_info)
            
            return jsonify({'success': True, 'message': 'Monitoring enabled'})
        else:
            return jsonify({'error': 'Failed to enable monitoring'}), 500
    
    @app.route('/api/horseapi/odds/<int:race_id>')
    def get_race_odds_history(race_id):
        """Get odds history for a race"""
        from flask import jsonify
        
        history = monitor.db.get_odds_history(race_id)
        movement = monitor.db.get_odds_movement_analysis(race_id)
        
        return jsonify({
            'history': history,
            'movement': movement
        })
    
    return monitor


if __name__ == "__main__":
    # Run as standalone monitor
    monitor = OddsMonitor()
    monitor.run_monitor()