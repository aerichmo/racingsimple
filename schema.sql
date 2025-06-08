-- Racing Simple Database Schema
DROP TABLE IF EXISTS analysis CASCADE;
DROP TABLE IF EXISTS entries CASCADE;
DROP TABLE IF EXISTS races CASCADE;

-- Races table
CREATE TABLE races (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    race_number INT NOT NULL,
    track_name VARCHAR(50) NOT NULL,
    distance VARCHAR(30),
    race_type VARCHAR(30),
    purse INT,
    post_time TIME,
    surface VARCHAR(20) DEFAULT 'Dirt',
    pdf_filename VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, race_number, track_name)
);

-- Entries table
CREATE TABLE entries (
    id SERIAL PRIMARY KEY,
    race_id INT REFERENCES races(id) ON DELETE CASCADE,
    program_number INT NOT NULL,
    post_position INT,
    horse_name VARCHAR(100) NOT NULL,
    jockey VARCHAR(100),
    trainer VARCHAR(100),
    win_pct DECIMAL(5,2),
    class_rating INT,
    last_speed INT,
    avg_speed INT,
    best_speed INT,
    jockey_win_pct DECIMAL(5,2),
    trainer_win_pct DECIMAL(5,2),
    jt_combo_pct DECIMAL(5,2),
    UNIQUE(race_id, program_number)
);

-- Analysis table
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
CREATE INDEX idx_entries_race ON entries(race_id);
CREATE INDEX idx_analysis_entry ON analysis(entry_id);
CREATE INDEX idx_analysis_score ON analysis(overall_score DESC);