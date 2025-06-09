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

# Use manual parser that works with any screenshots
from manual_parser import ManualParser as ScreenshotParser
logger.info("Using manual parser - will prompt for data entry")

# Initialize database
db_url = os.environ.get('DATABASE_URL', 'postgresql://localhost/racingsimple')
logger.info(f"Database URL configured: {'Yes' if 'DATABASE_URL' in os.environ else 'No (using default)'}")

# Check if database schema is applied
try:
    db = Database(db_url)
    # Test database connection and schema
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM sessions LIMIT 1")
    logger.info("Database schema verified")
except Exception as e:
    logger.error(f"Database not properly initialized: {e}")
    logger.error("Please run: python apply_schema.py")
    db = None

@app.route('/')
def index():
    """Main page - Race Data Logger"""
    return render_template('index.html')

@app.route('/api/analyze-screenshots', methods=['POST'])
def analyze_screenshots():
    """Handle screenshot uploads and save race data"""
    if db is None:
        return jsonify({'success': False, 'error': 'Database not initialized. Please contact administrator.'}), 503
    
    try:
        # Check for uploaded files
        if 'screenshots' not in request.files:
            return jsonify({'success': False, 'error': 'No screenshots uploaded'}), 400
        
        files = request.files.getlist('screenshots')
        if not files or len(files) == 0:
            return jsonify({'success': False, 'error': 'No screenshots selected'}), 400
        
        if len(files) > 5:
            return jsonify({'success': False, 'error': 'Maximum 5 screenshots allowed'}), 400
        
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
        
        # Parse screenshots
        parser = ScreenshotParser()
        races = parser.parse_multiple_screenshots(screenshot_paths)
        
        # Clean up temp files
        for path in screenshot_paths:
            try:
                os.unlink(path)
            except:
                pass
        
        if not races:
            return jsonify({'success': False, 'error': 'No race data found in screenshots'}), 400
        
        # Check if any races need manual entry
        needs_manual = any(race.get('needs_manual_entry', False) for race in races)
        
        if needs_manual:
            # Create a temporary session
            session_id = db.create_session()
            
            # Return redirect to manual entry
            return jsonify({
                'success': True,
                'needs_manual_entry': True,
                'session_id': session_id,
                'races': races,
                'redirect_url': f'/manual-entry?session={session_id}&races={request.host_url.replace("http://", "").replace("https://", "")}'
            })
        
        # Save to database if data is complete
        session_id = db.create_session()
        db.save_race_data(session_id, races)
        
        # Get saved data
        saved_data = db.get_session_data(session_id)
        
        # Return simple results
        return jsonify({
            'success': True,
            'session_id': session_id,
            'races': races,
            'total_races': len(races),
            'total_entries': sum(len(race.get('entries', [])) for race in races)
        })
        
    except Exception as e:
        logger.error(f"Error processing screenshots: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/session/<int:session_id>')
def get_session(session_id):
    """Get race data for a session"""
    try:
        data = db.get_session_data(session_id)
        if not data:
            return jsonify({'success': False, 'error': 'Session not found'}), 404
        
        return jsonify({
            'success': True,
            'data': data
        })
    except Exception as e:
        logger.error(f"Error retrieving session: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/manual-entry')
def manual_entry():
    """Manual data entry page"""
    return render_template('manual_entry.html')

@app.route('/api/save-manual-data', methods=['POST'])
def save_manual_data():
    """Save manually entered race data"""
    if db is None:
        return jsonify({'success': False, 'error': 'Database not initialized'}), 503
        
    try:
        data = request.json
        session_id = data.get('session_id')
        races = data.get('races', [])
        
        if not races:
            return jsonify({'success': False, 'error': 'No race data provided'}), 400
        
        # Save the manually entered data
        db.save_race_data(session_id, races)
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'total_races': len(races),
            'total_entries': sum(len(race.get('entries', [])) for race in races)
        })
        
    except Exception as e:
        logger.error(f"Error saving manual data: {e}", exc_info=True)
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