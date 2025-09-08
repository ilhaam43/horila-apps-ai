#!/bin/bash

# Horilla HR System Restore Script
# This script restores database and files from backup
# Designed for disaster recovery and system restoration

set -euo pipefail

# Configuration
BACKUP_DIR="/backups"
RESTORE_LOG="/tmp/restore_$(date +"%Y%m%d_%H%M%S").log"

# Database configuration
PG_HOST=${POSTGRES_HOST:-"postgres_primary"}
PG_DB=${POSTGRES_DB:-"horilla_db"}
PG_USER=${POSTGRES_USER:-"horilla_user"}
PG_PASSWORD=${POSTGRES_PASSWORD:-"horilla_pass"}

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$RESTORE_LOG"
}

# Error handling
error_exit() {
    log "ERROR: $1"
    exit 1
}

# Show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS] BACKUP_DATE

Restore Horilla HR System from backup

OPTIONS:
    -d, --database-only     Restore database only
    -f, --files-only        Restore files only
    -c, --config-only       Restore configuration only
    -a, --all              Restore everything (default)
    -l, --list             List available backups
    -v, --verify           Verify backup before restore
    -h, --help             Show this help message

BACKUP_DATE:
    Date in format YYYYMMDD_HHMMSS (e.g., 20240115_143022)
    Use -l option to see available backups

Examples:
    $0 -l                           # List available backups
    $0 20240115_143022              # Restore everything from backup
    $0 -d 20240115_143022           # Restore database only
    $0 -f 20240115_143022           # Restore files only
    $0 -v 20240115_143022           # Verify backup before restore

EOF
}

