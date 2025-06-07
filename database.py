import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_url: str = None):
        self.db_url = db_url or os.environ.get('DATABASE_URL')
        if not self.db_url:
            raise ValueError("Database URL not provided")
    
    @contextmanager
    def get_cursor(self, dict_cursor=False):
        """Context manager for database connections"""
        conn = psycopg2.connect(self.db_url)
        try:
            cursor_factory = RealDictCursor if dict_cursor else None
            cur = conn.cursor(cursor_factory=cursor_factory)
            yield cur
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            cur.close()
            conn.close()
    
    def create_tables(self):
        """Create database tables if they don't exist"""
        with self.get_cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS races (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL,
                    race_number INTEGER NOT NULL,
                    track_name VARCHAR(100),
                    post_time TIME,
                    purse VARCHAR(50),
                    distance VARCHAR(50),
                    surface VARCHAR(20),
                    race_type VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date, race_number, track_name)
                );
                
                CREATE TABLE IF NOT EXISTS horses (
                    id SERIAL PRIMARY KEY,
                    race_id INTEGER REFERENCES races(id) ON DELETE CASCADE,
                    program_number VARCHAR(10),
                    horse_name VARCHAR(100) NOT NULL,
                    jockey VARCHAR(100),
                    trainer VARCHAR(100),
                    morning_line_odds VARCHAR(20),
                    weight VARCHAR(20),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS odds_history (
                    id SERIAL PRIMARY KEY,
                    race_id INTEGER REFERENCES races(id) ON DELETE CASCADE,
                    horse_id INTEGER REFERENCES horses(id) ON DELETE CASCADE,
                    odds_type VARCHAR(20) NOT NULL,
                    odds_value VARCHAR(20),
                    captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    minutes_to_post INTEGER
                );
                
                CREATE INDEX IF NOT EXISTS idx_races_date ON races(date);
                CREATE INDEX IF NOT EXISTS idx_horses_race_id ON horses(race_id);
                CREATE INDEX IF NOT EXISTS idx_odds_history_race_id ON odds_history(race_id);
                CREATE INDEX IF NOT EXISTS idx_odds_history_captured_at ON odds_history(captured_at);
            """)
            logger.info("Database tables created successfully")
    
    def get_races_by_date(self, date):
        """Get all races for a specific date"""
        with self.get_cursor(dict_cursor=True) as cur:
            cur.execute("""
                SELECT r.*, 
                    array_agg(
                        json_build_object(
                            'program_number', h.program_number,
                            'horse_name', h.horse_name,
                            'jockey', h.jockey,
                            'trainer', h.trainer,
                            'morning_line_odds', h.morning_line_odds,
                            'weight', h.weight
                        ) ORDER BY h.program_number
                    ) as horses
                FROM races r
                LEFT JOIN horses h ON h.race_id = r.id
                WHERE r.date = %s
                GROUP BY r.id
                ORDER BY r.race_number
            """, (date,))
            return cur.fetchall()
    
    def get_track_statistics(self):
        """Get statistics by track"""
        with self.get_cursor(dict_cursor=True) as cur:
            cur.execute("""
                SELECT 
                    track_name,
                    COUNT(DISTINCT date) as racing_days,
                    COUNT(*) as total_races,
                    COUNT(DISTINCT h.horse_name) as unique_horses,
                    AVG(CAST(NULLIF(regexp_replace(purse, '[^0-9]', '', 'g'), '') AS INTEGER)) as avg_purse
                FROM races r
                JOIN horses h ON h.race_id = r.id
                GROUP BY track_name
                ORDER BY total_races DESC
            """)
            return cur.fetchall()
    
    def get_jockey_statistics(self):
        """Get statistics by jockey"""
        with self.get_cursor(dict_cursor=True) as cur:
            cur.execute("""
                SELECT 
                    h.jockey,
                    COUNT(*) as total_rides,
                    COUNT(DISTINCT r.date) as racing_days,
                    COUNT(DISTINCT h.horse_name) as unique_horses,
                    array_agg(DISTINCT r.track_name) as tracks
                FROM horses h
                JOIN races r ON r.id = h.race_id
                WHERE h.jockey IS NOT NULL AND h.jockey != ''
                GROUP BY h.jockey
                ORDER BY total_rides DESC
                LIMIT 50
            """)
            return cur.fetchall()
    
    def get_trainer_statistics(self):
        """Get statistics by trainer"""
        with self.get_cursor(dict_cursor=True) as cur:
            cur.execute("""
                SELECT 
                    h.trainer,
                    COUNT(*) as total_entries,
                    COUNT(DISTINCT r.date) as racing_days,
                    COUNT(DISTINCT h.horse_name) as unique_horses,
                    array_agg(DISTINCT r.track_name) as tracks
                FROM horses h
                JOIN races r ON r.id = h.race_id
                WHERE h.trainer IS NOT NULL AND h.trainer != ''
                GROUP BY h.trainer
                ORDER BY total_entries DESC
                LIMIT 50
            """)
            return cur.fetchall()
    
    def get_horse_history(self, horse_name):
        """Get racing history for a specific horse"""
        with self.get_cursor(dict_cursor=True) as cur:
            cur.execute("""
                SELECT 
                    r.date,
                    r.track_name,
                    r.race_number,
                    r.race_type,
                    r.distance,
                    r.surface,
                    r.purse,
                    h.program_number,
                    h.jockey,
                    h.trainer,
                    h.morning_line_odds,
                    h.weight
                FROM horses h
                JOIN races r ON r.id = h.race_id
                WHERE LOWER(h.horse_name) = LOWER(%s)
                ORDER BY r.date DESC
            """, (horse_name,))
            return cur.fetchall()


if __name__ == "__main__":
    # Test database connection and create tables
    db = Database()
    db.create_tables()
    print("Database initialized successfully")