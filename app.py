from flask import Flask, render_template, jsonify, request, redirect, url_for
from datetime import datetime
import os
import logging
from werkzeug.utils import secure_filename
import tempfile
import requests
from requests.auth import HTTPBasicAuth

from database import Database
from pdf_parser import EquibasePDFParser
from analyzer import RaceAnalyzer

app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database
db = Database(os.environ.get('DATABASE_URL', 'postgresql://localhost/racingsimple'))

@app.route('/')
def index():
    """Landing page with choice between Simple and Complex"""
    return render_template('landing.html')

@app.route('/stall10nsimple')
def stall10n_simple():
    """Stall10n Simple - PDF analysis page"""
    today = datetime.now().date()
    return render_template('index.html', today=today)

@app.route('/stall10ncomplex')
def stall10n_complex():
    """Stall10n Complex - Fair Meadows Tulsa recommendations page"""
    HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>STALL10N Complex - Fair Meadows Tulsa</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 0;
            background: #f5f5f5;
            color: #333;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            text-align: center;
            margin-bottom: 2rem;
            background: white;
            padding: 2rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #4CAF50;
            margin-bottom: 0.5rem;
        }
        .subtitle {
            color: #666;
        }
        .loading {
            text-align: center;
            padding: 3rem;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .error {
            background: #ffebee;
            color: #c62828;
            padding: 1rem;
            border-radius: 4px;
            margin-bottom: 1rem;
        }
        .no-races {
            text-align: center;
            padding: 3rem;
            background: white;
            border-radius: 8px;
            color: #666;
        }
        .race-card {
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            margin-bottom: 1.5rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .race-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
            padding-bottom: 1rem;
            border-bottom: 2px solid #f0f0f0;
        }
        .race-info {
            color: #666;
            font-size: 0.9rem;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th {
            background: #f0f0f0;
            padding: 0.75rem;
            text-align: left;
            font-weight: 600;
        }
        td {
            padding: 0.75rem;
            border-bottom: 1px solid #eee;
        }
        tr:hover {
            background: #f9f9f9;
        }
        .horse-name {
            font-weight: bold;
        }
        .score {
            font-weight: bold;
            font-size: 1.1rem;
        }
        .badge {
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: bold;
            display: inline-block;
        }
        .strong-play {
            background: #4CAF50;
            color: white;
        }
        .play {
            background: #2196F3;
            color: white;
        }
        .consider {
            background: #FF9800;
            color: white;
        }
        .pass {
            background: #9E9E9E;
            color: white;
        }
        .refresh-btn {
            background: #4CAF50;
            color: white;
            border: none;
            padding: 0.5rem 1.5rem;
            border-radius: 4px;
            cursor: pointer;
            font-size: 1rem;
        }
        .refresh-btn:hover {
            background: #45a049;
        }
        .top-plays {
            background: #e8f5e9;
            padding: 1rem;
            border-radius: 4px;
            margin-bottom: 2rem;
        }
        .top-plays h3 {
            margin-top: 0;
            color: #2e7d32;
        }
        .best-bets {
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
        }
        .best-bet {
            background: white;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            border: 2px solid #4CAF50;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>STALL10N Complex</h1>
            <p class="subtitle">Fair Meadows Tulsa - Live Race Recommendations</p>
            <button class="refresh-btn" onclick="loadRaces()">Refresh Data</button>
        </div>
        
        <div id="content">
            <div class="loading">Loading Fair Meadows races...</div>
        </div>
    </div>
    
    <script>
    async function loadRaces() {
        const contentDiv = document.getElementById('content');
        contentDiv.innerHTML = '<div class="loading">Loading Fair Meadows races...</div>';
        
        try {
            const response = await fetch('/api/fair-meadows-races');
            const data = await response.json();
            
            if (!data.success) {
                let errorMsg = `<div class="error">
                    <strong>Error:</strong> ${data.error}<br>`;
                if (data.details) {
                    errorMsg += `<strong>Details:</strong> ${data.details}<br>`;
                }
                if (data.credentials_configured === false) {
                    errorMsg += `<br><strong>Note:</strong> API credentials are not configured. Please ensure RACING_API_USERNAME and RACING_API_PASSWORD environment variables are set on Render.`;
                }
                errorMsg += `</div>`;
                contentDiv.innerHTML = errorMsg;
                return;
            }
            
            if (!data.races || data.races.length === 0) {
                let noRacesMsg = '<div class="no-races">';
                noRacesMsg += data.message || 'No Fair Meadows races scheduled for today.';
                if (data.available_tracks && data.available_tracks.length > 0) {
                    noRacesMsg += '<br><br><strong>Available tracks today:</strong><br>';
                    noRacesMsg += data.available_tracks.join('<br>');
                }
                noRacesMsg += '</div>';
                contentDiv.innerHTML = noRacesMsg;
                return;
            }
            
            // Find top plays across all races
            const topPlays = [];
            data.races.forEach(race => {
                race.entries.forEach(entry => {
                    if (entry.score >= 70) {
                        topPlays.push({
                            race_number: race.race_number,
                            ...entry
                        });
                    }
                });
            });
            
            let html = '';
            
            // Show top plays if any
            if (topPlays.length > 0) {
                const sortedPlays = topPlays.sort((a, b) => b.score - a.score).slice(0, 5);
                html += `
                    <div class="top-plays">
                        <h3>🎯 Today's Best Bets at Fair Meadows</h3>
                        <div class="best-bets">
                            ${sortedPlays.map(play => 
                                `<div class="best-bet">R${play.race_number} - #${play.post_position} ${play.horse_name} (${play.score})</div>`
                            ).join('')}
                        </div>
                    </div>
                `;
            }
            
            // Display each race
            data.races.forEach(race => {
                html += `
                    <div class="race-card">
                        <div class="race-header">
                            <div>
                                <h2>Race ${race.race_number}</h2>
                                <div class="race-info">
                                    ${race.race_time || 'Time TBA'} | 
                                    ${race.distance || 'Distance TBA'} | 
                                    ${race.race_type || 'Type TBA'} | 
                                    Purse: $${race.purse || 'TBA'}
                                </div>
                            </div>
                            <div class="race-info">${data.track}</div>
                        </div>
                        
                        <table>
                            <thead>
                                <tr>
                                    <th>PP</th>
                                    <th>Horse</th>
                                    <th>Jockey / Trainer</th>
                                    <th>ML Odds</th>
                                    <th>Form</th>
                                    <th>Score</th>
                                    <th>Recommendation</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${race.entries.map(entry => `
                                    <tr>
                                        <td>${entry.post_position}</td>
                                        <td class="horse-name">${entry.horse_name}</td>
                                        <td>
                                            <div>${entry.jockey || '-'}</div>
                                            <div style="font-size: 0.85rem; color: #666;">${entry.trainer || '-'}</div>
                                        </td>
                                        <td>${entry.morning_line_odds || '-'}</td>
                                        <td>${entry.recent_form || '-'}</td>
                                        <td class="score">${entry.score}</td>
                                        <td>
                                            <span class="badge ${entry.recommendation.toLowerCase().replace(' ', '-')}">${entry.recommendation}</span>
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                `;
            });
            
            contentDiv.innerHTML = html;
            
        } catch (error) {
            contentDiv.innerHTML = `<div class="error">Error loading races: ${error.message}</div>`;
        }
    }
    
    // Load races on page load
    loadRaces();
    
    // Auto-refresh every 5 minutes
    setInterval(loadRaces, 5 * 60 * 1000);
    </script>
</body>
</html>
"""
    return HTML_TEMPLATE

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

@app.route('/api/upload-and-analyze', methods=['POST'])
def upload_and_analyze():
    """Handle PDF upload, processing, and return full analysis data"""
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
        analysis_results = []
        
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
            
            # Prepare race analysis data
            race_analysis = {
                'race_id': race_id,
                'race_number': race['race_number'],
                'track_name': race['track'],
                'distance': race.get('distance'),
                'race_type': race.get('race_type'),
                'purse': race.get('purse'),
                'post_time': race.get('post_time'),
                'entries': []
            }
            
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
                
                # Add to race entries with analysis
                entry_with_analysis = {
                    **entry_data,
                    'overall_score': analysis['overall_score'],
                    'speed_score': analysis['speed_score'],
                    'class_score': analysis['class_score'],
                    'jockey_score': analysis['jockey_score'],
                    'trainer_score': analysis['trainer_score'],
                    'recommendation': analysis['recommendation'],
                    'confidence': analysis['confidence']
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


@app.route('/api/fair-meadows-races')
def get_fair_meadows_races():
    """Get today's races from Fair Meadows Tulsa via TheRacingAPI"""
    try:
        # Get API credentials from environment
        base_url = os.environ.get('RACING_API_BASE_URL', 'https://api.theracingapi.com/v1')
        username = os.environ.get('RACING_API_USERNAME')
        password = os.environ.get('RACING_API_PASSWORD')
        
        if not username or not password:
            return jsonify({'success': False, 'error': 'API credentials not configured'}), 500
        
        # Get today's date
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Get meets for today
        # Fix: Remove /v1 from base_url if it's included, as we'll add it in the path
        if base_url.endswith('/v1'):
            base_url = base_url[:-3]
        meets_url = f"{base_url}/v1/north-america/meets"
        params = {
            'start_date': today,
            'end_date': today
        }
        
        auth = HTTPBasicAuth(username, password)
        meets_response = requests.get(meets_url, params=params, auth=auth)
        meets_response.raise_for_status()
        meets_data = meets_response.json()
        
        # Find Fair Meadows meet
        fair_meadows_meet = None
        all_tracks = []
        
        for meet in meets_data.get('meets', []):
            track = meet.get('track', '')
            all_tracks.append(track)
            # More flexible search for Fair Meadows variations
            if any(term in track.upper() for term in ['FAIR MEADOWS', 'FMT', 'FAIRMEADOWS', 'TULSA']):
                fair_meadows_meet = meet
                break
        
        if not fair_meadows_meet:
            # Return list of all available tracks for debugging
            return jsonify({
                'success': True,
                'message': f'No Fair Meadows races found today. Available tracks: {", ".join(all_tracks)}',
                'races': [],
                'available_tracks': all_tracks,
                'total_meets': len(meets_data.get('meets', []))
            })
        
        # Get entries for Fair Meadows meet
        meet_id = fair_meadows_meet['meet_id']
        entries_url = f"{base_url}/v1/north-america/meets/{meet_id}/entries"
        entries_response = requests.get(entries_url, auth=auth)
        entries_response.raise_for_status()
        entries_data = entries_response.json()
        
        # Process races and entries
        races_with_analysis = []
        for race in entries_data.get('races', []):
            race_info = {
                'race_number': race.get('race_number'),
                'race_time': race.get('race_time'),
                'distance': race.get('distance'),
                'race_type': race.get('race_type'),
                'purse': race.get('purse'),
                'entries': []
            }
            
            # Analyze each entry
            for entry in race.get('entries', []):
                # Simple scoring based on available data
                score = 50  # Base score
                
                # Adjust based on morning line odds
                ml_odds = entry.get('morning_line_odds', 10)
                if ml_odds < 3:
                    score += 20
                elif ml_odds < 5:
                    score += 15
                elif ml_odds < 10:
                    score += 10
                
                # Adjust based on recent form
                recent_form = entry.get('recent_form', '')
                wins = recent_form.count('1')
                places = recent_form.count('2')
                shows = recent_form.count('3')
                score += (wins * 10) + (places * 5) + (shows * 2)
                
                # Determine recommendation
                if score >= 80:
                    recommendation = 'STRONG PLAY'
                elif score >= 70:
                    recommendation = 'PLAY'
                elif score >= 60:
                    recommendation = 'CONSIDER'
                else:
                    recommendation = 'PASS'
                
                entry_info = {
                    'post_position': entry.get('post_position'),
                    'horse_name': entry.get('horse_name'),
                    'jockey': entry.get('jockey_name'),
                    'trainer': entry.get('trainer_name'),
                    'morning_line_odds': ml_odds,
                    'recent_form': recent_form,
                    'score': score,
                    'recommendation': recommendation
                }
                race_info['entries'].append(entry_info)
            
            # Sort entries by score
            race_info['entries'].sort(key=lambda x: x['score'], reverse=True)
            races_with_analysis.append(race_info)
        
        return jsonify({
            'success': True,
            'track': fair_meadows_meet.get('track'),
            'date': fair_meadows_meet.get('date'),
            'races': races_with_analysis
        })
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Racing API error: {e}")
        logger.error(f"API URL attempted: {meets_url if 'meets_url' in locals() else 'Not set'}")
        logger.error(f"API credentials present: username={bool(username)}, password={bool(password)}")
        return jsonify({
            'success': False, 
            'error': 'Failed to fetch racing data',
            'details': str(e),
            'credentials_configured': bool(username and password)
        }), 500
    except Exception as e:
        logger.error(f"Fair Meadows races error: {e}")
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