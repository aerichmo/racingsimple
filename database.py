"""Simplified database operations for betting analysis"""
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from typing import Dict, List
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, connection_string):
        self.connection_string = connection_string
        
    @contextmanager
    def get_connection(self):
        """Get a database connection with automatic cleanup"""
        conn = None
        try:
            conn = psycopg2.connect(self.connection_string)
            yield conn
        finally:
            if conn:
                conn.close()
                
    def create_session(self) -> int:
        """Create a new session and return its ID"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO sessions DEFAULT VALUES RETURNING id")
                session_id = cur.fetchone()[0]
                conn.commit()
                return session_id
                
    def save_race_data(self, session_id: int, races: List[Dict]):
        """Save race data with only essential fields"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                for race in races:
                    # Save race
                    cur.execute(
                        "INSERT INTO races (session_id, race_number) VALUES (%s, %s) RETURNING id",
                        (session_id, race.get('race_number', 0))
                    )
                    race_id = cur.fetchone()[0]
                    
                    # Save entries
                    for entry in race.get('entries', []):
                        cur.execute("""
                            INSERT INTO race_entries (race_id, horse_name, win_probability, ml_odds)
                            VALUES (%s, %s, %s, %s)
                        """, (
                            race_id,
                            entry.get('horse_name', 'Unknown'),
                            entry.get('win_probability', 0),
                            entry.get('ml_odds', 'N/A')
                        ))
                
                conn.commit()
                
    def get_session_data(self, session_id: int) -> List[Dict]:
        """Get all races and entries for a session"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        r.race_number,
                        e.horse_name,
                        e.win_probability,
                        e.ml_odds
                    FROM races r
                    JOIN race_entries e ON e.race_id = r.id
                    WHERE r.session_id = %s
                    ORDER BY r.race_number, e.win_probability DESC
                """, (session_id,))
                
                return [dict(row) for row in cur.fetchall()]