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
    """Self-debugging sync endpoint that learns from HTML structure"""
    try:
        from self_debug_scraper import run_self_debugging_sync, SelfDebuggingScraper
        
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
        
        # Try self-debugging scraper first
        logger.info("Starting self-debugging sync...")
        scraper = SelfDebuggingScraper(os.environ.get('DATABASE_URL'))
        races = scraper.fetch_and_learn(datetime.now())
        
        debug_info = {
            'html_analyzed': True,
            'selectors_found': scraper.successful_selectors,
            'races_parsed': len(races) if races else 0,
            'learning_saved': bool(scraper.successful_selectors)
        }
        
        if races:
            # Save to database
            from scraper import EquibaseScraper
            eq_scraper = EquibaseScraper(os.environ.get('DATABASE_URL'))
            eq_scraper.save_to_database(races)
            
            return jsonify({
                'success': True,
                'message': f'Successfully learned HTML structure and synced {len(races)} races!',
                'debug': debug_info
            })
        else:
            # Fallback to regular scraper with debugging
            logger.warning("Self-debugging failed, trying regular scraper...")
            from scraper import EquibaseScraper
            scraper = EquibaseScraper(os.environ.get('DATABASE_URL'))
            
            try:
                scraper.run_daily_sync()
                return jsonify({
                    'success': True,
                    'message': 'Sync completed with regular scraper',
                    'debug': debug_info
                })
            except Exception as e:
                # Return detailed debugging information
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'debug': debug_info,
                    'suggestion': 'Check /tmp/equibase_*.html for the raw HTML structure',
                    'note': 'The scraper tried to learn from the HTML but needs manual selector updates'
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