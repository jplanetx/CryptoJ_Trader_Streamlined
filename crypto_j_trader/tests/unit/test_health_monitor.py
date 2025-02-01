"""Unit tests for health monitoring system."""
import pytest
import time
from datetime import datetime, timezone
from crypto_j_trader.src.trading.health_monitor import HealthMonitor

@pytest.fixture
def health_monitor():
    """Create a health monitor instance for testing."""
    return HealthMonitor()

class TestHealthMonitor:
    def test_initialization(self, health_monitor):
        """Test health monitor initialization."""
        assert health_monitor.start_time is not None
        assert health_monitor.last_check_time is not None
        assert isinstance(health_monitor.metrics_history, list)
        assert health_monitor.system_metrics['cpu_percent'] == 0.0
        assert health_monitor.trading_metrics['order_latency_ms'] == 0.0

    def test_record_order_latency(self, health_monitor):
        """Test order latency recording."""
        start_time = time.time() - 0.1  # Simulate 100ms latency
        latency = health_monitor.record_order_latency(start_time)
        assert latency == pytest.approx(100, abs = 1)  # At least 100ms
        assert health_monitor.trading_metrics['order_latency_ms'] == pytest.approx(100, abs=1)

    def test_record_market_data_delay(self, health_monitor):
        """Test market data delay recording."""
        data_time = time.time() - 0.05  # Simulate 50ms delay
        delay = health_monitor.record_market_data_delay(data_time)
        assert delay == pytest.approx(50, abs=1)  # At least 50ms
        assert health_monitor.trading_metrics['market_data_delay_ms'] == pytest.approx(50, abs=1)

    def test_record_websocket_reconnect(self, health_monitor):
        """Test WebSocket reconnection recording."""
        initial_count = health_monitor.trading_metrics['websocket_reconnects']
        health_monitor.record_websocket_reconnect()
        assert health_monitor.trading_metrics['websocket_reconnects'] == initial_count + 1

    def test_record_api_error(self, health_monitor):
        """Test API error recording."""
        initial_count = health_monitor.trading_metrics['api_errors']
        health_monitor.record_api_error()
        assert health_monitor.trading_metrics['api_errors'] == initial_count + 1

    def test_check_system_health(self, health_monitor):
        """Test system health check."""
        result = health_monitor.check_system_health()
        assert isinstance(result, dict)
        assert 'status' in result
        assert 'metrics' in result
        assert 'timestamp' in result
        assert 'alerts' in result
        assert 'uptime_seconds' in result

    def test_get_performance_metrics(self, health_monitor):
        """Test performance metrics retrieval."""
        # Add some history first
        health_monitor.check_system_health()
        time.sleep(0.1)
        health_monitor.check_system_health()

        metrics = health_monitor.get_performance_metrics()
        assert isinstance(metrics, dict)
        assert 'averages' in metrics
        assert 'current' in metrics
        assert 'events' in metrics
        assert 'uptime' in metrics

    def test_health_degradation(self, health_monitor):
        """Test health status degradation conditions."""
        # Simulate high CPU usage
        health_monitor.system_metrics['cpu_percent'] = 90.0
        result = health_monitor.check_system_health()
        assert result['status'] == 'degraded'
        assert any('High CPU usage detected' in alert for alert in result['alerts'])

    def test_metrics_history_maintenance(self, health_monitor):
        """Test metrics history maintenance."""
        # Add multiple metrics
        for _ in range(5):
            health_monitor.check_system_health()
            time.sleep(0.1)

        assert len(health_monitor.metrics_history) > 0
        # Verify timestamps are recent
        for metric in health_monitor.metrics_history:
            assert (datetime.now(timezone.utc) - metric['timestamp']).total_seconds() < 3600
