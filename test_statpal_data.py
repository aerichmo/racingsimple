#!/usr/bin/env python3
"""
Test StatPal API to document all available data fields
"""
import json
from statpal_service import StatPalService

def test_and_document_api():
    """Test API and document all available fields"""
    service = StatPalService()
    
    print("Testing StatPal API Data Structure\n")
    print("=" * 50)
    
    # Test UK data
    print("\n1. Testing UK Live Races...")
    uk_races = service.get_live_races('uk')
    
    if uk_races and len(uk_races) > 0:
        print(f"Found {len(uk_races)} UK races")
        print("\nSample Race Data Fields:")
        for key, value in uk_races[0].items():
            print(f"  - {key}: {type(value).__name__} = {value}")
        
        # Get detailed race info
        race_id = uk_races[0]['id']
        details = service.get_race_details(race_id, 'uk')
        
        if details:
            print("\n\nRace Info Fields:")
            for key, value in details['race_info'].items():
                print(f"  - {key}: {type(value).__name__} = {value}")
            
            if details['horses']:
                print("\n\nHorse Data Fields:")
                horse = details['horses'][0]
                for key, value in horse.items():
                    if key != 'form':
                        print(f"  - {key}: {type(value).__name__} = {value}")
                
                print("\n\nForm Data Structure:")
                if horse['form']:
                    print(json.dumps(horse['form'], indent=2))
                else:
                    print("  No form data available")
    
    # Test US data
    print("\n\n" + "=" * 50)
    print("\n2. Testing US Live Races...")
    us_races = service.get_live_races('us')
    
    if us_races and len(us_races) > 0:
        print(f"Found {len(us_races)} US races")
        
        # Find Prairie Meadows
        prairie_races = [r for r in us_races if 'prairie' in r['venue_name'].lower()]
        if prairie_races:
            print(f"\nFound {len(prairie_races)} Prairie Meadows races")
            race_id = prairie_races[0]['id']
            details = service.get_race_details(race_id, 'us')
            
            if details and details['horses']:
                print("\n\nUS Horse Data Fields:")
                horse = details['horses'][0]
                for key, value in horse.items():
                    if key != 'form':
                        print(f"  - {key}: {type(value).__name__} = {value}")
                
                if horse['form']:
                    print("\n\nUS Form Data:")
                    print(json.dumps(horse['form'], indent=2))
    
    # Get raw API response for deeper inspection
    print("\n\n" + "=" * 50)
    print("\n3. Raw API Response Structure...")
    
    raw_data = service._make_request('live', 'uk')
    if raw_data and 'scores' in raw_data:
        print("\nTop-level keys in response:")
        for key in raw_data.keys():
            print(f"  - {key}")
        
        if 'tournament' in raw_data['scores']:
            venue = raw_data['scores']['tournament'][0]
            print("\n\nVenue-level fields:")
            for key in venue.keys():
                if key != 'race':
                    print(f"  - {key}: {venue.get(key, '')}")
            
            if 'race' in venue and venue['race']:
                race = venue['race'][0]
                print("\n\nRace-level fields:")
                for key in race.keys():
                    if key != 'runners':
                        print(f"  - {key}: {race.get(key, '')}")
                
                if 'runners' in race and 'horse' in race['runners']:
                    horse = race['runners']['horse'][0]
                    print("\n\nALL Horse fields from raw API:")
                    for key in horse.keys():
                        print(f"  - {key}: {horse.get(key, '')}")

if __name__ == "__main__":
    test_and_document_api()