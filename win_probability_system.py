#!/usr/bin/env python3
"""
Win Probability System for Horse Racing
Mimics Equibase's STATS True Odds functionality using StatPal data
"""
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import json
import logging
from datetime import datetime
from statpal_service import StatPalService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class HorseMetrics:
    """Stores calculated metrics for a horse"""
    horse_id: str
    horse_name: str
    program_number: int
    
    # Form metrics
    win_rate: float = 0.0
    place_rate: float = 0.0
    recent_form_score: float = 0.0
    
    # Performance metrics
    speed_figure: float = 0.0
    class_rating: float = 0.0
    pace_rating: float = 0.0
    
    # Connections
    jockey_win_rate: float = 0.0
    trainer_win_rate: float = 0.0
    jockey_trainer_combo: float = 0.0
    
    # Current race factors
    weight_factor: float = 1.0
    distance_suitability: float = 1.0
    surface_preference: float = 1.0
    
    # Calculated probabilities
    raw_probability: float = 0.0
    adjusted_probability: float = 0.0
    final_odds: str = ""


class WinProbabilityCalculator:
    """
    Calculates win probabilities using available StatPal data
    Implements a simplified version of Equibase's methodology
    """
    
    # Default factor weights (adjustable)
    DEFAULT_WEIGHTS = {
        'form': 0.25,           # Recent performance
        'class': 0.20,          # Class/quality of competition
        'connections': 0.15,    # Jockey/trainer success
        'speed': 0.20,          # Speed/pace ratings
        'conditions': 0.10,     # Track/distance/surface
        'fitness': 0.10         # Current fitness indicators
    }
    
    def __init__(self, custom_weights: Optional[Dict[str, float]] = None):
        """Initialize calculator with optional custom weights"""
        self.weights = custom_weights or self.DEFAULT_WEIGHTS.copy()
        self._normalize_weights()
        
    def _normalize_weights(self):
        """Ensure weights sum to 1.0"""
        total = sum(self.weights.values())
        if total > 0:
            for key in self.weights:
                self.weights[key] /= total
    
    def calculate_probabilities(self, race_data: Dict) -> List[HorseMetrics]:
        """
        Calculate win probabilities for all horses in a race
        
        Args:
            race_data: Dictionary containing race and horse information
            
        Returns:
            List of HorseMetrics with calculated probabilities
        """
        horses = []
        
        # Extract horses from race data
        for horse_entry in race_data.get('horses', []):
            metrics = self._analyze_horse(horse_entry, race_data)
            horses.append(metrics)
        
        # Calculate raw probabilities
        horses = self._calculate_raw_probabilities(horses)
        
        # Adjust for field size and normalize
        horses = self._adjust_probabilities(horses)
        
        # Sort by probability
        horses.sort(key=lambda x: x.adjusted_probability, reverse=True)
        
        return horses
    
    def _analyze_horse(self, horse_data: Dict, race_data: Dict) -> HorseMetrics:
        """Analyze individual horse and create metrics"""
        metrics = HorseMetrics(
            horse_id=horse_data.get('id', ''),
            horse_name=horse_data.get('name', 'Unknown'),
            program_number=int(horse_data.get('number', 0))
        )
        
        # Extract form data if available
        form = horse_data.get('form', {})
        
        # Calculate form metrics
        metrics.win_rate = self._calculate_win_rate(form)
        metrics.place_rate = self._calculate_place_rate(form)
        metrics.recent_form_score = self._calculate_recent_form(horse_data)
        
        # Calculate performance metrics (simplified without full history)
        metrics.speed_figure = self._estimate_speed_figure(horse_data, race_data)
        metrics.class_rating = self._estimate_class_rating(race_data)
        metrics.pace_rating = self._estimate_pace_rating(horse_data)
        
        # Connection statistics (would need historical data)
        metrics.jockey_win_rate = self._estimate_connection_strength(horse_data.get('jockey', ''))
        metrics.trainer_win_rate = self._estimate_connection_strength(horse_data.get('trainer', ''))
        
        # Current conditions
        metrics.weight_factor = self._calculate_weight_factor(horse_data)
        metrics.distance_suitability = self._estimate_distance_suitability(horse_data, race_data)
        
        return metrics
    
    def _calculate_win_rate(self, form: Dict) -> float:
        """Calculate win rate from form data"""
        # Look for career or recent form statistics
        for section_name, section_data in form.items():
            if isinstance(section_data, dict):
                for stat_name, stat_data in section_data.items():
                    if isinstance(stat_data, dict) and 'win_pct' in stat_data:
                        try:
                            return float(stat_data['win_pct'].strip('%')) / 100.0
                        except:
                            pass
        return 0.15  # Default if no data
    
    def _calculate_place_rate(self, form: Dict) -> float:
        """Calculate in-the-money rate from form data"""
        for section_name, section_data in form.items():
            if isinstance(section_data, dict):
                for stat_name, stat_data in section_data.items():
                    if isinstance(stat_data, dict):
                        try:
                            wins = int(stat_data.get('wins', 0))
                            places = int(stat_data.get('places', 0))
                            runs = int(stat_data.get('runs', 1))
                            if runs > 0:
                                return (wins + places) / runs
                        except:
                            pass
        return 0.33  # Default if no data
    
    def _calculate_recent_form(self, horse_data: Dict) -> float:
        """Calculate recent form score (0-1)"""
        # Without detailed past performances, use basic heuristics
        rating = horse_data.get('rating', '')
        if rating:
            try:
                # Normalize rating to 0-1 scale (assuming 0-120 range)
                return min(float(rating) / 120.0, 1.0)
            except:
                pass
        return 0.5  # Neutral if no data
    
    def _estimate_speed_figure(self, horse_data: Dict, race_data: Dict) -> float:
        """Estimate speed figure (normalized 0-1)"""
        # Without past performance data, use rating as proxy
        rating = horse_data.get('rating', '')
        if rating:
            try:
                # Convert to speed figure estimate (70-110 range typical)
                speed_fig = 70 + (float(rating) / 120.0) * 40
                # Normalize to 0-1
                return (speed_fig - 70) / 40
            except:
                pass
        return 0.5
    
    def _estimate_class_rating(self, race_data: Dict) -> float:
        """Estimate class level of race"""
        race_class = race_data.get('race_info', {}).get('class', '').lower()
        
        # Simple class hierarchy
        class_levels = {
            'group 1': 1.0,
            'group 2': 0.9,
            'group 3': 0.8,
            'listed': 0.7,
            'handicap': 0.6,
            'maiden': 0.4,
            'claiming': 0.3,
            'seller': 0.2
        }
        
        for class_name, level in class_levels.items():
            if class_name in race_class:
                return level
        
        return 0.5  # Default middle class
    
    def _estimate_pace_rating(self, horse_data: Dict) -> float:
        """Estimate pace/early speed rating"""
        # Without sectional times, use stall position as weak proxy
        stall = horse_data.get('stall', '')
        if stall:
            try:
                # Lower stalls often correlate with speed
                stall_num = int(stall)
                return 1.0 - (stall_num / 20.0)  # Normalize assuming max 20 stalls
            except:
                pass
        return 0.5
    
    def _estimate_connection_strength(self, name: str) -> float:
        """Estimate jockey/trainer strength (would need historical DB)"""
        # Without historical data, use name recognition heuristic
        # In production, this would query a database
        top_connections = ['moore', 'dettori', 'doyle', 'buick', 'murphy']
        if any(top in name.lower() for top in top_connections):
            return 0.25
        return 0.15  # Average
    
    def _calculate_weight_factor(self, horse_data: Dict) -> float:
        """Calculate weight impact factor"""
        weight = horse_data.get('weight', '')
        if weight:
            try:
                # Parse weight (format: "9-7" means 9 stone 7 pounds)
                if '-' in str(weight):
                    stone, pounds = str(weight).split('-')
                    total_pounds = int(stone) * 14 + int(pounds)
                    # Normalize around typical weight (126 lbs)
                    return 1.0 - abs(total_pounds - 126) / 50.0
            except:
                pass
        return 1.0
    
    def _estimate_distance_suitability(self, horse_data: Dict, race_data: Dict) -> float:
        """Estimate how suitable the distance is for horse"""
        # Without past distance performances, return neutral
        return 0.75
    
    def _calculate_raw_probabilities(self, horses: List[HorseMetrics]) -> List[HorseMetrics]:
        """Calculate raw win probabilities using weighted factors"""
        
        for horse in horses:
            # Calculate component scores
            form_score = (
                horse.win_rate * 0.4 +
                horse.place_rate * 0.3 +
                horse.recent_form_score * 0.3
            )
            
            class_score = horse.class_rating
            
            connections_score = (
                horse.jockey_win_rate * 0.5 +
                horse.trainer_win_rate * 0.5
            )
            
            speed_score = (
                horse.speed_figure * 0.7 +
                horse.pace_rating * 0.3
            )
            
            conditions_score = (
                horse.weight_factor * 0.5 +
                horse.distance_suitability * 0.5
            )
            
            fitness_score = horse.recent_form_score  # Simplified
            
            # Calculate weighted total
            horse.raw_probability = (
                form_score * self.weights['form'] +
                class_score * self.weights['class'] +
                connections_score * self.weights['connections'] +
                speed_score * self.weights['speed'] +
                conditions_score * self.weights['conditions'] +
                fitness_score * self.weights['fitness']
            )
        
        return horses
    
    def _adjust_probabilities(self, horses: List[HorseMetrics]) -> List[HorseMetrics]:
        """Adjust and normalize probabilities"""
        if not horses:
            return horses
        
        # Get total of raw probabilities
        total_prob = sum(h.raw_probability for h in horses)
        
        if total_prob > 0:
            # Normalize to sum to 1.0
            for horse in horses:
                horse.adjusted_probability = horse.raw_probability / total_prob
                
                # Convert to odds format
                if horse.adjusted_probability > 0:
                    decimal_odds = 1 / horse.adjusted_probability
                    horse.final_odds = self._format_odds(decimal_odds)
                else:
                    horse.final_odds = "99/1"
        
        return horses
    
    def _format_odds(self, decimal_odds: float) -> str:
        """Convert decimal odds to fractional format"""
        if decimal_odds < 1.5:
            return "1/2"
        elif decimal_odds < 1.8:
            return "4/5"
        elif decimal_odds < 2.2:
            return "1/1"
        elif decimal_odds < 2.75:
            return "6/4"
        elif decimal_odds < 3.5:
            return "2/1"
        elif decimal_odds < 4.5:
            return "3/1"
        elif decimal_odds < 5.5:
            return "4/1"
        elif decimal_odds < 6.5:
            return "5/1"
        elif decimal_odds < 7.5:
            return "6/1"
        elif decimal_odds < 8.5:
            return "7/1"
        elif decimal_odds < 9.5:
            return "8/1"
        elif decimal_odds < 10.5:
            return "9/1"
        elif decimal_odds < 12:
            return "10/1"
        elif decimal_odds < 15:
            return "12/1"
        elif decimal_odds < 20:
            return "16/1"
        elif decimal_odds < 30:
            return "25/1"
        elif decimal_odds < 40:
            return "33/1"
        elif decimal_odds < 60:
            return "50/1"
        else:
            return "99/1"


