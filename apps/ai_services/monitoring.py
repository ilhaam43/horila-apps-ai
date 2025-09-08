from django.core.cache import cache
from django.utils import timezone
from django.conf import settings
import json
import time
import threading
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque

from .models import AIServiceLog, AIAnalytics
from .performance import get_system_health

logger = logging.getLogger(__name__)

class AIServiceMonitor:
    """
    Real-time monitoring system for AI services
    """
    
    def __init__(self):
        self.metrics_buffer = defaultdict(lambda: deque(maxlen=1000))  # Keep last 1000 metrics
        self.alert_thresholds = {
            'cpu_percent': 80,
            'memory_percent': 85,
            'disk_percent': 90,
            'execution_time': 30,  # seconds
            'error_rate': 10,  # percentage
            'response_time': 5  # seconds
        }
        self.monitoring_active = False
        self.monitor_thread = None
        self.alert_callbacks = []
    
    def start_monitoring(self, interval: int = 60):
        """Start real-time monitoring"""
        if self.monitoring_active:
            logger.warning("Monitoring is already active")
            return
        
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()
        logger.info(f"AI Service monitoring started with {interval}s interval")
    
    def stop_monitoring(self):
        """Stop real-time monitoring"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("AI Service monitoring stopped")
    
    def _monitoring_loop(self, interval: int):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Collect system health metrics
                health_data = get_system_health()
                timestamp = time.time()
                
                # Store metrics in buffer
                self.metrics_buffer['system_health'].append({
                    'timestamp': timestamp,
                    'data': health_data
                })
                
                # Check for alerts
                self._check_alerts(health_data, timestamp)
                
                # Store metrics in cache for API access
                cache.set('ai_monitoring_latest', {
                    'timestamp': timestamp,
                    'health_data': health_data
                }, timeout=300)  # 5 minutes
                
                # Sleep for the specified interval
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(interval)
    
    def _check_alerts(self, health_data: Dict[str, Any], timestamp: float):
        """Check for alert conditions"""
        alerts = []
        
        try:
            # System alerts
            if 'system' in health_data:
                sys_data = health_data['system']
                
                if sys_data.get('cpu_percent', 0) > self.alert_thresholds['cpu_percent']:
                    alerts.append({
                        'type': 'high_cpu',
                        'severity': 'warning',
                        'message': f"High CPU usage: {sys_data['cpu_percent']}%",
                        'value': sys_data['cpu_percent'],
                        'threshold': self.alert_thresholds['cpu_percent']
                    })
                
                if sys_data.get('memory_percent', 0) > self.alert_thresholds['memory_percent']:
                    alerts.append({
                        'type': 'high_memory',
                        'severity': 'warning',
                        'message': f"High memory usage: {sys_data['memory_percent']}%",
                        'value': sys_data['memory_percent'],
                        'threshold': self.alert_thresholds['memory_percent']
                    })
                
                if sys_data.get('disk_percent', 0) > self.alert_thresholds['disk_percent']:
                    alerts.append({
                        'type': 'high_disk',
                        'severity': 'critical',
                        'message': f"High disk usage: {sys_data['disk_percent']}%",
                        'value': sys_data['disk_percent'],
                        'threshold': self.alert_thresholds['disk_percent']
                    })
            
            # AI Service alerts
            if 'ai_services' in health_data:
                for service_name, service_stats in health_data['ai_services'].items():
                    if 'error' not in service_stats:
                        # Check success rate
                        success_rate = service_stats.get('success_rate', 100)
                        error_rate = 100 - success_rate
                        
                        if error_rate > self.alert_thresholds['error_rate']:
                            alerts.append({
                                'type': 'high_error_rate',
                                'severity': 'critical',
                                'message': f"High error rate in {service_name}: {error_rate:.2f}%",
                                'service': service_name,
                                'value': error_rate,
                                'threshold': self.alert_thresholds['error_rate']
                            })
                        
                        # Check execution time
                        avg_time = service_stats.get('avg_execution_time', 0)
                        if avg_time > self.alert_thresholds['execution_time']:
                            alerts.append({
                                'type': 'slow_execution',
                                'severity': 'warning',
                                'message': f"Slow execution in {service_name}: {avg_time:.2f}s",
                                'service': service_name,
                                'value': avg_time,
                                'threshold': self.alert_thresholds['execution_time']
                            })
            
            # Process alerts
            if alerts:
                self._process_alerts(alerts, timestamp)
                
        except Exception as e:
            logger.error(f"Alert checking failed: {e}")
    
    def _process_alerts(self, alerts: List[Dict[str, Any]], timestamp: float):
        """Process and handle alerts"""
        for alert in alerts:
            alert['timestamp'] = timestamp
            alert['datetime'] = datetime.fromtimestamp(timestamp)
            
            # Log the alert
            logger.warning(f"ALERT: {alert['message']}")
            
            # Store alert in cache
            alert_key = f"ai_alert:{alert['type']}:{int(timestamp)}"
            cache.set(alert_key, alert, timeout=3600)  # 1 hour
            
            # Add to recent alerts list
            recent_alerts = cache.get('ai_recent_alerts', [])
            recent_alerts.append(alert)
            
            # Keep only last 50 alerts
            if len(recent_alerts) > 50:
                recent_alerts = recent_alerts[-50:]
            
            cache.set('ai_recent_alerts', recent_alerts, timeout=3600)
            
            # Call alert callbacks
            for callback in self.alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    logger.error(f"Alert callback failed: {e}")
    
    def add_alert_callback(self, callback: callable):
        """Add a callback function for alerts"""
        self.alert_callbacks.append(callback)
    
    def get_recent_metrics(self, service: str = None, minutes: int = 60) -> List[Dict[str, Any]]:
        """Get recent metrics for a service or all services"""
        cutoff_time = time.time() - (minutes * 60)
        
        if service:
            metrics = list(self.metrics_buffer.get(service, []))
        else:
            metrics = list(self.metrics_buffer.get('system_health', []))
        
        # Filter by time
        recent_metrics = [
            metric for metric in metrics 
            if metric['timestamp'] > cutoff_time
        ]
        
        return recent_metrics
    
    def get_service_summary(self) -> Dict[str, Any]:
        """Get summary of all AI services"""
        try:
            health_data = get_system_health()
            recent_alerts = cache.get('ai_recent_alerts', [])
            
            # Count alerts by severity
            alert_counts = defaultdict(int)
            for alert in recent_alerts[-10:]:  # Last 10 alerts
                alert_counts[alert.get('severity', 'unknown')] += 1
            
            # Service status summary
            service_status = {}
            if 'ai_services' in health_data:
                for service_name, stats in health_data['ai_services'].items():
                    if 'error' in stats:
                        status = 'error'
                    elif stats.get('success_rate', 0) < 95:
                        status = 'warning'
                    elif stats.get('avg_execution_time', 0) > 10:
                        status = 'slow'
                    else:
                        status = 'healthy'
                    
                    service_status[service_name] = {
                        'status': status,
                        'success_rate': stats.get('success_rate', 0),
                        'avg_execution_time': stats.get('avg_execution_time', 0),
                        'total_calls': stats.get('total_calls', 0)
                    }
            
            return {
                'timestamp': time.time(),
                'system_health': health_data.get('system', {}),
                'service_status': service_status,
                'recent_alerts': {
                    'total': len(recent_alerts),
                    'critical': alert_counts['critical'],
                    'warning': alert_counts['warning'],
                    'info': alert_counts['info']
                },
                'monitoring_active': self.monitoring_active
            }
            
        except Exception as e:
            logger.error(f"Failed to get service summary: {e}")
            return {'error': str(e)}

class PerformanceAnalyzer:
    """
    Analyze AI service performance trends and patterns
    """
    
    @staticmethod
    def analyze_performance_trends(service_name: str, hours: int = 24) -> Dict[str, Any]:
        """Analyze performance trends for a specific service"""
        try:
            # Get performance metrics from cache
            metric_key = f"perf:{service_name}"
            metrics = cache.get(metric_key, [])
            
            if not metrics:
                return {'error': 'No metrics available'}
            
            # Filter by time range
            cutoff_time = time.time() - (hours * 3600)
            recent_metrics = [
                m for m in metrics 
                if m.get('timestamp', 0) > cutoff_time
            ]
            
            if not recent_metrics:
                return {'error': 'No recent metrics available'}
            
            # Calculate trends
            execution_times = [m['execution_time'] for m in recent_metrics if m['success']]
            memory_usage = [m['memory_used'] for m in recent_metrics if m['success']]
            
            # Success rate over time
            total_calls = len(recent_metrics)
            successful_calls = len(execution_times)
            success_rate = (successful_calls / total_calls * 100) if total_calls > 0 else 0
            
            # Performance trends
            if len(execution_times) >= 2:
                # Simple trend calculation (comparing first half vs second half)
                mid_point = len(execution_times) // 2
                first_half_avg = sum(execution_times[:mid_point]) / mid_point
                second_half_avg = sum(execution_times[mid_point:]) / (len(execution_times) - mid_point)
                
                performance_trend = 'improving' if second_half_avg < first_half_avg else 'degrading'
                trend_percentage = abs((second_half_avg - first_half_avg) / first_half_avg * 100)
            else:
                performance_trend = 'stable'
                trend_percentage = 0
            
            return {
                'service_name': service_name,
                'analysis_period_hours': hours,
                'total_calls': total_calls,
                'successful_calls': successful_calls,
                'success_rate': success_rate,
                'performance_trend': performance_trend,
                'trend_percentage': trend_percentage,
                'avg_execution_time': sum(execution_times) / len(execution_times) if execution_times else 0,
                'max_execution_time': max(execution_times) if execution_times else 0,
                'min_execution_time': min(execution_times) if execution_times else 0,
                'avg_memory_usage': sum(memory_usage) / len(memory_usage) if memory_usage else 0,
                'max_memory_usage': max(memory_usage) if memory_usage else 0
            }
            
        except Exception as e:
            logger.error(f"Performance trend analysis failed: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def get_bottleneck_analysis() -> Dict[str, Any]:
        """Identify performance bottlenecks across all AI services"""
        try:
            services = ['budget_ai', 'knowledge_ai', 'indonesian_nlp', 
                       'document_classifier', 'intelligent_search', 'rag_n8n']
            
            bottlenecks = []
            service_performance = {}
            
            for service in services:
                analysis = PerformanceAnalyzer.analyze_performance_trends(service, hours=6)
                
                if 'error' not in analysis:
                    service_performance[service] = analysis
                    
                    # Identify bottlenecks
                    if analysis['success_rate'] < 95:
                        bottlenecks.append({
                            'service': service,
                            'type': 'low_success_rate',
                            'severity': 'high',
                            'value': analysis['success_rate'],
                            'description': f"Success rate is {analysis['success_rate']:.1f}%"
                        })
                    
                    if analysis['avg_execution_time'] > 10:
                        bottlenecks.append({
                            'service': service,
                            'type': 'slow_execution',
                            'severity': 'medium',
                            'value': analysis['avg_execution_time'],
                            'description': f"Average execution time is {analysis['avg_execution_time']:.2f}s"
                        })
                    
                    if analysis['performance_trend'] == 'degrading' and analysis['trend_percentage'] > 20:
                        bottlenecks.append({
                            'service': service,
                            'type': 'performance_degradation',
                            'severity': 'medium',
                            'value': analysis['trend_percentage'],
                            'description': f"Performance degraded by {analysis['trend_percentage']:.1f}%"
                        })
            
            # Sort bottlenecks by severity
            severity_order = {'high': 3, 'medium': 2, 'low': 1}
            bottlenecks.sort(key=lambda x: severity_order.get(x['severity'], 0), reverse=True)
            
            return {
                'timestamp': time.time(),
                'bottlenecks': bottlenecks,
                'service_performance': service_performance,
                'recommendations': PerformanceAnalyzer._generate_recommendations(bottlenecks)
            }
            
        except Exception as e:
            logger.error(f"Bottleneck analysis failed: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def _generate_recommendations(bottlenecks: List[Dict[str, Any]]) -> List[str]:
        """Generate performance improvement recommendations"""
        recommendations = []
        
        # Group bottlenecks by type
        bottleneck_types = defaultdict(list)
        for bottleneck in bottlenecks:
            bottleneck_types[bottleneck['type']].append(bottleneck)
        
        if 'low_success_rate' in bottleneck_types:
            recommendations.append(
                "Investigate error logs for services with low success rates. "
                "Consider implementing retry mechanisms and better error handling."
            )
        
        if 'slow_execution' in bottleneck_types:
            recommendations.append(
                "Optimize slow-performing services by implementing caching, "
                "database query optimization, or async processing."
            )
        
        if 'performance_degradation' in bottleneck_types:
            recommendations.append(
                "Monitor services with degrading performance. "
                "Consider scaling resources or optimizing algorithms."
            )
        
        if not recommendations:
            recommendations.append("All services are performing well. Continue monitoring.")
        
        return recommendations

# Global monitor instance
ai_monitor = AIServiceMonitor()

# Alert callback for logging critical alerts
def log_critical_alert(alert: Dict[str, Any]):
    """Log critical alerts to database"""
    if alert.get('severity') == 'critical':
        try:
            AIServiceLog.objects.create(
                service_name='monitoring_system',
                operation='critical_alert',
                status='alert',
                details=alert,
                error_message=alert.get('message', '')
            )
        except Exception as e:
            logger.error(f"Failed to log critical alert: {e}")

# Register the alert callback
ai_monitor.add_alert_callback(log_critical_alert)