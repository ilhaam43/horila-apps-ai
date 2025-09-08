"""Database optimization utilities and query optimizations"""

from django.db import connection
from django.core.management.base import BaseCommand
from django.apps import apps
import logging

logger = logging.getLogger(__name__)


class DatabaseOptimizer:
    """Database optimization utilities"""
    
    @staticmethod
    def analyze_slow_queries():
        """Analyze slow queries and suggest optimizations"""
        with connection.cursor() as cursor:
            if connection.vendor == 'postgresql':
                # PostgreSQL specific queries
                cursor.execute("""
                    SELECT query, mean_time, calls, total_time
                    FROM pg_stat_statements
                    ORDER BY mean_time DESC
                    LIMIT 10;
                """)
                return cursor.fetchall()
            elif connection.vendor == 'mysql':
                # MySQL specific queries
                cursor.execute("""
                    SELECT sql_text, avg_timer_wait/1000000000 as avg_time_ms,
                           count_star as calls, sum_timer_wait/1000000000 as total_time_ms
                    FROM performance_schema.events_statements_summary_by_digest
                    ORDER BY avg_timer_wait DESC
                    LIMIT 10;
                """)
                return cursor.fetchall()
            else:
                logger.warning("Slow query analysis not supported for %s", connection.vendor)
                return []
    
    @staticmethod
    def get_table_sizes():
        """Get table sizes for optimization analysis"""
        with connection.cursor() as cursor:
            if connection.vendor == 'postgresql':
                cursor.execute("""
                    SELECT 
                        schemaname,
                        tablename,
                        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                        pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                    FROM pg_tables
                    WHERE schemaname = 'public'
                    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
                """)
                return cursor.fetchall()
            elif connection.vendor == 'mysql':
                cursor.execute("""
                    SELECT 
                        table_schema,
                        table_name,
                        ROUND(((data_length + index_length) / 1024 / 1024), 2) AS size_mb,
                        (data_length + index_length) as size_bytes
                    FROM information_schema.TABLES
                    WHERE table_schema = DATABASE()
                    ORDER BY (data_length + index_length) DESC;
                """)
                return cursor.fetchall()
            else:
                return []
    
    @staticmethod
    def check_missing_indexes():
        """Check for missing indexes on foreign keys"""
        missing_indexes = []
        
        for model in apps.get_models():
            for field in model._meta.get_fields():
                # Only check fields that can have db_index (ForeignKey, OneToOneField)
                if (hasattr(field, 'related_model') and field.related_model and 
                    hasattr(field, 'db_index') and not field.many_to_many):
                    # Check if foreign key has index
                    if not field.db_index and not any(
                        field.name in idx.fields for idx in model._meta.indexes
                    ):
                        missing_indexes.append({
                            'model': model.__name__,
                            'field': field.name,
                            'table': model._meta.db_table,
                            'suggestion': f'Add db_index=True to {field.name} field'
                        })
        
        return missing_indexes
    
    @staticmethod
    def optimize_queries_for_model(model_class):
        """Suggest query optimizations for a specific model"""
        suggestions = []
        
        # Check for select_related opportunities (ForeignKey and OneToOneField)
        foreign_keys = [
            field.name for field in model_class._meta.get_fields()
            if (hasattr(field, 'related_model') and field.related_model and 
                not field.many_to_many and not field.one_to_many)
        ]
        
        if foreign_keys:
            suggestions.append({
                'type': 'select_related',
                'fields': foreign_keys,
                'example': f"{model_class.__name__}.objects.select_related({', '.join(repr(fk) for fk in foreign_keys[:3])})"
            })
        
        # Check for prefetch_related opportunities (reverse ForeignKey and ManyToMany)
        reverse_relations = []
        for field in model_class._meta.get_fields():
            if hasattr(field, 'get_accessor_name'):
                try:
                    if field.one_to_many or field.many_to_many:
                        reverse_relations.append(field.get_accessor_name())
                except AttributeError:
                    # Some fields might not have these attributes
                    continue
        
        if reverse_relations:
            suggestions.append({
                'type': 'prefetch_related',
                'fields': reverse_relations,
                'example': f"{model_class.__name__}.objects.prefetch_related({', '.join(repr(rel) for rel in reverse_relations[:3])})"
            })
        
        return suggestions


