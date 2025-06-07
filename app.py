from flask import Flask, render_template, jsonify
from datetime import datetime, timedelta
import os
import re
from database import Database
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database
db = Database(os.environ.get('DATABASE_URL'))

@app.route('/test')
def test():
    """Test endpoint to verify app is running"""
    return jsonify({
        'status': 'ok',
        'message': 'Flask app is running',
        'time': datetime.now().isoformat(),
        'database_url_set': bool(os.environ.get('DATABASE_URL')),
        'port': os.environ.get('PORT', 'not set')
    })

@app.route('/init-db')
def init_db():
    """Initialize database tables"""
    try:
        db.create_tables()
        return jsonify({
            'success': True,
            'message': 'Database tables created successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/clear-data')
def clear_data():
    """Clear all race data"""
    try:
        with db.get_cursor() as cur:
            cur.execute("DELETE FROM horses")
            cur.execute("DELETE FROM races")
            
        return jsonify({
            'success': True,
            'message': 'All race data cleared successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/diagnose')
def diagnose():
    """Diagnose what's happening with the scraper"""
    try:
        import requests
        from bs4 import BeautifulSoup
        
        # Generate today's URL
        today = datetime.now()
        date_str = today.strftime("%m%d%y")
        url = f"https://www.equibase.com/static/entry/FMT{date_str}USA-EQB.html"
        
        logger.info(f"Diagnosing URL: {url}")
        
        # Fetch the page
        response = requests.get(url, timeout=30)
        html = response.text
        
        # Basic analysis
        soup = BeautifulSoup(html, 'html.parser')
        
        diagnosis = {
            'url': url,
            'status_code': response.status_code,
            'content_length': len(html),
            'title': soup.title.string if soup.title else 'No title',
            'sample_content': html[:500],
            'tables_found': len(soup.find_all('table')),
            'divs_found': len(soup.find_all('div')),
            'text_preview': soup.get_text()[:1000].replace('\n', ' ').strip()
        }
        
        # Look for common patterns
        patterns_found = {
            'race_mentions': len(soup.find_all(text=re.compile(r'Race\s+\d+', re.I))),
            'fonner_mentions': len(soup.find_all(text=re.compile(r'Fonner', re.I))),
            'horse_mentions': len(soup.find_all(text=re.compile(r'Horse|Jockey|Trainer', re.I))),
            'post_time_mentions': len(soup.find_all(text=re.compile(r'Post|Time', re.I)))
        }
        
        diagnosis['patterns'] = patterns_found
        
        # Save full HTML for manual inspection
        debug_file = f"/tmp/equibase_debug_{date_str}.html"
        with open(debug_file, 'w') as f:
            f.write(html)
        diagnosis['debug_file'] = debug_file
        
        return jsonify({
            'success': True,
            'diagnosis': diagnosis,
            'message': f'Diagnostics complete. HTML saved to {debug_file}'
        })
        
    except Exception as e:
        logger.error(f"Diagnosis error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/sync')
def sync_data():
    """Advanced sync endpoint with multiple bypass strategies"""
    try:
        from advanced_scraper import run_advanced_scraper
        from alternative_sources import fetch_from_alternatives
        
        # First ensure tables exist
        db.create_tables()
        
        # Clear old sample data for today
        with db.get_cursor() as cur:
            cur.execute("""
                DELETE FROM races 
                WHERE date = CURRENT_DATE 
                AND track_name IN ('Sample Track', 'Fonner Park')
            """)
            logger.info("Cleared old sample data")
        
        # Try advanced scraper with multiple strategies
        logger.info("Starting advanced sync with bypass strategies...")
        success, races = run_advanced_scraper(os.environ.get('DATABASE_URL'))
        
        if success and races:
            return jsonify({
                'success': True,
                'message': f'Successfully bypassed protection and synced {len(races)} races!',
                'strategy': 'Advanced multi-strategy scraper'
            })
        
        # Try alternative data sources
        logger.warning("Equibase blocked, trying alternative sources...")
        alt_success, alt_races, source = fetch_from_alternatives(
            os.environ.get('DATABASE_URL'), 
            datetime.now()
        )
        
        if alt_success and alt_races:
            from scraper import EquibaseScraper
            eq_scraper = EquibaseScraper(os.environ.get('DATABASE_URL'))
            eq_scraper.save_to_database(alt_races)
            
            return jsonify({
                'success': True,
                'message': f'Synced {len(alt_races)} races from {source}!',
                'strategy': f'Alternative source: {source}',
                'note': 'Using alternative data source due to Equibase protection'
            })
        
        # Try self-debugging scraper
        logger.warning("All sources failed, trying self-debugging scraper...")
        from self_debug_scraper import SelfDebuggingScraper
        
        scraper = SelfDebuggingScraper(os.environ.get('DATABASE_URL'))
        races = scraper.fetch_and_learn(datetime.now())
        
        if races:
            from scraper import EquibaseScraper
            eq_scraper = EquibaseScraper(os.environ.get('DATABASE_URL'))
            eq_scraper.save_to_database(races)
            
            return jsonify({
                'success': True,
                'message': f'Synced {len(races)} races with self-debugging scraper',
                'strategy': 'Self-debugging parser'
            })
        
        # Last resort - create sample data to demonstrate functionality
        logger.warning("All scrapers blocked, creating demonstration data...")
        from direct_parse import parse_any_available_data
        
        sample_success, sample_races, sample_source = parse_any_available_data(
            os.environ.get('DATABASE_URL'),
            datetime.now()
        )
        
        if sample_success and sample_races:
            from scraper import EquibaseScraper
            eq_scraper = EquibaseScraper(os.environ.get('DATABASE_URL'))
            eq_scraper.save_to_database(sample_races)
            
            return jsonify({
                'success': True,
                'message': f'Created {len(sample_races)} demonstration races',
                'strategy': sample_source,
                'warning': 'All real data sources blocked - showing sample data for demonstration',
                'note': 'The system is working correctly but cannot access live data due to anti-bot protection'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Unable to fetch or create any race data',
                'strategies_tried': [
                    'Equibase (CloudScraper, Undetected Chrome, API endpoints, Mobile)',
                    'Daily Racing Form',
                    'BloodHorse', 
                    'Track-specific websites (Fonner Park)',
                    'API aggregators',
                    'Self-debugging HTML parser',
                    'Sample data generation'
                ],
                'suggestion': 'Critical failure - please check logs'
            }), 500
                
    except Exception as e:
        logger.error(f"Sync error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': str(e.__traceback__),
            'note': 'Critical error in sync process'
        }), 500

@app.route('/')
def index():
    """Home page showing today's races"""
    today = datetime.now().date()
    return render_template('index.html', date=today)

@app.route('/manual-entry')
def manual_entry():
    """Manual entry page"""
    today = datetime.now().date()
    return render_template('manual_entry.html', date=today)

@app.route('/api/manual-entry', methods=['POST'])
def save_manual_entry():
    """Save manually entered race data"""
    try:
        from flask import request
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Save to database
        with db.get_cursor() as cur:
            # Insert race
            cur.execute("""
                INSERT INTO races (date, race_number, track_name, post_time, 
                                 purse, distance, surface, race_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (date, race_number, track_name) 
                DO UPDATE SET 
                    post_time = EXCLUDED.post_time,
                    purse = EXCLUDED.purse,
                    distance = EXCLUDED.distance,
                    surface = EXCLUDED.surface,
                    race_type = EXCLUDED.race_type
                RETURNING id
            """, (
                data['date'], data['race_number'], data['track_name'],
                data.get('post_time'), data.get('purse'), data.get('distance'),
                data.get('surface'), data.get('race_type')
            ))
            
            race_id = cur.fetchone()[0]
            
            # Delete existing horses for this race
            cur.execute("DELETE FROM horses WHERE race_id = %s", (race_id,))
            
            # Insert horses
            for horse in data.get('horses', []):
                cur.execute("""
                    INSERT INTO horses (race_id, program_number, horse_name, 
                                      jockey, trainer, morning_line_odds, weight)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    race_id, horse.get('program_number'), horse['horse_name'],
                    horse.get('jockey'), horse.get('trainer'), 
                    horse.get('morning_line_odds'), horse.get('weight')
                ))
        
        return jsonify({
            'success': True,
            'message': f"Race {data['race_number']} saved successfully",
            'race_id': race_id
        })
        
    except Exception as e:
        logger.error(f"Manual entry error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/races/<date>')
def get_races(date):
    """API endpoint to get races for a specific date"""
    try:
        races = db.get_races_by_date(date)
        return jsonify({
            'success': True,
            'date': date,
            'races': races
        })
    except Exception as e:
        logger.error(f"Error fetching races: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/odds/<int:race_id>')
def get_odds_history(race_id):
    """Get odds history for a specific race"""
    try:
        with db.get_cursor(dict_cursor=True) as cur:
            cur.execute("""
                SELECT 
                    h.horse_name,
                    h.program_number,
                    oh.odds_type,
                    oh.odds_value,
                    oh.captured_at,
                    oh.minutes_to_post
                FROM odds_history oh
                JOIN horses h ON h.id = oh.horse_id
                WHERE oh.race_id = %s
                ORDER BY h.program_number, oh.captured_at
            """, (race_id,))
            
            odds_data = cur.fetchall()
            
            # Group by horse
            horses_odds = {}
            for row in odds_data:
                horse_name = row['horse_name']
                if horse_name not in horses_odds:
                    horses_odds[horse_name] = {
                        'program_number': row['program_number'],
                        'odds_history': []
                    }
                horses_odds[horse_name]['odds_history'].append({
                    'type': row['odds_type'],
                    'value': row['odds_value'],
                    'captured_at': row['captured_at'].isoformat(),
                    'minutes_to_post': row['minutes_to_post']
                })
            
            return jsonify({
                'success': True,
                'race_id': race_id,
                'odds': horses_odds
            })
    except Exception as e:
        logger.error(f"Error fetching odds: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/stats')
def stats():
    """Statistics page"""
    return render_template('stats.html')

@app.route('/api/stats/jockeys')
def jockey_stats():
    """Get jockey statistics"""
    try:
        stats = db.get_jockey_statistics()
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/stats/trainers')
def trainer_stats():
    """Get trainer statistics"""
    try:
        stats = db.get_trainer_statistics()
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/stats/tracks')
def track_stats():
    """Get track statistics"""
    try:
        stats = db.get_track_statistics()
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    # Create tables on startup
    try:
        db.create_tables()
        logger.info("Database tables verified/created")
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)