# Dynamic Weight Calculation Documentation

## Overview
The dynamic weight calculation system determines optimal portfolio allocations based on market conditions and trading pair characteristics. This document explains the algorithm, configuration options, and implementation details.

## Key Concepts

### Weight Calculation Factors
1. **Price Momentum**: Recent price performance
2. **Volume Trend**: Trading volume changes over time
3. **Volatility**: Price stability/instability
4. **Spread**: Bid-ask spread tightness
5. **Correlation**: Relationship between pairs

### Configuration Parameters
```yaml
dynamic_weights:
  max_pairs: 50          # Maximum number of pairs to include
  rebalance_interval: 86400  # Seconds between rebalances
  min_weight: 0.01       # Minimum weight per pair
  max_weight: 0.5        # Maximum weight per pair
  momentum_window: 14    # Days for momentum calculation
  volume_window: 7       # Days for volume analysis
  volatility_window: 30  # Days for volatility calculation
```

## Algorithm Steps

1. **Data Collection**
   - Gather historical price and volume data
   - Calculate technical indicators

2. **Pair Scoring**
   ```python
   def calculate_pair_score(data):
       momentum = calculate_momentum(data['close'])
       volume_score = calculate_volume_score(data['volume'])
       volatility = calculate_volatility(data['close'])
       spread = calculate_spread(data['high'], data['low'])
       return (momentum * 0.4 + 
               volume_score * 0.3 + 
               (1 - volatility) * 0.2 + 
               (1 - spread) * 0.1)
   ```

3. **Weight Normalization**
   - Scale scores to sum to 1
   - Apply min/max weight constraints
   - Ensure portfolio diversification

4. **Rebalance Logic**
   - Check if rebalance interval has passed
   - Calculate new weights
   - Generate trade orders to reach target weights

## Performance Considerations

### Time Complexity
- O(n) for data collection
- O(n log n) for sorting and normalization
- Total: O(n log n)

### Memory Usage
- Scales linearly with number of pairs
- Approximately 100MB for 100 pairs

## Testing Strategy

### Unit Tests
- Individual calculation components
- Edge cases and boundary conditions

### Integration Tests
- Full weight calculation flow
- Rebalance logic

### Performance Tests
- Large dataset handling
- Memory usage monitoring
- Execution time benchmarks

## Example Usage

```python
from crypto_j_trader.j_trading import PortfolioManager

config = {
    # ... configuration ...
}

pm = PortfolioManager(config)
weights = pm.calculate_dynamic_weights(market_data)
orders = pm.calculate_rebalance_orders(current_prices)
```

## Troubleshooting

### Common Issues
1. **Insufficient Data**
   - Ensure enough historical data is available
   - Minimum data points: max(momentum_window, volume_window, volatility_window)

2. **Weight Constraints Violation**
   - Verify min_weight and max_weight settings
   - Check for extreme market conditions

3. **Performance Degradation**
   - Monitor execution time
   - Consider reducing max_pairs if needed
