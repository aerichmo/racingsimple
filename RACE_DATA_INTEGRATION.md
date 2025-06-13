# Race Data Integration Guide

## Overview
This system automatically pulls live odds 10 minutes before post time and previous race results in a single API call, storing everything in PostgreSQL.

## Database Schema

### New Tables Created:
1. **race_results** - Stores completed race results
2. **live_odds_snapshot** - Stores odds at specific time points
3. **race_schedule** - Tracks races and their post times

## Setup Instructions

### 1. Update Your Flask App

Add to your `app.py`:

```python
import psycopg2
from race_data_endpoints import add_race_data_endpoints

# After creating your Flask app
app = Flask(__name__)
# ... existing setup ...

# Add the new endpoints
add_race_data_endpoints(app)
```

### 2. Initialize Enhanced Database

Run once to create new tables:

```python
from race_data_puller import RaceDataPuller
puller = RaceDataPuller()
# Tables are created automatically
```

### 3. Set Up Automated Pulling

Option A: Using cron (Linux/Mac):
```bash
# Add to crontab (crontab -e)
*/5 * * * * /usr/bin/python3 /Users/alecrichmond/STALL10N/cron_scheduler.py >> /Users/alecrichmond/STALL10N/cron.log 2>&1
```

Option B: Using Python scheduler:
```python
import schedule
import time
from race_data_puller import run_scheduled_pull

schedule.every(5).minutes.do(run_scheduled_pull)

while True:
    schedule.run_pending()
    time.sleep(60)
```

## Usage

### Schedule a Race for Auto-Pull

1. In admin interface, go to "Race Data Management"
2. Enter:
   - Track name (e.g., "Fair Meadows")
   - Race date
   - Race number
   - Post time (important: must be accurate)
   - API race ID (if known)
3. Click "Schedule Race"

The system will automatically:
- Pull data 10 minutes before post time
- Get results from previous race (if race > 1)
- Get live odds for current race
- Use only 1-2 API calls per race

### Manual Data Pull

For testing or missed races:
1. Enter track, date, and race number
2. Provide API race IDs if known
3. Click "Pull Data Now"

### View Data

New API endpoints:
- `/api/race-results/2025-06-12` - Get all results for a date
- `/api/live-odds/Fair%20Meadows/3` - Get latest odds for a race
- `/api/upcoming-pulls` - See scheduled pulls and quota

## API Quota Management

- **Daily limit**: 40 calls
- **Per race**: 1-2 calls (previous results + current odds)
- **Maximum races/day**: ~20-30 races
- **Caching**: 1 hour to prevent duplicate calls

## Database Queries

### Get Latest Odds for a Race
```sql
SELECT DISTINCT ON (program_number)
    program_number, horse_name, live_odds, win_probability
FROM live_odds_snapshot
WHERE track_name = 'Fair Meadows' 
    AND race_number = 3
    AND race_date = '2025-06-14'
ORDER BY program_number, snapshot_taken_at DESC;
```

### Get Race Results
```sql
SELECT * FROM race_results
WHERE race_date = '2025-06-14'
ORDER BY track_name, race_number;
```

### Check Scheduled Races
```sql
SELECT * FROM race_schedule
WHERE scheduled_post_time > NOW()
ORDER BY scheduled_post_time;
```

## Important Notes

1. **Post Times**: Must be accurate! Data pulls 10 minutes before
2. **API Race IDs**: Need to discover these from API documentation
3. **Time Zones**: Ensure post times match your server timezone
4. **Quota Monitoring**: Check `/api/upcoming-pulls` regularly
5. **Results Timing**: Previous race must be finished for results

## Troubleshooting

### No Data Pulled
- Check cron logs: `tail -f /Users/alecrichmond/STALL10N/cron.log`
- Verify post time is correct
- Check API quota isn't exhausted
- Ensure race_schedule entry exists

### Missing Odds
- API might not have live odds yet
- Race might be too far in future
- Check api_race_id is correct

### Database Errors
- Check DATABASE_URL environment variable
- Verify PostgreSQL is running
- Check table permissions

## Next Steps

1. Find reliable source for API race IDs
2. Consider integrating with track websites for post times
3. Add alerts when quota is low
4. Build analytics on historical odds movements