# List available backups
list_backups() {
    log "Available backups:"
    
    if [ ! -d "$BACKUP_DIR" ]; then
        log "No backup directory found at $BACKUP_DIR"
        return 1
    fi
    
    local manifests=()
    while IFS= read -r -d '' manifest; do
        manifests+=("$manifest")
    done < <(find "$BACKUP_DIR" -name "manifest_*.json" -print0 2>/dev/null | sort -z)
    
    if [ ${#manifests[@]} -eq 0 ]; then
        log "No backups found"
        return 1
    fi
    
    printf "\n%-20s %-20s %-15s %-15s %-15s\n" "DATE" "TIMESTAMP" "DATABASE" "FILES" "CONFIG"
    printf "%-20s %-20s %-15s %-15s %-15s\n" "----" "---------" "--------" "-----" "------"
    
    for manifest in "${manifests[@]}"; do
        local backup_date=$(basename "$manifest" .json | sed 's/manifest_//')
        local timestamp=$(jq -r '.backup_timestamp // "N/A"' "$manifest" 2>/dev/null || echo "N/A")
        
        # Check if backup files exist
        local db_exists="❌"
        local files_exists="❌"
        local config_exists="❌"
        
        if [ -f "$BACKUP_DIR/database/horilla_db_$backup_date.sql.custom" ]; then
            db_exists="✅"
        fi
        
        if [ -f "$BACKUP_DIR/files/horilla_files_$backup_date.tar.gz" ]; then
            files_exists="✅"
        fi
        
        if [ -f "$BACKUP_DIR/config/horilla_config_$backup_date.tar.gz" ]; then
            config_exists="✅"
        fi
        
        printf "%-20s %-20s %-15s %-15s %-15s\n" "$backup_date" "${timestamp:0:19}" "$db_exists" "$files_exists" "$config_exists"
    done
    
    echo
}

# Verify backup integrity
verify_backup() {
    local backup_date=$1
    
    log "Verifying backup integrity for $backup_date..."
    
    local manifest_file="$BACKUP_DIR/manifest_$backup_date.json"
    
    if [ ! -f "$manifest_file" ]; then
        error_exit "Manifest file not found: $manifest_file"
    fi
    
    # Verify checksums
    local verification_failed=false
    
    while IFS= read -r line; do
        local filename=$(echo "$line" | jq -r '.key')
        local expected_checksum=$(echo "$line" | jq -r '.value')
        
        # Find the actual file
        local file_path=""
        for dir in "database" "files" "config"; do
            local candidate="$BACKUP_DIR/$dir/$filename"
            if [ -f "$candidate" ]; then
                file_path="$candidate"
                break
            fi
        done
        
        if [ -z "$file_path" ]; then
            log "Warning: File not found: $filename"
            verification_failed=true
            continue
        fi
        
        local actual_checksum=$(sha256sum "$file_path" | cut -d' ' -f1)
        
        if [ "$actual_checksum" = "$expected_checksum" ]; then
            log "✅ $filename: checksum verified"
        else
            log "❌ $filename: checksum mismatch"
            log "   Expected: $expected_checksum"
            log "   Actual:   $actual_checksum"
            verification_failed=true
        fi
        
    done < <(jq -r '.checksums | to_entries[] | @json' "$manifest_file" 2>/dev/null)
    
    if [ "$verification_failed" = true ]; then
        error_exit "Backup verification failed"
    else
        log "✅ Backup verification passed"
    fi
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if required tools are available
    command -v pg_restore >/dev/null 2>&1 || error_exit "pg_restore not found"
    command -v psql >/dev/null 2>&1 || error_exit "psql not found"
    command -v tar >/dev/null 2>&1 || error_exit "tar not found"
    command -v jq >/dev/null 2>&1 || error_exit "jq not found (required for manifest parsing)"
    
    # Check backup directory
    if [ ! -d "$BACKUP_DIR" ]; then
        error_exit "Backup directory not found: $BACKUP_DIR"
    fi
    
    log "Prerequisites check passed"
}

# Test database connectivity
test_db_connection() {
    log "Testing database connection..."
    
    export PGPASSWORD="$PG_PASSWORD"
    
    if ! pg_isready -h "$PG_HOST" -U "$PG_USER" >/dev/null 2>&1; then
        error_exit "Cannot connect to database server $PG_HOST"
    fi
    
    log "Database connection successful"
}

# Create database if it doesn't exist
ensure_database_exists() {
    log "Ensuring database exists..."
    
    export PGPASSWORD="$PG_PASSWORD"
    
    # Check if database exists
    if psql -h "$PG_HOST" -U "$PG_USER" -lqt | cut -d \| -f 1 | grep -qw "$PG_DB"; then
        log "Database $PG_DB already exists"
    else
        log "Creating database $PG_DB..."
        createdb -h "$PG_HOST" -U "$PG_USER" "$PG_DB" || error_exit "Failed to create database"
        log "Database $PG_DB created successfully"
    fi
}

# Restore database
restore_database() {
    local backup_date=$1
    
    log "Starting database restore for $backup_date..."
    
    local db_backup="$BACKUP_DIR/database/horilla_db_$backup_date.sql.custom"
    
    if [ ! -f "$db_backup" ]; then
        error_exit "Database backup not found: $db_backup"
    fi
    
    export PGPASSWORD="$PG_PASSWORD"
    
    # Verify backup file
    if ! pg_restore --list "$db_backup" >/dev/null 2>&1; then
        error_exit "Invalid database backup file: $db_backup"
    fi
    
    # Ensure database exists
    ensure_database_exists
    
    # Drop existing connections to the database
    log "Terminating existing connections to $PG_DB..."
    psql -h "$PG_HOST" -U "$PG_USER" -d postgres -c "
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = '$PG_DB' AND pid <> pg_backend_pid();
    " >/dev/null 2>&1 || true
    
    # Clean existing data
    log "Cleaning existing database data..."
    psql -h "$PG_HOST" -U "$PG_USER" -d "$PG_DB" -c "
        DROP SCHEMA public CASCADE;
        CREATE SCHEMA public;
        GRANT ALL ON SCHEMA public TO $PG_USER;
        GRANT ALL ON SCHEMA public TO public;
    " 2>"$RESTORE_LOG.db_error" || error_exit "Failed to clean database"
    
    # Restore database
    log "Restoring database from $db_backup..."
    if pg_restore -h "$PG_HOST" -U "$PG_USER" -d "$PG_DB" \
        --verbose \
        --clean \
        --no-owner \
        --no-privileges \
        "$db_backup" 2>>"$RESTORE_LOG.db_error"; then
        
        log "✅ Database restore completed successfully"
        
        # Verify restore by checking table count
        local table_count=$(psql -h "$PG_HOST" -U "$PG_USER" -d "$PG_DB" -t -c "
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = 'public';
        " 2>/dev/null | tr -d ' ')
        
        log "Restored database contains $table_count tables"
        
    else
        error_exit "Database restore failed. Check $RESTORE_LOG.db_error for details"
    fi
}

# Restore files
restore_files() {
    local backup_date=$1
    
    log "Starting files restore for $backup_date..."
    
    local files_backup="$BACKUP_DIR/files/horilla_files_$backup_date.tar.gz"
    
    if [ ! -f "$files_backup" ]; then
        error_exit "Files backup not found: $files_backup"
    fi
    
    # Verify archive
    if ! tar -tzf "$files_backup" >/dev/null 2>&1; then
        error_exit "Invalid files backup archive: $files_backup"
    fi
    
    # Create backup of existing files
    local existing_backup="/tmp/horilla_files_backup_$(date +%s).tar.gz"
    log "Creating backup of existing files to $existing_backup..."
    
    tar -czf "$existing_backup" \
        /app/media \
        /app/static \
        /app/logs 2>/dev/null || log "Warning: Some directories may not exist"
    
    # Restore files
    log "Extracting files from $files_backup..."
    if tar -xzf "$files_backup" -C / 2>"$RESTORE_LOG.files_error"; then
        log "✅ Files restore completed successfully"
        
        # Set proper permissions
        log "Setting file permissions..."
        chown -R www-data:www-data /app/media /app/static 2>/dev/null || true
        chmod -R 755 /app/media /app/static 2>/dev/null || true
        
    else
        log "Files restore failed. Restoring from backup..."
        tar -xzf "$existing_backup" -C / 2>/dev/null || true
        error_exit "Files restore failed. Check $RESTORE_LOG.files_error for details"
    fi
}

# Restore configuration
restore_config() {
    local backup_date=$1
    
    log "Starting configuration restore for $backup_date..."
    
    local config_backup="$BACKUP_DIR/config/horilla_config_$backup_date.tar.gz"
    
    if [ ! -f "$config_backup" ]; then
        error_exit "Configuration backup not found: $config_backup"
    fi
    
    # Verify archive
    if ! tar -tzf "$config_backup" >/dev/null 2>&1; then
        error_exit "Invalid configuration backup archive: $config_backup"
    fi
    
    # Create backup of existing configuration
    local existing_config_backup="/tmp/horilla_config_backup_$(date +%s).tar.gz"
    log "Creating backup of existing configuration to $existing_config_backup..."
    
    tar -czf "$existing_config_backup" \
        /app/horilla/settings.py \
        /app/docker-compose.yml \
        /app/docker-compose.ha.yml \
        /app/haproxy/haproxy.cfg \
        /app/prometheus/prometheus.yml \
        /app/prometheus/alert_rules.yml \
        /etc/nginx/nginx.conf \
        /app/.env 2>/dev/null || log "Warning: Some configuration files may not exist"
    
    # Restore configuration
    log "Extracting configuration from $config_backup..."
    if tar -xzf "$config_backup" -C / 2>"$RESTORE_LOG.config_error"; then
        log "✅ Configuration restore completed successfully"
        
        log "⚠️  Please review restored configuration files and restart services as needed"
        
    else
        log "Configuration restore failed. Restoring from backup..."
        tar -xzf "$existing_config_backup" -C / 2>/dev/null || true
        error_exit "Configuration restore failed. Check $RESTORE_LOG.config_error for details"
    fi
}

# Post-restore tasks
post_restore_tasks() {
    log "Running post-restore tasks..."
    
    # Collect static files (if Django)
    if [ -f "/app/manage.py" ]; then
        log "Collecting static files..."
        cd /app
        python manage.py collectstatic --noinput 2>/dev/null || log "Warning: Failed to collect static files"
    fi
    
    # Clear cache
    log "Clearing application cache..."
    if command -v redis-cli >/dev/null 2>&1; then
        redis-cli FLUSHALL 2>/dev/null || log "Warning: Failed to clear Redis cache"
    fi
    
    log "Post-restore tasks completed"
}

# Main restore function
main() {
    local restore_database=false
    local restore_files=false
    local restore_config=false
    local verify_only=false
    local list_only=false
    local backup_date=""
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -d|--database-only)
                restore_database=true
                shift
                ;;
            -f|--files-only)
                restore_files=true
                shift
                ;;
            -c|--config-only)
                restore_config=true
                shift
                ;;
            -a|--all)
                restore_database=true
                restore_files=true
                restore_config=true
                shift
                ;;
            -l|--list)
                list_only=true
                shift
                ;;
            -v|--verify)
                verify_only=true
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            -*)
                error_exit "Unknown option: $1"
                ;;
            *)
                backup_date="$1"
                shift
                ;;
        esac
    done
    
    # Handle list option
    if [ "$list_only" = true ]; then
        check_prerequisites
        list_backups
        exit 0
    fi
    
    # Validate backup date
    if [ -z "$backup_date" ]; then
        error_exit "Backup date is required. Use -l to list available backups."
    fi
    
    # Validate backup date format
    if ! [[ "$backup_date" =~ ^[0-9]{8}_[0-9]{6}$ ]]; then
        error_exit "Invalid backup date format. Expected: YYYYMMDD_HHMMSS"
    fi
    
    # Set default restore options if none specified
    if [ "$restore_database" = false ] && [ "$restore_files" = false ] && [ "$restore_config" = false ]; then
        restore_database=true
        restore_files=true
        restore_config=true
    fi
    
    log "Starting Horilla HR System restore process..."
    log "Backup date: $backup_date"
    log "Restore options: Database=$restore_database, Files=$restore_files, Config=$restore_config"
    
    local start_time=$(date +%s)
    
    # Run restore steps
    check_prerequisites
    verify_backup "$backup_date"
    
    if [ "$verify_only" = true ]; then
        log "Verification completed successfully"
        exit 0
    fi
    
    if [ "$restore_database" = true ]; then
        test_db_connection
        restore_database "$backup_date"
    fi
    
    if [ "$restore_files" = true ]; then
        restore_files "$backup_date"
    fi
    
    if [ "$restore_config" = true ]; then
        restore_config "$backup_date"
    fi
    
    post_restore_tasks
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log "✅ Restore process completed successfully in ${duration} seconds"
    log "Restore log saved to: $RESTORE_LOG"
    
    echo
    log "⚠️  IMPORTANT POST-RESTORE STEPS:"
    log "1. Restart all application services"
    log "2. Verify application functionality"
    log "3. Check logs for any errors"
    log "4. Update any environment-specific configurations"
    log "5. Test critical business processes"
}

# Run main function
main "$@"