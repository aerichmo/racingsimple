# RTN Video Capture Setup Guide

## Overview
This system captures live odds and race data from RTN (Racetrack Television Network) video streams for Fair Meadows races.

## Prerequisites

1. **RTN Subscription** ($15/month)
   - Sign up at https://online.rtn.tv
   - Save your username and password

2. **Install Dependencies**
   ```bash
   # Install Python packages
   pip install -r requirements_rtn.txt
   
   # Install system dependencies (macOS)
   brew install tesseract
   brew install --cask chromedriver
   
   # For Linux
   sudo apt-get install tesseract-ocr
   # Download chromedriver from https://chromedriver.chromium.org/
   ```

3. **Set Environment Variables**
   ```bash
   export RTN_USERNAME="your_rtn_username"
   export RTN_PASSWORD="your_rtn_password"
   export DATABASE_URL="your_existing_postgres_url"
   ```

## Files Created

1. **rtn_capture.py** - Main capture script
   - Automates Chrome browser
   - Logs into RTN
   - Captures screen regions
   - Saves raw images

2. **rtn_odds_parser.py** - OCR and parsing
   - Preprocesses images for OCR
   - Extracts odds, horse names, pools
   - Handles common OCR errors

3. **rtn_runner.py** - Database integration
   - Manages capture sessions
   - Saves data to PostgreSQL
   - Integrates with existing STALL10N system

## How to Run

### Test Mode (Single Race)
```bash
python rtn_capture.py
```

### Production Mode (Full Session)
```bash
python rtn_runner.py
```

### Schedule for Race Days
Add to crontab for Fair Meadows race days (Thu-Sun):
```bash
# Run at 5:30 PM on race days
30 17 * * 4-7 cd /path/to/STALL10N && python rtn_runner.py >> rtn_capture.log 2>&1
```

## Database Tables Created

- `rtn_capture_sessions` - Track capture sessions
- `rtn_odds_snapshots` - Store odds over time
- `rtn_pool_data` - Store pool amounts

## Data Flow

1. **Browser Automation** → Navigate to Fair Meadows stream
2. **Screen Capture** → Capture odds board, tote board, race info
3. **OCR Processing** → Extract text from images
4. **Data Parsing** → Structure the extracted data
5. **Database Storage** → Save to PostgreSQL
6. **API Access** → Query via existing endpoints

## Monitoring

Check capture status:
```sql
-- Latest capture session
SELECT * FROM rtn_capture_sessions 
ORDER BY session_start DESC LIMIT 1;

-- Latest odds for a race
SELECT * FROM rtn_odds_snapshots 
WHERE race_date = CURRENT_DATE 
AND race_number = 1 
ORDER BY snapshot_time DESC;
```

## Troubleshooting

1. **Login Failed**
   - Check RTN credentials
   - Verify subscription is active
   - RTN may have changed login page

2. **OCR Not Working**
   - Ensure Tesseract is installed
   - Check screen resolution matches expected regions
   - Save debug images to verify capture

3. **No Data Captured**
   - Fair Meadows might not be racing
   - Check RTN schedule
   - Verify track name in RTN interface

## Integration with Existing System

The captured data integrates with your existing:
- Win probability calculations
- Betting strategy analysis
- Web dashboard at `/api/live-odds/Fair%20Meadows/[race_number]`

## Next Steps

1. Test with live Fair Meadows stream
2. Adjust screen regions based on actual RTN layout
3. Train custom OCR model for better accuracy
4. Add race result capture
5. Implement alert system for value bets