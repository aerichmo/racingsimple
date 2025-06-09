"""Sophisticated betting analysis for horse racing"""
import logging
from typing import List, Dict, Tuple, Optional
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)

class BettingAnalyzer:
    """Analyze races and recommend bets based on probability and value"""
    
    def __init__(self):
        # Kelly Criterion fraction for bankroll management
        self.kelly_fraction = 0.25  # Conservative 1/4 Kelly
        
        # Minimum edge required for betting
        self.min_edge = 0.10  # 10% minimum edge
        
        # Maximum bet size as percentage of bankroll
        self.max_bet_pct = 0.05  # 5% max per bet
    
    def analyze_races(self, races: List[Dict], bankroll: float = 1000) -> Dict:
        """Analyze all races and generate betting recommendations"""
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'bankroll': bankroll,
            'races': [],
            'summary': {
                'total_bets': 0,
                'total_stake': 0,
                'expected_value': 0,
                'expected_roi': 0,
                'risk_score': 0
            }
        }
        
        for race in races:
            race_analysis = self._analyze_single_race(race, bankroll)
            if race_analysis['recommended_bets']:
                analysis['races'].append(race_analysis)
                
                # Update summary
                for bet in race_analysis['recommended_bets']:
                    analysis['summary']['total_bets'] += 1
                    analysis['summary']['total_stake'] += bet['stake']
                    analysis['summary']['expected_value'] += bet['expected_value']
        
        # Calculate overall metrics
        if analysis['summary']['total_stake'] > 0:
            analysis['summary']['expected_roi'] = (
                analysis['summary']['expected_value'] / analysis['summary']['total_stake'] - 1
            ) * 100
            
            # Risk score (0-100, higher is riskier)
            analysis['summary']['risk_score'] = self._calculate_risk_score(analysis['races'])
        
        return analysis
    
    def _analyze_single_race(self, race: Dict, bankroll: float) -> Dict:
        """Analyze a single race for betting opportunities"""
        race_analysis = {
            'race_number': race.get('race_number', 'Unknown'),
            'post_time': race.get('post_time', ''),
            'entries': [],
            'recommended_bets': [],
            'race_metrics': {}
        }
        
        # Convert odds and calculate implied probabilities
        entries_data = []
        for entry in race.get('entries', []):
            entry_data = self._process_entry(entry)
            if entry_data:
                entries_data.append(entry_data)
                race_analysis['entries'].append(entry_data)
        
        if not entries_data:
            return race_analysis
        
        # Calculate race metrics
        race_analysis['race_metrics'] = self._calculate_race_metrics(entries_data)
        
        # Find value bets
        value_bets = self._find_value_bets(entries_data, bankroll)
        
        # Apply sophisticated filters
        filtered_bets = self._apply_bet_filters(value_bets, race_analysis['race_metrics'])
        
        # Calculate optimal stakes
        for bet in filtered_bets:
            bet['stake'] = self._calculate_optimal_stake(bet, bankroll)
            bet['expected_value'] = bet['stake'] * (bet['edge'] + 1)
        
        race_analysis['recommended_bets'] = filtered_bets
        
        return race_analysis
    
    def _process_entry(self, entry: Dict) -> Optional[Dict]:
        """Process entry data and calculate key metrics"""
        try:
            # Get win probability
            win_prob = entry.get('win_probability', 0) / 100.0
            
            # Convert ML odds to decimal
            ml_odds = entry.get('ml_odds', 'N/A')
            if ml_odds == 'N/A' or not isinstance(ml_odds, str):
                return None
            
            decimal_odds = self._ml_to_decimal(ml_odds)
            if not decimal_odds:
                return None
            
            # Calculate implied probability from odds
            implied_prob = 1.0 / decimal_odds
            
            # Calculate edge (model probability - implied probability)
            edge = win_prob - implied_prob
            
            # Calculate expected value
            ev = (win_prob * decimal_odds) - 1
            
            return {
                'program_number': entry.get('program_number'),
                'horse_name': entry.get('horse_name'),
                'win_probability': win_prob,
                'ml_odds': ml_odds,
                'decimal_odds': decimal_odds,
                'implied_probability': implied_prob,
                'edge': edge,
                'expected_value': ev,
                'angles_matched': entry.get('angles_matched', 0),
                'value_rating': self._calculate_value_rating(edge, win_prob, implied_prob)
            }
            
        except Exception as e:
            logger.error(f"Error processing entry: {e}")
            return None
    
    def _ml_to_decimal(self, ml_odds: str) -> Optional[float]:
        """Convert morning line odds to decimal format"""
        try:
            if '/' in ml_odds:
                num, den = ml_odds.split('/')
                return 1 + (float(num) / float(den))
            else:
                # Handle single number odds (e.g., "5" means 5/1)
                return 1 + float(ml_odds)
        except:
            return None
    
    def _calculate_value_rating(self, edge: float, win_prob: float, implied_prob: float) -> float:
        """Calculate a sophisticated value rating for the bet"""
        # Base value from edge
        value = edge * 100
        
        # Bonus for high probability winners with edge
        if win_prob > 0.3 and edge > 0:
            value += 10
        
        # Bonus for significant probability discrepancy
        prob_diff = abs(win_prob - implied_prob)
        if prob_diff > 0.15:
            value += prob_diff * 50
        
        # Penalty for very low probability
        if win_prob < 0.05:
            value -= 20
        
        return max(0, value)
    
    def _calculate_race_metrics(self, entries: List[Dict]) -> Dict:
        """Calculate overall race metrics"""
        win_probs = [e['win_probability'] for e in entries]
        edges = [e['edge'] for e in entries]
        
        return {
            'total_probability': sum(win_probs),
            'favorite_probability': max(win_probs),
            'avg_edge': np.mean(edges),
            'max_edge': max(edges),
            'positive_edges': sum(1 for e in edges if e > 0),
            'field_size': len(entries),
            'competitiveness': 1 - np.std(win_probs)  # Higher = more competitive
        }
    
    def _find_value_bets(self, entries: List[Dict], bankroll: float) -> List[Dict]:
        """Find bets with positive expected value"""
        value_bets = []
        
        for entry in entries:
            if entry['edge'] >= self.min_edge:
                value_bets.append({
                    'type': 'win',
                    'program_number': entry['program_number'],
                    'horse_name': entry['horse_name'],
                    'win_probability': entry['win_probability'],
                    'decimal_odds': entry['decimal_odds'],
                    'ml_odds': entry['ml_odds'],
                    'edge': entry['edge'],
                    'value_rating': entry['value_rating'],
                    'angles_matched': entry['angles_matched']
                })
        
        # Sort by value rating
        value_bets.sort(key=lambda x: x['value_rating'], reverse=True)
        
        return value_bets
    
    def _apply_bet_filters(self, bets: List[Dict], race_metrics: Dict) -> List[Dict]:
        """Apply sophisticated filters to select best bets"""
        filtered = []
        
        for bet in bets:
            # Filter 1: Minimum value rating
            if bet['value_rating'] < 15:
                continue
            
            # Filter 2: Avoid heavy favorites with small edges
            if bet['win_probability'] > 0.5 and bet['edge'] < 0.15:
                continue
            
            # Filter 3: Require higher edge in competitive races
            if race_metrics['competitiveness'] > 0.8 and bet['edge'] < 0.15:
                continue
            
            # Filter 4: Bonus for angles matched
            if bet['angles_matched'] > 0:
                bet['value_rating'] *= (1 + 0.1 * bet['angles_matched'])
            
            filtered.append(bet)
        
        # Limit to top 2 bets per race
        return filtered[:2]
    
    def _calculate_optimal_stake(self, bet: Dict, bankroll: float) -> float:
        """Calculate optimal stake using Kelly Criterion with safety adjustments"""
        # Kelly formula: f = (bp - q) / b
        # where f = fraction to bet, b = decimal odds - 1, p = win prob, q = 1 - p
        b = bet['decimal_odds'] - 1
        p = bet['win_probability']
        q = 1 - p
        
        kelly_full = (b * p - q) / b
        
        # Apply fractional Kelly for safety
        kelly_stake = kelly_full * self.kelly_fraction * bankroll
        
        # Apply maximum bet constraint
        max_stake = bankroll * self.max_bet_pct
        
        # Round to nearest dollar
        stake = min(kelly_stake, max_stake)
        return round(stake, 2)
    
    def _calculate_risk_score(self, races: List[Dict]) -> float:
        """Calculate overall risk score for all bets"""
        if not races:
            return 0
        
        risk_factors = []
        
        for race in races:
            for bet in race['recommended_bets']:
                # Risk based on probability
                prob_risk = 1 - bet['win_probability']
                
                # Risk based on stake size
                stake_risk = bet['stake'] / 1000  # Normalized by $1000
                
                # Combined risk
                bet_risk = (prob_risk * 0.7 + stake_risk * 0.3) * 100
                risk_factors.append(bet_risk)
        
        return np.mean(risk_factors) if risk_factors else 0