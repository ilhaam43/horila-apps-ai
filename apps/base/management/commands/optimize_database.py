"""Management command for database optimization"""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from base.database_optimization import (
    DatabaseOptimizer, 
    create_performance_indexes, 
    analyze_query_performance
)
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Optimize database performance by creating indexes and analyzing queries'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--analyze-only',
            action='store_true',
            help='Only analyze performance, do not create indexes',
        )
        parser.add_argument(
            '--create-indexes',
            action='store_true',
            help='Create performance indexes',
        )
        parser.add_argument(
            '--vacuum',
            action='store_true',
            help='Run database vacuum/optimize (PostgreSQL/MySQL)',
        )
        parser.add_argument(
            '--update-stats',
            action='store_true',
            help='Update database statistics',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting database optimization...')
        )
        
        try:
            # Always run analysis
            self.stdout.write('\nAnalyzing database performance...')
            analyze_query_performance()
            
            if options['create_indexes'] or not options['analyze_only']:
                self.stdout.write('\nCreating performance indexes...')
                create_performance_indexes()
                self.stdout.write(
                    self.style.SUCCESS('✓ Performance indexes created')
                )
            
            if options['vacuum']:
                self.stdout.write('\nRunning database vacuum/optimize...')
                self._vacuum_database()
            
            if options['update_stats']:
                self.stdout.write('\nUpdating database statistics...')
                self._update_statistics()
            
            self.stdout.write(
                self.style.SUCCESS('\n✓ Database optimization completed!')
            )
            
        except Exception as e:
            logger.error(f"Database optimization failed: {e}")
            raise CommandError(f'Database optimization failed: {e}')
    
    def _vacuum_database(self):
        """Run database vacuum/optimize operations"""
        with connection.cursor() as cursor:
            try:
                if connection.vendor == 'postgresql':
                    # PostgreSQL VACUUM
                    cursor.execute('VACUUM ANALYZE;')
                    self.stdout.write('✓ PostgreSQL VACUUM ANALYZE completed')
                    
                elif connection.vendor == 'mysql':
                    # MySQL OPTIMIZE
                    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE();")
                    tables = cursor.fetchall()
                    
                    for table in tables:
                        cursor.execute(f'OPTIMIZE TABLE {table[0]};')
                    
                    self.stdout.write('✓ MySQL OPTIMIZE TABLE completed')
                    
                elif connection.vendor == 'sqlite':
                    # SQLite VACUUM
                    cursor.execute('VACUUM;')
                    cursor.execute('ANALYZE;')
                    self.stdout.write('✓ SQLite VACUUM and ANALYZE completed')
                    
                else:
                    self.stdout.write(
                        self.style.WARNING(f'VACUUM not supported for {connection.vendor}')
                    )
                    
            except Exception as e:
                logger.warning(f"Vacuum operation failed: {e}")
                self.stdout.write(
                    self.style.WARNING(f'Vacuum operation failed: {e}')
                )
    
    def _update_statistics(self):
        """Update database statistics"""
        with connection.cursor() as cursor:
            try:
                if connection.vendor == 'postgresql':
                    cursor.execute('ANALYZE;')
                    self.stdout.write('✓ PostgreSQL statistics updated')
                    
                elif connection.vendor == 'mysql':
                    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE();")
                    tables = cursor.fetchall()
                    
                    for table in tables:
                        cursor.execute(f'ANALYZE TABLE {table[0]};')
                    
                    self.stdout.write('✓ MySQL statistics updated')
                    
                elif connection.vendor == 'sqlite':
                    cursor.execute('ANALYZE;')
                    self.stdout.write('✓ SQLite statistics updated')
                    
                else:
                    self.stdout.write(
                        self.style.WARNING(f'Statistics update not supported for {connection.vendor}')
                    )
                    
            except Exception as e:
                logger.warning(f"Statistics update failed: {e}")
                self.stdout.write(
                    self.style.WARNING(f'Statistics update failed: {e}')
                )