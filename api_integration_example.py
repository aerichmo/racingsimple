"""
Example integration of Horse Racing USA API with STALL10N app

This shows how to add API endpoints to your existing Flask app
to fetch and update live odds data.
"""

from flask import jsonify, request
from odds_service import OddsService
import logging

# Initialize the odds service
odds_service = OddsService()

# Add these routes to your app.py file:

def add_odds_routes(app):
    """
    Add these routes to your existing Flask app
    """
    
    @app.route('/api/odds/<race_id>')
    def get_race_odds(race_id):
        """
        Fetch odds for a specific race
        Example: GET /api/odds/39302
        """
        try:
            race_data = odds_service.get_race_odds(race_id)
            
            if race_data:
                return jsonify({
                    'success': True,
                    'data': race_data
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Race not found'
                }), 404
                
        except Exception as e:
            logging.error(f"Error fetching odds: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/odds/update', methods=['POST'])
    def update_odds():
        """
        Update database with latest odds for a race
        Example: POST /api/odds/update
        Body: { "race_id": "39302" }
        """
        try:
            data = request.get_json()
            race_id = data.get('race_id')
            
            if not race_id:
                return jsonify({
                    'success': False,
                    'error': 'race_id required'
                }), 400
            
            # Fetch latest odds
            race_data = odds_service.get_race_odds(race_id)
            
            if not race_data:
                return jsonify({
                    'success': False,
                    'error': 'Failed to fetch race data'
                }), 404
            
            # Update database (you'll need to implement this in odds_service)
            success = odds_service.update_database_odds(race_data)
            
            return jsonify({
                'success': success,
                'message': f'Updated odds for {len(race_data["horses"])} horses'
            })
            
        except Exception as e:
            logging.error(f"Error updating odds: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/odds/search')
    def search_races():
        """
        Search for races (placeholder - needs API endpoint discovery)
        Example: GET /api/odds/search?date=2025-01-13&track=Parx
        """
        date = request.args.get('date')
        track = request.args.get('track')
        
        # This would search for races
        # Currently returns empty as we need to discover the API structure
        races = odds_service.api.search_races(date=date, track=track)
        
        return jsonify({
            'success': True,
            'data': races,
            'message': 'Search endpoint not yet implemented'
        })


# Integration steps for your app.py:
"""
1. Import the odds service at the top of app.py:
   from api_integration_example import add_odds_routes

2. After creating your Flask app, add the routes:
   app = Flask(__name__)
   # ... existing setup ...
   add_odds_routes(app)

3. Add a button in your admin interface to fetch/update odds:
   <button onclick="updateOdds(raceId)">Update Live Odds</button>

4. Add JavaScript function to call the API:
   async function updateOdds(raceId) {
       try {
           const response = await fetch('/api/odds/update', {
               method: 'POST',
               headers: { 'Content-Type': 'application/json' },
               body: JSON.stringify({ race_id: raceId })
           });
           const data = await response.json();
           if (data.success) {
               alert('Odds updated successfully!');
               location.reload();
           }
       } catch (error) {
           alert('Error updating odds: ' + error);
       }
   }

5. Update your database schema to store API race IDs:
   ALTER TABLE races ADD COLUMN api_race_id VARCHAR(50);

6. Set environment variable for API key (optional):
   export RAPIDAPI_KEY='your-api-key-here'
"""