import pytest
import json
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, Mock
from ...src.trading.health_monitor import HealthMonitor

@pytest.fixture
def thresholds():
    """Create test thresholds."""
    return {
        'warning_latency': 100.0,
        'critical_latency': 200.0,
        'warning_error_rate': 5.0,
        'critical_error_rate': 10.0,
        'warning_memory': 75.0,
        'critical_memory': 90.0,
        'warning_cpu': 70.0,
        'critical_cpu': 85.0
    }

@pytest.fixture
def metrics_file(tmp_path):
    """Create temporary metrics file path."""
    return str(tmp_path / "test_metrics.json")

@pytest.fixture
def health_monitor(thresholds, metrics_file):
    """Create HealthMonitor instance."""
    return HealthMonitor(thresholds, metrics_file)

@pytest.mark.asyncio
async def test_check_health_normal_conditions(health_monitor):
    """Test health check under normal conditions."""
    # Initialize metrics to healthy values
    health_monitor.metrics = {
        'latency': [Decimal('50.0')] * 5,  # Well below warning threshold
        'error_rate': Decimal('0'),
        'memory_usage': Decimal('50.0'),
        'cpu_usage': Decimal('50.0'),
        'api_errors': 0,
        'total_requests': 100,
        'last_heartbeat': datetime.now(timezone.utc)
    }
    
    health_status = await health_monitor.check_health()
    assert health_status['status'] == 'healthy'
    assert 'metrics' in health_status
    assert health_status['alert_count'] == 0

@pytest.mark.asyncio
async def test_check_health_warning_conditions(health_monitor):
    """Test health check under warning conditions."""
    # Initialize metrics with values that should trigger warnings
    health_monitor.metrics = {
        'latency': [Decimal('150.0')] * 5,  # Above warning (100) but below critical (200)
        'error_rate': Decimal('7.0'),  # Above warning (5) but below critical (10)
        'memory_usage': Decimal('50.0'),
        'cpu_usage': Decimal('50.0'),
        'api_errors': 7,
        'total_requests': 100,
        'last_heartbeat': datetime.now(timezone.utc)
    }
    
    health_status = await health_monitor.check_health()
    assert health_status['status'] == 'warning'
    assert health_status['metrics']['latency'] > float(health_monitor.thresholds['warning_latency'])

@pytest.mark.asyncio
async def test_check_health_critical_conditions(health_monitor):
    """Test health check under critical conditions."""
    # Initialize metrics with values that should trigger critical status
    health_monitor.metrics = {
        'latency': [Decimal('250.0')] * 5,  # Well above critical (200)
        'error_rate': Decimal('15.0'),  # Above critical (10)
        'memory_usage': Decimal('50.0'),
        'cpu_usage': Decimal('50.0'),
        'api_errors': 15,
        'total_requests': 100,
        'last_heartbeat': datetime.now(timezone.utc)
    }
    
    health_status = await health_monitor.check_health()
    assert health_status['status'] == 'critical'

@pytest.mark.asyncio
async def test_record_latency(health_monitor):
    """Test latency recording."""
    await health_monitor.record_latency('test_operation', 75.0)
    
    assert len(health_monitor.metrics['latency']) == 1
    assert health_monitor.metrics['latency'][0] == Decimal('75.0')
    assert health_monitor.metrics['total_requests'] == 1

@pytest.mark.asyncio
async def test_record_error(health_monitor):
    """Test error recording."""
    await health_monitor.record_error('test_error')
    
    assert health_monitor.metrics['api_errors'] == 1
    assert health_monitor.metrics['total_requests'] == 1
    
    error_rate = health_monitor._calculate_error_rate()
    assert error_rate == Decimal('100.0')  # 1 error out of 1 request

def test_calculate_average_latency(health_monitor):
    """Test average latency calculation."""
    health_monitor.metrics['latency'] = [Decimal('50.0'), Decimal('100.0'), Decimal('150.0')]
    
    avg_latency = health_monitor._calculate_average_latency()
    assert avg_latency == Decimal('100.0')

def test_calculate_error_rate(health_monitor):
    """Test error rate calculation."""
    health_monitor.metrics['api_errors'] = 5
    health_monitor.metrics['total_requests'] = 100
    
    error_rate = health_monitor._calculate_error_rate()
    assert error_rate == Decimal('5.0')  # 5% error rate

