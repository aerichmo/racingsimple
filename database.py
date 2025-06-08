"""Database connection and operations"""
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import os
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_url):
        self.db_url = db_url
        
    @contextmanager
    def get_cursor(self, dict_cursor=True):
        """Get database cursor with automatic cleanup"""
        conn = psycopg2.connect(self.db_url)
        try:
            cursor_factory = RealDictCursor if dict_cursor else None
            cur = conn.cursor(cursor_factory=cursor_factory)
            yield cur
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def create_tables(self):
        """Create database tables from schema"""
        with open('schema.sql', 'r') as f:
            schema = f.read()
        
        with self.get_cursor(dict_cursor=False) as cur:
            cur.execute(schema)
        logger.info("Database tables created successfully")
        
        # Run migrations
        self.run_migrations()
    
    def run_migrations(self):
        """Run database migrations"""
        try:
            with open('add_results.sql', 'r') as f:
                migration = f.read()
            
            with self.get_cursor(dict_cursor=False) as cur:
                cur.execute(migration)
            logger.info("Applied results migration successfully")
        except FileNotFoundError:
            logger.info("No migrations to run")
        except Exception as e:
            logger.warning(f"Migration may have already been applied: {e}")
    
    def save_race(self, race_data):
        """Save race and return race_id"""
        with self.get_cursor() as cur:
            cur.execute("""
                INSERT INTO races (date, race_number, track_name, distance, 
                                 race_type, purse, post_time, surface, pdf_filename)
                VALUES (%(date)s, %(race_number)s, %(track_name)s, %(distance)s,
                       %(race_type)s, %(purse)s, %(post_time)s, %(surface)s, %(pdf_filename)s)
                ON CONFLICT (date, race_number, track_name) 
                DO UPDATE SET 
                    distance = EXCLUDED.distance,
                    race_type = EXCLUDED.race_type,
                    purse = EXCLUDED.purse,
                    post_time = EXCLUDED.post_time
                RETURNING id
            """, race_data)
            return cur.fetchone()['id']
    
    def save_entry(self, entry_data):
        """Save race entry and return entry_id"""
        with self.get_cursor() as cur:
            cur.execute("""
                INSERT INTO entries (race_id, program_number, post_position, horse_name,
                                   jockey, trainer, win_pct, class_rating, last_speed,
                                   avg_speed, best_speed, jockey_win_pct, trainer_win_pct,
                                   jt_combo_pct)
                VALUES (%(race_id)s, %(program_number)s, %(post_position)s, %(horse_name)s,
                       %(jockey)s, %(trainer)s, %(win_pct)s, %(class_rating)s, %(last_speed)s,
                       %(avg_speed)s, %(best_speed)s, %(jockey_win_pct)s, %(trainer_win_pct)s,
                       %(jt_combo_pct)s)
                ON CONFLICT (race_id, program_number)
                DO UPDATE SET
                    horse_name = EXCLUDED.horse_name,
                    jockey = EXCLUDED.jockey,
                    trainer = EXCLUDED.trainer,
                    win_pct = EXCLUDED.win_pct,
                    class_rating = EXCLUDED.class_rating,
                    last_speed = EXCLUDED.last_speed,
                    avg_speed = EXCLUDED.avg_speed,
                    best_speed = EXCLUDED.best_speed
                RETURNING id
            """, entry_data)
            return cur.fetchone()['id']
    
    def save_analysis(self, analysis_data):
        """Save analysis results"""
        with self.get_cursor() as cur:
            cur.execute("""
                INSERT INTO analysis (entry_id, speed_score, class_score, jockey_score,
                                    trainer_score, overall_score, recommendation, confidence)
                VALUES (%(entry_id)s, %(speed_score)s, %(class_score)s, %(jockey_score)s,
                       %(trainer_score)s, %(overall_score)s, %(recommendation)s, %(confidence)s)
            """, analysis_data)
    
    def get_races_by_date(self, date):
        """Get all races for a specific date"""
        with self.get_cursor() as cur:
            cur.execute("""
                SELECT r.*, COUNT(e.id) as horse_count
                FROM races r
                LEFT JOIN entries e ON e.race_id = r.id
                WHERE r.date = %s
                GROUP BY r.id
                ORDER BY r.race_number
            """, (date,))
            return cur.fetchall()
    
    def get_race_entries(self, race_id):
        """Get all entries for a race with analysis"""
        with self.get_cursor() as cur:
            cur.execute("""
                SELECT e.*, a.overall_score, a.recommendation, a.confidence
                FROM entries e
                LEFT JOIN analysis a ON a.entry_id = e.id
                WHERE e.race_id = %s
                ORDER BY a.overall_score DESC NULLS LAST, e.program_number
            """, (race_id,))
            return cur.fetchall()
    
    def get_top_plays(self, date=None):
        """Get top recommended plays"""
        with self.get_cursor() as cur:
            query = """
                SELECT r.date as race_date, r.race_number, r.track_name, r.post_time,
                       e.program_number, e.horse_name, e.jockey, e.trainer,
                       a.overall_score, a.recommendation, a.confidence
                FROM analysis a
                JOIN entries e ON e.id = a.entry_id
                JOIN races r ON r.id = e.race_id
                WHERE a.overall_score >= 70
            """
            if date:
                query += " AND r.date = %s"
                cur.execute(query + " ORDER BY a.overall_score DESC", (date,))
            else:
                cur.execute(query + " ORDER BY r.date DESC, a.overall_score DESC LIMIT 20")
            return cur.fetchall()
    
    def save_race_results(self, race_id, results):
        """Save race results for a specific race"""
        with self.get_cursor() as cur:
            for result in results:
                # Try to match by program number first, then by horse name
                if result.get('program_number'):
                    cur.execute("""
                        UPDATE entries 
                        SET finish_position = %(finish_position)s,
                            final_odds = %(final_odds)s,
                            win_payoff = %(win_payoff)s,
                            place_payoff = %(place_payoff)s,
                            show_payoff = %(show_payoff)s,
                            result_scraped_at = CURRENT_TIMESTAMP
                        WHERE race_id = %(race_id)s 
                        AND program_number = %(program_number)s
                    """, {
                        'race_id': race_id,
                        'program_number': result.get('program_number'),
                        'finish_position': result.get('finish_position'),
                        'final_odds': result.get('final_odds'),
                        'win_payoff': result.get('win_payoff'),
                        'place_payoff': result.get('place_payoff'),
                        'show_payoff': result.get('show_payoff')
                    })
                elif result.get('horse_name'):
                    # Fallback to matching by horse name
                    cur.execute("""
                        UPDATE entries 
                        SET finish_position = %(finish_position)s,
                            final_odds = %(final_odds)s,
                            win_payoff = %(win_payoff)s,
                            place_payoff = %(place_payoff)s,
                            show_payoff = %(show_payoff)s,
                            result_scraped_at = CURRENT_TIMESTAMP
                        WHERE race_id = %(race_id)s 
                        AND LOWER(horse_name) = LOWER(%(horse_name)s)
                    """, {
                        'race_id': race_id,
                        'horse_name': result.get('horse_name'),
                        'finish_position': result.get('finish_position'),
                        'final_odds': result.get('final_odds'),
                        'win_payoff': result.get('win_payoff'),
                        'place_payoff': result.get('place_payoff'),
                        'show_payoff': result.get('show_payoff')
                    })
            
            # Mark race as having results
            cur.execute("""
                UPDATE races 
                SET results_scraped = TRUE, 
                    results_scraped_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (race_id,))
    
    def get_dates_with_data(self):
        """Get all dates that have race data"""
        with self.get_cursor() as cur:
            cur.execute("""
                SELECT DISTINCT date, 
                       COUNT(DISTINCT id) as race_count,
                       MAX(results_scraped) as has_results
                FROM races 
                GROUP BY date 
                ORDER BY date DESC
                LIMIT 30
            """)
            return cur.fetchall()
    
    def get_race_with_results(self, race_id):
        """Get race entries with both predictions and results"""
        with self.get_cursor() as cur:
            cur.execute("""
                SELECT e.*, 
                       a.overall_score, a.recommendation, a.confidence,
                       e.finish_position, e.final_odds, 
                       e.win_payoff, e.place_payoff, e.show_payoff
                FROM entries e
                LEFT JOIN analysis a ON a.entry_id = e.id
                WHERE e.race_id = %s
                ORDER BY COALESCE(e.finish_position, 999), e.post_position
            """, (race_id,))
            return cur.fetchall()