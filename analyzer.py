"""Horse Racing Analysis Engine"""
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

class RaceAnalyzer:
    """Analyze race entries and generate recommendations"""
    
    def analyze_entry(self, entry: Dict) -> Dict:
        """Analyze a single entry and return scores"""
        scores = {
            'speed_score': self._calculate_speed_score(entry),
            'class_score': self._calculate_class_score(entry),
            'jockey_score': self._calculate_jockey_score(entry),
            'trainer_score': self._calculate_trainer_score(entry)
        }
        
        # Calculate overall score (weighted average)
        overall = (
            scores['speed_score'] * 0.4 +
            scores['class_score'] * 0.3 +
            scores['jockey_score'] * 0.2 +
            scores['trainer_score'] * 0.1
        )
        # Cap at 99.9 to prevent DECIMAL(5,2) overflow (must be < 1000 after rounding)
        scores['overall_score'] = min(overall, 99.9)
        
        # Generate recommendation
        if scores['overall_score'] >= 80:
            scores['recommendation'] = 'STRONG PLAY'
            scores['confidence'] = 9
        elif scores['overall_score'] >= 70:
            scores['recommendation'] = 'PLAY'
            scores['confidence'] = 7
        elif scores['overall_score'] >= 60:
            scores['recommendation'] = 'CONSIDER'
            scores['confidence'] = 5
        else:
            scores['recommendation'] = 'PASS'
            scores['confidence'] = 3
        
        return scores
    
    def _calculate_speed_score(self, entry: Dict) -> float:
        """Calculate speed score based on speed figures"""
        score = 50.0  # Base score
        
        # Check if speed is improving
        last = entry.get('last_speed', 0) or 0
        avg = entry.get('avg_speed', 0) or 0
        best = entry.get('best_speed', 0) or 0
        
        if last > 0 and avg > 0:
            # Improvement over average
            if last > avg:
                improvement = min((last - avg) / avg * 100, 30)
                score += improvement
            
            # Close to best
            if best > 0 and last > 0:
                if last >= best * 0.95:  # Within 5% of best
                    score += 20
                elif last >= best * 0.90:  # Within 10% of best
                    score += 10
        
        # Raw speed bonus
        if last >= 70:
            score += 10
        elif last >= 60:
            score += 5
        
        return min(score, 99.9)
    
    def _calculate_class_score(self, entry: Dict) -> float:
        """Calculate class rating score"""
        score = 50.0
        
        class_rating = entry.get('class_rating', 0) or 0
        
        # Higher class rating = better
        if class_rating >= 60:
            score += 30
        elif class_rating >= 50:
            score += 20
        elif class_rating >= 40:
            score += 10
        
        # Win percentage factor
        win_pct = entry.get('win_pct', 0) or 0
        if win_pct >= 20:
            score += 20
        elif win_pct >= 15:
            score += 15
        elif win_pct >= 10:
            score += 10
        elif win_pct >= 5:
            score += 5
        
        return min(score, 99.9)
    
    def _calculate_jockey_score(self, entry: Dict) -> float:
        """Calculate jockey performance score"""
        score = 50.0
        
        jockey_win = entry.get('jockey_win_pct', 0) or 0
        
        if jockey_win >= 20:
            score += 40
        elif jockey_win >= 15:
            score += 30
        elif jockey_win >= 10:
            score += 20
        elif jockey_win >= 5:
            score += 10
        
        # J/T combo bonus
        jt_combo = entry.get('jt_combo_pct', 0) or 0
        if jt_combo >= 30:
            score += 10
        elif jt_combo >= 20:
            score += 5
        
        return min(score, 99.9)
    
    def _calculate_trainer_score(self, entry: Dict) -> float:
        """Calculate trainer performance score"""
        score = 50.0
        
        trainer_win = entry.get('trainer_win_pct', 0) or 0
        
        if trainer_win >= 20:
            score += 40
        elif trainer_win >= 15:
            score += 30
        elif trainer_win >= 10:
            score += 20
        elif trainer_win >= 5:
            score += 10
        
        # Trainer specialty bonus (could be enhanced with more data)
        if entry.get('race_type') == 'MAIDEN' and trainer_win >= 15:
            score += 10  # Good with first-time winners
        
        return min(score, 99.9)
    
    def find_value_plays(self, entries: List[Dict]) -> List[Dict]:
        """Find potential value plays based on win% vs expected odds"""
        value_plays = []
        
        for entry in entries:
            win_pct = entry.get('win_pct', 0)
            if win_pct > 0:
                # Calculate fair odds
                fair_odds = (100 / win_pct) - 1
                
                # If win% suggests better than 5-1 odds, it might be value
                if fair_odds <= 5 and entry.get('overall_score', 0) >= 65:
                    entry['fair_odds'] = f"{fair_odds:.1f}-1"
                    entry['value_flag'] = True
                    value_plays.append(entry)
        
        return value_plays