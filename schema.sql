-- Complete XML Racing Database Schema
-- This schema supports ALL fields from TrackMaster Plus XML format

-- Drop existing tables
DROP TABLE IF EXISTS pp_data CASCADE;
DROP TABLE IF EXISTS workouts CASCADE;
DROP TABLE IF EXISTS trainer_stats CASCADE;
DROP TABLE IF EXISTS jockey_stats CASCADE;
DROP TABLE IF EXISTS horse_stats CASCADE;
DROP TABLE IF EXISTS sire_stats CASCADE;
DROP TABLE IF EXISTS dam_stats CASCADE;
DROP TABLE IF EXISTS entries CASCADE;
DROP TABLE IF EXISTS races CASCADE;

-- Races table with all XML fields
CREATE TABLE races (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    race_number INT NOT NULL,
    track_name VARCHAR(100) NOT NULL,
    track_code VARCHAR(10) NOT NULL,
    country VARCHAR(10) DEFAULT 'USA',
    distance DECIMAL(6,1),
    dist_unit VARCHAR(1),
    dist_disp VARCHAR(20),
    surface VARCHAR(20) DEFAULT 'D',
    course_id VARCHAR(10),
    race_type VARCHAR(30),
    stk_clm_md VARCHAR(10),
    stkorclm VARCHAR(10),
    purse INT,
    claimamt INT,
    post_time VARCHAR(20),
    age_restr VARCHAR(10),
    sex_restriction VARCHAR(10),
    race_conditions TEXT,
    betting_options TEXT,
    track_record VARCHAR(20),
    partim VARCHAR(10),
    raceord INT,
    breed_type VARCHAR(10) DEFAULT 'TB',
    todays_cls INT,
    pdf_filename VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, race_number, track_code)
);

-- Entries table with all XML fields
CREATE TABLE entries (
    id SERIAL PRIMARY KEY,
    race_id INT REFERENCES races(id) ON DELETE CASCADE,
    program_number INT NOT NULL,
    post_position INT,
    horse_name VARCHAR(100) NOT NULL,
    owner_name TEXT,
    
    -- Physical attributes
    sex VARCHAR(5),
    age INT,
    foal_date DATE,
    color VARCHAR(20),
    breed_type VARCHAR(10) DEFAULT 'TB',
    breeder TEXT,
    where_bred VARCHAR(20),
    
    -- Racing attributes
    weight INT,
    weight_shift INT DEFAULT 0,
    medication VARCHAR(10),
    equipment VARCHAR(50),
    morning_line_odds VARCHAR(20),
    claiming_price INT,
    
    -- Performance metrics
    power_rating DECIMAL(5,1),
    power_symb VARCHAR(5),
    avg_speed INT,
    avg_class INT,
    todays_cls INT,
    last_speed INT,
    best_speed INT,
    class_rating INT,
    
    -- Speed/Style figures
    pstyerl DECIMAL(6,4),
    pstymid DECIMAL(6,4),
    pstyfin DECIMAL(6,4),
    pstynum INT,
    pstyoff INT,
    
    psprstyerl DECIMAL(6,4),
    psprstymid DECIMAL(6,4),
    psprstyfin DECIMAL(6,4),
    psprstynum INT,
    psprstyoff INT,
    
    prtestyerl DECIMAL(6,4),
    prtestymid DECIMAL(6,4),
    prtestyfin DECIMAL(6,4),
    prtestynum INT,
    prtestyoff INT,
    
    pallstyerl DECIMAL(6,4),
    pallstymid DECIMAL(6,4),
    pallstyfin DECIMAL(6,4),
    pallstynum INT,
    pallstyoff INT,
    
    -- Figure ratings
    pfigerl DECIMAL(6,4),
    pfigmid DECIMAL(6,4),
    pfigfin DECIMAL(6,4),
    pfignum INT,
    pfigoff INT,
    
    psprfigerl DECIMAL(6,4),
    psprfigmid DECIMAL(6,4),
    psprfigfin DECIMAL(6,4),
    psprfignum INT,
    psprfigoff INT,
    
    prtefigerl DECIMAL(6,4),
    prtefigmid DECIMAL(6,4),
    prtefigfin DECIMAL(6,4),
    prtefignum INT,
    prtefigoff INT,
    
    pallfigerl DECIMAL(6,4),
    pallfigmid DECIMAL(6,4),
    pallfigfin DECIMAL(6,4),
    pallfignum INT,
    pallfigoff INT,
    
    -- Additional metrics
    tmmark VARCHAR(5),
    av_pur_val DECIMAL(5,2),
    ae_flag VARCHAR(5),
    horse_comment TEXT,
    lst_salena VARCHAR(50),
    lst_salepr DECIMAL(10,2),
    lst_saleda INT,
    apprweight INT,
    axciskey VARCHAR(50),
    
    -- Standard deviation fields
    avg_spd_sd VARCHAR(10),
    ave_cl_sd VARCHAR(10),
    hi_spd_sd VARCHAR(10),
    
    -- Jockey/Trainer
    jockey VARCHAR(100),
    trainer VARCHAR(100),
    
    -- Calculated percentages
    win_pct DECIMAL(5,2),
    jockey_win_pct DECIMAL(5,2),
    trainer_win_pct DECIMAL(5,2),
    jt_combo_pct DECIMAL(5,2),
    
    -- Results (if available)
    finish_position INT,
    final_odds VARCHAR(20),
    win_payoff DECIMAL(8,2),
    place_payoff DECIMAL(8,2),
    show_payoff DECIMAL(8,2),
    result_scraped_at TIMESTAMP,
    
    UNIQUE(race_id, program_number)
);

