"""Strategy and system monitoring module for tracking performance and risk metrics."""

import logging
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pandas as pd

logger = logging.getLogger(__name__)

class TradingMonitor:
    """Monitors trading system performance, risk, and technical metrics"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.performance_metrics = {
            'trades': [],
            'returns': [],
            'drawdowns': [],
            'win_rate': 0.0,
            'profit_factor': 0.0
        }
        self.risk_metrics = {
            'var': 0.0,
            'position_correlation': 0.0,
            'max_position_size': 0.0,
            'stop_loss_violations': 0
        }
        self.technical_metrics = {
            'websocket_uptime': 100.0,
            'order_latencies': [],
            'failed_rebalances': 0,
            'error_count': 0
        }
        self.start_time = datetime.now()
        
    def update_trade_metrics(self, trade: Dict) -> None:
        """Update metrics with new trade information
        
        Args:
            trade: Dictionary containing trade details including:
                  entry_price, exit_price, size, timestamp, duration
        """
        self.performance_metrics['trades'].append(trade)
        returns = (trade['exit_price'] - trade['entry_price']) / trade['entry_price']
        self.performance_metrics['returns'].append(returns)
        
        # Update win rate
        wins = sum(1 for r in self.performance_metrics['returns'] if r > 0)
        total = len(self.performance_metrics['returns'])
        self.performance_metrics['win_rate'] = wins / total if total > 0 else 0
        
        # Update profit factor
        gains = sum(r for r in self.performance_metrics['returns'] if r > 0)
        losses = abs(sum(r for r in self.performance_metrics['returns'] if r < 0))
        self.performance_metrics['profit_factor'] = gains / losses if losses > 0 else 0
        
        # Update drawdown
        cumulative_returns = np.array([1.0] + [1.0 + r for r in self.performance_metrics['returns']])
        cumulative_value = np.cumprod(cumulative_returns)
        peak = np.maximum.accumulate(cumulative_value)
        drawdown = (peak - cumulative_value) / peak
        self.performance_metrics['drawdowns'].append(float(np.max(drawdown)))
        
    def update_risk_metrics(self, portfolio: Dict) -> None:
        """Update risk metrics based on current portfolio state
        
        Args:
            portfolio: Dictionary containing current positions and values
        """
        # Calculate Value at Risk (VaR)
        returns = pd.Series(self.performance_metrics['returns'])
        if len(returns) > 0:
            self.risk_metrics['var'] = float(returns.quantile(0.05))
        
        # Update position correlation
        # Calculate position correlation if we have multiple positions with history
        positions = portfolio.get('positions', [])
        if len(positions) > 1:
            position_values = np.array([p['value'] for p in positions])
            # Reshape to 2D array for correlation calculation
            position_values = position_values.reshape(-1, 1) if position_values.ndim == 1 else position_values
            if position_values.shape[1] > 1:
                correlation_matrix = np.corrcoef(position_values)
                np.fill_diagonal(correlation_matrix, np.nan)
                self.risk_metrics['position_correlation'] = float(np.nanmean(correlation_matrix))
            else:
                self.risk_metrics['position_correlation'] = 0.0
        
        # Update maximum position size
        if portfolio.get('positions'):
            max_size = max(p['value'] for p in portfolio['positions'])
            portfolio_value = sum(p['value'] for p in portfolio['positions'])
            self.risk_metrics['max_position_size'] = max_size / portfolio_value if portfolio_value > 0 else 0
            
    def update_technical_metrics(self, event: Dict) -> None:
        """Update technical metrics based on system events
        
        Args:
            event: Dictionary containing event details like type and data
        """
        event_type = event.get('type')
        
        if event_type == 'websocket_status':
            # Update websocket uptime
            total_time = (datetime.now() - self.start_time).total_seconds()
            downtime = event.get('downtime', 0)
            self.technical_metrics['websocket_uptime'] = ((total_time - downtime) / total_time) * 100
            
        elif event_type == 'order_latency':
            # Track order execution latency
            self.technical_metrics['order_latencies'].append(event.get('latency', 0))
            
        elif event_type == 'rebalance_failed':
            self.technical_metrics['failed_rebalances'] += 1
            
        elif event_type == 'error':
            self.technical_metrics['error_count'] += 1
            
    def get_validation_status(self) -> Dict:
        """Check if current metrics meet production criteria
        
        Returns:
            Dictionary containing validation status and details
        """
        # Define validation thresholds
        thresholds = {
            'sharpe_ratio': 1.5,
            'max_drawdown': 0.15,
            'win_rate': 0.55,
            'profit_factor': 1.3,
            'var': -0.02,
            'position_correlation': 0.7,
            'max_position_size': 0.1,
            'websocket_uptime': 99.9,
            'avg_order_latency': 200,  # milliseconds
            'failed_rebalances': 0
        }
        
        # Calculate metrics
        returns = pd.Series(self.performance_metrics['returns'])
        metrics = {
            'sharpe_ratio': float(returns.mean() / returns.std() * np.sqrt(252)) if len(returns) > 0 and returns.std() > 0 else 0,
            'max_drawdown': max(self.performance_metrics['drawdowns']) if self.performance_metrics['drawdowns'] else 0,
            'win_rate': self.performance_metrics['win_rate'],
            'profit_factor': self.performance_metrics['profit_factor'],
            'var': self.risk_metrics['var'],
            'position_correlation': self.risk_metrics['position_correlation'],
            'max_position_size': self.risk_metrics['max_position_size'],
            'websocket_uptime': self.technical_metrics['websocket_uptime'],
            'avg_order_latency': np.mean(self.technical_metrics['order_latencies']) if self.technical_metrics['order_latencies'] else 0,
            'failed_rebalances': self.technical_metrics['failed_rebalances']
        }
        
        # Check if all metrics meet thresholds
        validations = {
            metric: {
                'value': value,
                'threshold': thresholds[metric],
                'passed': (value >= thresholds[metric] if metric in ['sharpe_ratio', 'win_rate', 'profit_factor', 'websocket_uptime']
                          else value <= thresholds[metric])
            }
            for metric, value in metrics.items()
        }
        
        return {
            'passed_all': all(v['passed'] for v in validations.values()),
            'metrics': validations,
            'trade_count': len(self.performance_metrics['trades']),
            'monitoring_days': (datetime.now() - self.start_time).days
        }
        
    def generate_report(self) -> str:
        """Generate a formatted monitoring report
        
        Returns:
            String containing formatted report
        """
        validation = self.get_validation_status()
        
        report = [
            "Trading System Monitoring Report",
            "=" * 30,
            f"Report Date: {datetime.now()}",
            f"Monitoring Period: {validation['monitoring_days']} days",
            f"Total Trades: {validation['trade_count']}",
            "",
            "Validation Status:",
            f"Overall Status: {'PASSED' if validation['passed_all'] else 'FAILED'}",
            "",
            "Detailed Metrics:"
        ]
        
        for metric, data in validation['metrics'].items():
            status = "✓" if data['passed'] else "✗"
            report.append(f"{metric:20} {data['value']:10.4f} {status} (threshold: {data['threshold']})")
            
        return "\n".join(report)