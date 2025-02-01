"""Health monitoring system for trading bot."""
import logging
import psutil
import time
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class HealthMonitor:
    def __init__(self):
        """Initialize health monitoring system."""
        self.start_time = datetime.now(timezone.utc)
        self.last_check_time = self.start_time
        self.metrics_history: List[Dict[str, Any]] = []
        
        # Current system metrics
        self.system_metrics = {
            'cpu_percent': 0.0,
            'memory_percent': 0.0,
            'disk_usage_percent': 0.0,
            'process_memory_mb': 0.0
        }
        
        # Current trading metrics
        self.trading_metrics = {
            'order_latency_ms': 0.0,
            'market_data_delay_ms': 0.0,
            'websocket_reconnects': 0,
            'api_errors': 0,
            'orders_processed': 0,
            'active_positions': 0
        }

    def record_order_latency(self, start_time: float) -> float:
        """Record order processing latency."""
        latency_ms = (time.time() - start_time) * 1000
        self.trading_metrics['order_latency_ms'] = latency_ms
        return latency_ms

    def record_market_data_delay(self, data_time: float) -> float:
        """Record market data processing delay."""
        delay_ms = (time.time() - data_time) * 1000
        self.trading_metrics['market_data_delay_ms'] = delay_ms
        return delay_ms

    def record_websocket_reconnect(self) -> None:
        """Record WebSocket reconnection event."""
        self.trading_metrics['websocket_reconnects'] += 1

    def record_api_error(self) -> None:
        """Record API error event."""
        self.trading_metrics['api_errors'] += 1

    def _update_system_metrics(self) -> None:
        """Update current system metrics."""
        try:
            process = psutil.Process()
            
            self.system_metrics.update({
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_usage_percent': psutil.disk_usage('/').percent,
                'process_memory_mb': process.memory_info().rss / (1024 * 1024)
            })
        except Exception as e:
            logger.error(f"Error updating system metrics: {e}")

    def check_system_health(self) -> Dict[str, Any]:
        """Perform system health check."""
        current_time = datetime.now(timezone.utc)
        self.last_check_time = current_time
        
        # Update system metrics
        self._update_system_metrics()
        
        # Check for alerts
        alerts = []
        status = 'healthy'
        
        # CPU check
        if self.system_metrics['cpu_percent'] > 80:
            alerts.append('High CPU usage detected')
            status = 'degraded'
            
        # Memory check
        if self.system_metrics['memory_percent'] > 80:
            alerts.append('High memory usage detected')
            status = 'degraded'
            
        # Disk space check
        if self.system_metrics['disk_usage_percent'] > 90:
            alerts.append('Low disk space')
            status = 'degraded'
            
        # Trading metrics checks
        if self.trading_metrics['order_latency_ms'] > 1000:
            alerts.append('High order latency')
            status = 'degraded'
            
        if self.trading_metrics['market_data_delay_ms'] > 2000:
            alerts.append('Significant market data delay')
            status = 'degraded'
            
        if self.trading_metrics['api_errors'] > 10:
            alerts.append('High API error rate')
            status = 'degraded'

        # Create metrics snapshot
        metrics_snapshot = {
            'timestamp': current_time,
            'system': self.system_metrics.copy(),
            'trading': self.trading_metrics.copy()
        }
        
        # Add to history
        self.metrics_history.append(metrics_snapshot)
        
        # Keep only last hour of metrics
        cutoff_time = current_time.timestamp() - 3600
        self.metrics_history = [
            m for m in self.metrics_history 
            if m['timestamp'].timestamp() > cutoff_time
        ]
        
        return {
            'status': status,
            'metrics': metrics_snapshot,
            'timestamp': current_time.isoformat(),
            'alerts': alerts,
            'uptime_seconds': (current_time - self.start_time).total_seconds()
        }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics summary."""
        if not self.metrics_history:
            return {
                'averages': {},
                'current': self.system_metrics,
                'events': self.trading_metrics,
                'uptime': (datetime.now(timezone.utc) - self.start_time).total_seconds()
            }
            
        # Calculate averages
        cpu_values = [m['system']['cpu_percent'] for m in self.metrics_history]
        memory_values = [m['system']['memory_percent'] for m in self.metrics_history]
        latency_values = [m['trading']['order_latency_ms'] for m in self.metrics_history]
        
        averages = {
            'cpu_percent': sum(cpu_values) / len(cpu_values),
            'memory_percent': sum(memory_values) / len(memory_values),
            'order_latency_ms': sum(latency_values) / len(latency_values)
        }
        
        return {
            'averages': averages,
            'current': self.system_metrics,
            'events': self.trading_metrics,
            'uptime': (datetime.now(timezone.utc) - self.start_time).total_seconds()
        }