def create_performance_indexes():
    """Create performance indexes for common queries"""
    indexes_sql = [
        # Ollama models indexes
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ollama_models_active_task ON ollama_models(is_active, task_type);",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ollama_models_priority_active ON ollama_models(priority, is_active);",
        
        # Ollama processing jobs indexes
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ollama_jobs_status_priority ON ollama_processing_jobs(status, priority);",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ollama_jobs_user_status ON ollama_processing_jobs(created_by_id, status);",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ollama_jobs_model_status ON ollama_processing_jobs(model_id, status);",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ollama_jobs_created_at ON ollama_processing_jobs(created_at);",
        
        # Ollama model usage indexes
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ollama_usage_model_date ON ollama_model_usage(model_id, date);",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ollama_usage_user_date ON ollama_model_usage(user_id, date);",
        
        # Budget system indexes
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_budget_expenses_date ON budget_expense(expense_date);",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_budget_expenses_category ON budget_expense(category_id);",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_budget_plans_date_range ON budget_plan(start_date, end_date);",
        
        # Knowledge management indexes
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_knowledge_docs_category ON knowledge_document(category_id);",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_knowledge_docs_created ON knowledge_document(created_at);",
        
        # Indonesian NLP indexes
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_nlp_jobs_status ON indonesian_nlp_textanalysisjob(status);",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_nlp_jobs_model ON indonesian_nlp_textanalysisjob(model_id);",
        
        # Employee and attendance indexes (if using PostgreSQL)
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_attendance_employee_date ON attendance_attendance(employee_id, attendance_date);",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_attendance_date_range ON attendance_attendance(attendance_date) WHERE attendance_date >= CURRENT_DATE - INTERVAL '30 days';",
    ]
    
    with connection.cursor() as cursor:
        for sql in indexes_sql:
            try:
                if connection.vendor == 'postgresql':
                    cursor.execute(sql)
                elif connection.vendor == 'mysql':
                    # Convert PostgreSQL syntax to MySQL
                    mysql_sql = sql.replace('CONCURRENTLY', '').replace('IF NOT EXISTS', '')
                    cursor.execute(mysql_sql)
                elif connection.vendor == 'sqlite':
                    # SQLite doesn't support CONCURRENTLY or IF NOT EXISTS in same way
                    sqlite_sql = sql.replace('CREATE INDEX CONCURRENTLY IF NOT EXISTS', 'CREATE INDEX IF NOT EXISTS')
                    cursor.execute(sqlite_sql)
                logger.info(f"Created index: {sql}")
            except Exception as e:
                logger.warning(f"Failed to create index: {sql}, Error: {e}")


def analyze_query_performance():
    """Analyze and report query performance"""
    optimizer = DatabaseOptimizer()
    
    print("\n=== Database Performance Analysis ===")
    
    # Analyze slow queries
    print("\n1. Slow Queries:")
    slow_queries = optimizer.analyze_slow_queries()
    for query in slow_queries[:5]:
        print(f"   - Query: {query[0][:100]}...")
        print(f"     Avg Time: {query[1]}ms, Calls: {query[2]}")
    
    # Check table sizes
    print("\n2. Largest Tables:")
    table_sizes = optimizer.get_table_sizes()
    for table in table_sizes[:10]:
        print(f"   - {table[1]}: {table[2] if len(table) > 2 else 'N/A'}")
    
    # Check missing indexes
    print("\n3. Missing Indexes:")
    missing_indexes = optimizer.check_missing_indexes()
    for idx in missing_indexes[:10]:
        print(f"   - {idx['model']}.{idx['field']}: {idx['suggestion']}")
    
    # Model-specific optimizations
    print("\n4. Query Optimization Suggestions:")
    try:
        # Try to import and analyze common models
        model_classes = []
        
        # Try to get models from apps
        try:
            from django.apps import apps
            # Get some common models for analysis
            for app_name in ['budget', 'knowledge', 'indonesian_nlp', 'employee', 'attendance']:
                try:
                    app_models = apps.get_app_config(app_name).get_models()
                    model_classes.extend(list(app_models)[:2])  # Limit to 2 models per app
                except:
                    continue
        except:
            pass
        
        for model in model_classes[:5]:  # Limit to 5 models total
            try:
                suggestions = optimizer.optimize_queries_for_model(model)
                if suggestions:
                    print(f"   {model.__name__}:")
                    for suggestion in suggestions:
                        print(f"     - {suggestion['type']}: {suggestion['example']}")
            except Exception as e:
                print(f"   Error analyzing {model.__name__}: {e}")
                
    except Exception as e:
        print(f"   Error in model optimization analysis: {e}")