@pytest.mark.asyncio
async def test_check_memory_usage(health_monitor):
    """Test memory usage monitoring."""
    memory_usage = await health_monitor._check_memory_usage()
    assert isinstance(memory_usage, Decimal)
    assert memory_usage >= 0 and memory_usage <= 100

@pytest.mark.asyncio
async def test_check_cpu_usage(health_monitor):
    """Test CPU usage monitoring."""
    cpu_usage = await health_monitor._check_cpu_usage()
    assert isinstance(cpu_usage, Decimal)
    assert cpu_usage >= 0 and cpu_usage <= 100

def test_metrics_persistence(health_monitor, metrics_file):
    """Test metrics persistence to file."""
    health_monitor.metrics['latency'] = [Decimal('50.0')]
    health_monitor.status_history.append({
        'timestamp': datetime.utcnow().isoformat(),
        'status': 'healthy',
        'metrics': {'latency': 50.0}
    })
    
    health_monitor._save_metrics_history()
    
    # Verify file exists and contains valid data
    with open(metrics_file) as f:
        data = json.load(f)
        assert 'status_history' in data
        assert len(data['status_history']) == 1

@pytest.mark.asyncio
async def test_load_metrics_history(health_monitor, metrics_file):
    """Test loading metrics history from file."""
    # Add some test data
    test_data = {
        'status_history': [{
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'healthy',
            'metrics': {'latency': 50.0}
        }]
    }
    
    with open(metrics_file, 'w') as f:
        json.dump(test_data, f)
    
    # Create new monitor instance to test loading
    health_monitor._load_metrics_history()
    assert len(health_monitor.status_history) == 1

@pytest.mark.asyncio
async def test_get_health_history(health_monitor):
    """Test retrieving health history."""
    # Add some test history spaced 30 minutes apart
    base_time = datetime.now(timezone.utc)
    health_monitor.status_history = [
        {
            'timestamp': (base_time - timedelta(minutes=60)).isoformat(),
            'status': 'healthy',
            'metrics': {'latency': 50.0}
        },
        {
            'timestamp': (base_time - timedelta(minutes=30)).isoformat(),
            'status': 'warning',
            'metrics': {'latency': 150.0}
        },
        {
            'timestamp': base_time.isoformat(),
            'status': 'warning',
            'metrics': {'latency': 150.0}
        }
    ]
    
    # Get last hour's history (should get last 2 records)
    history = health_monitor.get_health_history(hours=1)
    assert len(history) == 2
    
    # Get last 90 minutes history (should get all 3 records)
    history = health_monitor.get_health_history(hours=1.5)
    assert len(history) == 3

    # Verify chronological order
    assert datetime.fromisoformat(history[0]['timestamp']) < datetime.fromisoformat(history[1]['timestamp'])

def test_reset_metrics(health_monitor):
    """Test metrics reset functionality."""
    # Add some test data
    health_monitor.metrics['latency'] = [Decimal('50.0')]
    health_monitor.metrics['api_errors'] = 5
    health_monitor.metrics['total_requests'] = 100
    
    health_monitor.reset_metrics()
    
    assert len(health_monitor.metrics['latency']) == 0
    assert health_monitor.metrics['api_errors'] == 0
    assert health_monitor.metrics['total_requests'] == 0

@pytest.mark.asyncio
async def test_error_rate_threshold_breach(health_monitor):
    """Test error rate threshold breach detection."""
    # Simulate high error rate
    for _ in range(10):
        await health_monitor.record_error('test_error')
    
    health_status = await health_monitor.check_health()
    assert health_status['status'] in ['warning', 'critical']
    assert health_status['metrics']['error_rate'] > float(health_monitor.thresholds['warning_error_rate'])

@pytest.mark.asyncio
async def test_get_current_metrics(health_monitor):
    """Test current metrics retrieval."""
    # Add some test data
    await health_monitor.record_latency('test_op', 75.0)
    await health_monitor.record_error('test_error')
    
    current_metrics = health_monitor.get_current_metrics()
    
    assert 'latency' in current_metrics
    assert 'error_rate' in current_metrics
    assert 'memory_usage' in current_metrics
    assert 'cpu_usage' in current_metrics
    assert 'timestamp' in current_metrics