def generate_probability_report(horses: List[HorseMetrics], race_info: Dict) -> str:
    """Generate a formatted probability report"""
    report = f"""
WIN PROBABILITY ANALYSIS
========================
Race: {race_info.get('name', 'Unknown')}
Venue: {race_info.get('venue', 'Unknown')}
Distance: {race_info.get('distance', 'Unknown')}
Going: {race_info.get('going', 'Unknown')}

PROBABILITIES & PROJECTED ODDS
==============================
"""
    
    for i, horse in enumerate(horses, 1):
        report += f"""
{i}. #{horse.program_number} {horse.horse_name}
   Win Probability: {horse.adjusted_probability * 100:.1f}%
   Projected Odds: {horse.final_odds}
   Form Score: {horse.recent_form_score:.2f}
   Speed Rating: {horse.speed_figure:.2f}
   Class Rating: {horse.class_rating:.2f}
"""
    
    return report


# Example usage
if __name__ == "__main__":
    # Initialize calculator
    calculator = WinProbabilityCalculator()
    
    # Create sample race data (would come from StatPal API)
    sample_race = {
        'race_info': {
            'name': 'Race 5',
            'venue': 'Prairie Meadows',
            'distance': '6f',
            'going': 'Fast',
            'class': 'Allowance'
        },
        'horses': [
            {
                'id': '1',
                'name': 'Thunder Strike',
                'number': '1',
                'jockey': 'J. Smith',
                'trainer': 'B. Jones',
                'weight': '9-0',
                'rating': '85',
                'form': {
                    'career': {
                        'all': {
                            'runs': '12',
                            'wins': '3',
                            'places': '4',
                            'win_pct': '25%'
                        }
                    }
                }
            },
            {
                'id': '2',
                'name': 'Lightning Bolt',
                'number': '2',
                'jockey': 'R. Moore',
                'trainer': 'C. Brown',
                'weight': '9-2',
                'rating': '90',
                'form': {
                    'career': {
                        'all': {
                            'runs': '8',
                            'wins': '4',
                            'places': '2',
                            'win_pct': '50%'
                        }
                    }
                }
            }
        ]
    }
    
    # Calculate probabilities
    results = calculator.calculate_probabilities(sample_race)
    
    # Generate report
    report = generate_probability_report(results, sample_race['race_info'])
    print(report)