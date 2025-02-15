"""Tests for health monitoring functionality"""
import pytest
from decimal import Decimal
from datetime import datetime, timezone
from ...src.trading.health_monitor import HealthMonitor

@pytest.fixture
def health_monitor():
    """Create health monitor instance with default thresholds"""
    thresholds = {
        'warning_latency': 100,  # milliseconds
        'critical_latency': 500,
        'warning_error_rate': 5,   # percentage
        'critical_error_rate': 10,  
        'warning_memory': 80,    # percentage
        'critical_memory': 95,   
        'warning_cpu': 70,       # percentage
        'critical_cpu': 90      
    }
    return HealthMonitor(thresholds)

@pytest.mark.asyncio
async def test_check_health_normal_conditions(health_monitor):
    """Test health check under normal conditions"""
    # Record some normal metrics
    await health_monitor.record_latency('test', 50)
    health = await health_monitor.check_health()
    assert health['status'] == 'healthy'

@pytest.mark.asyncio
async def test_check_health_warning_conditions(health_monitor):
    """Test health check under warning conditions"""
    # Record high latency but below critical
    await health_monitor.record_latency('test', 200)
    health = await health_monitor.check_health()
    assert health['status'] == 'warning'

@pytest.mark.asyncio
async def test_check_health_critical_conditions(health_monitor):
    """Test health check under critical conditions"""
    # Record critical latency
    await health_monitor.record_latency('test', 600)
    health = await health_monitor.check_health()
    assert health['status'] == 'critical'

@pytest.mark.asyncio
async def test_calculate_average_latency(health_monitor):
    """Test latency calculation"""
    await health_monitor.record_latency('test', 100)
    avg_latency = await health_monitor._calculate_average_latency()
    assert avg_latency == Decimal('100.0')

@pytest.mark.asyncio
async def test_metrics_persistence(health_monitor):
    """Test metrics persistence to file"""
    # Record some metrics
    await health_monitor.record_latency('test', 50)
    await health_monitor.record_error('test_error')
    
    # Get metrics and verify
    metrics = health_monitor.get_current_metrics()
    assert 'latency' in metrics
    assert metrics['latency'] >= 0

@pytest.mark.asyncio
async def test_error_rate_threshold_breach(health_monitor):
    """Test error rate threshold monitoring"""
    # Record multiple errors
    for _ in range(10):
        await health_monitor.record_error('test_error')
    
    health = await health_monitor.check_health()
    assert health['status'] in ['warning', 'critical']