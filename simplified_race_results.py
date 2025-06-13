"""
Simplified race results management
Stores race results in SQL and updates bet recommendations
"""

import os
import psycopg2
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RaceResultsManager:
    """Manage race results storage and display"""
    
    def __init__(self):
        self.db_url = os.environ.get('DATABASE_URL')
        if self.db_url:
            self.ensure_results_table()
    
    def ensure_results_table(self):
        """Ensure race_results table exists"""
        conn = psycopg2.connect(self.db_url)
        cur = conn.cursor()
        
        try:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS race_results (
                    id SERIAL PRIMARY KEY,
                    race_date DATE NOT NULL,
                    track_name VARCHAR(100) NOT NULL,
                    race_number INTEGER NOT NULL,
                    distance VARCHAR(50),
                    surface VARCHAR(20) DEFAULT 'Dirt',
                    
                    -- Winner information
                    winner_program_number INTEGER,
                    winner_horse_name VARCHAR(255) NOT NULL,
                    winner_jockey VARCHAR(255),
                    winner_trainer VARCHAR(255),
                    winner_odds VARCHAR(20),
                    
                    -- Race finish time
                    official_time VARCHAR(20),
                    
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    UNIQUE(race_date, track_name, race_number)
                )
            ''')
            
            conn.commit()
            logger.info("Race results table ready")
            
        except Exception as e:
            logger.error(f"Error creating table: {e}")
            conn.rollback()
        finally:
            cur.close()
            conn.close()
    
    def store_race_result(self, race_data):
        """
        Store a race result in the database
        
        Args:
            race_data: dict with keys:
                - race_date: '2025-06-13'
                - track_name: 'Fair Meadows'
                - race_number: 1
                - distance: '6F'
                - winner_program_number: 3
                - winner_horse_name: 'Thunder Bolt'
                - winner_jockey: 'John Smith'
                - winner_trainer: 'Jane Doe'
                - winner_odds: '5/2'
        """
        if not self.db_url:
            logger.error("No database URL configured")
            return False
        
        conn = psycopg2.connect(self.db_url)
        cur = conn.cursor()
        
        try:
            cur.execute('''
                INSERT INTO race_results (
                    race_date, track_name, race_number,
                    distance, winner_program_number,
                    winner_horse_name, winner_jockey,
                    winner_trainer, winner_odds
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (race_date, track_name, race_number)
                DO UPDATE SET
                    winner_horse_name = EXCLUDED.winner_horse_name,
                    winner_odds = EXCLUDED.winner_odds,
                    winner_jockey = EXCLUDED.winner_jockey,
                    winner_trainer = EXCLUDED.winner_trainer
            ''', (
                race_data['race_date'],
                race_data['track_name'],
                race_data['race_number'],
                race_data.get('distance'),
                race_data.get('winner_program_number'),
                race_data['winner_horse_name'],
                race_data.get('winner_jockey'),
                race_data.get('winner_trainer'),
                race_data.get('winner_odds')
            ))
            
            conn.commit()
            logger.info(f"Stored result for {race_data['track_name']} Race {race_data['race_number']}")
            
            # Also update bet recommendation to show result
            self.update_bet_recommendation(
                race_data['race_date'],
                race_data['track_name'],
                race_data['race_number'],
                race_data['winner_horse_name'],
                race_data.get('winner_odds')
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error storing result: {e}")
            conn.rollback()
            return False
        finally:
            cur.close()
            conn.close()
    
    def update_bet_recommendation(self, race_date, track_name, race_number, winner_name, odds):
        """Update bet recommendation to show race result"""
        if not self.db_url:
            return
        
        conn = psycopg2.connect(self.db_url)
        cur = conn.cursor()
        
        try:
            # Build result text
            result_text = f"RESULT: {winner_name} WON"
            if odds:
                result_text += f" ({odds})"
            
            # Update all horses in this race with the result
            cur.execute('''
                UPDATE races
                SET bet_recommendation = %s
                WHERE race_date = %s
                  AND race_number = %s
                  AND (track_name = %s OR track_name IS NULL)
            ''', (
                result_text,
                race_date,
                race_number,
                track_name
            ))
            
            conn.commit()
            logger.info(f"Updated bet recommendation for Race {race_number}")
            
        except Exception as e:
            logger.error(f"Error updating bet recommendation: {e}")
            conn.rollback()
        finally:
            cur.close()
            conn.close()
    
    def get_race_results(self, race_date, track_name=None):
        """Get all race results for a date"""
        if not self.db_url:
            return []
        
        conn = psycopg2.connect(self.db_url)
        cur = conn.cursor()
        
        try:
            if track_name:
                cur.execute('''
                    SELECT race_number, distance, winner_program_number,
                           winner_horse_name, winner_jockey, winner_odds
                    FROM race_results
                    WHERE race_date = %s AND track_name = %s
                    ORDER BY race_number
                ''', (race_date, track_name))
            else:
                cur.execute('''
                    SELECT track_name, race_number, distance, 
                           winner_program_number, winner_horse_name, 
                           winner_jockey, winner_odds
                    FROM race_results
                    WHERE race_date = %s
                    ORDER BY track_name, race_number
                ''', (race_date,))
            
            results = []
            for row in cur.fetchall():
                if track_name:
                    results.append({
                        'race_number': row[0],
                        'distance': row[1],
                        'winner_program_number': row[2],
                        'winner_horse_name': row[3],
                        'winner_jockey': row[4],
                        'winner_odds': row[5]
                    })
                else:
                    results.append({
                        'track_name': row[0],
                        'race_number': row[1],
                        'distance': row[2],
                        'winner_program_number': row[3],
                        'winner_horse_name': row[4],
                        'winner_jockey': row[5],
                        'winner_odds': row[6]
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting results: {e}")
            return []
        finally:
            cur.close()
            conn.close()


# Example usage
if __name__ == "__main__":
    manager = RaceResultsManager()
    
    # Example: Store a race result
    result = {
        'race_date': '2025-06-13',
        'track_name': 'Fair Meadows',
        'race_number': 1,
        'distance': '6F',
        'winner_program_number': 3,
        'winner_horse_name': 'Thunder Bolt',
        'winner_jockey': 'John Smith',
        'winner_trainer': 'Jane Doe',
        'winner_odds': '5/2'
    }
    
    manager.store_race_result(result)
    
    # Get results for a date
    results = manager.get_race_results('2025-06-13', 'Fair Meadows')
    for r in results:
        print(f"Race {r['race_number']}: {r['winner_horse_name']} ({r['winner_odds']})")