"""
Simplified endpoints for race results management
"""

from flask import jsonify, request
from simplified_race_results import RaceResultsManager
import logging

logger = logging.getLogger(__name__)

def add_simplified_endpoints(app):
    """Add simplified race results endpoints to Flask app"""
    
    results_manager = RaceResultsManager()
    
    @app.route('/api/race-result', methods=['POST'])
    def store_race_result():
        """
        Store a race result
        POST /api/race-result
        Body: {
            "race_date": "2025-06-13",
            "track_name": "Fair Meadows",
            "race_number": 1,
            "distance": "6F",
            "winner_program_number": 3,
            "winner_horse_name": "Thunder Bolt",
            "winner_jockey": "John Smith",
            "winner_trainer": "Jane Doe", 
            "winner_odds": "5/2"
        }
        """
        try:
            data = request.get_json()
            
            # Validate required fields
            required = ['race_date', 'track_name', 'race_number', 'winner_horse_name']
            for field in required:
                if field not in data:
                    return jsonify({
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }), 400
            
            # Store the result
            success = results_manager.store_race_result(data)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': f"Result stored for {data['track_name']} Race {data['race_number']}"
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to store result'
                }), 500
                
        except Exception as e:
            logger.error(f"Error storing race result: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/race-results/<date>')
    def get_race_results_simple(date):
        """
        Get race results for a specific date
        GET /api/race-results/2025-06-13?track=Fair%20Meadows
        """
        try:
            track = request.args.get('track')
            results = results_manager.get_race_results(date, track)
            
            return jsonify({
                'success': True,
                'date': date,
                'track': track,
                'results': results
            })
            
        except Exception as e:
            logger.error(f"Error fetching results: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/update-result-display', methods=['POST'])
    def update_result_display():
        """
        Update bet recommendation to show race result
        POST /api/update-result-display
        Body: {
            "race_date": "2025-06-13",
            "track_name": "Fair Meadows", 
            "race_number": 1,
            "winner_name": "Thunder Bolt",
            "winner_odds": "5/2"
        }
        """
        try:
            data = request.get_json()
            
            results_manager.update_bet_recommendation(
                data['race_date'],
                data.get('track_name', 'Fair Meadows'),
                data['race_number'],
                data['winner_name'],
                data.get('winner_odds')
            )
            
            return jsonify({
                'success': True,
                'message': 'Result display updated'
            })
            
        except Exception as e:
            logger.error(f"Error updating display: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500