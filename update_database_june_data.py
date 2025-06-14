import requests
import json

BASE_URL = 'https://stall10n.onrender.com'

print("Step 1: Removing June 11 and June 12 data...")

# We need to create a new endpoint or use existing ones
# First, let's check what endpoints we have available

# Since we don't have a direct delete by date endpoint, we'll need to delete individual entries
# Get all races first
response = requests.get(f'{BASE_URL}/api/races')
all_races = response.json()

# Filter June 11 and 12 races
june_11_12_races = [r for r in all_races if r['race_date'] in ['2025-06-11', '2025-06-12']]

print(f"Found {len(june_11_12_races)} horses to delete from June 11 and 12")

# Delete each entry
deleted_count = 0
for race in june_11_12_races:
    try:
        delete_url = f"{BASE_URL}/api/races/{race['race_date']}/{race['race_number']}/{race['program_number']}"
        response = requests.delete(delete_url)
        if response.status_code == 200:
            deleted_count += 1
            if deleted_count % 10 == 0:
                print(f"Deleted {deleted_count} entries...")
    except Exception as e:
        print(f"Error deleting {race['horse_name']}: {e}")

print(f"Successfully deleted {deleted_count} entries from June 11 and 12")

# Now let's prepare June 13 data with Live Odds
print("\nStep 2: Updating June 13 data with Live Odds...")

# Load the June 13 data
with open('fair_meadows_june13_2025.json', 'r') as f:
    june13_data = json.load(f)

# Delete existing June 13 data first
june_13_races = [r for r in all_races if r['race_date'] == '2025-06-13']
for race in june_13_races:
    try:
        delete_url = f"{BASE_URL}/api/races/{race['race_date']}/{race['race_number']}/{race['program_number']}"
        requests.delete(delete_url)
    except:
        pass

# Prepare batch data with Live Odds
batch_data = []
for race_num, race_data in june13_data['races'].items():
    for horse in race_data['horses']:
        win_prob = float(horse['true_odds'].rstrip('%'))
        adj_odds = float(horse['adj_true_odds'].rstrip('%'))
        
        batch_data.append({
            'race_date': june13_data['date'],
            'race_number': int(race_num),
            'program_number': horse['program_number'],
            'horse_name': horse['horse_name'],
            'win_probability': win_prob,
            'morning_line': horse['morning_line'],
            'adj_odds': adj_odds,
            'realtime_odds': horse['live_odds']  # This is the Live Odds field
        })

# Send batch data
response = requests.post(
    f'{BASE_URL}/api/races/batch',
    json={'races': batch_data},
    headers={'Content-Type': 'application/json'}
)

if response.status_code == 200:
    print(f"Successfully loaded {len(batch_data)} horses for June 13 with Live Odds!")
else:
    print(f"Error loading June 13 data: {response.status_code}")
    print(response.text)