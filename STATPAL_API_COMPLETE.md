# StatPal API Integration - Complete Guide

## ✅ GREAT NEWS: Both UK and US Racing Data Are Working!

Your API key `5aad32df-dc2d-4222-9023-64f422f9071f` has access to both UK and US racing data!

## Correct Endpoints

### UK Racing
```
GET https://statpal.io/api/v1/horse-racing/live/uk?access_key=YOUR_KEY
```

### US Racing  
```
GET https://statpal.io/api/v1/horse-racing/live/usa?access_key=YOUR_KEY
```

**Important**: Use `usa` not `us` for American racing data!

## Usage with StatPal Service

```python
from statpal_service import StatPalService

service = StatPalService()

# Get UK races
uk_races = service.get_live_races('uk')

# Get US races (use 'us' - it will be converted to 'usa' internally)
us_races = service.get_live_races('us')

# Get race details
details = service.get_race_details(race_id, country)
```

## Available Data

### UK Racing
- 5 venues (Ascot, Southwell, Beverley, Stratford, Thirsk)
- ~34 races per day
- Full horse details including form data

### US Racing  
- 8 venues (Finger Lakes, Horseshoe Indianapolis, Louisiana Downs, etc.)
- ~72 races per day
- Complete entries with jockey/trainer info

## Data Structure

Each race includes:
- Venue name and ID
- Race name and number
- Post time and distance
- Going conditions (UK)
- Number of horses

Horse details include:
- Program number and stall
- Horse name, age, weight
- Jockey and trainer
- Form statistics (wins, places, win percentage)

## Next Steps

1. **Database Integration**: Store race and horse data
2. **Live Updates**: Set up scheduled pulls for race data
3. **Odds Monitoring**: Track changes throughout the day
4. **UI Development**: Display races by country/venue

## Summary

No upgrade needed! Your StatPal subscription includes both UK and US racing data. The key was using the correct endpoint format (`usa` instead of `us`).