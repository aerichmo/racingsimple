"""
Flask endpoints for race data pulling and viewing
Add these to your app.py
"""

from flask import jsonify, request
from race_data_puller import RaceDataPuller
from datetime import datetime, timedelta
import logging
import psycopg2

logger = logging.getLogger(__name__)

def add_race_data_endpoints(app):
    """
    Add these endpoints to your existing Flask app
    """
    
    puller = RaceDataPuller()
    
    @app.route('/api/pull-race-data', methods=['POST'])
    def pull_race_data():
        """
        Manually trigger race data pull
        Example: POST /api/pull-race-data
        Body: {
            "track_name": "Fair Meadows",
            "race_date": "2025-06-14",
            "race_number": 3,
            "api_race_id": "12345",
            "current_race_id": "12346"
        }
        """
        try:
            data = request.get_json()
            
            results = puller.pull_race_data(
                track_name=data['track_name'],
                race_date=data['race_date'],
                race_number=data['race_number'],
                api_race_id=data.get('api_race_id'),
                current_race_id=data.get('current_race_id')
            )
            
            return jsonify({
                'success': True,
                'results': results
            })
            
        except Exception as e:
            logger.error(f"Error pulling race data: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/race-results/<date>')
    def get_race_results(date):
        """
        Get race results for a specific date
        Example: GET /api/race-results/2025-06-12
        """
        try:
            conn = psycopg2.connect(puller.db_url)
            cur = conn.cursor()
            
            cur.execute('''
                SELECT track_name, race_number, distance,
                       winner_horse_name, winner_jockey, winner_odds,
                       exacta_payout, data_pulled_at
                FROM race_results
                WHERE race_date = %s
                ORDER BY track_name, race_number
            ''', (date,))
            
            results = []
            for row in cur.fetchall():
                results.append({
                    'track': row[0],
                    'race_number': row[1],
                    'distance': row[2],
                    'winner': row[3],
                    'jockey': row[4],
                    'odds': row[5],
                    'exacta': row[6],
                    'pulled_at': row[7].isoformat() if row[7] else None
                })
            
            cur.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'date': date,
                'results': results
            })
            
        except Exception as e:
            logger.error(f"Error fetching results: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/live-odds/<track>/<int:race_number>')
    def get_live_odds(track, race_number):
        """
        Get latest live odds snapshot for a race
        Example: GET /api/live-odds/Fair%20Meadows/3
        """
        try:
            conn = psycopg2.connect(puller.db_url)
            cur = conn.cursor()
            
            # Get the most recent snapshot
            cur.execute('''
                SELECT DISTINCT ON (program_number)
                       program_number, horse_name, jockey, trainer,
                       morning_line, live_odds, win_probability,
                       snapshot_taken_at
                FROM live_odds_snapshot
                WHERE track_name = %s 
                  AND race_number = %s
                  AND race_date = CURRENT_DATE
                ORDER BY program_number, snapshot_taken_at DESC
            ''', (track, race_number))
            
            horses = []
            for row in cur.fetchall():
                horses.append({
                    'program_number': row[0],
                    'horse_name': row[1],
                    'jockey': row[2],
                    'trainer': row[3],
                    'morning_line': row[4],
                    'live_odds': row[5],
                    'win_probability': float(row[6]) if row[6] else None,
                    'snapshot_time': row[7].isoformat() if row[7] else None
                })
            
            cur.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'track': track,
                'race_number': race_number,
                'horses': horses
            })
            
        except Exception as e:
            logger.error(f"Error fetching live odds: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/schedule-race', methods=['POST'])
    def schedule_race():
        """
        Schedule a race for automatic data pulling
        Example: POST /api/schedule-race
        Body: {
            "track_name": "Fair Meadows",
            "race_date": "2025-06-14",
            "race_number": 3,
            "post_time": "2025-06-14 18:45:00",
            "api_race_id": "12345"
        }
        """
        try:
            data = request.get_json()
            
            conn = psycopg2.connect(puller.db_url)
            cur = conn.cursor()
            
            cur.execute('''
                INSERT INTO race_schedule (
                    race_date, track_name, race_number,
                    scheduled_post_time, api_race_id
                ) VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (race_date, track_name, race_number)
                DO UPDATE SET
                    scheduled_post_time = EXCLUDED.scheduled_post_time,
                    api_race_id = EXCLUDED.api_race_id
            ''', (
                data['race_date'],
                data['track_name'],
                data['race_number'],
                data['post_time'],
                data.get('api_race_id')
            ))
            
            conn.commit()
            cur.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': f"Scheduled {data['track_name']} Race {data['race_number']} for automatic data pull"
            })
            
        except Exception as e:
            logger.error(f"Error scheduling race: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/upcoming-pulls')
    def get_upcoming_pulls():
        """
        Get races scheduled for data pulling in the next hour
        """
        try:
            races = puller.get_races_needing_data_pull(minutes_before=60)
            
            upcoming = []
            for race in races:
                upcoming.append({
                    'date': race[0].isoformat() if race[0] else None,
                    'track': race[1],
                    'race_number': race[2],
                    'post_time': race[3].isoformat() if race[3] else None,
                    'api_race_id': race[4]
                })
            
            # Get quota status
            quota = puller.odds_service.get_quota_status()
            
            return jsonify({
                'success': True,
                'upcoming_races': upcoming,
                'quota_status': {
                    'remaining': quota['remaining'],
                    'limit': quota['daily_limit'],
                    'used_today': quota['calls_today']
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting upcoming pulls: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500


# Add to your admin interface HTML
admin_race_data_section = '''
<!-- Add this section to your admin page -->
<div class="section">
    <h3>Race Data Management</h3>
    
    <!-- Schedule Race for Auto-Pull -->
    <div class="form-group">
        <h4>Schedule Race for Automatic Data Pull</h4>
        <p>Data will be pulled 10 minutes before post time</p>
        
        <label>Track Name:</label>
        <input type="text" id="scheduleTrack" placeholder="Fair Meadows" />
        
        <label>Race Date:</label>
        <input type="date" id="scheduleDate" />
        
        <label>Race Number:</label>
        <input type="number" id="scheduleRaceNum" min="1" max="15" />
        
        <label>Post Time:</label>
        <input type="datetime-local" id="schedulePostTime" />
        
        <label>API Race ID (if known):</label>
        <input type="text" id="scheduleApiId" placeholder="Optional" />
        
        <button onclick="scheduleRace()">Schedule Race</button>
    </div>
    
    <!-- Manual Data Pull -->
    <div class="form-group">
        <h4>Manual Data Pull</h4>
        <p>Manually trigger data pull (uses API quota)</p>
        
        <label>Track:</label>
        <input type="text" id="pullTrack" placeholder="Fair Meadows" />
        
        <label>Date:</label>
        <input type="date" id="pullDate" />
        
        <label>Race Number:</label>
        <input type="number" id="pullRaceNum" min="1" max="15" />
        
        <label>Previous Race API ID:</label>
        <input type="text" id="pullPrevId" placeholder="For results" />
        
        <label>Current Race API ID:</label>
        <input type="text" id="pullCurrId" placeholder="For live odds" />
        
        <button onclick="pullRaceData()">Pull Data Now</button>
    </div>
    
    <!-- Upcoming Pulls -->
    <div class="form-group">
        <h4>Upcoming Automatic Pulls</h4>
        <div id="upcomingPulls"></div>
        <button onclick="loadUpcomingPulls()">Refresh</button>
    </div>
</div>

<script>
async function scheduleRace() {
    const data = {
        track_name: document.getElementById('scheduleTrack').value,
        race_date: document.getElementById('scheduleDate').value,
        race_number: parseInt(document.getElementById('scheduleRaceNum').value),
        post_time: document.getElementById('schedulePostTime').value.replace('T', ' ') + ':00',
        api_race_id: document.getElementById('scheduleApiId').value || null
    };
    
    try {
        const response = await fetch('/api/schedule-race', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        if (result.success) {
            alert('Race scheduled successfully!');
            loadUpcomingPulls();
        } else {
            alert('Error: ' + result.error);
        }
    } catch (error) {
        alert('Error: ' + error);
    }
}

async function pullRaceData() {
    const data = {
        track_name: document.getElementById('pullTrack').value,
        race_date: document.getElementById('pullDate').value,
        race_number: parseInt(document.getElementById('pullRaceNum').value),
        api_race_id: document.getElementById('pullPrevId').value || null,
        current_race_id: document.getElementById('pullCurrId').value || null
    };
    
    try {
        const response = await fetch('/api/pull-race-data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        if (result.success) {
            alert(`Data pulled! Quota remaining: ${result.results.quota_remaining}`);
        } else {
            alert('Error: ' + result.error);
        }
    } catch (error) {
        alert('Error: ' + error);
    }
}

async function loadUpcomingPulls() {
    try {
        const response = await fetch('/api/upcoming-pulls');
        const data = await response.json();
        
        if (data.success) {
            let html = `<p>API Quota: ${data.quota_status.remaining}/${data.quota_status.limit} remaining</p>`;
            
            if (data.upcoming_races.length > 0) {
                html += '<table><tr><th>Track</th><th>Race</th><th>Post Time</th></tr>';
                data.upcoming_races.forEach(race => {
                    html += `<tr>
                        <td>${race.track}</td>
                        <td>${race.race_number}</td>
                        <td>${new Date(race.post_time).toLocaleString()}</td>
                    </tr>`;
                });
                html += '</table>';
            } else {
                html += '<p>No races scheduled</p>';
            }
            
            document.getElementById('upcomingPulls').innerHTML = html;
        }
    } catch (error) {
        console.error('Error loading upcoming pulls:', error);
    }
}

// Load on page load
loadUpcomingPulls();
</script>
'''