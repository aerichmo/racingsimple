# HorseAPI Live Odds Integration

## Overview
This integration automatically fetches live horse racing odds at specific intervals before post time:
- 10 minutes before post
- 5 minutes before post  
- 2 minutes before post
- 1 minute before post
- At post time

## Setup

### 1. Get Your API Key
1. Sign up for a free trial at https://statpal.io
2. Get your access key from the dashboard

### 2. Configure API Key

#### Option A: Use Setup Script (Recommended)
```bash
python setup_horseapi.py
```
This will:
- Prompt for your API key
- Create a `.env.local` file (gitignored)
- Validate your configuration

#### Option B: Manual Setup
Create `.env.local` file:
```bash
HORSEAPI_ACCESS_KEY=your_access_key_here
DATABASE_URL=your_database_url_here
```

#### Option C: Environment Variables
```bash
export HORSEAPI_ACCESS_KEY="your_access_key_here"
export DATABASE_URL="your_database_url_here"
```

### 3. Deployment Configuration

**Heroku:**
```bash
heroku config:set HORSEAPI_ACCESS_KEY=your_key_here
```

**Render:**
Add in dashboard under Environment:
- `HORSEAPI_ACCESS_KEY` = your_key_here

**Other Platforms:**
Set environment variables according to platform docs

### 4. Database Setup
The integration will automatically create required tables on first run:
- Adds columns to `races` table
- Creates `odds_snapshots` table
- Creates `odds_movement` view for analysis

### 5. Install Dependencies
```bash
pip install -r requirements.txt
```

## Usage

### Running the Odds Monitor
As a standalone service:
```bash
python horseapi_odds_monitor.py
```

Or it will run automatically when you start the Flask app.

### API Endpoints

#### Enable Monitoring for a Race
```bash
POST /api/horseapi/monitor/race/{race_id}
{
    "horse_api_race_id": "ABC123",
    "post_time": "2025-06-16T14:30:00"
}
```

#### Get Monitoring Status
```bash
GET /api/horseapi/monitor/status
```

#### Get Odds History for a Race
```bash
GET /api/horseapi/odds/{race_id}
```

Returns:
- Complete odds history at each interval
- Odds movement analysis for each horse
- Percentage changes from 10min to post

### Admin Interface Integration

To enable odds monitoring for a race:

1. Add HorseAPI race ID to the race entry
2. Set the post time
3. Enable "Odds Monitoring" checkbox
4. The system will automatically schedule pulls

### Rate Limits
- HorseAPI allows 10 calls per hour
- Monitor schedules 5 calls per race (one for each interval)
- Plan accordingly - can monitor 2 races per hour

## Architecture

### Components

1. **horseapi_service.py**
   - Core API integration
   - Rate limiting
   - Request handling

2. **horseapi_db_integration.py**
   - Database operations
   - Odds storage
   - Movement analysis

3. **horseapi_odds_monitor.py**
   - Scheduling engine
   - Monitoring coordination
   - Flask endpoints

### Data Flow

1. Admin enables monitoring for a race
2. Monitor schedules 5 pulls based on post time
3. At each interval, odds are fetched and stored
4. UI can display real-time odds and movements
5. After post time, monitoring automatically stops

## Troubleshooting

### Common Issues

1. **Rate Limit Errors**
   - Check `/api/horseapi/monitor/status` for active monitors
   - Limit to 2 races per hour

2. **Missing Odds Data**
   - Verify HorseAPI race ID is correct
   - Check if race is available in your region (US/UK)
   - Ensure post time is accurate

3. **Database Errors**
   - Run `python horseapi_db_integration.py` to create tables
   - Check DATABASE_URL environment variable

### Logs
Monitor logs show:
- Scheduled pull times
- API requests and responses  
- Database operations
- Rate limit status

## Example Odds Movement Display

```
Horse #3 - Thunder Strike
10min: 5/1 → 5min: 9/2 → 2min: 4/1 → 1min: 7/2 → Post: 3/1
Total Change: -40% (Shortened)

Horse #7 - Lightning Bolt  
10min: 2/1 → 5min: 5/2 → 2min: 3/1 → 1min: 7/2 → Post: 4/1
Total Change: +100% (Drifted)
```