-- Horse statistics table
CREATE TABLE horse_stats (
    id SERIAL PRIMARY KEY,
    entry_id INTEGER REFERENCES entries(id) ON DELETE CASCADE,
    stat_type VARCHAR(50),
    starts INT DEFAULT 0,
    wins INT DEFAULT 0,
    places INT DEFAULT 0,
    shows INT DEFAULT 0,
    earnings DECIMAL(10,2) DEFAULT 0,
    paid DECIMAL(10,2),
    roi DECIMAL(6,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(entry_id, stat_type)
);

-- Jockey information and statistics
CREATE TABLE jockey_stats (
    id SERIAL PRIMARY KEY,
    entry_id INTEGER REFERENCES entries(id) ON DELETE CASCADE,
    jockey_name VARCHAR(100),
    jock_key VARCHAR(20),
    j_type VARCHAR(5),
    stat_breed VARCHAR(10),
    stat_type VARCHAR(50),
    starts INT DEFAULT 0,
    wins INT DEFAULT 0,
    places INT DEFAULT 0,
    shows INT DEFAULT 0,
    earnings DECIMAL(10,2),
    paid DECIMAL(10,2),
    roi DECIMAL(6,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(entry_id, stat_type)
);

-- Trainer information and statistics
CREATE TABLE trainer_stats (
    id SERIAL PRIMARY KEY,
    entry_id INTEGER REFERENCES entries(id) ON DELETE CASCADE,
    trainer_name VARCHAR(100),
    train_key VARCHAR(20),
    t_type VARCHAR(5),
    stat_breed VARCHAR(10),
    stat_type VARCHAR(50),
    starts INT DEFAULT 0,
    wins INT DEFAULT 0,
    places INT DEFAULT 0,
    shows INT DEFAULT 0,
    earnings DECIMAL(10,2),
    paid DECIMAL(10,2),
    roi DECIMAL(6,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(entry_id, stat_type)
);

-- Sire statistics
CREATE TABLE sire_stats (
    id SERIAL PRIMARY KEY,
    entry_id INTEGER REFERENCES entries(id) ON DELETE CASCADE,
    sire_name VARCHAR(100),
    stud_fee DECIMAL(10,2),
    stat_breed VARCHAR(10),
    tmmark VARCHAR(5),
    stat_type VARCHAR(50),
    starts INT DEFAULT 0,
    wins INT DEFAULT 0,
    places INT DEFAULT 0,
    shows INT DEFAULT 0,
    earnings DECIMAL(12,2),
    paid DECIMAL(10,2),
    roi DECIMAL(6,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(entry_id, stat_type)
);

-- Dam statistics
CREATE TABLE dam_stats (
    id SERIAL PRIMARY KEY,
    entry_id INTEGER REFERENCES entries(id) ON DELETE CASCADE,
    dam_name VARCHAR(100),
    damsire_name VARCHAR(100),
    stat_breed VARCHAR(10),
    tmmark VARCHAR(5),
    stat_type VARCHAR(50),
    starts INT DEFAULT 0,
    wins INT DEFAULT 0,
    places INT DEFAULT 0,
    shows INT DEFAULT 0,
    earnings DECIMAL(12,2),
    paid DECIMAL(10,2),
    roi DECIMAL(6,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(entry_id, stat_type)
);

-- Workouts table
CREATE TABLE workouts (
    id SERIAL PRIMARY KEY,
    entry_id INTEGER REFERENCES entries(id) ON DELETE CASCADE,
    workout_number INT,
    days_back INT,
    description TEXT,
    ranking INT,
    rank_group INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Past performance data
CREATE TABLE pp_data (
    id SERIAL PRIMARY KEY,
    entry_id INTEGER REFERENCES entries(id) ON DELETE CASCADE,
    racedate DATE,
    trackcode VARCHAR(10),
    trackname VARCHAR(100),
    racenumber INT,
    racebreed VARCHAR(10),
    country VARCHAR(10),
    racetype VARCHAR(10),
    raceclass VARCHAR(10),
    claimprice INT,
    purse INT,
    classratin INT,
    trackcondi VARCHAR(10),
    distance INT,
    disttype VARCHAR(1),
    aboutdist VARCHAR(10),
    courseid VARCHAR(10),
    surface VARCHAR(10),
    pulledofft INT,
    winddirect VARCHAR(10),
    windspeed INT,
    trackvaria INT,
    sealedtrac VARCHAR(1),
    racegrade INT,
    agerestric VARCHAR(10),
    sexrestric VARCHAR(10),
    statebredr VARCHAR(10),
    abbrevcond VARCHAR(20),
    postpositi INT,
    favorite INT,
    weightcarr INT,
    jockfirst VARCHAR(50),
    jockmiddle VARCHAR(50),
    jocklast VARCHAR(50),
    jocksuffix VARCHAR(10),
    jockdisp VARCHAR(100),
    equipment VARCHAR(20),
    medication VARCHAR(10),
    fieldsize INT,
    posttimeod VARCHAR(10),
    shortcomme TEXT,
    longcommen TEXT,
    gatebreak INT,
    position1 INT,
    lenback1 DECIMAL(8,2),
    horsetime1 DECIMAL(8,2),
    leadertime DECIMAL(8,2),
    pacefigure INT,
    position2 INT,
    lenback2 DECIMAL(8,2),
    horsetime2 DECIMAL(8,2),
    leadertim2 DECIMAL(8,2),
    pacefigur2 INT,
    positionst INT,
    lenbackstr DECIMAL(8,2),
    horsetimes DECIMAL(8,2),
    leadertim3 DECIMAL(8,2),
    dqindicato VARCHAR(10),
    positionfi INT,
    lenbackfin DECIMAL(8,2),
    horsetimef DECIMAL(8,2),
    leadertim4 DECIMAL(8,2),
    speedfigur INT,
    turffigure DECIMAL(8,2),
    winnersspe INT,
    foreignspe INT,
    horseclaim INT,
    biasstyle VARCHAR(10),
    biaspath VARCHAR(10),
    complineho VARCHAR(100),
    complinele DECIMAL(8,2),
    complinewe INT,
    complinedq VARCHAR(10),
    complineh2 VARCHAR(100),
    complinel2 DECIMAL(8,2),
    complinew2 INT,
    complined2 VARCHAR(10),
    complineh3 VARCHAR(100),
    complinel3 DECIMAL(8,2),
    complinew3 INT,
    complined3 VARCHAR(10),
    linebefore TEXT,
    lineafter TEXT,
    domesticpp INT,
    oflfinish INT,
    runup_dist INT,
    rail_dist INT,
    apprweight INT,
    vd_claim VARCHAR(50),
    vd_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Analysis table (keep existing structure)
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

-- Create indexes for performance
CREATE INDEX idx_races_date ON races(date);
CREATE INDEX idx_races_track_code ON races(track_code);
CREATE INDEX idx_entries_race ON entries(race_id);
CREATE INDEX idx_entries_power ON entries(power_rating);
CREATE INDEX idx_analysis_entry ON analysis(entry_id);
CREATE INDEX idx_analysis_score ON analysis(overall_score DESC);
CREATE INDEX idx_horse_stats_entry ON horse_stats(entry_id);
CREATE INDEX idx_jockey_stats_entry ON jockey_stats(entry_id);
CREATE INDEX idx_trainer_stats_entry ON trainer_stats(entry_id);
CREATE INDEX idx_sire_stats_entry ON sire_stats(entry_id);
CREATE INDEX idx_dam_stats_entry ON dam_stats(entry_id);
CREATE INDEX idx_workouts_entry ON workouts(entry_id);
CREATE INDEX idx_pp_data_entry ON pp_data(entry_id);
CREATE INDEX idx_pp_data_date ON pp_data(racedate);