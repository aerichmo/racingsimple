from flask import Flask, render_template, jsonify, request, redirect, url_for
from datetime import datetime
import os
import logging
from werkzeug.utils import secure_filename
import tempfile

from database import Database
from pdf_parser import EquibasePDFParser
from analyzer import RaceAnalyzer

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database
db = Database(os.environ.get('DATABASE_URL', 'postgresql://localhost/racingsimple'))

@app.route('/')
def index():
    """Home page showing today's races and top plays"""
    today = datetime.now().date()
    return render_template('index.html', today=today)

@app.route('/upload')
def upload_page():
    """PDF upload page"""
    return render_template('upload.html')

@app.route('/api/upload', methods=['POST'])
def upload_pdf():
    """Handle PDF upload and processing"""
    try:
        if 'pdf' not in request.files:
            return jsonify({'success': False, 'error': 'No PDF file uploaded'}), 400
        
        file = request.files['pdf']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'success': False, 'error': 'File must be a PDF'}), 400
        
        # Save file temporarily
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            file.save(tmp_file.name)
            tmp_path = tmp_file.name
        
        # Parse the PDF
        parser = EquibasePDFParser()
        races = parser.parse_pdf_file(tmp_path)
        
        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except:
            pass
        
        if not races:
            return jsonify({'success': False, 'error': 'No races found in PDF'}), 400
        
        # Save to database and analyze
        analyzer = RaceAnalyzer()
        total_entries = 0
        top_plays = []
        
        for race in races:
            # Save race
            race_data = {
                'date': race['race_date'],
                'race_number': race['race_number'],
                'track_name': race['track'],
                'distance': race.get('distance'),
                'race_type': race.get('race_type'),
                'purse': race.get('purse'),
                'post_time': race.get('post_time'),
                'surface': race.get('surface', 'Dirt'),
                'pdf_filename': secure_filename(file.filename)
            }
            race_id = db.save_race(race_data)
            
            # Save and analyze entries
            for entry in race['entries']:
                entry_data = {
                    'race_id': race_id,
                    'program_number': entry['program_number'],
                    'post_position': entry.get('post_position', entry['program_number']),
                    'horse_name': entry['horse_name'],
                    'jockey': entry.get('jockey'),
                    'trainer': entry.get('trainer'),
                    'win_pct': entry.get('win_pct'),
                    'class_rating': entry.get('class_rating'),
                    'last_speed': entry.get('last_speed'),
                    'avg_speed': entry.get('avg_speed'),
                    'best_speed': entry.get('best_speed'),
                    'jockey_win_pct': entry.get('jockey_win_pct'),
                    'trainer_win_pct': entry.get('trainer_win_pct'),
                    'jt_combo_pct': entry.get('jt_combo_pct')
                }
                entry_id = db.save_entry(entry_data)
                
                # Analyze
                analysis = analyzer.analyze_entry(entry_data)
                analysis['entry_id'] = entry_id
                db.save_analysis(analysis)
                
                # Track top plays
                if analysis['overall_score'] >= 70:
                    play = {
                        'race_number': race['race_number'],
                        'horse_name': entry['horse_name'],
                        'score': analysis['overall_score'],
                        'recommendation': analysis['recommendation']
                    }
                    top_plays.append(play)
                
                total_entries += 1
        
        return jsonify({
            'success': True,
            'message': f'Processed {len(races)} races with {total_entries} entries',
            'races_count': len(races),
            'entries_count': total_entries,
            'top_plays': sorted(top_plays, key=lambda x: x['score'], reverse=True)[:5]
        })
        
    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/races/<date>')
def get_races(date):
    """Get races for a specific date"""
    try:
        races = db.get_races_by_date(date)
        return jsonify({'success': True, 'races': races})
    except Exception as e:
        logger.error(f"Error fetching races: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/race/<int:race_id>/entries')
def get_race_entries(race_id):
    """Get entries for a specific race"""
    try:
        entries = db.get_race_entries(race_id)
        return jsonify({'success': True, 'entries': entries})
    except Exception as e:
        logger.error(f"Error fetching entries: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/top-plays')
def get_top_plays():
    """Get top recommended plays"""
    try:
        date = request.args.get('date')
        plays = db.get_top_plays(date)
        return jsonify({'success': True, 'plays': plays})
    except Exception as e:
        logger.error(f"Error fetching top plays: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/analysis')
def analysis_page():
    """Analysis and recommendations page"""
    return render_template('analysis.html')

@app.route('/init-db')
def init_db():
    """Initialize database tables"""
    try:
        db.create_tables()
        return jsonify({'success': True, 'message': 'Database initialized'})
    except Exception as e:
        logger.error(f"Database init error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    # Initialize database on startup
    try:
        db.create_tables()
        logger.info("Database tables verified")
    except Exception as e:
        logger.error(f"Database startup error: {e}")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)