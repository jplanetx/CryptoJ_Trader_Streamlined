import asyncio
import logging
import time
import psutil
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path

class HealthMonitor:
    def __init__(self, thresholds: Dict[str, float], metrics_file: str = "health_metrics.json"):
        """
        Initialize the health monitor with thresholds and metrics storage.

        Args:
            thresholds (Dict[str, float]): Monitoring thresholds
            metrics_file (str): File to store metrics history
        """
        self.logger = logging.getLogger(__name__)
        self.thresholds = {k: Decimal(str(v)) for k, v in thresholds.items()}
        self.metrics_file = Path(metrics_file)
        self._initialize_metrics()
        self._load_metrics_history()

    def _initialize_metrics(self) -> None:
        """Initialize monitoring metrics and states."""
        self.metrics = {
            'latency': [],
            'error_rate': Decimal('0'),
            'memory_usage': Decimal('0'),
            'cpu_usage': Decimal('0'),
            'api_errors': 0,
            'total_requests': 0,
            'last_heartbeat': datetime.now(timezone.utc)
        }
        self.status_history = []
        self.alert_count = 0
        self.last_check = datetime.now(timezone.utc)

    def _load_metrics_history(self) -> None:
        """Load historical metrics from file."""
        try:
            if self.metrics_file.exists():
                with open(self.metrics_file) as f:
                    data = json.load(f)
                self.status_history = data.get('status_history', [])
                # Keep only last 1000 records
                self.status_history = self.status_history[-1000:]
        except Exception as e:
            self.logger.error(f"Failed to load metrics history: {str(e)}")
            self.status_history = []

    def _save_metrics_history(self) -> None:
        """Save metrics history to file."""
        try:
            metrics_data = {
                'status_history': self.status_history,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            with open(self.metrics_file, 'w') as f:
                json.dump(metrics_data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save metrics history: {str(e)}")

    async def check_health(self) -> Dict[str, Any]:
        """
        Perform a comprehensive health check of the system.

        Returns:
            Dict[str, Any]: Health check results
        """
        try:
            current_time = datetime.now(timezone.utc)
            
            # Calculate metrics
            avg_latency = self._calculate_average_latency()
            error_rate = self._calculate_error_rate()
            memory_usage = await self._check_memory_usage()
            cpu_usage = await self._check_cpu_usage()
            
            # Calculate health status
            status = self._evaluate_health_status()
            
            # Prepare metrics record
            metrics_record = {
                'timestamp': current_time.isoformat(),
                'status': status,
                'metrics': {
                    'latency': float(avg_latency),
                    'error_rate': float(error_rate),
                    'memory_usage': float(memory_usage),
                    'cpu_usage': float(cpu_usage)
                }
            }
            
            # Update metrics history
            self.status_history.append(metrics_record)
            self.status_history = self.status_history[-1000:]  # Keep last 1000 records
            
            # Save metrics history
            self._save_metrics_history()
            
            return {
                'status': status,
                'metrics': metrics_record['metrics'],
                'timestamp': current_time.isoformat(),
                'alert_count': self.alert_count
            }
            
        except Exception as e:
            self.logger.error(f"Health check error: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

    def _evaluate_health_status(self) -> str:
        """
        Evaluate overall system health status based on metrics.

        Returns:
            str: Health status ('healthy', 'warning', or 'critical')
        """
        try:
            avg_latency = self._calculate_average_latency()
            error_rate = self._calculate_error_rate()
            
            # Check critical thresholds first
            if (avg_latency >= Decimal(str(self.thresholds['critical_latency'])) or
                error_rate >= Decimal(str(self.thresholds['critical_error_rate'])) or
                self.metrics['memory_usage'] >= Decimal(str(self.thresholds['critical_memory'])) or
                self.metrics['cpu_usage'] >= Decimal(str(self.thresholds['critical_cpu']))):
                self.alert_count += 1
                return 'critical'
                
            # Then check warning thresholds
            if (avg_latency >= Decimal(str(self.thresholds['warning_latency'])) or
                error_rate >= Decimal(str(self.thresholds['warning_error_rate'])) or
                self.metrics['memory_usage'] >= Decimal(str(self.thresholds['warning_memory'])) or
                self.metrics['cpu_usage'] >= Decimal(str(self.thresholds['warning_cpu']))):
                return 'warning'
            
            return 'healthy'
            
        except Exception as e:
            self.logger.error(f"Health status evaluation error: {str(e)}")
            return 'error'

    def _calculate_average_latency(self) -> Decimal:
        """
        Calculate average latency from recent measurements.

        Returns:
            Decimal: Average latency
        """
        try:
            if not self.metrics['latency']:
                return Decimal('0')
            return Decimal(sum(self.metrics['latency'])) / Decimal(len(self.metrics['latency']))
        except Exception as e:
            self.logger.error(f"Latency calculation error: {str(e)}")
            return Decimal('0')

    def _calculate_error_rate(self) -> Decimal:
        """
        Calculate current error rate.

        Returns:
            Decimal: Error rate as a percentage
        """
        try:
            if self.metrics['total_requests'] == 0:
                return Decimal('0')
            return (Decimal(str(self.metrics['api_errors'])) / 
                   Decimal(str(self.metrics['total_requests']))) * Decimal('100')
        except Exception as e:
            self.logger.error(f"Error rate calculation error: {str(e)}")
            return Decimal('0')

    async def _check_memory_usage(self) -> Decimal:
        """
        Check current memory usage using psutil.

        Returns:
            Decimal: Memory usage as a percentage
        """
        try:
            memory = psutil.virtual_memory()
            return Decimal(str(memory.percent))
        except Exception as e:
            self.logger.error(f"Memory check error: {str(e)}")
            return Decimal('0')

    async def _check_cpu_usage(self) -> Decimal:
        """
        Check current CPU usage using psutil.

        Returns:
            Decimal: CPU usage as a percentage
        """
        try:
            return Decimal(str(psutil.cpu_percent(interval=1)))
        except Exception as e:
            self.logger.error(f"CPU check error: {str(e)}")
            return Decimal('0')

    async def record_latency(self, operation: str, latency: float) -> None:
        """
        Record operation latency measurement.

        Args:
            operation (str): Operation being measured
            latency (float): Latency in milliseconds
        """
        try:
            self.metrics['latency'].append(Decimal(str(latency)))
            self.metrics['total_requests'] += 1
            
            # Log if latency exceeds warning threshold
            if latency > float(self.thresholds['warning_latency']):
                self.logger.warning(f"High latency detected for {operation}: {latency}ms")
                
        except Exception as e:
            self.logger.error(f"Latency recording error: {str(e)}")

    async def record_error(self, error_type: str) -> None:
        """
        Record an API error occurrence.

        Args:
            error_type (str): Type of error encountered
        """
        try:
            self.metrics['api_errors'] += 1
            self.metrics['total_requests'] += 1
            error_rate = self._calculate_error_rate()
            
            if error_rate > Decimal(str(self.thresholds['warning_error_rate'])):
                self.logger.warning(f"High error rate detected: {float(error_rate)}%")
                self.logger.warning(f"Error recorded: {error_type}")
                
        except Exception as e:
            self.logger.error(f"Error recording error: {str(e)}")
            
        # Check health status after recording error
        try:
            await self.check_health()
        except Exception as e:
            self.logger.error(f"Health check after error failed: {str(e)}")

    def get_health_history(self, hours: int = 24) -> List[Dict]:
        """
        Get health status history for specified time period.

        Args:
            hours (int): Number of hours of history to retrieve

        Returns:
            List[Dict]: List of historical health status records
        """
        try:
            current_time = datetime.now(timezone.utc)
            cutoff = current_time - timedelta(hours=hours)
            return [
                status for status in self.status_history
                if datetime.fromisoformat(status['timestamp']).replace(tzinfo=timezone.utc) > cutoff
            ]
        except Exception as e:
            self.logger.error(f"Health history retrieval error: {str(e)}")
            return []

    def reset_metrics(self) -> None:
        """Reset all health metrics to initial state."""
        try:
            self._initialize_metrics()
            self.logger.info("Health metrics reset")
        except Exception as e:
            self.logger.error(f"Metrics reset error: {str(e)}")

    def get_current_metrics(self) -> Dict[str, Any]:
        """
        Get current system metrics.

        Returns:
            Dict[str, Any]: Current system metrics
        """
        try:
            return {
                'latency': {
                    'current': float(self._calculate_average_latency()),
                    'warning_threshold': float(self.thresholds['warning_latency']),
                    'critical_threshold': float(self.thresholds['critical_latency'])
                },
                'error_rate': {
                    'current': float(self._calculate_error_rate()),
                    'warning_threshold': float(self.thresholds['warning_error_rate']),
                    'critical_threshold': float(self.thresholds['critical_error_rate'])
                },
                'memory_usage': {
                    'current': float(self.metrics['memory_usage']),
                    'warning_threshold': float(self.thresholds['warning_memory']),
                    'critical_threshold': float(self.thresholds['critical_memory'])
                },
                'cpu_usage': {
                    'current': float(self.metrics['cpu_usage']),
                    'warning_threshold': float(self.thresholds['warning_cpu']),
                    'critical_threshold': float(self.thresholds['critical_cpu'])
                },
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Metrics retrieval error: {str(e)}")
            return {}