from flask import Flask, render_template, jsonify, request, redirect
from datetime import datetime
import os
import logging
from werkzeug.utils import secure_filename
import tempfile
import zipfile

app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from database import Database
from xml_parser import EquibasePDFParser
from analyzer import RaceAnalyzer

# Initialize database with XML schema
db_url = os.environ.get('DATABASE_URL', 'postgresql://localhost/racingsimple')
logger.info(f"Database URL configured: {'Yes' if 'DATABASE_URL' in os.environ else 'No (using default)'}")
db = Database(db_url)

@app.route('/')
def index():
    """Landing page"""
    return redirect('/stall10nsimple')

@app.route('/stall10nsimple')
def stall10n_simple():
    """Stall10n Simple - XML analysis page"""
    today = datetime.now().date()
    return render_template('index_unified.html', today=today)

@app.route('/api/upload-and-analyze', methods=['POST'])
def upload_and_analyze():
    """Handle XML/ZIP upload, processing, and return full analysis data"""
    try:
        if 'pdf' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
        
        file = request.files['pdf']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        filename_lower = file.filename.lower()
        if not (filename_lower.endswith('.xml') or filename_lower.endswith('.zip')):
            return jsonify({'success': False, 'error': 'File must be an XML or ZIP file'}), 400
        
        # Save file temporarily
        suffix = '.zip' if filename_lower.endswith('.zip') else '.xml'
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_file:
            file.save(tmp_file.name)
            tmp_path = tmp_file.name
        
        # Handle ZIP files
        if filename_lower.endswith('.zip'):
            # Extract XML from ZIP
            xml_path = None
            try:
                with zipfile.ZipFile(tmp_path, 'r') as zip_file:
                    # Find XML file in ZIP
                    xml_files = [f for f in zip_file.namelist() if f.lower().endswith('.xml')]
                    if not xml_files:
                        return jsonify({'success': False, 'error': 'No XML file found in ZIP'}), 400
                    
                    # Extract the first XML file
                    xml_filename = xml_files[0]
                    with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as xml_tmp:
                        xml_tmp.write(zip_file.read(xml_filename))
                        xml_path = xml_tmp.name
                
                # Clean up ZIP file
                os.unlink(tmp_path)
                tmp_path = xml_path
            except Exception as e:
                logger.error(f"Error extracting XML from ZIP: {e}")
                if xml_path and os.path.exists(xml_path):
                    os.unlink(xml_path)
                return jsonify({'success': False, 'error': f'Error extracting XML from ZIP: {str(e)}'}), 400
        
        # Parse the XML file
        parser = EquibasePDFParser()
        races = parser.parse_pdf_file(tmp_path)
        
        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except:
            pass
        
        if not races:
            return jsonify({'success': False, 'error': 'No races found in XML'}), 400
            
        logger.info(f"Parsed {len(races)} races from XML")
        
        # Get the date from form data (if provided) or use the XML date
        form_date = request.form.get('date')
        if form_date:
            # Override XML date with user-selected date
            for race in races:
                race['race_date'] = form_date
        
        # Save to database and analyze
        analyzer = RaceAnalyzer()
        total_entries = 0
        analysis_results = []
        
        for race in races:
            # Prepare race data with all fields
            race_data = {
                'date': race['race_date'],
                'race_number': race['race_number'],
                'track_name': race['track'],
                'track_code': race.get('track_code', race['track']),
                'country': race.get('country', 'USA'),
                'distance': race.get('distance'),
                'dist_unit': race.get('dist_unit', 'F'),
                'dist_disp': race.get('dist_disp'),
                'surface': race.get('surface', 'D'),
                'course_id': race.get('course_id', 'D'),
                'race_type': race.get('race_type'),
                'stk_clm_md': race.get('stk_clm_md'),
                'stkorclm': race.get('stkorclm'),
                'purse': race.get('purse'),
                'claimamt': race.get('claimamt'),
                'post_time': race.get('post_time'),
                'age_restr': race.get('age_restr'),
                'sex_restriction': race.get('sex_restriction'),
                'race_conditions': race.get('race_conditions'),
                'betting_options': race.get('betting_options'),
                'track_record': race.get('track_record'),
                'partim': race.get('partim'),
                'raceord': race.get('raceord'),
                'breed_type': race.get('breed_type', 'TB'),
                'todays_cls': race.get('todays_cls'),
                'pdf_filename': secure_filename(file.filename)
            }
            race_id = db.save_race(race_data)
            
            # Prepare race analysis data
            race_analysis = {
                'race_id': race_id,
                'race_number': race['race_number'],
                'track_name': race['track'],
                'date': race['race_date'],
                'distance': race.get('dist_disp') or race.get('distance'),
                'race_type': race.get('race_type'),
                'purse': race.get('purse'),
                'post_time': race.get('post_time'),
                'entries': []
            }
            
            # Save and analyze entries
            for entry in race['entries']:
                # Prepare entry data with all fields
                entry_data = {
                    'race_id': race_id,
                    'program_number': entry['program_number'],
                    'post_position': entry.get('post_position', entry['program_number']),
                    'horse_name': entry['horse_name'],
                    'owner_name': entry.get('owner_name'),
                    'sex': entry.get('sex'),
                    'age': entry.get('age'),
                    'foal_date': entry.get('foal_date'),
                    'color': entry.get('color'),
                    'breed_type': entry.get('breed_type', 'TB'),
                    'breeder': entry.get('breeder'),
                    'where_bred': entry.get('where_bred'),
                    'weight': entry.get('weight'),
                    'weight_shift': entry.get('weight_shift', 0),
                    'medication': entry.get('medication'),
                    'equipment': entry.get('equipment'),
                    'morning_line_odds': entry.get('morning_line_odds'),
                    'claiming_price': entry.get('claiming_price'),
                    'power_rating': entry.get('power_rating'),
                    'power_symb': entry.get('power_symb'),
                    'avg_speed': entry.get('avg_speed'),
                    'avg_class': entry.get('avg_class'),
                    'todays_cls': entry.get('todays_cls'),
                    'last_speed': entry.get('last_speed'),
                    'best_speed': entry.get('best_speed'),
                    'class_rating': entry.get('class_rating'),
                    'pstyerl': entry.get('pstyerl'),
                    'pstymid': entry.get('pstymid'),
                    'pstyfin': entry.get('pstyfin'),
                    'pstynum': entry.get('pstynum'),
                    'pstyoff': entry.get('pstyoff'),
                    'psprstyerl': entry.get('psprstyerl'),
                    'psprstymid': entry.get('psprstymid'),
                    'psprstyfin': entry.get('psprstyfin'),
                    'psprstynum': entry.get('psprstynum'),
                    'psprstyoff': entry.get('psprstyoff'),
                    'prtestyerl': entry.get('prtestyerl'),
                    'prtestymid': entry.get('prtestymid'),
                    'prtestyfin': entry.get('prtestyfin'),
                    'prtestynum': entry.get('prtestynum'),
                    'prtestyoff': entry.get('prtestyoff'),
                    'pallstyerl': entry.get('pallstyerl'),
                    'pallstymid': entry.get('pallstymid'),
                    'pallstyfin': entry.get('pallstyfin'),
                    'pallstynum': entry.get('pallstynum'),
                    'pallstyoff': entry.get('pallstyoff'),
                    'pfigerl': entry.get('pfigerl'),
                    'pfigmid': entry.get('pfigmid'),
                    'pfigfin': entry.get('pfigfin'),
                    'pfignum': entry.get('pfignum'),
                    'pfigoff': entry.get('pfigoff'),
                    'psprfigerl': entry.get('psprfigerl'),
                    'psprfigmid': entry.get('psprfigmid'),
                    'psprfigfin': entry.get('psprfigfin'),
                    'psprfignum': entry.get('psprfignum'),
                    'psprfigoff': entry.get('psprfigoff'),
                    'prtefigerl': entry.get('prtefigerl'),
                    'prtefigmid': entry.get('prtefigmid'),
                    'prtefigfin': entry.get('prtefigfin'),
                    'prtefignum': entry.get('prtefignum'),
                    'prtefigoff': entry.get('prtefigoff'),
                    'pallfigerl': entry.get('pallfigerl'),
                    'pallfigmid': entry.get('pallfigmid'),
                    'pallfigfin': entry.get('pallfigfin'),
                    'pallfignum': entry.get('pallfignum'),
                    'pallfigoff': entry.get('pallfigoff'),
                    'tmmark': entry.get('tmmark'),
                    'av_pur_val': entry.get('av_pur_val'),
                    'ae_flag': entry.get('ae_flag'),
                    'horse_comment': entry.get('horse_comment'),
                    'lst_salena': entry.get('lst_salena'),
                    'lst_salepr': entry.get('lst_salepr'),
                    'lst_saleda': entry.get('lst_saleda'),
                    'apprweight': entry.get('apprweight'),
                    'axciskey': entry.get('axciskey'),
                    'avg_spd_sd': entry.get('avg_spd_sd'),
                    'ave_cl_sd': entry.get('ave_cl_sd'),
                    'hi_spd_sd': entry.get('hi_spd_sd'),
                    'jockey': entry.get('jockey'),
                    'trainer': entry.get('trainer'),
                    'win_pct': entry.get('win_pct'),
                    'jockey_win_pct': entry.get('jockey_win_pct'),
                    'trainer_win_pct': entry.get('trainer_win_pct'),
                    'jt_combo_pct': entry.get('jt_combo_pct')
                }
                entry_id = db.save_entry(entry_data)
                
                # Save horse statistics
                if 'horse_stats' in entry:
                    db.save_horse_stats(entry_id, entry['horse_stats'])
                
                # Save jockey information and statistics
                if 'jockey_data' in entry:
                    db.save_jockey_info_and_stats(entry_id, entry['jockey_data'])
                
                # Save trainer information and statistics
                if 'trainer_data' in entry:
                    db.save_trainer_info_and_stats(entry_id, entry['trainer_data'])
                
                # Save sire information and statistics
                if 'sire_data' in entry:
                    db.save_sire_info_and_stats(entry_id, entry['sire_data'])
                
                # Save dam information and statistics
                if 'dam_data' in entry:
                    db.save_dam_info_and_stats(entry_id, entry['dam_data'])
                
                # Save workouts
                if 'workouts' in entry:
                    db.save_workouts(entry_id, entry['workouts'])
                
                # Save past performance data
                if 'pp_data' in entry:
                    db.save_pp_data(entry_id, entry['pp_data'])
                
                # Analyze (simplified for compatibility)
                analysis_entry_data = {
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
                
                analysis = analyzer.analyze_entry(analysis_entry_data)
                analysis['entry_id'] = entry_id
                db.save_analysis(analysis)
                
                # Add to race entries with analysis
                entry_with_analysis = {
                    **analysis_entry_data,
                    'overall_score': analysis['overall_score'],
                    'speed_score': analysis['speed_score'],
                    'class_score': analysis['class_score'],
                    'jockey_score': analysis['jockey_score'],
                    'trainer_score': analysis['trainer_score'],
                    'recommendation': analysis['recommendation'],
                    'confidence': analysis['confidence'],
                    'power_rating': entry.get('power_rating'),
                    'morning_line_odds': entry.get('morning_line_odds'),
                    'weight': entry.get('weight'),
                    'medication': entry.get('medication'),
                    'equipment': entry.get('equipment')
                }
                race_analysis['entries'].append(entry_with_analysis)
                
                total_entries += 1
            
            # Sort entries by score
            race_analysis['entries'].sort(key=lambda x: x['overall_score'], reverse=True)
            analysis_results.append(race_analysis)
        
        return jsonify({
            'success': True,
            'races_count': len(races),
            'entries_count': total_entries,
            'analysis': analysis_results
        })
        
    except Exception as e:
        logger.error(f"Upload and analyze error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500

@app.route('/api/dates-with-data')
def get_dates_with_data():
    """Get all dates that have race data"""
    try:
        dates = db.get_dates_with_data()
        return jsonify({'success': True, 'dates': dates})
    except Exception as e:
        logger.error(f"Error fetching dates: {e}")
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

@app.route('/api/clear-all-data', methods=['DELETE'])
def clear_all_data():
    """Clear all data from the database"""
    try:
        db.clear_all_data()
        return jsonify({
            'success': True,
            'message': 'All data cleared from database'
        })
    except Exception as e:
        logger.error(f"Error clearing data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    health_status = {
        'server': 'ok',
        'timestamp': datetime.now().isoformat(),
        'database': 'unknown',
        'xml_parser': 'ok'
    }
    
    # Test database connection
    try:
        with db.get_cursor() as cur:
            cur.execute('SELECT 1')
            health_status['database'] = 'ok'
    except Exception as e:
        health_status['database'] = f'error: {str(e)}'
    
    return jsonify(health_status)

# Initialize database tables on startup
try:
    db.create_tables()
    logger.info("XML database tables created/verified successfully")
except Exception as e:
    logger.error(f"Database initialization error: {e}", exc_info=True)
    logger.error("Application will continue but database operations may fail")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)