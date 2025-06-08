-- STALL10N Database Schema for TrackMaster Plus XML
-- Optimized and cleaned version

-- Drop existing tables
DROP TABLE IF EXISTS analysis CASCADE;
DROP TABLE IF EXISTS pp_data CASCADE;
DROP TABLE IF EXISTS workouts CASCADE;
DROP TABLE IF EXISTS trainer_stats CASCADE;
DROP TABLE IF EXISTS jockey_stats CASCADE;
DROP TABLE IF EXISTS horse_stats CASCADE;
DROP TABLE IF EXISTS entries CASCADE;
DROP TABLE IF EXISTS races CASCADE;

-- Races table
CREATE TABLE races (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    race_number INT NOT NULL,
    track_name VARCHAR(100) NOT NULL,
    track_code VARCHAR(10) NOT NULL,
    country VARCHAR(10) DEFAULT 'USA',
    distance DECIMAL(6,1),
    dist_unit VARCHAR(1) DEFAULT 'F',
    surface VARCHAR(20) DEFAULT 'D',
    race_type VARCHAR(30),
    purse INT,
    claiming_price INT,
    post_time VARCHAR(20),
    age_restriction VARCHAR(10),
    sex_restriction VARCHAR(10),
    race_conditions TEXT,
    file_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, race_number, track_code)
);

-- Entries table
CREATE TABLE entries (
    id SERIAL PRIMARY KEY,
    race_id INT REFERENCES races(id) ON DELETE CASCADE,
    program_number INT NOT NULL,
    post_position INT,
    horse_name VARCHAR(100) NOT NULL,
    
    -- Horse info
    age INT,
    sex VARCHAR(5),
    color VARCHAR(20),
    sire VARCHAR(100),
    dam VARCHAR(100),
    owner_name TEXT,
    breeder TEXT,
    
    -- Race day info
    jockey VARCHAR(100),
    trainer VARCHAR(100),
    weight INT,
    medication VARCHAR(10),
    equipment VARCHAR(50),
    morning_line_odds VARCHAR(20),
    claiming_price INT,
    
    -- Performance metrics
    power_rating DECIMAL(5,1),
    avg_speed INT,
    avg_class INT,
    last_speed INT,
    best_speed INT,
    
    -- Calculated percentages
    win_pct DECIMAL(5,2),
    jockey_win_pct DECIMAL(5,2),
    trainer_win_pct DECIMAL(5,2),
    
    -- Results (if available)
    finish_position INT,
    final_odds VARCHAR(20),
    
    UNIQUE(race_id, program_number)
);

-- Horse statistics (simplified)
CREATE TABLE horse_stats (
    id SERIAL PRIMARY KEY,
    entry_id INTEGER REFERENCES entries(id) ON DELETE CASCADE,
    stat_type VARCHAR(50) NOT NULL,
    starts INT DEFAULT 0,
    wins INT DEFAULT 0,
    places INT DEFAULT 0,
    shows INT DEFAULT 0,
    earnings DECIMAL(10,2) DEFAULT 0,
    roi DECIMAL(6,2),
    UNIQUE(entry_id, stat_type)
);

-- Jockey statistics (simplified)
CREATE TABLE jockey_stats (
    id SERIAL PRIMARY KEY,
    entry_id INTEGER REFERENCES entries(id) ON DELETE CASCADE,
    jockey_name VARCHAR(100) NOT NULL,
    stat_type VARCHAR(50) NOT NULL,
    starts INT DEFAULT 0,
    wins INT DEFAULT 0,
    places INT DEFAULT 0,
    shows INT DEFAULT 0,
    roi DECIMAL(6,2),
    UNIQUE(entry_id, stat_type)
);

-- Trainer statistics (simplified)
CREATE TABLE trainer_stats (
    id SERIAL PRIMARY KEY,
    entry_id INTEGER REFERENCES entries(id) ON DELETE CASCADE,
    trainer_name VARCHAR(100) NOT NULL,
    stat_type VARCHAR(50) NOT NULL,
    starts INT DEFAULT 0,
    wins INT DEFAULT 0,
    places INT DEFAULT 0,
    shows INT DEFAULT 0,
    roi DECIMAL(6,2),
    UNIQUE(entry_id, stat_type)
);

-- Workouts
CREATE TABLE workouts (
    id SERIAL PRIMARY KEY,
    entry_id INTEGER REFERENCES entries(id) ON DELETE CASCADE,
    days_back INT,
    description TEXT,
    ranking INT
);

-- Past performances (simplified - key fields only)
CREATE TABLE pp_data (
    id SERIAL PRIMARY KEY,
    entry_id INTEGER REFERENCES entries(id) ON DELETE CASCADE,
    race_date DATE,
    track_code VARCHAR(10),
    race_type VARCHAR(10),
    distance INT,
    surface VARCHAR(10),
    finish_position INT,
    beaten_lengths DECIMAL(5,2),
    speed_figure INT,
    class_rating INT,
    jockey VARCHAR(100),
    weight INT,
    odds VARCHAR(10),
    comments TEXT
);

-- Analysis results
CREATE TABLE analysis (
    id SERIAL PRIMARY KEY,
    entry_id INT REFERENCES entries(id) ON DELETE CASCADE,
    speed_score DECIMAL(5,2),
    class_score DECIMAL(5,2),
    jockey_score DECIMAL(5,2),
    trainer_score DECIMAL(5,2),
    overall_score DECIMAL(5,2),
    recommendation VARCHAR(20),
    confidence INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_races_date ON races(date);
CREATE INDEX idx_races_track ON races(track_code);
CREATE INDEX idx_entries_race ON entries(race_id);
CREATE INDEX idx_entries_horse ON entries(horse_name);
CREATE INDEX idx_entries_power ON entries(power_rating);
CREATE INDEX idx_analysis_entry ON analysis(entry_id);
CREATE INDEX idx_analysis_score ON analysis(overall_score DESC);
CREATE INDEX idx_horse_stats_entry ON horse_stats(entry_id);
CREATE INDEX idx_jockey_stats_entry ON jockey_stats(entry_id);
CREATE INDEX idx_trainer_stats_entry ON trainer_stats(entry_id);
CREATE INDEX idx_workouts_entry ON workouts(entry_id);
CREATE INDEX idx_pp_data_entry ON pp_data(entry_id);
CREATE INDEX idx_pp_data_date ON pp_data(race_date);