# StatPal Horse Racing API Integration Guide

## API Configuration
- **API Key**: Configured in `.env` as `STATPAL_ACCESS_KEY`
- **Base URL**: `https://statpal.io/api/v1/horse-racing`
- **Coverage**: UK races (US requires subscription upgrade)

## Setup

1. **API Key**: Already configured in `.env`
   ```
   STATPAL_ACCESS_KEY=5aad32df-dc2d-4222-9023-64f422f9071f
   ```

2. **Service Module**: Use `statpal_service.py`
   ```python
   from statpal_service import StatPalService
   
   service = StatPalService()
   ```

## Available Endpoints

### UK Racing (Working)
```python
# Get live UK races
races = service.get_live_races('uk')

# Get race details with runners
details = service.get_race_details(race_id, 'uk')
```

### US Racing (Requires Upgrade)
Contact support@statpal.io to enable US racing data.

## Integration with STALL10N

1. **Add to your Flask app** (in `app.py`):
```python
from statpal_service import StatPalService

statpal_service = StatPalService()

@app.route('/api/uk-races')
def get_uk_races():
    races = statpal_service.get_live_races('uk')
    return jsonify(races)

@app.route('/api/race/<race_id>')
def get_race_details(race_id):
    details = statpal_service.get_race_details(race_id, 'uk')
    return jsonify(details)
```

2. **Data Structure**:
   - Races include: venue, race number, post time, distance, going conditions
   - Horse details: name, jockey, trainer, age, weight, form statistics

## Important Notes

1. **Authentication**: 
   - UK endpoints use `?access_key=YOUR_KEY` parameter
   - US endpoints require `Authorization: Bearer YOUR_KEY` header

2. **Data Format**: 
   - Races grouped by venue/tournament
   - Rich horse form data including win percentages and race records

3. **Real-time Updates**:
   - Live race data available
   - No specific odds endpoint (integrated in race details)

## Next Steps

1. For US racing access:
   - Email support@statpal.io
   - Include API key: 5aad32df-dc2d-4222-9023-64f422f9071f
   - Request US racing data access

2. Implement database integration:
   - Store race and horse data
   - Build sync mechanism for updates
   - Create UI for race monitoring

3. Set up automated data pulls:
   - Schedule regular updates for live races
   - Cache results to minimize API calls
   - Monitor specific venues of interest