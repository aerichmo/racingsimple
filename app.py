from flask import Flask, request, jsonify, render_template_string
import os
import psycopg2
from psycopg2 import sql
from datetime import datetime
import json
import base64
from io import BytesIO
from otb_scraper import OTBScraper
import logging

app = Flask(__name__)

@app.route('/')
def hello():
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>STALL10N Horse Racing</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            background-color: #FFFFFF;
            color: #001E60;
            line-height: 1.6;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        h1 { 
            color: #0053E2;
            font-size: 2.5rem;
            margin-bottom: 30px;
            text-align: center;
            font-weight: 300;
            letter-spacing: 2px;
            text-transform: uppercase;
        }
        h2 {
            color: #001E60;
            font-size: 1.8rem;
            margin: 30px 0 15px;
            font-weight: 400;
            border-bottom: 2px solid #0053E2;
            padding-bottom: 10px;
        }
        h3 {
            color: #0053E2;
            font-size: 1.3rem;
            margin: 20px 0 10px;
            font-weight: 400;
        }
        .race-date { 
            margin: 40px 0;
            background: #FFFFFF;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 5px 20px rgba(0, 30, 96, 0.1);
            border: 1px solid #A9DDF7;
        }
        table { 
            border-collapse: collapse; 
            width: 100%; 
            margin: 20px 0;
            background-color: #FFFFFF;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 3px 15px rgba(0, 30, 96, 0.1);
            border: 1px solid #A9DDF7;
        }
        th, td { 
            padding: 15px;
            text-align: center;
            width: 16.66%;
        }
        th { 
            background-color: #0053E2;
            color: #FFFFFF;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-size: 0.9rem;
            border-bottom: 3px solid #4DBDF5;
        }
        td {
            background-color: #FFFFFF;
            border-bottom: 1px solid #A9DDF7;
            font-weight: 400;
            color: #001E60;
        }
        tr:hover td {
            background-color: #A9DDF7;
            transition: background-color 0.3s ease;
        }
        tr:last-child td {
            border-bottom: none;
        }
        .program-number {
            font-weight: 700;
            color: #4DBDF5;
        }
        .horse-name {
            font-weight: 500;
            color: #001E60;
        }
        .probability {
            color: #001E60;
        }
        .adj-odds {
            color: #0053E2;
            font-weight: 600;
        }
        .morning-line {
            color: #001E60;
        }
        .realtime-odds {
            color: #0053E2;
            font-weight: 500;
        }
        .bet-recommendation {
            margin: 20px 0;
            padding: 20px;
            background-color: #A9DDF7;
            border-radius: 10px;
            color: #001E60;
        }
        .bet-recommendation h4 {
            color: #0053E2;
            margin-bottom: 10px;
            font-size: 1.1rem;
            font-weight: 600;
        }
        .bet-recommendation p {
            font-size: 1rem;
            line-height: 1.6;
        }
        .date-selector {
            text-align: center;
            margin-bottom: 30px;
        }
        .date-selector label {
            font-size: 1.1rem;
            color: #001E60;
            margin-right: 10px;
            font-weight: 500;
        }
        .date-selector select {
            padding: 10px 20px;
            font-size: 1rem;
            border: 2px solid #0053E2;
            border-radius: 8px;
            background-color: #FFFFFF;
            color: #001E60;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .date-selector select:hover {
            background-color: #A9DDF7;
        }
        .date-selector select:focus {
            outline: none;
            box-shadow: 0 0 0 3px rgba(0, 83, 226, 0.2);
        }
        .no-data { 
            color: #001E60; 
            font-style: italic;
            text-align: center;
            padding: 50px;
            font-size: 1.2rem;
        }
        @media (max-width: 768px) {
            .container {
                padding: 10px;
            }
            h1 {
                font-size: 1.8rem;
            }
            h2 {
                font-size: 1.4rem;
            }
            h3 {
                font-size: 1.1rem;
            }
            th, td {
                padding: 10px 5px;
                font-size: 0.9rem;
            }
            .race-date {
                padding: 20px 15px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>STALL10N</h1>
        <div style="text-align: center; margin-bottom: 20px;">
            <a href="/admin" style="color: #0053E2; text-decoration: none; font-weight: 600;">Admin Panel →</a>
        </div>
        <div class="date-selector">
            <label for="raceDate">Select Date:</label>
            <select id="raceDate">
                <option value="">All Dates</option>
            </select>
        </div>
        <div id="races"></div>
    </div>
    <script>
        let allRaceData = [];
        
        function renderRaces(selectedDate = '') {
            const container = document.getElementById('races');
            const filteredData = selectedDate ? allRaceData.filter(race => race.race_date === selectedDate) : allRaceData;
            
            if (filteredData.length === 0) {
                container.innerHTML = '<p class="no-data">No race data available for the selected date.</p>';
                return;
            }
            
            const racesByDate = {};
            filteredData.forEach(race => {
                if (!racesByDate[race.race_date]) {
                    racesByDate[race.race_date] = [];
                }
                racesByDate[race.race_date].push(race);
            });
            
            let html = '';
            for (const [date, races] of Object.entries(racesByDate)) {
                html += `<div class="race-date"><h2>Date: ${date}</h2>`;
                
                const racesByNumber = {};
                races.forEach(race => {
                    if (!racesByNumber[race.race_number]) {
                        racesByNumber[race.race_number] = [];
                    }
                    racesByNumber[race.race_number].push(race);
                });
                
                for (const [raceNum, horses] of Object.entries(racesByNumber)) {
                    html += `<h3>Race ${raceNum}</h3>`;
                    html += `<table>
                        <tr>
                            <th>Program #</th>
                            <th>Horse Name</th>
                            <th>Win Probability</th>
                            <th>Adjusted Probability</th>
                            <th>Morning Line</th>
                        </tr>`;
                    
                    horses.forEach(horse => {
                        html += `<tr>
                            <td class="program-number">${horse.program_number}</td>
                            <td class="horse-name">${horse.horse_name}</td>
                            <td class="probability">${horse.win_probability}%</td>
                            <td class="adj-odds">${horse.adj_odds ? horse.adj_odds + '%' : '-'}</td>
                            <td class="morning-line">${horse.morning_line}</td>
                        </tr>`;
                    });
                    
                    html += '</table>';
                    
                    // Add bet recommendation section
                    const betRec = horses[0]?.bet_recommendation;
                    if (betRec) {
                        html += `<div class="bet-recommendation">
                            <h4>Bet Recommendation</h4>
                            <p>${betRec}</p>
                        </div>`;
                    }
                }
                html += '</div>';
            }
            container.innerHTML = html;
        }
        
        fetch('/api/races')
            .then(response => response.json())
            .then(data => {
                allRaceData = data;
                
                if (data.length === 0) {
                    document.getElementById('races').innerHTML = '<p class="no-data">No race data available yet.</p>';
                    return;
                }
                
                // Populate date dropdown
                const uniqueDates = [...new Set(data.map(race => race.race_date))].sort();
                const dateSelect = document.getElementById('raceDate');
                
                uniqueDates.forEach(date => {
                    const option = document.createElement('option');
                    option.value = date;
                    option.textContent = date;
                    dateSelect.appendChild(option);
                });
                
                // Set default to most recent date
                if (uniqueDates.length > 0) {
                    dateSelect.value = uniqueDates[uniqueDates.length - 1];
                    renderRaces(uniqueDates[uniqueDates.length - 1]);
                } else {
                    renderRaces();
                }
                
                // Add event listener for date changes
                dateSelect.addEventListener('change', (e) => {
                    renderRaces(e.target.value);
                });
            })
            .catch(error => {
                document.getElementById('races').innerHTML = `<p class="no-data">Error loading data: ${error}</p>`;
            });
    </script>
</body>
</html>
''')

@app.route('/clear-database-completely')
def clear_database():
    try:
        DATABASE_URL = os.environ.get('DATABASE_URL')
        if not DATABASE_URL:
            return 'No database configured'
        
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Get all table names
        cur.execute("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
        """)
        
        tables = cur.fetchall()
        
        # Drop all tables
        for table in tables:
            table_name = table[0]
            cur.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(
                sql.Identifier(table_name)
            ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return f'Database cleared - dropped {len(tables)} tables'
    except Exception as e:
        return f'Error: {str(e)}'

@app.route('/api/setup-database')
def setup_database():
    try:
        DATABASE_URL = os.environ.get('DATABASE_URL')
        if not DATABASE_URL:
            return jsonify({'error': 'No database configured'}), 500
        
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Create races table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS races (
                id SERIAL PRIMARY KEY,
                race_date DATE NOT NULL,
                race_number INTEGER NOT NULL,
                program_number INTEGER NOT NULL,
                horse_name VARCHAR(255) NOT NULL,
                win_probability DECIMAL(5,2),
                adj_odds DECIMAL(5,2),
                morning_line VARCHAR(50),
                realtime_odds VARCHAR(50),
                bet_recommendation TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Add new columns if they don't exist
        cur.execute('''
            ALTER TABLE races 
            ADD COLUMN IF NOT EXISTS adj_odds DECIMAL(5,2)
        ''')
        
        cur.execute('''
            ALTER TABLE races 
            ADD COLUMN IF NOT EXISTS realtime_odds VARCHAR(50)
        ''')
        
        cur.execute('''
            ALTER TABLE races 
            ADD COLUMN IF NOT EXISTS bet_recommendation TEXT
        ''')
        
        # Create index for faster queries
        cur.execute('''
            CREATE INDEX IF NOT EXISTS idx_race_date_number 
            ON races(race_date, race_number)
        ''')
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'message': 'Database setup completed successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/races', methods=['GET', 'POST'])
def races():
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        return jsonify({'error': 'No database configured'}), 500
    
    if request.method == 'POST':
        try:
            data = request.json
            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()
            
            # Insert race data
            cur.execute('''
                INSERT INTO races (race_date, race_number, program_number, 
                                 horse_name, win_probability, adj_odds, morning_line,
                                 realtime_odds, bet_recommendation)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                data['race_date'],
                data['race_number'],
                data['program_number'],
                data['horse_name'],
                data['win_probability'],
                data.get('adj_odds'),
                data['morning_line'],
                data.get('realtime_odds'),
                data.get('bet_recommendation')
            ))
            
            conn.commit()
            cur.close()
            conn.close()
            
            return jsonify({'message': 'Race data added successfully'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    else:  # GET
        try:
            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()
            
            cur.execute('''
                SELECT race_date, race_number, program_number, 
                       horse_name, win_probability, adj_odds, morning_line,
                       realtime_odds, bet_recommendation
                FROM races
                ORDER BY race_date, race_number, program_number
            ''')
            
            races = []
            for row in cur.fetchall():
                races.append({
                    'race_date': row[0].strftime('%Y-%m-%d'),
                    'race_number': row[1],
                    'program_number': row[2],
                    'horse_name': row[3],
                    'win_probability': float(row[4]) if row[4] else None,
                    'adj_odds': float(row[5]) if row[5] else None,
                    'morning_line': row[6],
                    'realtime_odds': row[7],
                    'bet_recommendation': row[8]
                })
            
            cur.close()
            conn.close()
            
            return jsonify(races)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@app.route('/api/races/<int:race_id>/adj-odds', methods=['PUT'])
def update_adj_odds(race_id):
    try:
        DATABASE_URL = os.environ.get('DATABASE_URL')
        if not DATABASE_URL:
            return jsonify({'error': 'No database configured'}), 500
        
        data = request.json
        adj_odds = data.get('adj_odds')
        
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        cur.execute('''
            UPDATE races 
            SET adj_odds = %s
            WHERE id = %s
        ''', (adj_odds, race_id))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'message': 'ADJ Odds updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/races/batch-adj-odds', methods=['POST'])
def batch_update_adj_odds():
    try:
        DATABASE_URL = os.environ.get('DATABASE_URL')
        if not DATABASE_URL:
            return jsonify({'error': 'No database configured'}), 500
        
        data = request.json
        updates = data.get('updates', [])
        
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        for update in updates:
            cur.execute('''
                UPDATE races 
                SET adj_odds = %s
                WHERE race_date = %s 
                AND race_number = %s 
                AND program_number = %s
            ''', (
                update['adj_odds'],
                update['race_date'],
                update['race_number'],
                update['program_number']
            ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'message': f'{len(updates)} ADJ Odds updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/races/batch', methods=['POST'])
def batch_races():
    try:
        DATABASE_URL = os.environ.get('DATABASE_URL')
        if not DATABASE_URL:
            return jsonify({'error': 'No database configured'}), 500
        
        data = request.json
        races = data.get('races', [])
        
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Insert multiple races at once
        for race in races:
            cur.execute('''
                INSERT INTO races (race_date, race_number, program_number, 
                                 horse_name, win_probability, adj_odds, morning_line,
                                 realtime_odds, bet_recommendation)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                race['race_date'],
                race['race_number'],
                race['program_number'],
                race['horse_name'],
                race['win_probability'],
                race.get('adj_odds'),
                race['morning_line'],
                race.get('realtime_odds'),
                race.get('bet_recommendation')
            ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'message': f'{len(races)} races added successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin')
def admin():
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>STALL10N Admin - Upload Race Data</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            background-color: #FFFFFF;
            color: #001E60;
            line-height: 1.6;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        h1 { 
            color: #0053E2;
            font-size: 2.5rem;
            margin-bottom: 30px;
            text-align: center;
            font-weight: 300;
            letter-spacing: 2px;
            text-transform: uppercase;
        }
        .upload-section {
            background: #FFFFFF;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 5px 20px rgba(0, 30, 96, 0.1);
            border: 1px solid #A9DDF7;
            margin-bottom: 30px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            font-weight: 600;
            color: #001E60;
            margin-bottom: 8px;
        }
        input[type="date"], input[type="number"], select {
            width: 100%;
            padding: 12px;
            border: 2px solid #A9DDF7;
            border-radius: 8px;
            font-size: 1rem;
            transition: border-color 0.3s;
        }
        input[type="date"]:focus, input[type="number"]:focus, select:focus {
            outline: none;
            border-color: #0053E2;
        }
        .file-upload {
            position: relative;
            display: inline-block;
            cursor: pointer;
            width: 100%;
        }
        .file-upload input[type=file] {
            position: absolute;
            opacity: 0;
            width: 100%;
            height: 100%;
            cursor: pointer;
        }
        .file-upload-label {
            display: block;
            padding: 15px;
            background-color: #A9DDF7;
            color: #001E60;
            text-align: center;
            border-radius: 8px;
            font-weight: 600;
            transition: background-color 0.3s;
        }
        .file-upload:hover .file-upload-label {
            background-color: #4DBDF5;
        }
        .selected-files {
            margin-top: 10px;
            font-size: 0.9rem;
            color: #0053E2;
        }
        .button {
            background-color: #0053E2;
            color: #FFFFFF;
            padding: 15px 30px;
            border: none;
            border-radius: 8px;
            font-size: 1.1rem;
            font-weight: 600;
            cursor: pointer;
            transition: background-color 0.3s;
            width: 100%;
            margin-top: 20px;
        }
        .button:hover {
            background-color: #001E60;
        }
        .button:disabled {
            background-color: #A9DDF7;
            cursor: not-allowed;
        }
        .preview-section {
            margin-top: 30px;
        }
        .preview-image {
            max-width: 100%;
            margin: 10px 0;
            border: 1px solid #A9DDF7;
            border-radius: 8px;
        }
        .status-message {
            padding: 15px;
            margin: 20px 0;
            border-radius: 8px;
            text-align: center;
            font-weight: 600;
        }
        .success {
            background-color: #4DBDF5;
            color: #FFFFFF;
        }
        .error {
            background-color: #FF6B6B;
            color: #FFFFFF;
        }
        .processing {
            background-color: #A9DDF7;
            color: #001E60;
        }
        .manual-entry {
            background: #F0F8FF;
            padding: 20px;
            border-radius: 10px;
            margin-top: 20px;
        }
        .race-entry {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
            margin-bottom: 15px;
            padding: 15px;
            background: #FFFFFF;
            border-radius: 8px;
            border: 1px solid #A9DDF7;
        }
        .race-entry input {
            padding: 8px;
            border: 1px solid #A9DDF7;
            border-radius: 4px;
        }
        .add-horse-btn {
            background-color: #4DBDF5;
            color: #FFFFFF;
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            margin-top: 10px;
        }
        .nav-link {
            display: inline-block;
            margin-bottom: 20px;
            color: #0053E2;
            text-decoration: none;
            font-weight: 600;
        }
        .nav-link:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="nav-link">← Back to Races</a>
        <h1>STALL10N Admin</h1>
        
        
        <div class="upload-section">
            <h2>Race Results Import</h2>
            <div style="background-color: #FFE5B4; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <p style="margin: 0 0 10px 0;"><strong>Data Source:</strong> OffTrackBetting.com Results</p>
                <button class="button" onclick="fetchRaceResults()" style="background-color: #FF6B35; margin-right: 10px;">
                    Fetch Today's Results
                </button>
                <button class="button" onclick="checkResultsStatus()" style="background-color: #6B8E23;">
                    Check Status
                </button>
                <div id="resultsStatus" style="margin-top: 10px;"></div>
            </div>
        </div>
        
        <div class="upload-section">
            <h2>Manual Race Entry</h2>
            <div style="background-color: #A9DDF7; padding: 10px; border-radius: 8px; margin-bottom: 20px;">
                <p style="margin: 0; font-size: 0.9rem;"><strong>Note:</strong> For June 12-14, this will override existing data. All entries go through SQL database and are automatically synced to Render.</p>
            </div>
            <div class="form-group">
                <label for="manualDate">Race Date:</label>
                <select id="manualDate">
                    <option value="2025-06-12">June 12, 2025 (Override)</option>
                    <option value="2025-06-13">June 13, 2025 (Override)</option>
                    <option value="2025-06-14">June 14, 2025 (Override)</option>
                    <option value="2025-06-18">June 18, 2025</option>
                    <option value="2025-06-19">June 19, 2025</option>
                    <option value="2025-06-20">June 20, 2025</option>
                    <option value="2025-06-21">June 21, 2025</option>
                </select>
            </div>
            
            <div class="form-group">
                <label for="raceNumber">Race Number:</label>
                <input type="number" id="raceNumber" min="1" max="20" value="1" />
            </div>
            
            <div class="manual-entry" id="manualEntries">
                <h3>Horses</h3>
                <div id="horseEntries"></div>
                <button class="add-horse-btn" onclick="addHorseEntry()">Add Horse</button>
            </div>
            
            <button class="button" onclick="submitManualRace()">Submit Race Data</button>
        </div>
        
        <div class="preview-section" id="previewSection"></div>
        
        <div class="upload-section">
            <h2>Update Bet Recommendations</h2>
            <div class="form-group">
                <label for="betDate">Race Date:</label>
                <select id="betDate">
                    <option value="2025-06-11">June 11, 2025</option>
                    <option value="2025-06-12">June 12, 2025</option>
                    <option value="2025-06-13">June 13, 2025</option>
                    <option value="2025-06-14">June 14, 2025</option>
                    <option value="2025-06-18">June 18, 2025</option>
                    <option value="2025-06-19">June 19, 2025</option>
                    <option value="2025-06-20">June 20, 2025</option>
                    <option value="2025-06-21">June 21, 2025</option>
                </select>
            </div>
            
            <div class="form-group">
                <label for="betRaceNumber">Race Number:</label>
                <input type="number" id="betRaceNumber" min="1" max="20" value="1" />
            </div>
            
            <div class="form-group">
                <label for="betRecommendation">Bet Recommendation:</label>
                <textarea id="betRecommendation" style="width: 100%; padding: 12px; border: 2px solid #A9DDF7; border-radius: 8px; font-size: 1rem; min-height: 100px;" placeholder="Enter bet recommendation for this race..."></textarea>
            </div>
            
            <button class="button" onclick="updateBetRecommendation()">Update Bet Recommendation</button>
        </div>
    </div>
    
    <script>
        function showStatus(message, type) {
            const statusDiv = document.getElementById('statusMessage');
            statusDiv.textContent = message;
            statusDiv.className = `status-message ${type}`;
        }
        
        // Manual entry functions
        let horseCount = 0;
        
        function addHorseEntry() {
            horseCount++;
            const container = document.getElementById('horseEntries');
            const horseDiv = document.createElement('div');
            horseDiv.className = 'race-entry';
            horseDiv.innerHTML = `
                <input type="number" placeholder="Program #" id="program_${horseCount}" min="1" max="20" />
                <input type="text" placeholder="Horse Name" id="horse_${horseCount}" />
                <input type="text" placeholder="M/L" id="ml_${horseCount}" />
                <input type="number" placeholder="Win %" id="win_${horseCount}" step="0.1" />
                <input type="number" placeholder="Adj %" id="adj_${horseCount}" step="0.1" />
            `;
            container.appendChild(horseDiv);
        }
        
        // Add first horse entry by default
        addHorseEntry();
        
        async function submitManualRace() {
            const raceDate = document.getElementById('manualDate').value;
            const raceNumber = document.getElementById('raceNumber').value;
            
            const races = [];
            for (let i = 1; i <= horseCount; i++) {
                const program = document.getElementById(`program_${i}`)?.value;
                const horseName = document.getElementById(`horse_${i}`)?.value;
                const ml = document.getElementById(`ml_${i}`)?.value;
                const winProb = document.getElementById(`win_${i}`)?.value;
                const adjOdds = document.getElementById(`adj_${i}`)?.value;
                
                if (program && horseName) {
                    races.push({
                        race_date: raceDate,
                        race_number: parseInt(raceNumber),
                        program_number: parseInt(program),
                        horse_name: horseName,
                        morning_line: ml || null,
                        win_probability: parseFloat(winProb) || null,
                        adj_odds: parseFloat(adjOdds) || null
                    });
                }
            }
            
            if (races.length === 0) {
                showStatus('Please enter at least one horse', 'error');
                return;
            }
            
            try {
                const response = await fetch('/api/races/batch', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ races })
                });
                
                const result = await response.json();
                if (response.ok) {
                    showStatus(`Successfully added ${races.length} horses for Race ${raceNumber} on ${raceDate}`, 'success');
                    // Clear form
                    document.getElementById('horseEntries').innerHTML = '';
                    horseCount = 0;
                    addHorseEntry();
                } else {
                    showStatus(`Error: ${result.error}`, 'error');
                }
            } catch (error) {
                showStatus(`Error: ${error.message}`, 'error');
            }
        }
        
        // Fetch race results
        async function fetchRaceResults() {
            showStatus('Fetching race results from OTB...', 'info');
            document.getElementById('resultsStatus').innerHTML = 
                '<p style="color: blue;">⟳ Checking for completed races...</p>';
            
            try {
                const response = await fetch('/api/fetch-results', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                
                const result = await response.json();
                if (response.ok) {
                    showStatus(result.message, 'success');
                    document.getElementById('resultsStatus').innerHTML = 
                        `<p style="color: green;">✓ ${result.message}</p>
                         <p style="font-size: 0.9rem;">Tracks checked: ${result.tracks_checked || 0}</p>`;
                } else {
                    showStatus(`Error: ${result.error}`, 'error');
                    document.getElementById('resultsStatus').innerHTML = 
                        `<p style="color: red;">✗ Failed to fetch results</p>`;
                }
            } catch (error) {
                showStatus(`Error: ${error.message}`, 'error');
            }
        }
        
        // Check results status
        async function checkResultsStatus() {
            try {
                const response = await fetch('/api/results-status');
                const result = await response.json();
                
                if (response.ok) {
                    document.getElementById('resultsStatus').innerHTML = 
                        `<p><strong>Last Check:</strong> ${result.last_check || 'Never'}</p>
                         <p><strong>Results Found:</strong> ${result.results_count || 0}</p>`;
                } else {
                    showStatus(`Error: ${result.error}`, 'error');
                }
            } catch (error) {
                showStatus(`Error: ${error.message}`, 'error');
            }
        }
        
        // Update bet recommendation
        async function updateBetRecommendation() {
            const date = document.getElementById('betDate').value;
            const raceNumber = document.getElementById('betRaceNumber').value;
            const betRecommendation = document.getElementById('betRecommendation').value;
            
            if (!betRecommendation) {
                showStatus('Please enter a bet recommendation', 'error');
                return;
            }
            
            try {
                const response = await fetch('/api/races/update-bet-recommendation', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        race_date: date,
                        race_number: parseInt(raceNumber),
                        bet_recommendation: betRecommendation
                    })
                });
                
                const result = await response.json();
                if (response.ok) {
                    showStatus(`Successfully updated bet recommendation for Race ${raceNumber}`, 'success');
                    document.getElementById('betRecommendation').value = '';
                } else {
                    showStatus(`Error: ${result.error}`, 'error');
                }
            } catch (error) {
                showStatus(`Error: ${error.message}`, 'error');
            }
        }
    </script>
</body>
</html>
''')


@app.route('/api/races/update-bet-recommendation', methods=['POST'])
def update_bet_recommendation():
    try:
        DATABASE_URL = os.environ.get('DATABASE_URL')
        if not DATABASE_URL:
            return jsonify({'error': 'No database configured'}), 500
        
        data = request.json
        
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Update all horses in the race with the same bet recommendation
        cur.execute('''
            UPDATE races 
            SET bet_recommendation = %s
            WHERE race_date = %s 
            AND race_number = %s
        ''', (
            data['bet_recommendation'],
            data['race_date'],
            data['race_number']
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'message': 'Bet recommendation updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload-screenshot', methods=['POST'])
def upload_screenshot():
    """
    Endpoint for future OCR processing of screenshots
    Currently returns a message about manual entry requirement
    """
    try:
        # In a real implementation, this would:
        # 1. Receive the image file
        # 2. Process it with OCR (like Tesseract or cloud OCR service)
        # 3. Extract the race data
        # 4. Return the structured data
        
        return jsonify({
            'message': 'OCR processing not yet implemented. Please use manual entry.',
            'status': 'manual_entry_required'
        }), 501
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/fetch-results', methods=['POST'])
def fetch_results():
    """Fetch race results from OffTrackBetting.com"""
    try:
        scraper = OTBScraper()
        
        # Get race schedule to find completed races
        race_schedule = scraper.get_current_races()
        if not race_schedule:
            return jsonify({'error': 'Could not fetch OTB race schedule'}), 500
        
        tracks = race_schedule.get('tracks', [])
        completed_count = 0
        
        # Check major US tracks for completed races
        major_track_names = ['Belmont Park', 'Gulfstream Park', 'Santa Anita', 'Churchill Downs', 
                           'Keeneland', 'Del Mar', 'Aqueduct', 'Saratoga']
        
        for track in tracks:
            track_name = track.get('name', '')
            current_race = track.get('currentRace', '1')
            
            # Check if this is a major track and has completed races
            if any(major in track_name for major in major_track_names):
                if int(current_race) > 1:  # Has completed races
                    completed_count += 1
        
        return jsonify({
            'message': f'Found {completed_count} tracks with completed races',
            'tracks_checked': len(tracks),
            'completed_tracks': completed_count
        })
        
    except Exception as e:
        app.logger.error(f"Scraping error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/results-status', methods=['GET'])
def results_status():
    """Get the status of results fetching"""
    try:
        # In a real implementation, you'd track last check time and results
        return jsonify({
            'last_check': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'results_count': 0,
            'status': 'ready'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Scheduler removed - no real-time odds tracking needed

if __name__ == '__main__':
    app.run()