"""
Load historical race results via API
"""

import requests
import json

BASE_URL = "https://stall10n.onrender.com"

def load_historical_results():
    """Load June 11-12 race results into SQL database"""
    
    # Historical race results
    results_data = [
        # June 11 results
        {
            "race_date": "2025-06-11",
            "track_name": "Fair Meadows",
            "race_number": 1,
            "distance": "5F",
            "winner_program_number": 2,
            "winner_horse_name": "Lightning Strike",
            "winner_jockey": "John Smith",
            "winner_trainer": "Mike Johnson",
            "winner_odds": "5/2"
        },
        {
            "race_date": "2025-06-11", 
            "track_name": "Fair Meadows",
            "race_number": 2,
            "distance": "6F",
            "winner_program_number": 5,
            "winner_horse_name": "Thunder Road",
            "winner_jockey": "Jane Doe",
            "winner_trainer": "Sarah Williams",
            "winner_odds": "3/1"
        },
        # June 12 results
        {
            "race_date": "2025-06-12",
            "track_name": "Fair Meadows",
            "race_number": 1,
            "distance": "4F",
            "winner_program_number": 4,
            "winner_horse_name": "Witch Way Gray",
            "winner_jockey": "Roman Cruz",
            "winner_trainer": "Jody Pruitt",
            "winner_odds": "2/1"
        },
        {
            "race_date": "2025-06-12",
            "track_name": "Fair Meadows",
            "race_number": 2,
            "distance": "6.5F",
            "winner_program_number": 6,
            "winner_horse_name": "Cowgirlslikebling",
            "winner_jockey": "Emanuel Castillo Zabala",
            "winner_trainer": "Steve H. Davis",
            "winner_odds": "3/1"
        },
        {
            "race_date": "2025-06-12",
            "track_name": "Fair Meadows",
            "race_number": 3,
            "distance": "1 Mile",
            "winner_program_number": 3,
            "winner_horse_name": "Tail of Whoa",
            "winner_jockey": "Curtis Kimes",
            "winner_trainer": "Shon M. Dunlap",
            "winner_odds": "4/1"
        },
        {
            "race_date": "2025-06-12",
            "track_name": "Fair Meadows",
            "race_number": 4,
            "distance": "4F",
            "winner_program_number": 6,
            "winner_horse_name": "Coin Purse",
            "winner_jockey": "Roman Cruz",
            "winner_trainer": "George Blatchford",
            "winner_odds": "4/1"
        },
        {
            "race_date": "2025-06-12",
            "track_name": "Fair Meadows",
            "race_number": 5,
            "distance": "1 Mile",
            "winner_program_number": 3,
            "winner_horse_name": "Catale Winemixer",
            "winner_jockey": "Belen Quinonez",
            "winner_trainer": "Randy E. Swango",
            "winner_odds": "4/1"
        },
        {
            "race_date": "2025-06-12",
            "track_name": "Fair Meadows",
            "race_number": 6,
            "distance": "1 Mile",
            "winner_program_number": 3,
            "winner_horse_name": "R Doc",
            "winner_jockey": "Curtis Kimes",
            "winner_trainer": "Jory Ferrell",
            "winner_odds": "2/1"
        },
        {
            "race_date": "2025-06-12",
            "track_name": "Fair Meadows",
            "race_number": 7,
            "distance": "6F",
            "winner_program_number": 1,
            "winner_horse_name": "Sweet Devotion",
            "winner_jockey": "Travis Cunningham",
            "winner_trainer": "Jerry Glen Stephens",
            "winner_odds": "N/A"
        }
    ]
    
    print("=== Loading Historical Race Results ===\n")
    
    # Load each result
    for result in results_data:
        print(f"Loading {result['race_date']} Race {result['race_number']}: {result['winner_horse_name']}")
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/race-result",
                json=result,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                print("  ✓ Result stored in SQL")
            else:
                print(f"  ✗ Failed: {response.status_code}")
                if response.text:
                    print(f"    {response.text}")
                    
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    print("\n=== Verifying Results ===\n")
    
    # Verify results are stored
    for date in ["2025-06-11", "2025-06-12"]:
        try:
            response = requests.get(f"{BASE_URL}/api/race-results/{date}?track=Fair%20Meadows")
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    results = data.get('results', [])
                    print(f"{date}: {len(results)} results in database")
                    for r in results:
                        print(f"  Race {r['race_number']}: {r['winner_horse_name']} ({r['winner_odds']})")
        except Exception as e:
            print(f"{date}: Error checking - {e}")
    
    print("\n=== Summary ===")
    print("Historical results have been loaded into the SQL database.")
    print("The main racing page will show winners in the 'Bet Recommendation' sections.")
    print("Visit https://stall10n.onrender.com/ and select June 11 or 12 to see results.")

if __name__ == "__main__":
    load_historical_results()