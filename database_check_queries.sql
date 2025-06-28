-- Database Check Queries for STALL10N
-- Check for data on dates: 2025-06-13, 2025-06-14, 2025-06-27

-- 1. List all tables in the database
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- 2. Check races table
SELECT 'races' as table_name, COUNT(*) as count, race_date
FROM races 
WHERE race_date IN ('2025-06-13', '2025-06-14', '2025-06-27')
GROUP BY race_date
ORDER BY race_date;

-- Sample data from races table
SELECT * FROM races 
WHERE race_date IN ('2025-06-13', '2025-06-14', '2025-06-27')
LIMIT 5;

-- 3. Check predictions table
SELECT 'predictions' as table_name, COUNT(*) as count, date_column
FROM (
    SELECT DISTINCT 
        CASE 
            WHEN column_name = 'created_at' THEN created_at::date
            WHEN column_name = 'race_date' THEN race_date
            WHEN column_name = 'prediction_date' THEN prediction_date
        END as date_column
    FROM predictions, 
    (SELECT column_name FROM information_schema.columns 
     WHERE table_name = 'predictions' 
     AND column_name IN ('created_at', 'race_date', 'prediction_date')) cols
) subquery
WHERE date_column IN ('2025-06-13', '2025-06-14', '2025-06-27')
GROUP BY date_column;

-- 4. Check rtn_odds_snapshots table
SELECT 'rtn_odds_snapshots' as table_name, COUNT(*) as count, snapshot_date::date as date
FROM rtn_odds_snapshots 
WHERE snapshot_date::date IN ('2025-06-13', '2025-06-14', '2025-06-27')
GROUP BY snapshot_date::date
ORDER BY snapshot_date::date;

-- Sample data from rtn_odds_snapshots
SELECT * FROM rtn_odds_snapshots 
WHERE snapshot_date::date IN ('2025-06-13', '2025-06-14', '2025-06-27')
ORDER BY snapshot_date DESC
LIMIT 5;

-- 5. Check betting_recommendations table
SELECT 'betting_recommendations' as table_name, COUNT(*) as count, recommendation_date::date as date
FROM betting_recommendations 
WHERE recommendation_date::date IN ('2025-06-13', '2025-06-14', '2025-06-27')
GROUP BY recommendation_date::date
ORDER BY recommendation_date::date;

-- 6. Check race_results table
SELECT 'race_results' as table_name, COUNT(*) as count, race_date
FROM race_results 
WHERE race_date IN ('2025-06-13', '2025-06-14', '2025-06-27')
GROUP BY race_date
ORDER BY race_date;

-- Sample data from race_results
SELECT * FROM race_results 
WHERE race_date IN ('2025-06-13', '2025-06-14', '2025-06-27')
ORDER BY race_date, race_number
LIMIT 10;

-- 7. Check for any other tables with date columns containing our target dates
SELECT DISTINCT
    t.table_name,
    c.column_name,
    COUNT(*) OVER (PARTITION BY t.table_name) as potential_date_columns
FROM information_schema.tables t
JOIN information_schema.columns c ON t.table_name = c.table_name
WHERE t.table_schema = 'public'
AND (c.data_type LIKE '%date%' OR c.data_type LIKE '%timestamp%' OR c.column_name LIKE '%date%')
AND t.table_name NOT IN ('races', 'predictions', 'rtn_odds_snapshots', 'betting_recommendations', 'race_results')
ORDER BY t.table_name, c.column_name;

-- 8. Summary query to check all tables for row counts
SELECT 
    schemaname,
    tablename,
    n_live_tup as row_count
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY n_live_tup DESC;

-- 9. Check for any JSON data that might contain dates
-- This checks if there are any JSONB columns that might store race data
SELECT 
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema = 'public'
AND data_type IN ('json', 'jsonb')
ORDER BY table_name, column_name;