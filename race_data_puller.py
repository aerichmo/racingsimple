"""
Automated Race Data Puller
Pulls live odds for upcoming race and results from previous race
10 minutes before post time
"""

import os
import psycopg2
from psycopg2 import sql
from datetime import datetime, timedelta
import logging
from api_quota_tracker import QuotaManagedOddsService
import json
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RaceDataPuller:
    """
    Automated system to pull race data 10 minutes before post
    """
    
    def __init__(self):
        self.db_url = os.environ.get('DATABASE_URL')
        self.odds_service = QuotaManagedOddsService()
        self.setup_enhanced_database()
    
    def setup_enhanced_database(self):
        """
        Create enhanced database schema for results and live odds
        """
        if not self.db_url:
            logger.error("No database URL configured")
            return
        
        conn = psycopg2.connect(self.db_url)
        cur = conn.cursor()
        
        try:
            # Create race_results table for historical results
            cur.execute('''
                CREATE TABLE IF NOT EXISTS race_results (
                    id SERIAL PRIMARY KEY,
                    race_date DATE NOT NULL,
                    track_name VARCHAR(100) NOT NULL,
                    race_number INTEGER NOT NULL,
                    distance VARCHAR(50),
                    surface VARCHAR(20),
                    race_type VARCHAR(100),
                    
                    -- Winner information
                    winner_program_number INTEGER,
                    winner_horse_name VARCHAR(255) NOT NULL,
                    winner_jockey VARCHAR(255),
                    winner_trainer VARCHAR(255),
                    winner_odds VARCHAR(20),
                    
                    -- Payouts
                    win_payout DECIMAL(10,2),
                    exacta_combination VARCHAR(20),
                    exacta_payout DECIMAL(10,2),
                    trifecta_combination VARCHAR(30),
                    trifecta_payout DECIMAL(10,2),
                    
                    -- Metadata
                    api_race_id VARCHAR(50),
                    data_pulled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    UNIQUE(race_date, track_name, race_number)
                )
            ''')
            
            # Create live_odds_snapshot table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS live_odds_snapshot (
                    id SERIAL PRIMARY KEY,
                    race_date DATE NOT NULL,
                    track_name VARCHAR(100) NOT NULL,
                    race_number INTEGER NOT NULL,
                    post_time TIMESTAMP,
                    minutes_to_post INTEGER,
                    
                    -- Horse data
                    program_number INTEGER NOT NULL,
                    horse_name VARCHAR(255) NOT NULL,
                    jockey VARCHAR(255),
                    trainer VARCHAR(255),
                    morning_line VARCHAR(20),
                    
                    -- Live odds at time of snapshot
                    live_odds VARCHAR(20),
                    live_odds_decimal DECIMAL(10,2),
                    win_pool_percentage DECIMAL(5,2),
                    
                    -- Our calculations
                    win_probability DECIMAL(5,2),
                    adj_odds DECIMAL(5,2),
                    value_flag BOOLEAN DEFAULT FALSE,
                    
                    -- Metadata
                    api_race_id VARCHAR(50),
                    snapshot_taken_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    UNIQUE(race_date, track_name, race_number, program_number, snapshot_taken_at)
                )
            ''')
            
            # Create race_schedule table for tracking post times
            cur.execute('''
                CREATE TABLE IF NOT EXISTS race_schedule (
                    id SERIAL PRIMARY KEY,
                    race_date DATE NOT NULL,
                    track_name VARCHAR(100) NOT NULL,
                    race_number INTEGER NOT NULL,
                    scheduled_post_time TIMESTAMP NOT NULL,
                    api_race_id VARCHAR(50),
                    data_pull_scheduled BOOLEAN DEFAULT FALSE,
                    data_pull_completed BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    UNIQUE(race_date, track_name, race_number)
                )
            ''')
            
            # Add indexes for performance
            cur.execute('CREATE INDEX IF NOT EXISTS idx_race_results_date ON race_results(race_date)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_live_odds_date ON live_odds_snapshot(race_date)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_race_schedule_post ON race_schedule(scheduled_post_time)')
            
            conn.commit()
            logger.info("Enhanced database schema created successfully")
            
        except Exception as e:
            logger.error(f"Error creating database schema: {e}")
            conn.rollback()
        finally:
            cur.close()
            conn.close()
    
    def pull_race_data(self, track_name, race_date, race_number, api_race_id, current_race_id=None):
        """
        Pull both previous race results and current race live odds
        """
        logger.info(f"Pulling data for {track_name} Race {race_number} on {race_date}")
        
        results = {
            'previous_race_results': None,
            'live_odds': None,
            'quota_remaining': None,
            'errors': []
        }
        
        # Pull previous race results if race_number > 1
        if race_number > 1 and api_race_id:
            try:
                prev_race_data = self.odds_service.get_race_odds(api_race_id)
                if 'data' in prev_race_data:
                    self.save_race_results(prev_race_data['data'], track_name, race_date, race_number - 1)
                    results['previous_race_results'] = 'Saved'
                results['quota_remaining'] = prev_race_data.get('remaining_quota')
            except Exception as e:
                logger.error(f"Error pulling previous race results: {e}")
                results['errors'].append(str(e))
        
        # Pull current race live odds if we have the race ID
        if current_race_id:
            try:
                live_data = self.odds_service.get_race_odds(current_race_id)
                if 'data' in live_data:
                    self.save_live_odds_snapshot(live_data['data'], track_name, race_date, race_number)
                    results['live_odds'] = 'Saved'
                results['quota_remaining'] = live_data.get('remaining_quota')
            except Exception as e:
                logger.error(f"Error pulling live odds: {e}")
                results['errors'].append(str(e))
        
        return results
    
    def save_race_results(self, race_data, track_name, race_date, race_number):
        """
        Save race results to database
        """
        if not race_data or not race_data.get('finished'):
            return
        
        conn = psycopg2.connect(self.db_url)
        cur = conn.cursor()
        
        try:
            # Find the winner (position = 1)
            winner = None
            for horse in race_data.get('horses', []):
                if horse.get('position') == '1':
                    winner = horse
                    break
            
            if winner:
                cur.execute('''
                    INSERT INTO race_results (
                        race_date, track_name, race_number,
                        distance, surface, race_type,
                        winner_program_number, winner_horse_name,
                        winner_jockey, winner_trainer, winner_odds,
                        api_race_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (race_date, track_name, race_number) 
                    DO UPDATE SET
                        winner_horse_name = EXCLUDED.winner_horse_name,
                        winner_odds = EXCLUDED.winner_odds,
                        data_pulled_at = CURRENT_TIMESTAMP
                ''', (
                    race_date, track_name, race_number,
                    race_data.get('distance'), 'Dirt', None,
                    winner.get('program_number'), winner.get('horse_name'),
                    winner.get('jockey'), winner.get('trainer'),
                    winner.get('real_time_odds') or winner.get('sp'),
                    race_data.get('race_id')
                ))
                
                conn.commit()
                logger.info(f"Saved results for {track_name} Race {race_number}")
                
        except Exception as e:
            logger.error(f"Error saving race results: {e}")
            conn.rollback()
        finally:
            cur.close()
            conn.close()
    
    def save_live_odds_snapshot(self, race_data, track_name, race_date, race_number):
        """
        Save live odds snapshot to database
        """
        conn = psycopg2.connect(self.db_url)
        cur = conn.cursor()
        
        try:
            for horse in race_data.get('horses', []):
                if horse.get('non_runner') == '1':
                    continue
                
                # Convert odds to decimal if possible
                live_odds = horse.get('real_time_odds')
                decimal_odds = self.convert_odds_to_decimal(live_odds)
                
                # Calculate win probability from odds
                win_prob = None
                if decimal_odds:
                    win_prob = (1 / (decimal_odds + 1)) * 100
                
                cur.execute('''
                    INSERT INTO live_odds_snapshot (
                        race_date, track_name, race_number,
                        minutes_to_post, program_number, horse_name,
                        jockey, trainer, morning_line,
                        live_odds, live_odds_decimal, win_probability,
                        api_race_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    race_date, track_name, race_number,
                    10,  # 10 minutes to post
                    horse.get('program_number'), horse.get('horse_name'),
                    horse.get('jockey'), horse.get('trainer'),
                    horse.get('morning_line_odds'),
                    live_odds, decimal_odds, win_prob,
                    race_data.get('race_id')
                ))
            
            conn.commit()
            logger.info(f"Saved live odds snapshot for {track_name} Race {race_number}")
            
        except Exception as e:
            logger.error(f"Error saving live odds: {e}")
            conn.rollback()
        finally:
            cur.close()
            conn.close()
    
    def convert_odds_to_decimal(self, odds_str):
        """
        Convert odds string (e.g., "5/2", "3-1") to decimal
        """
        if not odds_str:
            return None
        
        try:
            # Handle fractional odds like "5/2"
            if '/' in odds_str:
                num, den = odds_str.split('/')
                return float(num) / float(den)
            # Handle odds like "3-1"
            elif '-' in odds_str:
                num, den = odds_str.split('-')
                return float(num) / float(den)
            # Handle decimal odds
            else:
                return float(odds_str)
        except:
            return None
    
    def get_races_needing_data_pull(self, minutes_before=10):
        """
        Find races that need data pulled in the next X minutes
        """
        if not self.db_url:
            return []
        
        conn = psycopg2.connect(self.db_url)
        cur = conn.cursor()
        
        try:
            # Find races with post time in the next 10-15 minutes
            cur.execute('''
                SELECT race_date, track_name, race_number, 
                       scheduled_post_time, api_race_id
                FROM race_schedule
                WHERE scheduled_post_time BETWEEN %s AND %s
                  AND data_pull_completed = FALSE
                ORDER BY scheduled_post_time
            ''', (
                datetime.now(),
                datetime.now() + timedelta(minutes=minutes_before + 5)
            ))
            
            races = cur.fetchall()
            return races
            
        except Exception as e:
            logger.error(f"Error finding races: {e}")
            return []
        finally:
            cur.close()
            conn.close()
    
    def mark_race_completed(self, race_date, track_name, race_number):
        """
        Mark a race as having data pulled
        """
        conn = psycopg2.connect(self.db_url)
        cur = conn.cursor()
        
        try:
            cur.execute('''
                UPDATE race_schedule 
                SET data_pull_completed = TRUE
                WHERE race_date = %s 
                  AND track_name = %s 
                  AND race_number = %s
            ''', (race_date, track_name, race_number))
            
            conn.commit()
        except Exception as e:
            logger.error(f"Error marking race completed: {e}")
            conn.rollback()
        finally:
            cur.close()
            conn.close()


