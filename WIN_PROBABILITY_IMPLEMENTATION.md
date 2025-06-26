# Win Probability Implementation for STALL10N

## Overview

This implementation mimics Equibase's STATS True Odds win probability system using available data from the StatPal API. While we don't have access to the same depth of historical data as Equibase, our system uses intelligent heuristics and available metrics to generate meaningful probability estimates.

## How Equibase's System Works

Equibase's STATS True Odds system:
- Uses proprietary machine learning algorithms
- Analyzes dozens of factors including speed figures, class ratings, pace figures
- Provides customizable factor weighting
- Generates win probabilities and projected odds
- Optimizes for ROI rather than just win frequency

## Our Implementation

### Core Components

1. **Win Probability Calculator** (`win_probability_system.py`)
   - Calculates probabilities using weighted factors
   - Supports customizable weights
   - Normalizes probabilities across the field

2. **Fair Meadows Enhancer** (`fair_meadows_probability_calculator.py`)
   - Integrates with existing JSON data structure
   - Adds probability calculations to race data
   - Generates enhanced HTML visualizations

### Factors Analyzed

Our system considers six main factor categories:

1. **Form (25% default weight)**
   - Win rate from available data
   - Place rate (in-the-money percentage)
   - Recent form score

2. **Class (20% default weight)**
   - Race class level
   - Quality of competition

3. **Connections (15% default weight)**
   - Jockey win rate
   - Trainer win rate
   - Jockey/trainer combination success

4. **Speed (20% default weight)**
   - Speed figure estimates
   - Pace ratings

5. **Conditions (10% default weight)**
   - Weight carried
   - Distance suitability
   - Surface preference

6. **Fitness (10% default weight)**
   - Current form indicators
   - Recent performance trends

### Data Sources and Limitations

**Available from StatPal:**
- Current day races only
- Basic horse information (name, jockey, trainer, weight)
- Limited form data
- Race conditions

**What we're missing (vs Equibase):**
- Detailed past performance data
- Actual speed figures
- Sectional times
- Track variants
- Complete historical database

### Intelligent Workarounds

To compensate for limited data, our system uses:

1. **Morning Line Analysis**
   - Converts ML odds to implied probabilities
   - Uses as proxy for expert assessment

2. **True Odds Integration**
   - Leverages existing "true_odds" calculations
   - Validates against ITM percentages

3. **Synthetic Ratings**
   - Generates estimated ratings from available data
   - Normalizes across field

4. **Pattern Recognition**
   - Identifies top connections by name
   - Applies class-based adjustments

## Usage

### Basic Usage

```python
from fair_meadows_probability_calculator import FairMeadowsProbabilityEnhancer

# Create enhancer with default weights
enhancer = FairMeadowsProbabilityEnhancer()

# Process race data
enhanced_data = enhancer.enhance_race_data('fair_meadows_june13_2025.json')
```

### Custom Weights

```python
# Emphasize form and speed over other factors
custom_weights = {
    'form': 0.30,      # 30% weight on form
    'speed': 0.25,     # 25% weight on speed
    'class': 0.20,     # 20% weight on class
    'connections': 0.15,
    'conditions': 0.05,
    'fitness': 0.05
}

enhancer = FairMeadowsProbabilityEnhancer(custom_weights)
```

### Integration with Pull Script

To automatically add probabilities when pulling data:

```python
# In pull_fair_meadows_data.py, after saving JSON:
from fair_meadows_probability_calculator import FairMeadowsProbabilityEnhancer

enhancer = FairMeadowsProbabilityEnhancer()
enhanced_data = enhancer.enhance_race_data(json_path)

# Save enhanced version
with open(json_path.replace('.json', '_enhanced.json'), 'w') as f:
    json.dump(enhanced_data, f, indent=2)
```

## Output Format

### Enhanced JSON Structure

```json
{
  "track": "Fair Meadows",
  "races": {
    "1": {
      "horses": [
        {
          "program_number": 1,
          "horse_name": "Thunder Strike",
          "win_probability": "15.5%",
          "projected_odds": "5/1",
          "probability_rank": 3,
          "probability_factors": {
            "form_score": 0.65,
            "speed_rating": 0.72,
            "class_rating": 0.60,
            "connections": 0.18
          }
        }
      ]
    }
  },
  "probability_analysis": {
    "generated_at": "2025-06-16 22:30:00",
    "method": "StatPal-based Win Probability Model",
    "weights": {
      "form": 0.25,
      "class": 0.20,
      "connections": 0.15,
      "speed": 0.20,
      "conditions": 0.10,
      "fitness": 0.10
    }
  }
}
```

### HTML Visualization

The enhanced HTML includes:
- Probability rankings (1 = most likely winner)
- Win percentage for each horse
- Projected odds based on probability
- Factor scores breakdown
- Visual highlighting of top 3 contenders

## Future Enhancements

### With Additional Data Sources

1. **Historical Database**
   - Build local database of past StatPal results
   - Calculate actual speed figures over time
   - Track jockey/trainer statistics

2. **Odds API Integration**
   - Real-time odds updates
   - Market efficiency analysis
   - Value identification

3. **Machine Learning**
   - Train models on accumulated data
   - Optimize factor weights automatically
   - Pattern recognition improvements

### Algorithm Improvements

1. **Pace Modeling**
   - Predict race shape
   - Early/late speed analysis
   - Position probability charts

2. **Track Bias Detection**
   - Surface preference analysis
   - Post position statistics
   - Weather impact factors

3. **Betting Strategy Integration**
   - Kelly Criterion calculations
   - Value bet identification
   - Multi-race sequence analysis

## Testing and Validation

To test the system:

```bash
# Process existing data
python3 fair_meadows_probability_calculator.py fair_meadows_june13_2025.json

# View results
open fair_meadows_june13_2025_probability.html
```

## Comparison with Equibase

| Feature | Equibase STATS True Odds | Our Implementation |
|---------|-------------------------|-------------------|
| Historical Data | 10+ years | Current day only |
| Speed Figures | Actual measurements | Estimated from ratings |
| ML Algorithm | Proprietary neural network | Weighted factor model |
| Customization | Slider interface | Code-based weights |
| Track Variants | Yes | No |
| ROI Optimization | Yes | Basic probability |
| Cost | Subscription required | Free with StatPal API |

## Conclusion

While our implementation cannot match Equibase's depth of data and sophisticated algorithms, it provides a solid foundation for probability-based handicapping using available StatPal data. The system is designed to be extensible, allowing for improvements as more data becomes available.

The key advantages of our approach:
- Transparent methodology
- Customizable weights
- Integration with existing STALL10N infrastructure
- No additional API costs
- Expandable architecture

As we accumulate historical data and refine the algorithms, the accuracy and utility of the system will continue to improve.