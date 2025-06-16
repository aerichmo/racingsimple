import psycopg2
from psycopg2 import sql
import json
from datetime import datetime
import logging
from typing import Dict, List, Optional
import os
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HorseAPIOddsDB:
    """Database integration for storing HorseAPI odds data"""
    
    def __init__(self):
        self.db_url = Config.DATABASE_URL
        if not self.db_url:
            raise ValueError("DATABASE_URL not found. Please set DATABASE_URL environment variable.")
        
    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.db_url)
    
    def create_odds_tables(self):
        """Create tables for storing odds data if they don't exist"""
        create_tables_sql = """
        -- Add column to races table if not exists
        ALTER TABLE races ADD COLUMN IF NOT EXISTS horse_api_race_id VARCHAR(50);
        ALTER TABLE races ADD COLUMN IF NOT EXISTS post_time TIMESTAMP;
        ALTER TABLE races ADD COLUMN IF NOT EXISTS odds_monitoring_enabled BOOLEAN DEFAULT FALSE;
        
        -- Create odds snapshots table
        CREATE TABLE IF NOT EXISTS odds_snapshots (
            id SERIAL PRIMARY KEY,
            race_id INTEGER REFERENCES races(id),
            horse_api_race_id VARCHAR(50),
            snapshot_time TIMESTAMP NOT NULL,
            interval_name VARCHAR(20) NOT NULL, -- '10min_before', '5min_before', etc
            odds_data JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Create index for faster lookups
        CREATE INDEX IF NOT EXISTS idx_odds_race_interval 
        ON odds_snapshots(race_id, interval_name);
        
        CREATE INDEX IF NOT EXISTS idx_odds_horse_api_race 
        ON odds_snapshots(horse_api_race_id);
        
        -- Create odds history view for easy querying
        CREATE OR REPLACE VIEW odds_movement AS
        SELECT 
            os.race_id,
            os.horse_api_race_id,
            os.interval_name,
            os.snapshot_time,
            r.race_number,
            r.race_name,
            r.track,
            jsonb_array_elements(os.odds_data->'horses') as horse_odds
        FROM odds_snapshots os
        JOIN races r ON os.race_id = r.id
        ORDER BY os.race_id, os.snapshot_time;
        """
        
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            cur.execute(create_tables_sql)
            conn.commit()
            logger.info("Odds tables created/verified successfully")
        except Exception as e:
            logger.error(f"Error creating tables: {str(e)}")
            if conn:
                conn.rollback()
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()
    
    def save_odds_snapshot(self, race_id: int, horse_api_race_id: str, 
                          interval_name: str, odds_data: Dict) -> bool:
        """Save an odds snapshot to the database"""
        insert_sql = """
        INSERT INTO odds_snapshots 
        (race_id, horse_api_race_id, snapshot_time, interval_name, odds_data)
        VALUES (%s, %s, %s, %s, %s)
        """
        
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            cur.execute(insert_sql, (
                race_id,
                horse_api_race_id,
                datetime.now(),
                interval_name,
                json.dumps(odds_data)
            ))
            
            conn.commit()
            logger.info(f"Saved {interval_name} odds for race {race_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving odds snapshot: {str(e)}")
            if conn:
                conn.rollback()
            return False
            
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()
    
    def get_races_for_monitoring(self) -> List[Dict]:
        """Get races that need odds monitoring"""
        query = """
        SELECT 
            id, 
            horse_api_race_id, 
            post_time,
            race_number,
            race_name,
            track
        FROM races
        WHERE 
            odds_monitoring_enabled = TRUE
            AND horse_api_race_id IS NOT NULL
            AND post_time IS NOT NULL
            AND post_time > NOW()
            AND post_time < NOW() + INTERVAL '3 hours'
        ORDER BY post_time
        """
        
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            cur.execute(query)
            
            races = []
            for row in cur.fetchall():
                races.append({
                    'id': row[0],
                    'horse_api_race_id': row[1],
                    'post_time': row[2],
                    'race_number': row[3],
                    'race_name': row[4],
                    'track': row[5]
                })
            
            return races
            
        except Exception as e:
            logger.error(f"Error fetching races for monitoring: {str(e)}")
            return []
            
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()
    
    def get_odds_history(self, race_id: int) -> Dict[str, Dict]:
        """Get all odds snapshots for a race"""
        query = """
        SELECT 
            interval_name,
            snapshot_time,
            odds_data
        FROM odds_snapshots
        WHERE race_id = %s
        ORDER BY 
            CASE interval_name
                WHEN '10min_before' THEN 1
                WHEN '5min_before' THEN 2
                WHEN '2min_before' THEN 3
                WHEN '1min_before' THEN 4
                WHEN 'at_post' THEN 5
            END
        """
        
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            cur.execute(query, (race_id,))
            
            history = {}
            for row in cur.fetchall():
                history[row[0]] = {
                    'snapshot_time': row[1].isoformat(),
                    'odds_data': row[2]
                }
            
            return history
            
        except Exception as e:
            logger.error(f"Error fetching odds history: {str(e)}")
            return {}
            
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()
    
    def get_odds_movement_analysis(self, race_id: int) -> List[Dict]:
        """Analyze odds movement for each horse in a race"""
        query = """
        WITH odds_by_interval AS (
            SELECT 
                (horse_odds->>'horse_name') as horse_name,
                (horse_odds->>'horse_number') as horse_number,
                interval_name,
                CAST(horse_odds->>'win_odds' AS FLOAT) as win_odds,
                snapshot_time
            FROM odds_movement
            WHERE race_id = %s
        ),
        odds_comparison AS (
            SELECT 
                horse_name,
                horse_number,
                MAX(CASE WHEN interval_name = '10min_before' THEN win_odds END) as odds_10min,
                MAX(CASE WHEN interval_name = '5min_before' THEN win_odds END) as odds_5min,
                MAX(CASE WHEN interval_name = '2min_before' THEN win_odds END) as odds_2min,
                MAX(CASE WHEN interval_name = '1min_before' THEN win_odds END) as odds_1min,
                MAX(CASE WHEN interval_name = 'at_post' THEN win_odds END) as odds_at_post
            FROM odds_by_interval
            GROUP BY horse_name, horse_number
        )
        SELECT 
            *,
            CASE 
                WHEN odds_at_post IS NOT NULL AND odds_10min IS NOT NULL 
                THEN ROUND(((odds_at_post - odds_10min) / odds_10min * 100)::numeric, 2)
                ELSE NULL 
            END as total_change_pct
        FROM odds_comparison
        ORDER BY horse_number::int
        """
        
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            cur.execute(query, (race_id,))
            
            movements = []
            columns = [desc[0] for desc in cur.description]
            
            for row in cur.fetchall():
                movements.append(dict(zip(columns, row)))
            
            return movements
            
        except Exception as e:
            logger.error(f"Error analyzing odds movement: {str(e)}")
            return []
            
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()
    
    def enable_race_monitoring(self, race_id: int, horse_api_race_id: str, 
                              post_time: datetime) -> bool:
        """Enable odds monitoring for a race"""
        update_sql = """
        UPDATE races 
        SET 
            horse_api_race_id = %s,
            post_time = %s,
            odds_monitoring_enabled = TRUE
        WHERE id = %s
        """
        
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            cur.execute(update_sql, (horse_api_race_id, post_time, race_id))
            conn.commit()
            
            logger.info(f"Enabled monitoring for race {race_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error enabling race monitoring: {str(e)}")
            if conn:
                conn.rollback()
            return False
            
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()


# Example usage
if __name__ == "__main__":
    db = HorseAPIOddsDB()
    
    # Create tables
    db.create_odds_tables()
    
    # Get races to monitor
    races = db.get_races_for_monitoring()
    print(f"Found {len(races)} races to monitor")
    
    # Example: Save odds snapshot
    # db.save_odds_snapshot(
    #     race_id=1,
    #     horse_api_race_id="ABC123",
    #     interval_name="10min_before",
    #     odds_data={"horses": [...]}
    # )