# Scheduler function to be called by cron or scheduler
def run_scheduled_pull():
    """
    Run the scheduled data pull for races starting soon
    """
    puller = RaceDataPuller()
    
    # Check quota first
    status = puller.odds_service.get_quota_status()
    if status['remaining'] < 2:
        logger.warning(f"Low API quota: {status['remaining']} calls remaining")
        return
    
    # Get races needing data
    races = puller.get_races_needing_data_pull(minutes_before=10)
    
    for race in races:
        race_date, track_name, race_number, post_time, api_race_id = race
        
        logger.info(f"Processing {track_name} Race {race_number} (post: {post_time})")
        
        # Pull the data
        results = puller.pull_race_data(
            track_name=track_name,
            race_date=race_date,
            race_number=race_number,
            api_race_id=api_race_id,  # Previous race ID
            current_race_id=None  # Would need current race ID from API
        )
        
        # Mark as completed
        puller.mark_race_completed(race_date, track_name, race_number)
        
        logger.info(f"Results: {results}")
        
        # Check remaining quota
        if results.get('quota_remaining', 0) < 2:
            logger.warning("Stopping due to low quota")
            break


if __name__ == "__main__":
    # Test the system
    puller = RaceDataPuller()
    
    # Example: Pull data for a specific race
    results = puller.pull_race_data(
        track_name="Fair Meadows",
        race_date="2025-06-12",
        race_number=2,
        api_race_id="39302",  # Example from earlier
        current_race_id=None  # Would need to find current race ID
    )
    
    print(f"Pull results: {results}")