from flask import Flask, render_template, jsonify, request, redirect
from datetime import datetime
import os
import logging
from werkzeug.utils import secure_filename
import tempfile

app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from database import Database
try:
    from screenshot_parser import ScreenshotParser
except ImportError:
    # Use simple parser if OCR dependencies not available
    from screenshot_parser_simple import ScreenshotParser
from betting_analyzer import BettingAnalyzer

# Initialize database
db_url = os.environ.get('DATABASE_URL', 'postgresql://localhost/racingsimple')
logger.info(f"Database URL configured: {'Yes' if 'DATABASE_URL' in os.environ else 'No (using default)'}")
db = Database(db_url)

@app.route('/')
def index():
    """Main page - Betting Analysis"""
    return render_template('index.html')

@app.route('/api/analyze-screenshots', methods=['POST'])
def analyze_screenshots():
    """Handle screenshot uploads and perform betting analysis"""
    try:
        # Check for uploaded files
        if 'screenshots' not in request.files:
            return jsonify({'success': False, 'error': 'No screenshots uploaded'}), 400
        
        files = request.files.getlist('screenshots')
        if not files or len(files) == 0:
            return jsonify({'success': False, 'error': 'No screenshots selected'}), 400
        
        if len(files) > 5:
            return jsonify({'success': False, 'error': 'Maximum 5 screenshots allowed'}), 400
        
        # Get bankroll from form
        bankroll = float(request.form.get('bankroll', 1000))
        
        # Save uploaded screenshots temporarily
        screenshot_paths = []
        for file in files:
            if file.filename == '':
                continue
            
            # Validate file type
            if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                return jsonify({'success': False, 'error': 'Only PNG and JPEG images are allowed'}), 400
            
            # Save file temporarily
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                file.save(tmp_file.name)
                screenshot_paths.append(tmp_file.name)
        
        if not screenshot_paths:
            return jsonify({'success': False, 'error': 'No valid screenshots found'}), 400
        
        logger.info(f"Processing {len(screenshot_paths)} screenshots")
        logger.info(f"Screenshot paths: {screenshot_paths}")
        
        # Parse screenshots
        parser = ScreenshotParser()
        logger.info(f"Using parser: {parser.__class__.__name__}")
        
        races = parser.parse_multiple_screenshots(screenshot_paths)
        logger.info(f"Parser returned {len(races)} races")
        
        # Clean up temp files
        for path in screenshot_paths:
            try:
                os.unlink(path)
            except:
                pass
        
        if not races:
            logger.error("No races found by parser")
            return jsonify({'success': False, 'error': 'No race data found in screenshots'}), 400
        
        # Perform betting analysis
        analyzer = BettingAnalyzer()
        analysis = analyzer.analyze_races(races, bankroll)
        
        # Save to database
        session_id = db.create_analysis_session(bankroll)
        
        for race_analysis in analysis['races']:
            # Save race data
            race_data = {
                'race_number': race_analysis['race_number'],
                'post_time': race_analysis['post_time'],
                'track_name': 'Unknown',  # Not in screenshots
                'total_probability': race_analysis['race_metrics']['total_probability'],
                'favorite_probability': race_analysis['race_metrics']['favorite_probability'],
                'avg_edge': race_analysis['race_metrics']['avg_edge'],
                'max_edge': race_analysis['race_metrics']['max_edge'],
                'positive_edges': race_analysis['race_metrics']['positive_edges'],
                'field_size': race_analysis['race_metrics']['field_size'],
                'competitiveness': race_analysis['race_metrics']['competitiveness']
            }
            race_id = db.save_race(session_id, race_data)
            
            # Save entries
            db.save_entries(race_id, race_analysis['entries'])
            
            # Save recommendations
            if race_analysis['recommended_bets']:
                db.save_recommendations(race_id, race_analysis['recommended_bets'])
        
        # Update session summary
        analysis['summary']['total_races'] = len(analysis['races'])
        db.update_session_summary(session_id, analysis['summary'])
        
        # Return analysis results
        return jsonify({
            'success': True,
            'session_id': session_id,
            'analysis': analysis
        })
        
    except Exception as e:
        logger.error(f"Error analyzing screenshots: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/session/<int:session_id>')
def get_session(session_id):
    """Get analysis results for a session"""
    try:
        analysis = db.get_session_analysis(session_id)
        if not analysis:
            return jsonify({'success': False, 'error': 'Session not found'}), 404
        
        return jsonify({
            'success': True,
            'analysis': analysis
        })
    except Exception as e:
        logger.error(f"Error retrieving session: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/recent-sessions')
def recent_sessions():
    """Get recent analysis sessions"""
    try:
        sessions = db.get_recent_sessions(limit=10)
        return jsonify({
            'success': True,
            'sessions': sessions
        })
    except Exception as e:
        logger.error(f"Error retrieving sessions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'server': 'ok',
        'database': 'ok',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/test-parser')
def test_parser():
    """Test the screenshot parser"""
    parser = ScreenshotParser()
    test_data = parser.parse_screenshot("/tmp/test.png")
    return jsonify({
        'parser_class': parser.__class__.__name__,
        'test_data': test_data,
        'has_entries': bool(test_data.get('entries')),
        'entry_count': len(test_data.get('entries', []))
    })

if __name__ == '__main__':
    app.run(debug=True, port=5001)