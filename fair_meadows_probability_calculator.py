#!/usr/bin/env python3
"""
Fair Meadows Win Probability Calculator
Integrates with existing JSON data structure to add probability calculations
"""
import json
import os
from typing import Dict, List, Optional
from win_probability_system import WinProbabilityCalculator, HorseMetrics
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FairMeadowsProbabilityEnhancer:
    """
    Enhances Fair Meadows race data with win probability calculations
    Designed to work with existing JSON structure
    """
    
    def __init__(self, custom_weights: Optional[Dict[str, float]] = None):
        """Initialize with probability calculator"""
        self.calculator = WinProbabilityCalculator(custom_weights)
        
    def enhance_race_data(self, json_path: str) -> Dict:
        """
        Load Fair Meadows JSON and add probability calculations
        
        Args:
            json_path: Path to Fair Meadows JSON file
            
        Returns:
            Enhanced race data with probabilities
        """
        # Load existing data
        with open(json_path, 'r') as f:
            race_data = json.load(f)
        
        # Process each race
        for race_num, race_info in race_data['races'].items():
            # Convert to format expected by calculator
            calc_format = self._convert_to_calc_format(race_info, race_data)
            
            # Calculate probabilities
            horse_metrics = self.calculator.calculate_probabilities(calc_format)
            
            # Merge results back into original format
            self._merge_probabilities(race_info, horse_metrics)
        
        # Add metadata
        race_data['probability_analysis'] = {
            'generated_at': race_data.get('last_updated', ''),
            'method': 'StatPal-based Win Probability Model',
            'weights': self.calculator.weights
        }
        
        return race_data
    
    def _convert_to_calc_format(self, race_info: Dict, full_data: Dict) -> Dict:
        """Convert Fair Meadows format to calculator format"""
        # Extract race details
        calc_data = {
            'race_info': {
                'name': f"Race {race_info['race_number']}",
                'venue': full_data.get('track', 'Fair Meadows'),
                'distance': race_info.get('distance', ''),
                'class': race_info.get('race_type', ''),
                'going': 'Fast'  # Default for US tracks
            },
            'horses': []
        }
        
        # Convert each horse
        for horse in race_info.get('horses', []):
            horse_data = {
                'id': str(horse['program_number']),
                'name': horse['horse_name'],
                'number': str(horse['program_number']),
                'jockey': horse.get('jockey', ''),
                'trainer': horse.get('trainer', ''),
                'weight': horse.get('weight', ''),
                'rating': self._estimate_rating_from_odds(horse),
                'form': self._create_form_from_odds(horse)
            }
            calc_data['horses'].append(horse_data)
        
        return calc_data
    
    def _estimate_rating_from_odds(self, horse: Dict) -> str:
        """Estimate a rating based on morning line odds"""
        ml_odds = horse.get('morning_line', '99/1')
        
        # Convert fractional odds to probability
        try:
            if '/' in ml_odds:
                num, denom = ml_odds.split('/')
                decimal_odds = float(num) / float(denom) + 1
                implied_prob = 1 / decimal_odds
                
                # Convert to rating (0-100 scale)
                rating = int(implied_prob * 100)
                return str(rating)
        except:
            pass
        
        return '50'  # Default middle rating
    
    def _create_form_from_odds(self, horse: Dict) -> Dict:
        """Create synthetic form data from available odds"""
        # Use true odds percentages if available
        true_odds = horse.get('true_odds', '10%')
        itm_odds = horse.get('itm_true_odds', '33%')
        
        try:
            win_pct = float(true_odds.strip('%'))
            itm_pct = float(itm_odds.strip('%'))
            
            # Estimate runs based on typical samples
            estimated_runs = 10
            estimated_wins = int(win_pct / 100 * estimated_runs)
            estimated_places = int((itm_pct - win_pct) / 100 * estimated_runs)
            
            return {
                'recent': {
                    'last_10': {
                        'runs': str(estimated_runs),
                        'wins': str(estimated_wins),
                        'places': str(estimated_places),
                        'win_pct': true_odds
                    }
                }
            }
        except:
            return {}
    
    def _merge_probabilities(self, race_info: Dict, horse_metrics: List[HorseMetrics]):
        """Merge calculated probabilities back into race data"""
        # Create lookup by program number
        metrics_by_num = {m.program_number: m for m in horse_metrics}
        
        # Update each horse
        for horse in race_info.get('horses', []):
            pgm_num = horse['program_number']
            if pgm_num in metrics_by_num:
                metrics = metrics_by_num[pgm_num]
                
                # Add new probability fields
                horse['win_probability'] = f"{metrics.adjusted_probability * 100:.1f}%"
                horse['projected_odds'] = metrics.final_odds
                horse['probability_rank'] = horse_metrics.index(metrics) + 1
                
                # Add component scores for transparency
                horse['probability_factors'] = {
                    'form_score': round(metrics.recent_form_score, 2),
                    'speed_rating': round(metrics.speed_figure, 2),
                    'class_rating': round(metrics.class_rating, 2),
                    'connections': round((metrics.jockey_win_rate + metrics.trainer_win_rate) / 2, 2)
                }


