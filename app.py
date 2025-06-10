from flask import Flask, request, jsonify, render_template_string
import os
import psycopg2
from psycopg2 import sql
from datetime import datetime
import json

app = Flask(__name__)

@app.route('/')
def hello():
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>STALL10N Horse Racing</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        .race-date { margin: 20px 0; }
        table { border-collapse: collapse; width: 100%; margin: 10px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .no-data { color: #888; font-style: italic; }
    </style>
</head>
<body>
    <h1>STALL10N Horse Racing Platform</h1>
    <div id="races"></div>
    <script>
        fetch('/api/races')
            .then(response => response.json())
            .then(data => {
                const container = document.getElementById('races');
                if (data.length === 0) {
                    container.innerHTML = '<p class="no-data">No race data available yet.</p>';
                    return;
                }
                
                const racesByDate = {};
                data.forEach(race => {
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
                                <th>ADJ Odds</th>
                                <th>Morning Line</th>
                            </tr>`;
                        
                        horses.forEach(horse => {
                            html += `<tr>
                                <td>${horse.program_number}</td>
                                <td>${horse.horse_name}</td>
                                <td>${horse.win_probability}%</td>
                                <td>${horse.adj_odds ? horse.adj_odds + '%' : '-'}</td>
                                <td>${horse.morning_line}</td>
                            </tr>`;
                        });
                        
                        html += '</table>';
                    }
                    html += '</div>';
                }
                container.innerHTML = html;
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Add adj_odds column if it doesn't exist
        cur.execute('''
            ALTER TABLE races 
            ADD COLUMN IF NOT EXISTS adj_odds DECIMAL(5,2)
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
                                 horse_name, win_probability, adj_odds, morning_line)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (
                data['race_date'],
                data['race_number'],
                data['program_number'],
                data['horse_name'],
                data['win_probability'],
                data.get('adj_odds'),
                data['morning_line']
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
                       horse_name, win_probability, adj_odds, morning_line
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
                    'morning_line': row[6]
                })
            
            cur.close()
            conn.close()
            
            return jsonify(races)
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
                                 horse_name, win_probability, adj_odds, morning_line)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (
                race['race_date'],
                race['race_number'],
                race['program_number'],
                race['horse_name'],
                race['win_probability'],
                race.get('adj_odds'),
                race['morning_line']
            ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'message': f'{len(races)} races added successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run()