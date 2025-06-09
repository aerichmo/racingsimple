"""Database operations for betting analysis"""
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from typing import Dict, List, Optional
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
                
    def create_analysis_session(self, bankroll: float = 1000) -> int:
        """Create a new analysis session and return its ID"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO analysis_sessions (bankroll)
                    VALUES (%s)
                    RETURNING id
                """, (bankroll,))
                session_id = cur.fetchone()[0]
                conn.commit()
                return session_id
                
    def save_race(self, session_id: int, race_data: Dict) -> int:
        """Save race data and return race ID"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO races (
                        session_id, race_number, post_time, track_name,
                        distance, dist_unit, surface, purse, class_rating,
                        image_path, total_probability, favorite_probability,
                        avg_edge, max_edge, positive_edges, field_size,
                        competitiveness
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s
                    ) RETURNING id
                """, (
                    session_id,
                    race_data.get('race_number'),
                    race_data.get('post_time'),
                    race_data.get('track_name', 'Unknown'),
                    race_data.get('distance'),
                    race_data.get('dist_unit', 'F'),
                    race_data.get('surface', 'D'),
                    race_data.get('purse'),
                    race_data.get('class_rating'),
                    race_data.get('image_path'),
                    race_data.get('total_probability'),
                    race_data.get('favorite_probability'),
                    race_data.get('avg_edge'),
                    race_data.get('max_edge'),
                    race_data.get('positive_edges'),
                    race_data.get('field_size'),
                    race_data.get('competitiveness')
                ))
                race_id = cur.fetchone()[0]
                conn.commit()
                return race_id
                
    def save_entries(self, race_id: int, entries: List[Dict]) -> List[int]:
        """Save race entries and return their IDs"""
        entry_ids = []
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                for entry in entries:
                    cur.execute("""
                        INSERT INTO race_entries (
                            race_id, program_number, horse_name,
                            win_probability, ml_odds, decimal_odds,
                            implied_probability, edge, expected_value,
                            angles_matched, value_rating
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        ) RETURNING id
                    """, (
                        race_id,
                        entry.get('program_number'),
                        entry.get('horse_name'),
                        entry.get('win_probability', 0) * 100,  # Store as percentage
                        entry.get('ml_odds'),
                        entry.get('decimal_odds'),
                        entry.get('implied_probability', 0) * 100,
                        entry.get('edge', 0) * 100,
                        entry.get('expected_value', 0) * 100,
                        entry.get('angles_matched', 0),
                        entry.get('value_rating', 0)
                    ))
                    entry_id = cur.fetchone()[0]
                    entry_ids.append(entry_id)
                conn.commit()
        return entry_ids
        
    def save_recommendations(self, race_id: int, recommendations: List[Dict]):
        """Save betting recommendations"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # First get entry IDs for the recommendations
                for rec in recommendations:
                    cur.execute("""
                        SELECT id FROM race_entries 
                        WHERE race_id = %s AND program_number = %s
                    """, (race_id, rec.get('program_number')))
                    result = cur.fetchone()
                    if result:
                        entry_id = result[0]
                        cur.execute("""
                            INSERT INTO betting_recommendations (
                                race_id, entry_id, bet_type, stake,
                                expected_return, confidence_score
                            ) VALUES (%s, %s, %s, %s, %s, %s)
                        """, (
                            race_id,
                            entry_id,
                            rec.get('type', 'win'),
                            rec.get('stake', 0),
                            rec.get('expected_value', 0),
                            rec.get('value_rating', 0)
                        ))
                conn.commit()
                
    def update_session_summary(self, session_id: int, summary: Dict):
        """Update session summary statistics"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE analysis_sessions
                    SET total_races = %s,
                        total_bets = %s,
                        total_stake = %s,
                        expected_value = %s,
                        expected_roi = %s,
                        risk_score = %s
                    WHERE id = %s
                """, (
                    summary.get('total_races', 0),
                    summary.get('total_bets', 0),
                    summary.get('total_stake', 0),
                    summary.get('expected_value', 0),
                    summary.get('expected_roi', 0),
                    summary.get('risk_score', 0),
                    session_id
                ))
                conn.commit()
                
    def get_session_analysis(self, session_id: int) -> Dict:
        """Get complete analysis for a session"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get session info
                cur.execute("""
                    SELECT * FROM analysis_sessions WHERE id = %s
                """, (session_id,))
                session = cur.fetchone()
                
                if not session:
                    return {}
                
                # Get recommendations
                cur.execute("""
                    SELECT * FROM betting_summary
                    WHERE session_id = %s
                    ORDER BY race_number, value_rating DESC
                """, (session_id,))
                recommendations = cur.fetchall()
                
                return {
                    'session': dict(session),
                    'recommendations': [dict(r) for r in recommendations]
                }
                
    def get_recent_sessions(self, limit: int = 10) -> List[Dict]:
        """Get recent analysis sessions"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM analysis_sessions
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (limit,))
                return [dict(row) for row in cur.fetchall()]