def create_enhanced_html(enhanced_data: Dict) -> str:
    """Generate HTML with probability analysis"""
    date_str = enhanced_data.get('date', '')
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Fair Meadows - {date_str} (Enhanced with Probabilities) | STALL10N</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            background-color: #FFFFFF;
            color: #001E60;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1600px;
            margin: 0 auto;
            padding: 20px;
        }}
        h1 {{ 
            color: #0053E2;
            font-size: 2.5rem;
            margin-bottom: 30px;
            text-align: center;
            font-weight: 300;
            letter-spacing: 2px;
            text-transform: uppercase;
        }}
        h2 {{
            color: #001E60;
            font-size: 1.8rem;
            margin: 30px 0 15px;
            font-weight: 400;
            border-bottom: 2px solid #0053E2;
            padding-bottom: 10px;
        }}
        h3 {{
            color: #0053E2;
            font-size: 1.3rem;
            margin: 20px 0 10px;
            font-weight: 400;
        }}
        .update-time {{
            text-align: center;
            color: #666;
            font-size: 0.9rem;
            margin-bottom: 30px;
        }}
        .race-date {{ 
            margin: 40px 0;
            background: #FFFFFF;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 5px 20px rgba(0, 30, 96, 0.1);
            border: 1px solid #A9DDF7;
        }}
        table {{ 
            border-collapse: collapse; 
            width: 100%; 
            margin: 20px 0;
            background-color: #FFFFFF;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 3px 15px rgba(0, 30, 96, 0.1);
            border: 1px solid #A9DDF7;
        }}
        th, td {{ 
            padding: 15px 10px;
            text-align: center;
        }}
        th {{ 
            background-color: #0053E2;
            color: #FFFFFF;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-size: 0.85rem;
            border-bottom: 3px solid #4DBDF5;
        }}
        td {{
            background-color: #FFFFFF;
            border-bottom: 1px solid #A9DDF7;
            font-weight: 400;
            color: #001E60;
            font-size: 0.9rem;
        }}
        tr:hover td {{
            background-color: #A9DDF7;
            transition: background-color 0.3s ease;
        }}
        tr:last-child td {{
            border-bottom: none;
        }}
        .program-number {{
            font-weight: 700;
            color: #4DBDF5;
        }}
        .horse-name {{
            font-weight: 500;
            color: #001E60;
            text-align: left;
            padding-left: 15px;
        }}
        .win-prob {{
            color: #0053E2;
            font-weight: 700;
            font-size: 1.1rem;
        }}
        .projected-odds {{
            color: #FF6B00;
            font-weight: 600;
        }}
        .rank-1 {{ background-color: #F0F8FF; }}
        .rank-2 {{ background-color: #F5FBFF; }}
        .rank-3 {{ background-color: #FAFEFF; }}
        .factors {{
            font-size: 0.8rem;
            color: #666;
        }}
        .legend {{
            margin: 20px 0;
            padding: 15px;
            background-color: #F0F8FF;
            border-radius: 10px;
            font-size: 0.9rem;
        }}
        .legend h4 {{
            color: #0053E2;
            margin-bottom: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Fair Meadows Racing - Probability Analysis</h1>
        <h2>{date_str}</h2>
        <div class="update-time">Last Updated: {enhanced_data.get('last_updated', '')}</div>
        
        <div class="legend">
            <h4>Win Probability Analysis</h4>
            <p>Probabilities calculated using form, speed ratings, class, connections, and race conditions. 
            Rankings indicate likelihood of winning (1 = most likely).</p>
        </div>
"""
    
    # Add each race
    for race_num in sorted(enhanced_data['races'].keys(), key=int):
        race = enhanced_data['races'][race_num]
        
        html += f"""
        <div class="race-date">
            <h3>Race {race['race_number']} - {race.get('race_type', '')} - {race.get('distance', '')}</h3>
            <p style="color: #666; margin-bottom: 15px;">Post Time: {race.get('post_time', '')}</p>
            <table>
                <thead>
                    <tr>
                        <th style="width: 5%;">Rank</th>
                        <th style="width: 5%;">PGM</th>
                        <th style="width: 20%;">Horse</th>
                        <th style="width: 8%;">Win %</th>
                        <th style="width: 8%;">Proj Odds</th>
                        <th style="width: 8%;">ML</th>
                        <th style="width: 12%;">Jockey</th>
                        <th style="width: 12%;">Trainer</th>
                        <th style="width: 22%;">Factors (Form/Speed/Class/Conn)</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        # Sort horses by probability rank
        sorted_horses = sorted(race['horses'], 
                             key=lambda h: h.get('probability_rank', 999))
        
        for horse in sorted_horses:
            rank = horse.get('probability_rank', '-')
            rank_class = f"rank-{rank}" if rank <= 3 else ""
            
            factors = horse.get('probability_factors', {})
            factors_str = f"{factors.get('form_score', 0):.2f}/{factors.get('speed_rating', 0):.2f}/{factors.get('class_rating', 0):.2f}/{factors.get('connections', 0):.2f}"
            
            html += f"""
                    <tr class="{rank_class}">
                        <td><strong>{rank}</strong></td>
                        <td class="program-number">{horse['program_number']}</td>
                        <td class="horse-name">{horse['horse_name']}</td>
                        <td class="win-prob">{horse.get('win_probability', '-')}</td>
                        <td class="projected-odds">{horse.get('projected_odds', '-')}</td>
                        <td>{horse.get('morning_line', '-')}</td>
                        <td>{horse.get('jockey', '-')}</td>
                        <td>{horse.get('trainer', '-')}</td>
                        <td class="factors">{factors_str}</td>
                    </tr>
"""
        
        html += """
                </tbody>
            </table>
        </div>
"""
    
    # Add probability model info
    if 'probability_analysis' in enhanced_data:
        weights = enhanced_data['probability_analysis']['weights']
        html += f"""
        <div class="legend" style="margin-top: 40px;">
            <h4>Model Weights</h4>
            <p>Form: {weights['form']*100:.0f}% | Class: {weights['class']*100:.0f}% | 
            Connections: {weights['connections']*100:.0f}% | Speed: {weights['speed']*100:.0f}% | 
            Conditions: {weights['conditions']*100:.0f}% | Fitness: {weights['fitness']*100:.0f}%</p>
        </div>
"""
    
    html += """
    </div>
</body>
</html>"""
    
    return html


# Example usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        json_path = sys.argv[1]
    else:
        # Default to June 13 file for testing
        json_path = "fair_meadows_june13_2025.json"
    
    if os.path.exists(json_path):
        # Create enhancer
        enhancer = FairMeadowsProbabilityEnhancer()
        
        # Enhance data
        enhanced_data = enhancer.enhance_race_data(json_path)
        
        # Save enhanced JSON
        enhanced_json_path = json_path.replace('.json', '_enhanced.json')
        with open(enhanced_json_path, 'w') as f:
            json.dump(enhanced_data, f, indent=2)
        
        print(f"✅ Created enhanced JSON: {enhanced_json_path}")
        
        # Generate HTML
        html_content = create_enhanced_html(enhanced_data)
        html_path = json_path.replace('.json', '_probability.html')
        
        with open(html_path, 'w') as f:
            f.write(html_content)
        
        print(f"📊 Created probability HTML: {html_path}")
        
        # Print summary
        print("\nProbability Summary:")
        for race_num, race in enhanced_data['races'].items():
            print(f"\nRace {race_num}:")
            sorted_horses = sorted(race['horses'], 
                                 key=lambda h: h.get('probability_rank', 999))
            for horse in sorted_horses[:3]:
                print(f"  {horse.get('probability_rank')}. #{horse['program_number']} "
                      f"{horse['horse_name']}: {horse.get('win_probability', '-')} "
                      f"({horse.get('projected_odds', '-')})")
    else:
        print(f"❌ File not found: {json_path}")