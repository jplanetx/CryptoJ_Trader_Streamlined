import asyncio
import logging
import time
import psutil
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path
import os
import tempfile

class HealthMonitor:
    """Monitors system health and performance metrics"""
    
    def __init__(self, thresholds: Dict = None):
        self.thresholds = thresholds or {
            'warning_latency': 100,  # milliseconds
            'critical_latency': 500,
            'warning_error_rate': 5,  # percentage
            'critical_error_rate': 10,
            'warning_memory': 80,  # percentage
            'critical_memory': 95,
            'warning_cpu': 70,  # percentage
            'critical_cpu': 90
        }
        self.metrics = {
            'latency': [],
            'error_rate': [],
            'memory': [],
            'cpu': []
        }
        self.errors = []
        self.latencies = []
        self.last_check = datetime.now(timezone.utc)
        self._setup_persistence()

    def _setup_persistence(self) -> None:
        """Set up metrics persistence"""
        self.metrics_file = os.path.join(
            tempfile.gettempdir(),
            'test_metrics.json'
        )
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.metrics_file), exist_ok=True)
        self._save_metrics()

    def _save_metrics(self) -> None:
        """Save metrics to file"""
        try:
            with open(self.metrics_file, 'w') as f:
                json.dump({
                    'metrics': self.metrics,
                    'errors': [
                        (e[0].isoformat(), e[1]) 
                        for e in self.errors
                    ],
                    'latencies': self.latencies,
                    'last_check': self.last_check.isoformat()
                }, f)
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")

    def _load_metrics(self) -> None:
        """Load metrics from file"""
        try:
            if os.path.exists(self.metrics_file):
                with open(self.metrics_file, 'r') as f:
                    data = json.load(f)
                    self.metrics = data.get('metrics', self.metrics)
                    self.errors = [
                        (datetime.fromisoformat(e[0]), e[1])
                        for e in data.get('errors', [])
                    ]
                    self.latencies = data.get('latencies', [])
                    last_check = data.get('last_check')
                    if last_check:
                        self.last_check = datetime.fromisoformat(last_check)
        except Exception as e:
            logger.error(f"Failed to load metrics: {e}")

    async def record_latency(self, operation: str, latency: float) -> None:
        """Record operation latency"""
        self.latencies.append((operation, latency))
        if len(self.latencies) > 1000:  # Keep last 1000 measurements
            self.latencies = self.latencies[-1000:]
        self.metrics['latency'].append(latency)
        if len(self.metrics['latency']) > 1000:
            self.metrics['latency'] = self.metrics['latency'][-1000:]
        self._save_metrics()

    async def record_error(self, error: str) -> None:
        """Record an error occurrence"""
        now = datetime.now(timezone.utc)
        self.errors.append((now, error))
        if len(self.errors) > 1000:  # Keep last 1000 errors
            self.errors = self.errors[-1000:]
        error_rate = await self._calculate_error_rate()
        self.metrics['error_rate'].append(float(error_rate))
        if len(self.metrics['error_rate']) > 1000:
            self.metrics['error_rate'] = self.metrics['error_rate'][-1000:]
        self._save_metrics()

    async def check_health(self) -> Dict:
        """Check system health and return status"""
        try:
            avg_latency = await self._calculate_average_latency()
            error_rate = await self._calculate_error_rate()
            
            status = 'healthy'
            if avg_latency > self.thresholds['critical_latency'] or error_rate > self.thresholds['critical_error_rate']:
                status = 'critical'
            elif avg_latency > self.thresholds['warning_latency'] or error_rate > self.thresholds['warning_error_rate']:
                status = 'warning'
                
            self.last_check = datetime.now(timezone.utc)
            
            return {
                'status': status,
                'latency': float(avg_latency),
                'error_rate': float(error_rate),
                'last_check': self.last_check.isoformat(),
                'metrics': self.metrics
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'last_check': datetime.now(timezone.utc).isoformat()
            }

    async def _calculate_average_latency(self) -> Decimal:
        """Calculate average latency from recent measurements"""
        if not self.latencies:
            return Decimal('0')
        recent = self.latencies[-100:]  # Use last 100 measurements
        return Decimal(sum(l[1] for l in recent) / len(recent))

    async def _calculate_error_rate(self) -> Decimal:
        """Calculate error rate percentage"""
        if not self.errors:
            return Decimal('0')
        window = datetime.now(timezone.utc) - timedelta(minutes=5)
        recent_errors = [e for e in self.errors if e[0] > window]
        return Decimal(len(recent_errors)) / Decimal('5') * Decimal('100')  # Errors per minute * 100 for percentage

    def get_current_metrics(self) -> Dict:
        """Get current system metrics"""
        self._load_metrics()
        metrics = {}
        for key in ['latency', 'error_rate', 'memory', 'cpu']:
            values = self.metrics.get(key, [])
            metrics[key] = sum(values) / len(values) if values else 0
        metrics['last_check'] = self.last_check.isoformat()
        return metrics