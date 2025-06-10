from flask import Flask
import os
import psycopg2
from psycopg2 import sql

app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello World'

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

if __name__ == '__main__':
    app.run()