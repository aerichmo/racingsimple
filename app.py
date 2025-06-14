from flask import Flask, request, jsonify, render_template_string
import os
import psycopg2
from psycopg2 import sql
from datetime import datetime
import json
import base64
from io import BytesIO
import logging
from simplified_endpoints import add_simplified_endpoints

app = Flask(__name__)

# Add simplified race results endpoints
add_simplified_endpoints(app)

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
        .live-odds {
            color: #FF6B00;
            font-weight: 600;
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
                            <th>Live Odds</th>
                        </tr>`;
                    
                    horses.forEach(horse => {
                        html += `<tr>
                            <td class="program-number">${horse.program_number}</td>
                            <td class="horse-name">${horse.horse_name}</td>
                            <td class="probability">${horse.win_probability}%</td>
                            <td class="adj-odds">${horse.adj_odds ? horse.adj_odds + '%' : '-'}</td>
                            <td class="morning-line">${horse.morning_line}</td>
                            <td class="live-odds">${horse.realtime_odds || '-'}</td>
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
                                 bet_recommendation, realtime_odds)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                data['race_date'],
                data['race_number'],
                data['program_number'],
                data['horse_name'],
                data['win_probability'],
                data.get('adj_odds'),
                data['morning_line'],
                data.get('bet_recommendation'),
                data.get('realtime_odds')
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
                       bet_recommendation, realtime_odds
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
                    'bet_recommendation': row[7],
                    'realtime_odds': row[8] if len(row) > 8 else None
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
                                 bet_recommendation, realtime_odds)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                race['race_date'],
                race['race_number'],
                race['program_number'],
                race['horse_name'],
                race['win_probability'],
                race.get('adj_odds'),
                race['morning_line'],
                race.get('bet_recommendation'),
                race.get('realtime_odds')
            ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'message': f'{len(races)} races added successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/races/delete-null-morning-lines', methods=['DELETE'])
def delete_null_morning_lines():
    """
    Delete all races that have NULL morning lines
    """
    try:
        DATABASE_URL = os.environ.get('DATABASE_URL')
        if not DATABASE_URL:
            return jsonify({'error': 'No database configured'}), 500
        
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Delete all races with NULL morning lines
        cur.execute('''
            DELETE FROM races 
            WHERE morning_line IS NULL
        ''')
        
        deleted_count = cur.rowcount
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'message': f'Successfully deleted {deleted_count} races with null morning lines',
            'deleted_count': deleted_count
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/races/<race_date>/<int:race_number>/<int:program_number>', methods=['DELETE'])
def delete_race_entry(race_date, race_number, program_number):
    """
    Delete a specific race entry
    """
    try:
        DATABASE_URL = os.environ.get('DATABASE_URL')
        if not DATABASE_URL:
            return jsonify({'error': 'No database configured'}), 500
        
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Delete the specific race entry
        cur.execute('''
            DELETE FROM races 
            WHERE race_date = %s 
            AND race_number = %s 
            AND program_number = %s
        ''', (race_date, race_number, program_number))
        
        deleted_count = cur.rowcount
        
        conn.commit()
        cur.close()
        conn.close()
        
        if deleted_count > 0:
            return jsonify({
                'message': f'Successfully deleted race entry',
                'deleted': True
            })
        else:
            return jsonify({
                'message': 'No matching race entry found',
                'deleted': False
            }), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run()