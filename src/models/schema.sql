-- Create races table
CREATE TABLE IF NOT EXISTS races (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    race_number INTEGER NOT NULL,
    track_name VARCHAR(100),
    post_time TIME,
    purse VARCHAR(50),
    distance VARCHAR(50),
    surface VARCHAR(20),
    race_type VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, race_number, track_name)
);

-- Create horses table
CREATE TABLE IF NOT EXISTS horses (
    id SERIAL PRIMARY KEY,
    race_id INTEGER REFERENCES races(id) ON DELETE CASCADE,
    program_number VARCHAR(10),
    horse_name VARCHAR(100) NOT NULL,
    jockey VARCHAR(100),
    trainer VARCHAR(100),
    morning_line_odds VARCHAR(20),
    weight VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create odds tracking table
CREATE TABLE IF NOT EXISTS odds_history (
    id SERIAL PRIMARY KEY,
    race_id INTEGER REFERENCES races(id) ON DELETE CASCADE,
    horse_id INTEGER REFERENCES horses(id) ON DELETE CASCADE,
    odds_type VARCHAR(20) NOT NULL, -- 'morning_line' or 'live'
    odds_value VARCHAR(20),
    captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    minutes_to_post INTEGER -- NULL for morning line, calculated for live odds
);

-- Create index for faster queries
CREATE INDEX idx_races_date ON races(date);
CREATE INDEX idx_horses_race_id ON horses(race_id);
CREATE INDEX idx_odds_history_race_id ON odds_history(race_id);
CREATE INDEX idx_odds_history_captured_at ON odds_history(captured_at);