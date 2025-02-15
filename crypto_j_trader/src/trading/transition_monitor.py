"""System transition status monitoring"""
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from decimal import Decimal

logger = logging.getLogger(__name__)

@dataclass
class TransitionStatus:
    """Tracks system transition state"""
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    component_states: Dict[str, bool] = field(default_factory=dict)
    metrics: Dict[str, List[float]] = field(default_factory=lambda: {
        'latency': [],
        'error_rate': [],
        'memory': [],
        'cpu': []
    })
    errors: List[str] = field(default_factory=list)

class TransitionMonitor:
    """Monitors system state during transitions"""
    
    def __init__(self):
        self.status = TransitionStatus()
        self.thresholds = {
            'max_latency': 500,  # ms
            'max_error_rate': 5,  # percent
            'max_memory': 85,  # percent
            'max_cpu': 80  # percent
        }
    
    async def start_monitoring(self, components: Dict[str, Any]) -> None:
        """Start monitoring system components"""
        self.status = TransitionStatus()
        for name in components:
            self.status.component_states[name] = True
            
    async def record_metric(self, metric_type: str, value: float) -> None:
        """Record a metric measurement"""
        if metric_type in self.status.metrics:
            self.status.metrics[metric_type].append(value)
            # Keep last 100 measurements
            self.status.metrics[metric_type] = self.status.metrics[metric_type][-100:]
            
    async def record_error(self, error: str) -> None:
        """Record an error during transition"""
        self.status.errors.append(error)
        logger.error(f"Transition error: {error}")
        
    async def check_transition_health(self) -> Dict[str, Any]:
        """Check overall transition health"""
        status = {
            'healthy': True,
            'metrics': {},
            'errors': len(self.status.errors)
        }
        
        # Check component states
        status['components'] = {
            name: state 
            for name, state in self.status.component_states.items()
        }
        
        # Calculate metric averages
        for metric, values in self.status.metrics.items():
            if values:
                avg = sum(values) / len(values)
                status['metrics'][metric] = avg
                
                # Check threshold breaches
                threshold = self.thresholds.get(f'max_{metric}')
                if threshold and avg > threshold:
                    status['healthy'] = False
                    
        return status
        
    def complete_transition(self) -> None:
        """Mark transition as complete"""
        self.status.completed_at = datetime.now(timezone.utc)
        duration = (self.status.completed_at - self.status.started_at).total_seconds()
        logger.info(f"System transition completed in {duration:.2f} seconds")