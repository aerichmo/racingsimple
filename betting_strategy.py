"""
Betting Strategy Calculator for STALL10N

This module calculates a betting strategy based on:
1. Adjusted Probability (adj_odds) - Model's prediction
2. Live Odds - Market's assessment
3. Expected Value calculation
4. Kelly Criterion for optimal bet sizing
"""

def parse_odds(odds_str):
    """Convert odds string (e.g., '5/2', '3/1') to decimal odds"""
    if not odds_str or odds_str == '-':
        return None
    
    try:
        if '/' in odds_str:
            num, den = odds_str.split('/')
            return float(num) / float(den) + 1  # Convert to decimal odds
        else:
            return float(odds_str)
    except:
        return None

def calculate_implied_probability(decimal_odds):
    """Convert decimal odds to implied probability"""
    if not decimal_odds:
        return None
    return 100 / decimal_odds

def calculate_expected_value(adj_probability, decimal_odds):
    """
    Calculate Expected Value (EV)
    EV = (Probability of Win × Amount Won) - (Probability of Loss × Amount Bet)
    
    For $1 bet:
    EV = (adj_prob × (decimal_odds - 1)) - ((100 - adj_prob) × 1)
    """
    if not adj_probability or not decimal_odds:
        return None
    
    adj_prob = adj_probability / 100  # Convert to decimal
    ev = (adj_prob * (decimal_odds - 1)) - ((1 - adj_prob) * 1)
    return ev * 100  # Return as percentage

def calculate_value_rating(adj_probability, live_odds_str):
    """
    Calculate value rating comparing model probability to market odds
    
    Value = (Model Probability - Market Implied Probability) / Market Implied Probability
    
    Positive value indicates overlay (good bet)
    Negative value indicates underlay (poor bet)
    """
    decimal_odds = parse_odds(live_odds_str)
    if not decimal_odds or not adj_probability:
        return None
    
    market_probability = calculate_implied_probability(decimal_odds)
    if not market_probability:
        return None
    
    value = ((adj_probability - market_probability) / market_probability) * 100
    return value

def calculate_kelly_percentage(adj_probability, decimal_odds):
    """
    Calculate Kelly Criterion percentage for optimal bet sizing
    
    Kelly % = (p × (b + 1) - 1) / b
    where:
    p = probability of winning (as decimal)
    b = net odds (decimal odds - 1)
    """
    if not adj_probability or not decimal_odds or decimal_odds <= 1:
        return None
    
    p = adj_probability / 100
    b = decimal_odds - 1
    
    kelly = ((p * (b + 1) - 1) / b) * 100
    
    # Cap at 25% for safety (quarter Kelly)
    return min(max(0, kelly), 25)

def determine_bet_type(score, adj_probability, kelly_pct):
    """
    Determine whether to bet Win, Place, or Show based on strategy score and probability
    
    Returns: Dictionary with bet type and reasoning
    """
    if score < 20:
        return {
            'type': 'NONE',
            'display': 'No Bet',
            'reason': 'Insufficient value'
        }
    
    # High probability + High score = WIN bet
    if score >= 60 and adj_probability >= 30:
        return {
            'type': 'WIN',
            'display': 'WIN',
            'reason': 'Strong value and probability'
        }
    
    # Medium-high score with moderate probability = WIN or PLACE
    elif score >= 50 and adj_probability >= 20:
        if adj_probability >= 25:
            return {
                'type': 'WIN',
                'display': 'WIN',
                'reason': 'Good value with decent probability'
            }
        else:
            return {
                'type': 'PLACE',
                'display': 'PLACE',
                'reason': 'Good value, moderate probability'
            }
    
    # Lower scores or probabilities = PLACE or SHOW
    elif score >= 40:
        if adj_probability >= 15:
            return {
                'type': 'PLACE',
                'display': 'PLACE',
                'reason': 'Fair value, safer bet'
            }
        else:
            return {
                'type': 'SHOW',
                'display': 'SHOW',
                'reason': 'Some value, conservative bet'
            }
    
    # Marginal bets = SHOW only
    elif score >= 20:
        return {
            'type': 'SHOW',
            'display': 'SHOW',
            'reason': 'Marginal value, safest option'
        }
    
    return {
        'type': 'NONE',
        'display': 'No Bet',
        'reason': 'Below threshold'
    }

