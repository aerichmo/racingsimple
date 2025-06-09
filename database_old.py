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
    
    def save_race(self, race_data):
        """Save race and return race_id"""
        with self.get_cursor() as cur:
            cur.execute("""
                INSERT INTO races (
                    date, race_number, track_name, track_code, country, 
                    distance, dist_unit, surface, race_type, purse,
                    claiming_price, post_time, age_restriction, sex_restriction,
                    race_conditions, file_name
                )
                VALUES (
                    %(date)s, %(race_number)s, %(track_name)s, %(track_code)s, %(country)s,
                    %(distance)s, %(dist_unit)s, %(surface)s, %(race_type)s, %(purse)s,
                    %(claiming_price)s, %(post_time)s, %(age_restriction)s, %(sex_restriction)s,
                    %(race_conditions)s, %(file_name)s
                )
                ON CONFLICT (date, race_number, track_code) 
                DO UPDATE SET 
                    distance = EXCLUDED.distance,
                    race_type = EXCLUDED.race_type,
                    purse = EXCLUDED.purse,
                    post_time = EXCLUDED.post_time,
                    race_conditions = EXCLUDED.race_conditions
                RETURNING id
            """, race_data)
            return cur.fetchone()['id']
    
    def save_entry(self, entry_data):
        """Save race entry and return entry_id"""
        with self.get_cursor() as cur:
            # Convert empty strings to None for numeric fields
            for field in ['age', 'weight', 'avg_speed', 'avg_class', 'last_speed', 
                         'best_speed', 'claiming_price', 'finish_position']:
                if field in entry_data and entry_data[field] == '':
                    entry_data[field] = None
            
            # Convert empty strings to None for decimal fields and cap values
            for field in ['power_rating', 'win_pct', 'jockey_win_pct', 'trainer_win_pct']:
                if field in entry_data:
                    if entry_data[field] == '':
                        entry_data[field] = None
                    elif entry_data[field] is not None:
                        try:
                            val = float(entry_data[field])
                            if field == 'power_rating':
                                # power_rating is DECIMAL(5,1) - max value is 9999.9
                                if val > 9999.9:
                                    logger.warning(f"Capping {field} from {val} to 9999.9 for horse {entry_data.get('horse_name', 'unknown')}")
                                entry_data[field] = min(val, 9999.9)
                            elif field.endswith('_pct'):
                                # percentage fields are DECIMAL(5,2) but should be capped at 99.9 to avoid rounding to 100
                                if val > 99.9:
                                    logger.warning(f"Capping {field} from {val} to 99.9 for horse {entry_data.get('horse_name', 'unknown')}")
                                entry_data[field] = min(val, 99.9)
                        except (ValueError, TypeError):
                            logger.warning(f"Invalid value for {field}: {entry_data[field]}")
                            entry_data[field] = None
                    
            cur.execute("""
                INSERT INTO entries (
                    race_id, program_number, post_position, horse_name,
                    age, sex, color, sire, dam, owner_name, breeder,
                    jockey, trainer, weight, medication, equipment,
                    morning_line_odds, claiming_price,
                    power_rating, avg_speed, avg_class, last_speed, best_speed,
                    win_pct, jockey_win_pct, trainer_win_pct,
                    finish_position, final_odds
                )
                VALUES (
                    %(race_id)s, %(program_number)s, %(post_position)s, %(horse_name)s,
                    %(age)s, %(sex)s, %(color)s, %(sire)s, %(dam)s, %(owner_name)s, %(breeder)s,
                    %(jockey)s, %(trainer)s, %(weight)s, %(medication)s, %(equipment)s,
                    %(morning_line_odds)s, %(claiming_price)s,
                    %(power_rating)s, %(avg_speed)s, %(avg_class)s, %(last_speed)s, %(best_speed)s,
                    %(win_pct)s, %(jockey_win_pct)s, %(trainer_win_pct)s,
                    %(finish_position)s, %(final_odds)s
                )
                ON CONFLICT (race_id, program_number)
                DO UPDATE SET
                    horse_name = EXCLUDED.horse_name,
                    jockey = EXCLUDED.jockey,
                    trainer = EXCLUDED.trainer,
                    power_rating = EXCLUDED.power_rating,
                    morning_line_odds = EXCLUDED.morning_line_odds,
                    weight = EXCLUDED.weight
                RETURNING id
            """, entry_data)
            return cur.fetchone()['id']
    
    def save_horse_stats(self, entry_id, stats_dict):
        """Save horse statistics"""
        with self.get_cursor() as cur:
            for stat_type, stats in stats_dict.items():
                if isinstance(stats, dict) and 'starts' in stats:
                    cur.execute("""
                        INSERT INTO horse_stats (
                            entry_id, stat_type, starts, wins, places, shows, earnings, roi
                        )
                        VALUES (
                            %(entry_id)s, %(stat_type)s, %(starts)s, %(wins)s, 
                            %(places)s, %(shows)s, %(earnings)s, %(roi)s
                        )
                        ON CONFLICT (entry_id, stat_type)
                        DO UPDATE SET
                            starts = EXCLUDED.starts,
                            wins = EXCLUDED.wins,
                            places = EXCLUDED.places,
                            shows = EXCLUDED.shows,
                            earnings = EXCLUDED.earnings,
                            roi = EXCLUDED.roi
                    """, {
                        'entry_id': entry_id,
                        'stat_type': stat_type,
                        'starts': stats.get('starts', 0),
                        'wins': stats.get('wins', 0),
                        'places': stats.get('places', 0),
                        'shows': stats.get('shows', 0),
                        'earnings': stats.get('earnings', 0),
                        'roi': min(float(stats.get('roi', 0) or 0), 9999.99) if stats.get('roi') is not None else None
                    })
    
    def save_jockey_stats(self, entry_id, jockey_name, stats_dict):
        """Save jockey statistics"""
        with self.get_cursor() as cur:
            for stat_type, stats in stats_dict.items():
                if isinstance(stats, dict) and 'starts' in stats:
                    cur.execute("""
                        INSERT INTO jockey_stats (
                            entry_id, jockey_name, stat_type, starts, wins, places, shows, roi
                        )
                        VALUES (
                            %(entry_id)s, %(jockey_name)s, %(stat_type)s, %(starts)s, 
                            %(wins)s, %(places)s, %(shows)s, %(roi)s
                        )
                        ON CONFLICT (entry_id, stat_type)
                        DO UPDATE SET
                            jockey_name = EXCLUDED.jockey_name,
                            starts = EXCLUDED.starts,
                            wins = EXCLUDED.wins,
                            places = EXCLUDED.places,
                            shows = EXCLUDED.shows,
                            roi = EXCLUDED.roi
                    """, {
                        'entry_id': entry_id,
                        'jockey_name': jockey_name,
                        'stat_type': stat_type,
                        'starts': stats.get('starts', 0),
                        'wins': stats.get('wins', 0),
                        'places': stats.get('places', 0),
                        'shows': stats.get('shows', 0),
                        'roi': min(float(stats.get('roi', 0) or 0), 9999.99) if stats.get('roi') is not None else None
                    })
    
    def save_trainer_stats(self, entry_id, trainer_name, stats_dict):
        """Save trainer statistics"""
        with self.get_cursor() as cur:
            for stat_type, stats in stats_dict.items():
                if isinstance(stats, dict) and 'starts' in stats:
                    cur.execute("""
                        INSERT INTO trainer_stats (
                            entry_id, trainer_name, stat_type, starts, wins, places, shows, roi
                        )
                        VALUES (
                            %(entry_id)s, %(trainer_name)s, %(stat_type)s, %(starts)s, 
                            %(wins)s, %(places)s, %(shows)s, %(roi)s
                        )
                        ON CONFLICT (entry_id, stat_type)
                        DO UPDATE SET
                            trainer_name = EXCLUDED.trainer_name,
                            starts = EXCLUDED.starts,
                            wins = EXCLUDED.wins,
                            places = EXCLUDED.places,
                            shows = EXCLUDED.shows,
                            roi = EXCLUDED.roi
                    """, {
                        'entry_id': entry_id,
                        'trainer_name': trainer_name,
                        'stat_type': stat_type,
                        'starts': stats.get('starts', 0),
                        'wins': stats.get('wins', 0),
                        'places': stats.get('places', 0),
                        'shows': stats.get('shows', 0),
                        'roi': min(float(stats.get('roi', 0) or 0), 9999.99) if stats.get('roi') is not None else None
                    })
    
    def save_workouts(self, entry_id, workouts):
        """Save workout data"""
        with self.get_cursor() as cur:
            # Delete existing workouts for this entry
            cur.execute("DELETE FROM workouts WHERE entry_id = %s", (entry_id,))
            
            # Insert new workouts
            for workout in workouts:
                cur.execute("""
                    INSERT INTO workouts (entry_id, days_back, description, ranking)
                    VALUES (%(entry_id)s, %(days_back)s, %(description)s, %(ranking)s)
                """, {
                    'entry_id': entry_id,
                    'days_back': workout.get('days_back'),
                    'description': workout.get('description'),
                    'ranking': workout.get('ranking')
                })
    
    def save_pp_data(self, entry_id, pp_data_list):
        """Save simplified past performance data"""
        with self.get_cursor() as cur:
            for pp in pp_data_list:
                # Convert date format
                race_date = pp.get('racedate', '')
                if race_date and len(race_date) == 8:
                    race_date = f"{race_date[:4]}-{race_date[4:6]}-{race_date[6:8]}"
                
                # Extract key fields only
                cur.execute("""
                    INSERT INTO pp_data (
                        entry_id, race_date, track_code, race_type, distance, surface,
                        finish_position, beaten_lengths, speed_figure, class_rating,
                        jockey, weight, odds, comments
                    )
                    VALUES (
                        %(entry_id)s, %(race_date)s, %(track_code)s, %(race_type)s, 
                        %(distance)s, %(surface)s, %(finish_position)s, %(beaten_lengths)s, 
                        %(speed_figure)s, %(class_rating)s, %(jockey)s, %(weight)s, 
                        %(odds)s, %(comments)s
                    )
                """, {
                    'entry_id': entry_id,
                    'race_date': race_date,
                    'track_code': pp.get('trackcode'),
                    'race_type': pp.get('racetype'),
                    'distance': pp.get('distance'),
                    'surface': pp.get('surface'),
                    'finish_position': pp.get('positionfi'),
                    # beaten_lengths in XML is in hundredths (e.g., 1300 = 13.00 lengths)
                    'beaten_lengths': min(float(pp.get('lenbackfin', 0) or 0) / 100, 999.9) if pp.get('lenbackfin') else None,
                    'speed_figure': pp.get('speedfigur'),
                    'class_rating': pp.get('classratin'),
                    'jockey': pp.get('jockdisp'),
                    'weight': pp.get('weightcarr'),
                    'odds': pp.get('posttimeod'),
                    'comments': pp.get('longcommen')
                })
    
    def save_analysis(self, analysis_data):
        """Save analysis results"""
        # Cap all score fields at 99.99 to prevent DECIMAL(5,2) overflow
        score_fields = ['speed_score', 'class_score', 'jockey_score', 'trainer_score', 'overall_score']
        for field in score_fields:
            if field in analysis_data and analysis_data[field] is not None:
                try:
                    val = float(analysis_data[field])
                    if val > 99.9:
                        logger.warning(f"Capping analysis {field} from {val} to 99.9 for entry_id {analysis_data.get('entry_id', 'unknown')}")
                    analysis_data[field] = min(val, 99.9)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid value for analysis {field}: {analysis_data[field]}")
                    analysis_data[field] = 0.0
        
        with self.get_cursor() as cur:
            cur.execute("""
                INSERT INTO analysis (
                    entry_id, speed_score, class_score, jockey_score,
                    trainer_score, overall_score, recommendation, confidence
                )
                VALUES (
                    %(entry_id)s, %(speed_score)s, %(class_score)s, %(jockey_score)s,
                    %(trainer_score)s, %(overall_score)s, %(recommendation)s, %(confidence)s
                )
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
    
    def get_dates_with_data(self):
        """Get all dates that have race data"""
        with self.get_cursor() as cur:
            cur.execute("""
                SELECT DISTINCT date, 
                       COUNT(DISTINCT id) as race_count,
                       track_code,
                       track_name
                FROM races 
                GROUP BY date, track_code, track_name
                ORDER BY date DESC
                LIMIT 30
            """)
            return cur.fetchall()
    
    def clear_all_data(self):
        """Clear all data from all tables"""
        with self.get_cursor() as cur:
            # Tables will cascade delete due to foreign key constraints
            cur.execute("TRUNCATE TABLE races CASCADE")
            logger.info("All data cleared from database")