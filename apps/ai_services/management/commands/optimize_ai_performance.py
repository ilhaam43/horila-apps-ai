from django.core.management.base import BaseCommand
from django.utils import timezone
from ai_services.performance import optimize_all_services, get_system_health
from ai_services.models import AIServiceLog
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Optimize AI services performance including caching, database queries, and system health'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--health-check',
            action='store_true',
            help='Only perform health check without optimization',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output',
        )
    
    def handle(self, *args, **options):
        start_time = timezone.now()
        
        if options['verbose']:
            self.stdout.write(self.style.SUCCESS('Starting AI Performance Optimization...'))
        
        try:
            if options['health_check']:
                # Only perform health check
                health_data = get_system_health()
                
                self.stdout.write(self.style.SUCCESS('\n=== SYSTEM HEALTH REPORT ==='))
                
                # System metrics
                if 'system' in health_data:
                    sys_data = health_data['system']
                    self.stdout.write(f"CPU Usage: {sys_data.get('cpu_percent', 'N/A')}%")
                    self.stdout.write(f"Memory Usage: {sys_data.get('memory_percent', 'N/A')}%")
                    self.stdout.write(f"Available Memory: {sys_data.get('memory_available_gb', 'N/A'):.2f} GB")
                    self.stdout.write(f"Disk Usage: {sys_data.get('disk_percent', 'N/A')}%")
                    self.stdout.write(f"Free Disk Space: {sys_data.get('disk_free_gb', 'N/A'):.2f} GB")
                
                # Database metrics
                if 'database' in health_data:
                    db_data = health_data['database']
                    self.stdout.write(f"\nDatabase Connections: {db_data.get('active_connections', 'N/A')}")
                
                # Cache metrics
                if 'cache' in health_data:
                    cache_data = health_data['cache']
                    hits = cache_data.get('cache_hits', 0)
                    misses = cache_data.get('cache_misses', 0)
                    total = hits + misses
                    hit_rate = (hits / total * 100) if total > 0 else 0
                    self.stdout.write(f"\nCache Hit Rate: {hit_rate:.2f}%")
                    self.stdout.write(f"Cache Hits: {hits}")
                    self.stdout.write(f"Cache Misses: {misses}")
                
                # AI Services performance
                if 'ai_services' in health_data:
                    self.stdout.write(f"\n=== AI SERVICES PERFORMANCE ===")
                    for service, stats in health_data['ai_services'].items():
                        if 'error' not in stats:
                            self.stdout.write(f"\n{service.upper()}:")
                            self.stdout.write(f"  Total Calls: {stats.get('total_calls', 0)}")
                            self.stdout.write(f"  Success Rate: {stats.get('success_rate', 0):.2f}%")
                            self.stdout.write(f"  Avg Execution Time: {stats.get('avg_execution_time', 0):.3f}s")
                            self.stdout.write(f"  Max Execution Time: {stats.get('max_execution_time', 0):.3f}s")
                            self.stdout.write(f"  Avg Memory Usage: {stats.get('avg_memory_usage', 0):.2f}MB")
                        else:
                            self.stdout.write(f"\n{service.upper()}: {stats['error']}")
                
                # Connection pool
                if 'connection_pool' in health_data:
                    pool_data = health_data['connection_pool']
                    self.stdout.write(f"\nConnection Pool: {pool_data.get('active_connections', 0)}/{pool_data.get('max_connections', 0)}")
                
                self.stdout.write(self.style.SUCCESS('\nHealth check completed successfully!'))
                
            else:
                # Perform full optimization
                if options['verbose']:
                    self.stdout.write('Running comprehensive optimization...')
                
                result = optimize_all_services()
                
                if result['status'] == 'success':
                    self.stdout.write(self.style.SUCCESS(f"✓ {result['message']}"))
                    
                    # Log the optimization
                    AIServiceLog.objects.create(
                        service_type='performance_optimizer',
                        operation='full_optimization',
                        log_level='INFO',
                        message=f"Optimization completed: {result['message']}",
                        extra_data={
                            'execution_time': (timezone.now() - start_time).total_seconds(),
                            'result': result
                        }
                    )
                    
                    if options['verbose']:
                        # Show health report after optimization
                        health_data = get_system_health()
                        self.stdout.write('\n=== POST-OPTIMIZATION HEALTH ===')
                        
                        if 'system' in health_data:
                            sys_data = health_data['system']
                            self.stdout.write(f"CPU: {sys_data.get('cpu_percent', 'N/A')}% | Memory: {sys_data.get('memory_percent', 'N/A')}%")
                        
                        if 'ai_services' in health_data:
                            active_services = sum(1 for stats in health_data['ai_services'].values() if 'error' not in stats)
                            self.stdout.write(f"Active AI Services: {active_services}/6")
                    
                else:
                    self.stdout.write(self.style.ERROR(f"✗ Optimization failed: {result['message']}"))
                    
                    # Log the failure
                    AIServiceLog.objects.create(
                        service_type='performance_optimizer',
                        operation='full_optimization',
                        log_level='ERROR',
                        message=f"Optimization failed: {result['message']}",
                        extra_data={
                            'execution_time': (timezone.now() - start_time).total_seconds(),
                            'error': result['message']
                        }
                    )
        
        except Exception as e:
            error_msg = f"Optimization command failed: {str(e)}"
            self.stdout.write(self.style.ERROR(error_msg))
            logger.error(error_msg)
            
            # Log the exception
            AIServiceLog.objects.create(
                service_type='performance_optimizer',
                operation='full_optimization',
                log_level='ERROR',
                message=f"Optimization command failed: {str(e)}",
                extra_data={
                    'execution_time': (timezone.now() - start_time).total_seconds(),
                    'error': str(e)
                }
            )
        
        finally:
            total_time = (timezone.now() - start_time).total_seconds()
            if options['verbose']:
                self.stdout.write(f"\nTotal execution time: {total_time:.2f} seconds")