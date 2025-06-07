from flask import Flask, render_template, jsonify, request, session
from datetime import datetime
import os
import logging
from werkzeug.utils import secure_filename
from pdf_parser import parse_pdf_file
import tempfile
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Store races in memory (in production, you might want to use Redis or file storage)
races_data = {}

@app.route('/test')
def test():
    """Test endpoint to verify app is running"""
    return jsonify({
        'status': 'ok',
        'message': 'Flask app is running',
        'time': datetime.now().isoformat()
    })

@app.route('/')
def index():
    """Home page showing uploaded races"""
    return render_template('index.html')

@app.route('/pdf-upload')
def pdf_upload():
    """PDF upload page"""
    return render_template('pdf_upload.html')

@app.route('/api/upload-pdf', methods=['POST'])
def upload_pdf():
    """Handle PDF file upload and parsing"""
    try:
        # Check if file was uploaded
        if 'pdf' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No PDF file uploaded'
            }), 400
        
        file = request.files['pdf']
        
        # Check if file is selected
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        # Check file extension
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({
                'success': False,
                'error': 'File must be a PDF'
            }), 400
        
        # Save file temporarily
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            file.save(tmp_file.name)
            tmp_path = tmp_file.name
        
        # Parse the PDF
        logger.info(f"Parsing uploaded PDF: {secure_filename(file.filename)}")
        success, message, races = parse_pdf_file(tmp_path)
        
        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except:
            pass
        
        if success and races:
            # Store races in memory with timestamp
            upload_id = datetime.now().isoformat()
            races_data[upload_id] = {
                'filename': secure_filename(file.filename),
                'uploaded_at': datetime.now().isoformat(),
                'races': races
            }
            
            # Store in session for easy access
            if 'uploads' not in session:
                session['uploads'] = []
            session['uploads'].append(upload_id)
            
            return jsonify({
                'success': True,
                'message': message,
                'filename': secure_filename(file.filename),
                'upload_id': upload_id,
                'races_count': len(races)
            })
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 500
            
    except Exception as e:
        logger.error(f"PDF upload error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Error processing PDF: {str(e)}'
        }), 500

@app.route('/api/races')
def get_all_races():
    """Get all uploaded races"""
    try:
        all_races = []
        
        # Get races from all uploads
        for upload_id, upload_data in races_data.items():
            for race in upload_data['races']:
                race_copy = race.copy()
                race_copy['upload_id'] = upload_id
                race_copy['filename'] = upload_data['filename']
                all_races.append(race_copy)
        
        # Sort by date and race number
        all_races.sort(key=lambda x: (x.get('date', ''), x.get('race_number', 0)))
        
        return jsonify({
            'success': True,
            'races': all_races,
            'total_uploads': len(races_data)
        })
    except Exception as e:
        logger.error(f"Error fetching races: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/races/<upload_id>')
def get_races_by_upload(upload_id):
    """Get races from a specific upload"""
    try:
        if upload_id not in races_data:
            return jsonify({
                'success': False,
                'error': 'Upload not found'
            }), 404
        
        upload_data = races_data[upload_id]
        
        return jsonify({
            'success': True,
            'filename': upload_data['filename'],
            'uploaded_at': upload_data['uploaded_at'],
            'races': upload_data['races']
        })
    except Exception as e:
        logger.error(f"Error fetching races: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/clear')
def clear_data():
    """Clear all uploaded data"""
    global races_data
    races_data = {}
    session.pop('uploads', None)
    
    return jsonify({
        'success': True,
        'message': 'All data cleared'
    })

@app.route('/stats')
def stats():
    """Statistics page"""
    return render_template('stats.html')

@app.route('/api/stats')
def get_stats():
    """Get statistics from uploaded data"""
    try:
        # Collect all horses from all races
        all_horses = []
        for upload_data in races_data.values():
            for race in upload_data['races']:
                for horse in race.get('horses', []):
                    horse_copy = horse.copy()
                    horse_copy['track'] = race.get('track_name', 'Unknown')
                    horse_copy['date'] = race.get('date')
                    all_horses.append(horse_copy)
        
        # Calculate jockey stats
        jockey_stats = {}
        for horse in all_horses:
            jockey = horse.get('jockey', 'Unknown')
            if jockey and jockey != '-':
                if jockey not in jockey_stats:
                    jockey_stats[jockey] = {
                        'name': jockey,
                        'mounts': 0,
                        'tracks': set()
                    }
                jockey_stats[jockey]['mounts'] += 1
                jockey_stats[jockey]['tracks'].add(horse['track'])
        
        # Calculate trainer stats
        trainer_stats = {}
        for horse in all_horses:
            trainer = horse.get('trainer', 'Unknown')
            if trainer and trainer != '-':
                if trainer not in trainer_stats:
                    trainer_stats[trainer] = {
                        'name': trainer,
                        'entries': 0,
                        'tracks': set()
                    }
                trainer_stats[trainer]['entries'] += 1
                trainer_stats[trainer]['tracks'].add(horse['track'])
        
        # Convert sets to lists for JSON serialization
        jockey_list = []
        for jockey, stats in jockey_stats.items():
            jockey_list.append({
                'name': stats['name'],
                'mounts': stats['mounts'],
                'tracks': list(stats['tracks'])
            })
        
        trainer_list = []
        for trainer, stats in trainer_stats.items():
            trainer_list.append({
                'name': stats['name'],
                'entries': stats['entries'],
                'tracks': list(stats['tracks'])
            })
        
        # Sort by activity
        jockey_list.sort(key=lambda x: x['mounts'], reverse=True)
        trainer_list.sort(key=lambda x: x['entries'], reverse=True)
        
        return jsonify({
            'success': True,
            'jockeys': jockey_list[:20],  # Top 20
            'trainers': trainer_list[:20],  # Top 20
            'total_races': sum(len(upload['races']) for upload in races_data.values()),
            'total_horses': len(all_horses)
        })
        
    except Exception as e:
        logger.error(f"Error calculating stats: {e}")
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
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)