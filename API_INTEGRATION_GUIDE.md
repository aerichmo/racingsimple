# Horse Racing USA API Integration Guide

## API Limits
- **Daily Quota**: 50 calls/day (40 allocated for STALL10N)
- **Cost**: Check RapidAPI pricing page
- **Caching**: 1-hour cache implemented to preserve quota

## Setup

1. **API Key**: Already configured in `odds_service.py`
   ```
   1c6ef83f5bmshae8b269821b23dep1c77dbjsn9ed69f94d9fa
   ```

2. **Quota Tracking**: Automatic tracking in `api_quota_tracker.py`
   - Tracks daily usage in `api_quota.json`
   - Prevents exceeding 40 calls/day limit
   - Shows warnings when approaching limit

## Usage

### Basic Race Data Fetch
```python
from api_quota_tracker import QuotaManagedOddsService

service = QuotaManagedOddsService()
result = service.get_race_odds(39302)  # Race ID from API

if 'error' not in result:
    race_data = result['data']
    print(f"Remaining API calls today: {result['remaining_quota']}")
```

### Check Quota Status
```python
status = service.get_quota_status()
print(f"Used {status['calls_today']} of {status['daily_limit']} calls today")
```

## Integration with STALL10N

1. **Add to your Flask app** (in `app.py`):
```python
from api_quota_tracker import QuotaManagedOddsService

odds_service = QuotaManagedOddsService()

@app.route('/api/odds/<race_id>')
def get_odds(race_id):
    result = odds_service.get_race_odds(race_id)
    return jsonify(result)

@app.route('/api/quota-status')
def quota_status():
    return jsonify(odds_service.get_quota_status())
```

2. **Add to Admin Interface**:
   - Add field for API Race ID in your race entry form
   - Add "Fetch Live Odds" button that calls `/api/odds/<race_id>`
   - Display remaining quota on admin page

## Important Notes

1. **Quota Management**: 
   - Only 40 API calls per day allowed
   - Cache is set to 1 hour to minimize calls
   - Check quota before important operations

2. **Race IDs**: 
   - Need to discover how to find current race IDs
   - Example ID 39302 is from 2022 (historical data)
   - May need to explore API documentation for live race discovery

3. **Data Limitations**:
   - API provides race results and horse info
   - Live odds arrays were empty in test data
   - May need to verify with RapidAPI support for real-time odds

## Next Steps

1. Contact RapidAPI support to understand:
   - How to get current/today's race IDs
   - Whether live odds are available
   - API endpoint documentation

2. Implement database integration:
   - Add `api_race_id` column to races table
   - Create sync mechanism for odds updates
   - Build UI for quota monitoring

3. Set up automated odds updates:
   - Cron job or scheduled task
   - Respect quota limits
   - Update only active races