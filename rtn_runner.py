#!/usr/bin/env python3
"""
RTN Runner - Main script to run RTN capture for Fair Meadows
Integrates with existing STALL10N database and systems
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
import psycopg2
from rtn_capture import RTNCapture
from rtn_odds_parser import RTNOddsParser
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RTNRunner:
    def __init__(self):
        self.db_conn = None
        self.capture = None
        self.parser = RTNOddsParser()
        self.setup_database()
        
    def setup_database(self):
        """Connect to PostgreSQL database"""
        try:
            db_url = Config.get_database_url()
            self.db_conn = psycopg2.connect(db_url)
            logger.info("Connected to database")
            
            # Create RTN-specific tables if needed
            self._create_tables()
            
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            sys.exit(1)
    
    def _create_tables(self):
        """Create RTN capture tables if they don't exist"""
        cursor = self.db_conn.cursor()
        
        # RTN capture sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rtn_capture_sessions (
                id SERIAL PRIMARY KEY,
                track_name VARCHAR(100),
                session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                session_end TIMESTAMP,
                status VARCHAR(50) DEFAULT 'active'
            )
        """)
        
        # RTN odds snapshots table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rtn_odds_snapshots (
                id SERIAL PRIMARY KEY,
                session_id INTEGER REFERENCES rtn_capture_sessions(id),
                race_date DATE,
                race_number INTEGER,
                program_number INTEGER,
                horse_name VARCHAR(100),
                odds VARCHAR(20),
                confidence INTEGER,
                snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(race_date, race_number, program_number, snapshot_time)
            )
        """)
        
        # RTN pool data table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rtn_pool_data (
                id SERIAL PRIMARY KEY,
                session_id INTEGER REFERENCES rtn_capture_sessions(id),
                race_date DATE,
                race_number INTEGER,
                pool_type VARCHAR(20),
                amount INTEGER,
                snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.db_conn.commit()
        logger.info("Database tables ready")
    
    def start_capture_session(self, track_name="Fair Meadows"):
        """Start a new RTN capture session"""
        cursor = self.db_conn.cursor()
        
        # Create session record
        cursor.execute("""
            INSERT INTO rtn_capture_sessions (track_name, session_start)
            VALUES (%s, %s)
            RETURNING id
        """, (track_name, datetime.now()))
        
        session_id = cursor.fetchone()[0]
        self.db_conn.commit()
        
        logger.info(f"Started capture session {session_id} for {track_name}")
        return session_id
    
    def save_odds_snapshot(self, session_id, race_date, race_number, odds_data):
        """Save odds snapshot to database"""
        cursor = self.db_conn.cursor()
        
        for horse in odds_data:
            try:
                cursor.execute("""
                    INSERT INTO rtn_odds_snapshots 
                    (session_id, race_date, race_number, program_number, 
                     horse_name, odds, confidence, snapshot_time)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (race_date, race_number, program_number, snapshot_time) 
                    DO UPDATE SET odds = EXCLUDED.odds, confidence = EXCLUDED.confidence
                """, (
                    session_id,
                    race_date,
                    race_number,
                    horse['program_number'],
                    horse['horse_name'],
                    horse['odds'],
                    horse.get('confidence', 90),
                    datetime.now()
                ))
            except Exception as e:
                logger.error(f"Error saving odds for horse {horse}: {e}")
        
        self.db_conn.commit()
        logger.info(f"Saved {len(odds_data)} odds entries for Race {race_number}")
    
    def save_pool_data(self, session_id, race_date, race_number, pool_data):
        """Save pool information to database"""
        cursor = self.db_conn.cursor()
        
        for pool_type, amount in pool_data.items():
            cursor.execute("""
                INSERT INTO rtn_pool_data 
                (session_id, race_date, race_number, pool_type, amount, snapshot_time)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                session_id,
                race_date,
                race_number,
                pool_type,
                amount,
                datetime.now()
            ))
        
        self.db_conn.commit()
        logger.info(f"Saved pool data for Race {race_number}")
    
    def run_fair_meadows_capture(self, username, password, duration_hours=3):
        """Main capture routine for Fair Meadows"""
        session_id = self.start_capture_session("Fair Meadows")
        
        try:
            # Initialize capture
            self.capture = RTNCapture(username, password)
            self.capture.setup_browser()
            
            # Login to RTN
            if not self.capture.login_to_rtn():
                raise Exception("Failed to login to RTN")
            
            # Navigate to Fair Meadows
            if not self.capture.navigate_to_track("Fair Meadows"):
                raise Exception("Failed to navigate to Fair Meadows")
            
            # Get today's date for race tracking
            race_date = datetime.now().date()
            
            # Monitor races
            end_time = datetime.now() + timedelta(hours=duration_hours)
            race_number = 1
            
            while datetime.now() < end_time:
                logger.info(f"Monitoring Race {race_number}")
                
                # Capture race header info
                race_info_img = self.capture.capture_screen_region('race_info')
                if race_info_img is not None:
                    race_info = self.parser.parse_race_info(race_info_img)
                    if 'race_number' in race_info:
                        race_number = race_info['race_number']
                
                # Capture odds multiple times before race
                for i in range(10):  # 10 captures, 1 minute apart
                    # Capture odds board
                    odds_img = self.capture.capture_screen_region('odds_board')
                    if odds_img is not None:
                        odds_data = self.parser.parse_odds_board(odds_img)
                        if odds_data:
                            self.save_odds_snapshot(session_id, race_date, race_number, odds_data)
                    
                    # Capture tote board
                    tote_img = self.capture.capture_screen_region('tote_board')
                    if tote_img is not None:
                        pool_data = self.parser.parse_tote_board(tote_img)
                        if pool_data:
                            self.save_pool_data(session_id, race_date, race_number, pool_data)
                    
                    # Wait 1 minute between captures
                    time.sleep(60)
                
                # Move to next race
                race_number += 1
                
                # Wait for next race (adjust based on typical race intervals)
                logger.info("Waiting for next race...")
                time.sleep(600)  # 10 minutes
            
        except Exception as e:
            logger.error(f"Capture error: {e}")
        
        finally:
            # End session
            self.end_capture_session(session_id)
            if self.capture:
                self.capture.cleanup()
    
    def end_capture_session(self, session_id):
        """End capture session"""
        cursor = self.db_conn.cursor()
        cursor.execute("""
            UPDATE rtn_capture_sessions 
            SET session_end = %s, status = 'completed'
            WHERE id = %s
        """, (datetime.now(), session_id))
        self.db_conn.commit()
        logger.info(f"Ended capture session {session_id}")
    
    def get_latest_odds(self, race_date, race_number):
        """Get latest odds for a race"""
        cursor = self.db_conn.cursor()
        cursor.execute("""
            SELECT DISTINCT ON (program_number)
                program_number, horse_name, odds, confidence, snapshot_time
            FROM rtn_odds_snapshots
            WHERE race_date = %s AND race_number = %s
            ORDER BY program_number, snapshot_time DESC
        """, (race_date, race_number))
        
        return cursor.fetchall()


def main():
    """Main entry point"""
    # Get RTN credentials from environment or config
    username = os.getenv('RTN_USERNAME')
    password = os.getenv('RTN_PASSWORD')
    
    if not username or not password:
        logger.error("RTN credentials not found. Set RTN_USERNAME and RTN_PASSWORD environment variables.")
        sys.exit(1)
    
    runner = RTNRunner()
    
    try:
        # Run capture for 3 hours (typical race card duration)
        runner.run_fair_meadows_capture(username, password, duration_hours=3)
        
    except KeyboardInterrupt:
        logger.info("Capture interrupted by user")
    
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    
    finally:
        if runner.db_conn:
            runner.db_conn.close()


if __name__ == "__main__":
    main()