#!/usr/bin/env python3
"""
Comprehensive database check for STALL10N racing data
Checks for data on specific dates: 2025-06-13, 2025-06-14, 2025-06-27

To use this script:
1. Set the DATABASE_URL environment variable with your PostgreSQL connection string
2. Run: python3 comprehensive_database_check.py

The script will:
- List all tables in the database
- Check each table for date-related columns
- Search for data on the specified dates
- Generate a comprehensive report
"""

import os
import sys
import psycopg2
from psycopg2 import sql
from datetime import datetime
import json

# Target dates to check
TARGET_DATES = ['2025-06-13', '2025-06-14', '2025-06-27']

# Known racing-related tables
RACING_TABLES = [
    'races', 
    'predictions', 
    'rtn_odds_snapshots', 
    'betting_recommendations', 
    'race_results',
    'race_schedule',
    'live_odds_snapshot',
    'horses',
    'race_horses'
]

def get_database_connection():
    """Get database connection from environment variable"""
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("ERROR: DATABASE_URL environment variable is not set")
        print("\nTo set it:")
        print("export DATABASE_URL='postgresql://username:password@host:port/database'")
        sys.exit(1)
    
    try:
        return psycopg2.connect(database_url)
    except Exception as e:
        print(f"ERROR: Failed to connect to database: {e}")
        sys.exit(1)

def check_table_exists(cur, table_name):
    """Check if a table exists in the database"""
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = %s
        );
    """, (table_name,))
    return cur.fetchone()[0]

def get_date_columns(cur, table_name):
    """Get all date-related columns from a table"""
    cur.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = %s
        AND (data_type LIKE '%date%' 
             OR data_type LIKE '%timestamp%' 
             OR column_name LIKE '%date%'
             OR column_name LIKE '%_at'
             OR column_name LIKE '%time%')
        ORDER BY ordinal_position;
    """, (table_name,))
    return cur.fetchall()

def check_data_for_dates(cur, table_name, date_column, target_dates):
    """Check if table has data for specific dates"""
    results = {}
    
    for target_date in target_dates:
        try:
            # Build query to check for data on this date
            query = sql.SQL("""
                SELECT COUNT(*) as count,
                       MIN({date_col}) as min_time,
                       MAX({date_col}) as max_time
                FROM {table}
                WHERE {date_col}::date = %s
            """).format(
                table=sql.Identifier(table_name),
                date_col=sql.Identifier(date_column)
            )
            
            cur.execute(query, (target_date,))
            count, min_time, max_time = cur.fetchone()
            
            if count > 0:
                results[target_date] = {
                    'count': count,
                    'min_time': str(min_time) if min_time else None,
                    'max_time': str(max_time) if max_time else None
                }
                
                # Get sample data
                sample_query = sql.SQL("""
                    SELECT * FROM {table}
                    WHERE {date_col}::date = %s
                    LIMIT 2
                """).format(
                    table=sql.Identifier(table_name),
                    date_col=sql.Identifier(date_column)
                )
                
                cur.execute(sample_query, (target_date,))
                samples = cur.fetchall()
                col_names = [desc[0] for desc in cur.description]
                
                results[target_date]['samples'] = [
                    dict(zip(col_names, row)) for row in samples
                ]
                
        except Exception as e:
            results[target_date] = {'error': str(e)}
    
    return results

def generate_report(findings):
    """Generate a comprehensive report of findings"""
    print("\n" + "="*80)
    print("STALL10N DATABASE CHECK REPORT")
    print("="*80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target dates: {', '.join(TARGET_DATES)}")
    print("\n")
    
    # Summary
    tables_with_data = 0
    total_records = 0
    
    for table_name, table_data in findings.items():
        if table_data.get('has_data'):
            tables_with_data += 1
            for date_col, date_data in table_data.get('date_columns', {}).items():
                for date, info in date_data.items():
                    if isinstance(info, dict) and 'count' in info:
                        total_records += info['count']
    
    print(f"SUMMARY:")
    print(f"- Total tables checked: {len(findings)}")
    print(f"- Tables with data on target dates: {tables_with_data}")
    print(f"- Total records found: {total_records}")
    print("\n")
    
    # Detailed findings
    print("DETAILED FINDINGS:")
    print("-"*80)
    
    for table_name, table_data in sorted(findings.items()):
        if not table_data.get('exists'):
            print(f"\n❌ Table '{table_name}' does not exist")
            continue
        
        print(f"\n📊 TABLE: {table_name}")
        print(f"   Total rows: {table_data.get('total_rows', 'Unknown')}")
        
        if not table_data.get('date_columns'):
            print("   No date columns found")
            continue
        
        has_relevant_data = False
        for date_col, date_data in table_data['date_columns'].items():
            data_found = False
            for date, info in date_data.items():
                if isinstance(info, dict) and 'count' in info and info['count'] > 0:
                    data_found = True
                    has_relevant_data = True
                    print(f"\n   ✅ Column '{date_col}' has data for {date}:")
                    print(f"      - Records: {info['count']}")
                    print(f"      - Time range: {info['min_time']} to {info['max_time']}")
                    
                    if 'samples' in info and info['samples']:
                        print(f"      - Sample record:")
                        sample = info['samples'][0]
                        for key, value in list(sample.items())[:5]:  # Show first 5 fields
                            print(f"        • {key}: {value}")
            
            if not data_found:
                print(f"   ❌ Column '{date_col}' has no data for target dates")
        
        if has_relevant_data:
            table_data['has_data'] = True
    
    # Write detailed JSON report
    report_file = f"database_check_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(findings, f, indent=2, default=str)
    
    print(f"\n\n📄 Detailed JSON report saved to: {report_file}")

def main():
    """Main function to run the database check"""
    conn = get_database_connection()
    cur = conn.cursor()
    
    print("Connected to database successfully")
    print(f"Checking for data on dates: {', '.join(TARGET_DATES)}")
    print("-"*80)
    
    findings = {}
    
    # Get all tables
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name;
    """)
    all_tables = [row[0] for row in cur.fetchall()]
    
    print(f"Found {len(all_tables)} tables in database")
    
    # Check each racing-related table first
    tables_to_check = RACING_TABLES + [t for t in all_tables if t not in RACING_TABLES]
    
    for table_name in tables_to_check:
        print(f"\nChecking table: {table_name}")
        findings[table_name] = {}
        
        # Check if table exists
        if not check_table_exists(cur, table_name):
            findings[table_name]['exists'] = False
            continue
        
        findings[table_name]['exists'] = True
        
        # Get total row count
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table_name}")
            findings[table_name]['total_rows'] = cur.fetchone()[0]
        except:
            findings[table_name]['total_rows'] = 'Error'
        
        # Get date columns
        date_columns = get_date_columns(cur, table_name)
        
        if not date_columns:
            findings[table_name]['date_columns'] = None
            continue
        
        findings[table_name]['date_columns'] = {}
        
        # Check each date column
        for col_name, col_type in date_columns:
            print(f"  Checking column: {col_name} ({col_type})")
            results = check_data_for_dates(cur, table_name, col_name, TARGET_DATES)
            
            if any(r.get('count', 0) > 0 for r in results.values() if isinstance(r, dict)):
                findings[table_name]['date_columns'][col_name] = results
    
    # Generate report
    generate_report(findings)
    
    # Close connection
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()