def calculate_betting_strategy(adj_probability, live_odds_str, win_probability=None):
    """
    Main function to calculate comprehensive betting strategy
    
    Returns:
    - strategy_score: 0-100 score indicating bet strength
    - recommendation: Text recommendation
    - metrics: Dictionary of calculated metrics
    """
    
    decimal_odds = parse_odds(live_odds_str)
    if not decimal_odds or not adj_probability:
        return {
            'strategy_score': 0,
            'recommendation': 'SKIP - Insufficient data',
            'metrics': {}
        }
    
    # Calculate key metrics
    ev = calculate_expected_value(adj_probability, decimal_odds)
    value_rating = calculate_value_rating(adj_probability, live_odds_str)
    kelly_pct = calculate_kelly_percentage(adj_probability, decimal_odds)
    market_prob = calculate_implied_probability(decimal_odds)
    
    # Calculate strategy score (0-100)
    score = 0
    
    # Expected Value component (0-40 points)
    if ev and ev > 0:
        # Scale: 0% EV = 0 points, 20%+ EV = 40 points
        ev_score = min(40, (ev / 20) * 40)
        score += ev_score
    
    # Value Rating component (0-30 points)
    if value_rating and value_rating > 0:
        # Scale: 0% value = 0 points, 30%+ value = 30 points
        value_score = min(30, (value_rating / 30) * 30)
        score += value_score
    
    # Probability Edge component (0-30 points)
    if market_prob:
        prob_edge = adj_probability - market_prob
        if prob_edge > 0:
            # Scale: 0% edge = 0 points, 20%+ edge = 30 points
            edge_score = min(30, (prob_edge / 20) * 30)
            score += edge_score
    
    # Generate bet type recommendation based on score and probability
    bet_type = determine_bet_type(score, adj_probability, kelly_pct)
    
    # Generate recommendation
    if score >= 80:
        recommendation = f"STRONG BET"
    elif score >= 60:
        recommendation = f"GOOD BET"
    elif score >= 40:
        recommendation = f"FAIR BET"
    elif score >= 20:
        recommendation = "MARGINAL"
    else:
        recommendation = "SKIP"
    
    # Add Kelly percentage if applicable
    if kelly_pct and score >= 40:
        recommendation += f" - Kelly: {kelly_pct:.1f}%"
    
    return {
        'strategy_score': round(score, 1),
        'recommendation': recommendation,
        'bet_type': bet_type,
        'metrics': {
            'expected_value': round(ev, 2) if ev else None,
            'value_rating': round(value_rating, 1) if value_rating else None,
            'kelly_percentage': round(kelly_pct, 1) if kelly_pct else None,
            'market_probability': round(market_prob, 1) if market_prob else None,
            'probability_edge': round(adj_probability - market_prob, 1) if market_prob else None
        }
    }

# Example usage
if __name__ == "__main__":
    # Test cases
    test_cases = [
        {"adj_odds": 36.5, "live_odds": "9/5", "name": "Rr Crown This Dash"},
        {"adj_odds": 60.7, "live_odds": "4/5", "name": "Dm Heza Dan D"},
        {"adj_odds": 11.1, "live_odds": "6/1", "name": "B Playin for Keeps"},
        {"adj_odds": 2.9, "live_odds": "30/1", "name": "Pt Cowgirl"},
    ]
    
    print("Betting Strategy Analysis:")
    print("-" * 80)
    
    for test in test_cases:
        result = calculate_betting_strategy(test['adj_odds'], test['live_odds'])
        print(f"\nHorse: {test['name']}")
        print(f"Adjusted Probability: {test['adj_odds']}%")
        print(f"Live Odds: {test['live_odds']}")
        print(f"Strategy Score: {result['strategy_score']}/100")
        print(f"Recommendation: {result['recommendation']}")
        print(f"Bet Type: {result['bet_type']['display']} - {result['bet_type']['reason']}")
        print(f"Metrics: {result['metrics']}")