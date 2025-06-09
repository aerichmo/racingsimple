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

# Try to use OCR parser, but test if it actually works
USE_OCR = False
try:
    import pytesseract
    import cv2
    from screenshot_parser import ScreenshotParser as OCRScreenshotParser
    # Test if tesseract is actually installed
    pytesseract.get_tesseract_version()
    USE_OCR = True
    logger.info("Using OCR-based screenshot parser")
except Exception as e:
    logger.info(f"OCR not available ({e}), using simple parser")

if not USE_OCR:
    from screenshot_parser_simple import ScreenshotParser
else:
    ScreenshotParser = OCRScreenshotParser

# Initialize database
db_url = os.environ.get('DATABASE_URL', 'postgresql://localhost/racingsimple')
logger.info(f"Database URL configured: {'Yes' if 'DATABASE_URL' in os.environ else 'No (using default)'}")
db = Database(db_url)

@app.route('/')
def index():
    """Main page - Race Data Logger"""
    return render_template('index_simple.html')

@app.route('/api/analyze-screenshots', methods=['POST'])
def analyze_screenshots():
    """Handle screenshot uploads and save race data"""
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
        
        # Save to database
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