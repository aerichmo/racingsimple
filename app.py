from flask import Flask, render_template, jsonify
from datetime import datetime, timedelta
import os
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

@app.route('/sync')
def sync_data():
    """Manual sync endpoint - fetches real data from Equibase"""
    try:
        from scraper import EquibaseScraper
        from odds_scraper import OddsScraper
        
        # First ensure tables exist
        db.create_tables()
        
        # Run the real scrapers
        scraper = EquibaseScraper(os.environ.get('DATABASE_URL'))
        scraper.run_daily_sync()
        
        # Also fetch morning line odds
        odds_scraper = OddsScraper(os.environ.get('DATABASE_URL'))
        odds_scraper.save_morning_line_odds(datetime.now())
        
        return jsonify({
            'success': True,
            'message': 'Real data sync completed. Note: HTML selectors may need updating.'
        })
    except Exception as e:
        logger.error(f"Sync error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'note': 'The scraper HTML selectors need to be updated for the actual Equibase HTML structure'
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