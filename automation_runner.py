#!/usr/bin/env python3
"""
ST0CK Automation Runner - Continuous Operation System
Runs 24/7 to automatically collect race data without manual intervention
"""

import os
import sys
import time
import schedule
import logging
from datetime import datetime, timedelta
import threading
import signal
from pathlib import Path

# Import project modules
from race_data_puller import RaceDataPuller, run_scheduled_pull
from fair_meadows_monitor import FairMeadowsMonitor
from betting_strategy import calculate_betting_strategy

# Setup logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / f'automation_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class ST0CKAutomation:
    """
    Main automation controller for ST0CK project
    """
    
    def __init__(self):
        self.running = True
        self.puller = RaceDataPuller()
        self.monitor = FairMeadowsMonitor()
        self.setup_signal_handlers()
        
    def setup_signal_handlers(self):
        """
        Setup graceful shutdown on CTRL+C
        """
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)
    
    def shutdown(self, signum, frame):
        """
        Graceful shutdown
        """
        logger.info("Shutdown signal received. Stopping automation...")
        self.running = False
        sys.exit(0)
    
    def hourly_tasks(self):
        """
        Tasks that run every hour
        """
        logger.info("=" * 50)
        logger.info("Running hourly tasks")
        
        try:
            # Check for upcoming races in next 2 hours
            races = self.puller.get_races_needing_data_pull(minutes_before=120)
            logger.info(f"Found {len(races)} races in next 2 hours")
            
            # Log quota status
            status = self.puller.odds_service.get_quota_status()
            logger.info(f"API Quota - Used: {status['used_today']}/{status['daily_limit']}")
            
        except Exception as e:
            logger.error(f"Error in hourly tasks: {e}")
    
    def five_minute_tasks(self):
        """
        Tasks that run every 5 minutes (main data collection)
        """
        logger.info("Running 5-minute data collection")
        
        try:
            # Run the scheduled race data pull
            run_scheduled_pull()
            
        except Exception as e:
            logger.error(f"Error in 5-minute tasks: {e}")
    
    def daily_tasks(self):
        """
        Tasks that run once per day
        """
        logger.info("=" * 70)
        logger.info("RUNNING DAILY TASKS")
        logger.info("=" * 70)
        
        try:
            # Rotate logs
            self.rotate_logs()
            
            # Check and populate race schedule for next 3 days
            self.populate_race_schedule()
            
            # Generate daily report
            self.generate_daily_report()
            
        except Exception as e:
            logger.error(f"Error in daily tasks: {e}")
    
    def populate_race_schedule(self):
        """
        Populate race schedule for upcoming days
        """
        logger.info("Populating race schedule for next 3 days")
        
        # This would connect to race schedule APIs
        # For now, log the action
        tracks = ['Fair Meadows', 'Remington Park', 'Will Rogers Downs']
        
        for days_ahead in range(3):
            target_date = datetime.now().date() + timedelta(days=days_ahead)
            logger.info(f"Checking schedule for {target_date}")
            
            for track in tracks:
                # Would make API calls here to get race schedules
                logger.info(f"  - {track}: Schedule check would happen here")
    
    def generate_daily_report(self):
        """
        Generate daily summary report
        """
        report_file = log_dir / f"daily_report_{datetime.now().strftime('%Y%m%d')}.txt"
        
        with open(report_file, 'w') as f:
            f.write(f"ST0CK Daily Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write("=" * 70 + "\n\n")
            
            # API Usage
            status = self.puller.odds_service.get_quota_status()
            f.write(f"API Usage: {status['used_today']}/{status['daily_limit']}\n")
            f.write(f"Remaining: {status['remaining']}\n\n")
            
            # Would add more stats here from database
            f.write("Race Data Collection Summary:\n")
            f.write("- Races Monitored: [Would query DB]\n")
            f.write("- Successful Pulls: [Would query DB]\n")
            f.write("- Failed Pulls: [Would query DB]\n")
            
        logger.info(f"Daily report saved to {report_file}")
    
    def rotate_logs(self):
        """
        Keep only last 7 days of logs
        """
        cutoff_date = datetime.now() - timedelta(days=7)
        
        for log_file in log_dir.glob("*.log"):
            try:
                # Parse date from filename
                date_str = log_file.stem.split('_')[1]
                file_date = datetime.strptime(date_str, "%Y%m%d")
                
                if file_date < cutoff_date:
                    log_file.unlink()
                    logger.info(f"Deleted old log: {log_file.name}")
                    
            except Exception as e:
                logger.error(f"Error processing log file {log_file}: {e}")
    
    def setup_schedule(self):
        """
        Setup all scheduled tasks
        """
        # Every 5 minutes - main data collection
        schedule.every(5).minutes.do(self.five_minute_tasks)
        
        # Every hour - status checks
        schedule.every().hour.do(self.hourly_tasks)
        
        # Daily at 6 AM - maintenance tasks
        schedule.every().day.at("06:00").do(self.daily_tasks)
        
        logger.info("Schedule configured:")
        logger.info("- Data collection: Every 5 minutes")
        logger.info("- Status checks: Every hour") 
        logger.info("- Daily maintenance: 6:00 AM")
    
    def run(self):
        """
        Main run loop
        """
        logger.info("=" * 70)
        logger.info("ST0CK AUTOMATION STARTING")
        logger.info(f"Start time: {datetime.now()}")
        logger.info("=" * 70)
        
        # Setup scheduled tasks
        self.setup_schedule()
        
        # Run initial tasks
        self.daily_tasks()
        self.hourly_tasks()
        
        # Main loop
        while self.running:
            try:
                # Run pending scheduled tasks
                schedule.run_pending()
                
                # Sleep for 30 seconds
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(60)  # Wait a minute before retrying
        
        logger.info("Automation stopped")


def main():
    """
    Entry point for automation
    """
    automation = ST0CKAutomation()
    
    try:
        automation.run()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()