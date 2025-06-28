#!/usr/bin/env python3
"""
Script to check PostgreSQL database for data on specific dates:
- 2025-06-13
- 2025-06-14
- 2025-06-27
"""

import os
import psycopg2
from psycopg2 import sql
from datetime import datetime
from dotenv import load_dotenv
# from tabulate import tabulate

# Load environment variables
load_dotenv()

# Get database URL
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable is not set")
    print("Please ensure you have a .env file with DATABASE_URL or set it as an environment variable")
    exit(1)

def check_database():
    """Check database for data on specific dates"""
    
    target_dates = ['2025-06-13', '2025-06-14', '2025-06-27']
    
    try:
        # Connect to database
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        print("Successfully connected to database\n")
        
        # First, get list of all tables
        print("=== ALL TABLES IN DATABASE ===")
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        
        tables = cur.fetchall()
        print(f"Found {len(tables)} tables:")
        for table in tables:
            print(f"  - {table[0]}")
        print()
        
        # For each table, check structure and data for target dates
        racing_tables = [
            'races', 'predictions', 'rtn_odds_snapshots', 
            'betting_recommendations', 'race_results'
        ]
        
        # Add any other tables that might contain race data
        all_table_names = [t[0] for t in tables]
        for table_name in all_table_names:
            if any(keyword in table_name.lower() for keyword in ['race', 'horse', 'bet', 'odd', 'prediction', 'result']):
                if table_name not in racing_tables:
                    racing_tables.append(table_name)
        
        print(f"=== CHECKING {len(racing_tables)} RACING-RELATED TABLES ===\n")
        
        for table_name in racing_tables:
            if table_name not in all_table_names:
                print(f"\n--- Table '{table_name}' does not exist ---")
                continue
                
            print(f"\n--- TABLE: {table_name} ---")
            
            # Get table structure
            cur.execute(f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public' 
                AND table_name = %s
                ORDER BY ordinal_position;
            """, (table_name,))
            
            columns = cur.fetchall()
            print("\nTable Structure:")
            print(f"{'Column':<30} {'Type':<20} {'Nullable':<10}")
            print("-" * 60)
            for col in columns:
                print(f"{col[0]:<30} {col[1]:<20} {col[2]:<10}")
            
            # Find date columns
            date_columns = []
            for col in columns:
                if 'date' in col[1].lower() or 'timestamp' in col[1].lower():
                    date_columns.append(col[0])
                elif 'date' in col[0].lower():
                    date_columns.append(col[0])
            
            if not date_columns:
                print(f"\nNo date columns found in {table_name}")
                # Still check if there's any data at all
                cur.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cur.fetchone()[0]
                print(f"Total rows in table: {count}")
                continue
            
            print(f"\nDate columns found: {date_columns}")
            
            # Check data for each date column and target date
            for date_col in date_columns:
                for target_date in target_dates:
                    try:
                        # Count records for this date
                        query = sql.SQL("""
                            SELECT COUNT(*) 
                            FROM {} 
                            WHERE {}::date = %s
                        """).format(
                            sql.Identifier(table_name),
                            sql.Identifier(date_col)
                        )
                        
                        cur.execute(query, (target_date,))
                        count = cur.fetchone()[0]
                        
                        if count > 0:
                            print(f"\n  ✓ Found {count} records for {target_date} in column '{date_col}'")
                            
                            # Show sample data
                            sample_query = sql.SQL("""
                                SELECT * 
                                FROM {} 
                                WHERE {}::date = %s 
                                LIMIT 3
                            """).format(
                                sql.Identifier(table_name),
                                sql.Identifier(date_col)
                            )
                            
                            cur.execute(sample_query, (target_date,))
                            sample_data = cur.fetchall()
                            
                            # Get column names for display
                            col_names = [desc[0] for desc in cur.description]
                            
                            print(f"\n  Sample data (first 3 rows):")
                            # Print column headers
                            header_line = " | ".join(f"{name[:20]:<20}" for name in col_names[:5])  # Show first 5 columns
                            print(f"  {header_line}")
                            print("  " + "-" * len(header_line))
                            # Print data rows
                            for row in sample_data:
                                row_line = " | ".join(f"{str(val)[:20]:<20}" for val in row[:5])  # Show first 5 columns
                                print(f"  {row_line}")
                            
                    except Exception as e:
                        print(f"\n  ✗ Error checking {date_col} for {target_date}: {str(e)}")
            
            # Also check total row count
            cur.execute(f"SELECT COUNT(*) FROM {table_name}")
            total_count = cur.fetchone()[0]
            print(f"\nTotal rows in {table_name}: {total_count}")
        
        # Close connection
        cur.close()
        conn.close()
        
        print("\n=== DATABASE CHECK COMPLETE ===")
        
    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
        print("\nPlease check:")
        print("1. DATABASE_URL is correctly set")
        print("2. PostgreSQL server is running")
        print("3. Network connection is available")

if __name__ == "__main__":
    check_database()