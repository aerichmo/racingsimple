-- Racing Data Analysis Queries

-- 1. Daily race summary
SELECT 
    date,
    COUNT(DISTINCT track_name) as tracks_running,
    COUNT(*) as total_races,
    SUM((SELECT COUNT(*) FROM horses WHERE race_id = r.id)) as total_horses,
    AVG(CAST(NULLIF(regexp_replace(purse, '[^0-9]', '', 'g'), '') AS INTEGER)) as avg_purse
FROM races r
GROUP BY date
ORDER BY date DESC;

-- 2. Most competitive races (by number of horses)
SELECT 
    r.date,
    r.track_name,
    r.race_number,
    r.race_type,
    r.purse,
    COUNT(h.id) as horse_count
FROM races r
JOIN horses h ON h.race_id = r.id
GROUP BY r.id, r.date, r.track_name, r.race_number, r.race_type, r.purse
HAVING COUNT(h.id) >= 10
ORDER BY horse_count DESC, r.date DESC;

-- 3. Jockey-Trainer combinations
SELECT 
    h.jockey,
    h.trainer,
    COUNT(*) as rides_together,
    COUNT(DISTINCT r.date) as days_together,
    COUNT(DISTINCT h.horse_name) as different_horses,
    STRING_AGG(DISTINCT r.track_name, ', ') as tracks
FROM horses h
JOIN races r ON r.id = h.race_id
WHERE h.jockey IS NOT NULL AND h.trainer IS NOT NULL
GROUP BY h.jockey, h.trainer
HAVING COUNT(*) >= 5
ORDER BY rides_together DESC;

-- 4. Track analysis by day of week
SELECT 
    track_name,
    EXTRACT(DOW FROM date) as day_of_week,
    CASE EXTRACT(DOW FROM date)
        WHEN 3 THEN 'Wednesday'
        WHEN 4 THEN 'Thursday'
        WHEN 5 THEN 'Friday'
        WHEN 6 THEN 'Saturday'
    END as day_name,
    COUNT(*) as races_count,
    AVG(CAST(NULLIF(regexp_replace(purse, '[^0-9]', '', 'g'), '') AS INTEGER)) as avg_purse
FROM races
GROUP BY track_name, EXTRACT(DOW FROM date)
ORDER BY track_name, day_of_week;

-- 5. Popular horse names
SELECT 
    horse_name,
    COUNT(*) as appearances,
    COUNT(DISTINCT trainer) as different_trainers,
    COUNT(DISTINCT jockey) as different_jockeys,
    COUNT(DISTINCT r.track_name) as different_tracks,
    MIN(r.date) as first_race,
    MAX(r.date) as last_race
FROM horses h
JOIN races r ON r.id = h.race_id
GROUP BY horse_name
HAVING COUNT(*) > 1
ORDER BY appearances DESC;

-- 6. Morning line odds distribution
SELECT 
    morning_line_odds,
    COUNT(*) as frequency,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM horses
WHERE morning_line_odds IS NOT NULL AND morning_line_odds != ''
GROUP BY morning_line_odds
ORDER BY frequency DESC;

-- 7. Busiest racing days
SELECT 
    date,
    COUNT(DISTINCT track_name) as tracks_running,
    COUNT(*) as total_races,
    SUM((SELECT COUNT(*) FROM horses WHERE race_id = r.id)) as total_horses,
    STRING_AGG(DISTINCT track_name, ', ') as tracks
FROM races r
GROUP BY date
ORDER BY total_races DESC
LIMIT 10;

-- 8. Trainer workload analysis
SELECT 
    h.trainer,
    r.date,
    COUNT(*) as horses_entered,
    COUNT(DISTINCT r.track_name) as tracks_on_day,
    STRING_AGG(DISTINCT h.horse_name, ', ') as horses,
    STRING_AGG(DISTINCT r.track_name, ', ') as tracks
FROM horses h
JOIN races r ON r.id = h.race_id
WHERE h.trainer IS NOT NULL
GROUP BY h.trainer, r.date
HAVING COUNT(*) >= 3
ORDER BY r.date DESC, horses_entered DESC;

-- 9. Race type analysis
SELECT 
    race_type,
    COUNT(*) as race_count,
    COUNT(DISTINCT track_name) as tracks_offering,
    AVG(CAST(NULLIF(regexp_replace(purse, '[^0-9]', '', 'g'), '') AS INTEGER)) as avg_purse,
    AVG((SELECT COUNT(*) FROM horses WHERE race_id = r.id)) as avg_field_size
FROM races r
GROUP BY race_type
ORDER BY race_count DESC;

-- 10. Weekly summary
SELECT 
    DATE_TRUNC('week', date) as week_start,
    COUNT(DISTINCT date) as racing_days,
    COUNT(DISTINCT track_name) as unique_tracks,
    COUNT(*) as total_races,
    SUM((SELECT COUNT(*) FROM horses WHERE race_id = r.id)) as total_entries
FROM races r
GROUP BY DATE_TRUNC('week', date)
ORDER BY week_start DESC;