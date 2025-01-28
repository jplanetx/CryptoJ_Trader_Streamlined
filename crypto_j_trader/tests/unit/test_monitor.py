import pytest
import numpy as np
from datetime import datetime, timedelta
from crypto_j_trader.src.utils.monitoring import TradingMonitor

@pytest.fixture
def config():
    return {
        'risk_management': {
            'daily_loss_limit': 0.02,
            'position_size_limit': 0.1
        }
    }

@pytest.fixture
def monitor(config):
    return TradingMonitor(config)

def test_trade_metrics_update():
    monitor = TradingMonitor({'risk_management': {}})
    
    # Test single winning trade
    trade = {
        'entry_price': 100,
        'exit_price': 110,
        'size': 1,
        'timestamp': datetime.now(),
        'duration': 300  # seconds
    }
    monitor.update_trade_metrics(trade)
    
    assert len(monitor.performance_metrics['trades']) == 1
    assert monitor.performance_metrics['win_rate'] == 1.0
    assert monitor.performance_metrics['returns'][0] == 0.1  # 10% return
    
    # Add losing trade
    trade = {
        'entry_price': 100,
        'exit_price': 95,
        'size': 1,
        'timestamp': datetime.now(),
        'duration': 300
    }
    monitor.update_trade_metrics(trade)
    
    assert len(monitor.performance_metrics['trades']) == 2
    assert monitor.performance_metrics['win_rate'] == 0.5
    assert len(monitor.performance_metrics['drawdowns']) == 2

def test_risk_metrics_update():
    monitor = TradingMonitor({'risk_management': {}})
    
    # Test portfolio with multiple positions
    portfolio = {
        'positions': [
            {'asset': 'BTC', 'value': 1000},
            {'asset': 'ETH', 'value': 500},
            {'asset': 'SOL', 'value': 300}
        ]
    }
    
    monitor.update_risk_metrics(portfolio)
    
    assert 0 <= monitor.risk_metrics['position_correlation'] <= 1
    assert monitor.risk_metrics['max_position_size'] == pytest.approx(0.5555, rel=1e-3)  # 1000/(1000+500+300)

def test_technical_metrics_update():
    monitor = TradingMonitor({'risk_management': {}})
    
    # Test websocket status update
    event = {
        'type': 'websocket_status',
        'downtime': 30  # seconds
    }
    monitor.start_time = datetime.now() - timedelta(hours=1)
    monitor.update_technical_metrics(event)
    
    # 30 seconds downtime in 1 hour = 99.17% uptime
    assert 99.0 <= monitor.technical_metrics['websocket_uptime'] <= 99.2
    
    # Test order latency
    event = {
        'type': 'order_latency',
        'latency': 150  # milliseconds
    }
    monitor.update_technical_metrics(event)
    assert monitor.technical_metrics['order_latencies'] == [150]
    
    # Test error counting
    event = {'type': 'error'}
    monitor.update_technical_metrics(event)
    assert monitor.technical_metrics['error_count'] == 1

def test_validation_status():
    monitor = TradingMonitor({'risk_management': {}})
    
    # Add some successful trades
    for _ in range(10):
        trade = {
            'entry_price': 100,
            'exit_price': 110,
            'size': 1,
            'timestamp': datetime.now(),
            'duration': 300
        }
        monitor.update_trade_metrics(trade)
    
    # Update risk metrics
    portfolio = {
        'positions': [
            {'asset': 'BTC', 'value': 1000},
            {'asset': 'ETH', 'value': 500}
        ]
    }
    monitor.update_risk_metrics(portfolio)
    
    # Update technical metrics
    event = {
        'type': 'websocket_status',
        'downtime': 10
    }
    monitor.start_time = datetime.now() - timedelta(days=1)
    monitor.update_technical_metrics(event)
    
    validation = monitor.get_validation_status()
    
    assert isinstance(validation['passed_all'], bool)
    assert 'metrics' in validation
    assert validation['trade_count'] == 10
    assert validation['monitoring_days'] >= 0

def test_report_generation():
    monitor = TradingMonitor({'risk_management': {}})
    
    # Add some test data
    trade = {
        'entry_price': 100,
        'exit_price': 110,
        'size': 1,
        'timestamp': datetime.now(),
        'duration': 300
    }
    monitor.update_trade_metrics(trade)
    
    portfolio = {
        'positions': [
            {'asset': 'BTC', 'value': 1000},
            {'asset': 'ETH', 'value': 500}
        ]
    }
    monitor.update_risk_metrics(portfolio)
    
    report = monitor.generate_report()
    
    assert isinstance(report, str)
    assert "Trading System Monitoring Report" in report
    assert "Validation Status:" in report
    assert "Detailed Metrics:" in report

def test_edge_cases():
    monitor = TradingMonitor({'risk_management': {}})
    
    # Test empty portfolio
    portfolio = {'positions': []}
    monitor.update_risk_metrics(portfolio)
    assert monitor.risk_metrics['max_position_size'] == 0
    
    # Test single trade drawdown
    trade = {
        'entry_price': 100,
        'exit_price': 90,
        'size': 1,
        'timestamp': datetime.now(),
        'duration': 300
    }
    monitor.update_trade_metrics(trade)
    assert len(monitor.performance_metrics['drawdowns']) == 1
    assert abs(monitor.performance_metrics['drawdowns'][0] - 0.1) < 1e-10  # Use approximate comparison
    
    # Test validation with no trades
    monitor = TradingMonitor({'risk_management': {}})
    validation = monitor.get_validation_status()
    assert not validation['passed_all']
    assert validation['trade_count'] == 0