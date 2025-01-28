"""Test data fixtures for integration testing"""
from typing import Dict, List
import pandas as pd
from datetime import datetime, timedelta

def generate_market_data(pair: str, periods: int = 100) -> pd.DataFrame:
    """Generate synthetic market data for testing
    
    Args:
        pair: Trading pair identifier (e.g., 'BTC-USD')
        periods: Number of periods to generate
        
    Returns:
        DataFrame with OHLCV data
    """
    now = datetime.now()
    dates = [now - timedelta(minutes=5*i) for i in range(periods)]
    
    # Generate synthetic price data with some volatility
    if pair == 'BTC-USD':
        base_price = 45000
        volatility = 1000
    elif pair == 'ETH-USD':
        base_price = 2500
        volatility = 100
    else:
        base_price = 100
        volatility = 10
        
    import numpy as np
    np.random.seed(42)  # For reproducibility
    
    # Generate prices with random walk
    prices = np.random.normal(0, 1, periods).cumsum() * volatility + base_price
    
    data = {
        'timestamp': dates,
        'open': prices + np.random.normal(0, volatility*0.01, periods),
        'high': prices + np.random.normal(volatility*0.02, volatility*0.01, periods),
        'low': prices - np.random.normal(volatility*0.02, volatility*0.01, periods),
        'close': prices + np.random.normal(0, volatility*0.01, periods),
        'volume': np.random.gamma(2, 1000, periods)
    }
    
    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)
    return df

def generate_portfolio_state() -> Dict:
    """Generate initial portfolio state for testing
    
    Returns:
        Dictionary containing portfolio positions and balances
    """
    return {
        'positions': {
            'BTC-USD': {
                'quantity': 0.1,
                'entry_price': 45000,
                'current_price': 45100,
                'last_update': datetime.now().isoformat()
            },
            'ETH-USD': {
                'quantity': 1.5,
                'entry_price': 2500,
                'current_price': 2520,
                'last_update': datetime.now().isoformat()
            }
        },
        'balances': {
            'USD': 25000,
            'BTC': 0.1,
            'ETH': 1.5
        }
    }

def generate_trade_history() -> List[Dict]:
    """Generate trade history for testing
    
    Returns:
        List of trade records
    """
    base_time = datetime.now()
    return [
        {
            'pair': 'BTC-USD',
            'side': 'buy',
            'price': 44800,
            'quantity': 0.1,
            'timestamp': (base_time - timedelta(hours=24)).isoformat(),
            'fee': 2.24,
            'strategy_signals': {
                'rsi': 32,
                'macd': 'positive',
                'volume': 'high'
            }
        },
        {
            'pair': 'ETH-USD',
            'side': 'buy',
            'price': 2480,
            'quantity': 1.5,
            'timestamp': (base_time - timedelta(hours=12)).isoformat(),
            'fee': 1.86,
            'strategy_signals': {
                'rsi': 35,
                'macd': 'positive',
                'volume': 'normal'
            }
        }
    ]

def generate_risk_metrics() -> Dict:
    """Generate risk management metrics for testing
    
    Returns:
        Dictionary containing risk metrics
    """
    return {
        'portfolio_volatility': 0.15,
        'max_drawdown': 0.08,
        'daily_var': 0.02,
        'position_limits': {
            'BTC-USD': 0.25,
            'ETH-USD': 0.20
        },
        'correlation_matrix': {
            'BTC-USD': {'BTC-USD': 1.0, 'ETH-USD': 0.75},
            'ETH-USD': {'BTC-USD': 0.75, 'ETH-USD': 1.0}
        },
        'risk_scores': {
            'BTC-USD': 0.65,
            'ETH-USD': 0.58
        }
    }

def generate_websocket_messages(pair: str, count: int = 10) -> List[Dict]:
    """Generate WebSocket market data messages for testing
    
    Args:
        pair: Trading pair identifier
        count: Number of messages to generate
        
    Returns:
        List of WebSocket message dictionaries
    """
    messages = []
    now = datetime.now()
    
    if pair == 'BTC-USD':
        base_price = 45000
        tick_size = 1
    else:  # ETH-USD
        base_price = 2500
        tick_size = 0.1
        
    for i in range(count):
        price = base_price + (i - count//2) * tick_size
        messages.append({
            'type': 'ticker',
            'product_id': pair,
            'price': str(price),
            'time': (now + timedelta(seconds=i)).isoformat(),
            'volume_24h': str(1000 + i),
            'side': 'buy' if i % 2 == 0 else 'sell'
        })
        
    return messages