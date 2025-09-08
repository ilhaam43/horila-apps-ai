#!/bin/bash

# Horilla HR System Backup Script
# This script creates automated backups of database and important files
# Designed for high availability and disaster recovery

set -euo pipefail

# Configuration
BACKUP_DIR="/backups"
DATE=$(date +"%Y%m%d_%H%M%S")
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}
LOG_FILE="$BACKUP_DIR/backup_$DATE.log"

# Database configuration
PG_HOST=${POSTGRES_HOST:-"postgres_primary"}
PG_DB=${POSTGRES_DB:-"horilla_db"}
PG_USER=${POSTGRES_USER:-"horilla_user"}
PG_PASSWORD=${POSTGRES_PASSWORD:-"horilla_pass"}

# Backup paths
DB_BACKUP_DIR="$BACKUP_DIR/database"
FILES_BACKUP_DIR="$BACKUP_DIR/files"
CONFIG_BACKUP_DIR="$BACKUP_DIR/config"

# Create backup directories
mkdir -p "$DB_BACKUP_DIR" "$FILES_BACKUP_DIR" "$CONFIG_BACKUP_DIR"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    log "ERROR: $1"
    exit 1
}

# Check if required tools are available
check_dependencies() {
    log "Checking dependencies..."
    
    command -v pg_dump >/dev/null 2>&1 || error_exit "pg_dump not found"
    command -v gzip >/dev/null 2>&1 || error_exit "gzip not found"
    command -v tar >/dev/null 2>&1 || error_exit "tar not found"
    
    log "All dependencies are available"
}

# Test database connectivity
test_db_connection() {
    log "Testing database connection..."
    
    export PGPASSWORD="$PG_PASSWORD"
    
    if ! pg_isready -h "$PG_HOST" -U "$PG_USER" -d "$PG_DB" >/dev/null 2>&1; then
        error_exit "Cannot connect to database $PG_DB on $PG_HOST"
    fi
    
    log "Database connection successful"
}

# Create database backup
backup_database() {
    log "Starting database backup..."
    
    local backup_file="$DB_BACKUP_DIR/horilla_db_$DATE.sql"
    local compressed_file="$backup_file.gz"
    
    export PGPASSWORD="$PG_PASSWORD"
    
    # Create database dump
    if pg_dump -h "$PG_HOST" -U "$PG_USER" -d "$PG_DB" \
        --verbose \
        --no-password \
        --format=custom \
        --compress=9 \
        --file="$backup_file.custom" 2>"$LOG_FILE.db_error"; then
        
        log "Database dump created successfully"
        
        # Also create SQL format for easier restoration
        pg_dump -h "$PG_HOST" -U "$PG_USER" -d "$PG_DB" \
            --verbose \
            --no-password \
            --format=plain \
            --file="$backup_file" 2>>"$LOG_FILE.db_error"
        
        # Compress SQL dump
        gzip "$backup_file"
        
        # Get backup size
        local custom_size=$(du -h "$backup_file.custom" | cut -f1)
        local sql_size=$(du -h "$compressed_file" | cut -f1)
        
        log "Database backup completed - Custom format: $custom_size, SQL format: $sql_size"
        
    else
        error_exit "Database backup failed. Check $LOG_FILE.db_error for details"
    fi
}

# Backup application files
backup_files() {
    log "Starting files backup..."
    
    local files_backup="$FILES_BACKUP_DIR/horilla_files_$DATE.tar.gz"
    
    # List of directories to backup
    local dirs_to_backup=(
        "/app/media"
        "/app/static"
        "/app/logs"
    )
    
    # Create tar archive of important files
    local tar_args=()
    for dir in "${dirs_to_backup[@]}"; do
        if [ -d "$dir" ]; then
            tar_args+=("$dir")
        else
            log "Warning: Directory $dir not found, skipping"
        fi
    done
    
    if [ ${#tar_args[@]} -gt 0 ]; then
        if tar -czf "$files_backup" "${tar_args[@]}" 2>"$LOG_FILE.files_error"; then
            local size=$(du -h "$files_backup" | cut -f1)
            log "Files backup completed - Size: $size"
        else
            log "Warning: Files backup failed. Check $LOG_FILE.files_error for details"
        fi
    else
        log "No directories found to backup"
    fi
}

# Backup configuration files
backup_config() {
    log "Starting configuration backup..."
    
    local config_backup="$CONFIG_BACKUP_DIR/horilla_config_$DATE.tar.gz"
    
    # List of configuration files to backup
    local configs_to_backup=(
        "/app/horilla/settings.py"
        "/app/docker-compose.yml"
        "/app/docker-compose.ha.yml"
        "/app/haproxy/haproxy.cfg"
        "/app/prometheus/prometheus.yml"
        "/app/prometheus/alert_rules.yml"
        "/etc/nginx/nginx.conf"
        "/app/.env"
    )
    
    # Create tar archive of configuration files
    local tar_args=()
    for config in "${configs_to_backup[@]}"; do
        if [ -f "$config" ]; then
            tar_args+=("$config")
        else
            log "Warning: Configuration file $config not found, skipping"
        fi
    done
    
    if [ ${#tar_args[@]} -gt 0 ]; then
        if tar -czf "$config_backup" "${tar_args[@]}" 2>"$LOG_FILE.config_error"; then
            local size=$(du -h "$config_backup" | cut -f1)
            log "Configuration backup completed - Size: $size"
        else
            log "Warning: Configuration backup failed. Check $LOG_FILE.config_error for details"
        fi
    else
        log "No configuration files found to backup"
    fi
}

# Create backup manifest
create_manifest() {
    log "Creating backup manifest..."
    
    local manifest_file="$BACKUP_DIR/manifest_$DATE.json"
    
    cat > "$manifest_file" << EOF
{
    "backup_date": "$DATE",
    "backup_timestamp": "$(date -Iseconds)",
    "database": {
        "host": "$PG_HOST",
        "database": "$PG_DB",
        "user": "$PG_USER"
    },
    "files": {
        "database_backup": "$DB_BACKUP_DIR/horilla_db_$DATE.sql.custom",
        "database_sql_backup": "$DB_BACKUP_DIR/horilla_db_$DATE.sql.gz",
        "files_backup": "$FILES_BACKUP_DIR/horilla_files_$DATE.tar.gz",
        "config_backup": "$CONFIG_BACKUP_DIR/horilla_config_$DATE.tar.gz"
    },
    "checksums": {
EOF

    # Add checksums for verification
    for file in "$DB_BACKUP_DIR"/horilla_db_$DATE.* "$FILES_BACKUP_DIR"/horilla_files_$DATE.* "$CONFIG_BACKUP_DIR"/horilla_config_$DATE.*; do
        if [ -f "$file" ]; then
            local checksum=$(sha256sum "$file" | cut -d' ' -f1)
            local filename=$(basename "$file")
            echo "        \"$filename\": \"$checksum\"," >> "$manifest_file"
        fi
    done
    
    # Remove trailing comma and close JSON
    sed -i '$ s/,$//' "$manifest_file"
    echo "    }" >> "$manifest_file"
    echo "}" >> "$manifest_file"
    
    log "Backup manifest created: $manifest_file"
}

# Clean old backups
cleanup_old_backups() {
    log "Cleaning up backups older than $RETENTION_DAYS days..."
    
    local deleted_count=0
    
    # Clean database backups
    while IFS= read -r -d '' file; do
        rm "$file"
        ((deleted_count++))
    done < <(find "$DB_BACKUP_DIR" -name "horilla_db_*.sql*" -mtime +$RETENTION_DAYS -print0 2>/dev/null)
    
    # Clean file backups
    while IFS= read -r -d '' file; do
        rm "$file"
        ((deleted_count++))
    done < <(find "$FILES_BACKUP_DIR" -name "horilla_files_*.tar.gz" -mtime +$RETENTION_DAYS -print0 2>/dev/null)
    
    # Clean config backups
    while IFS= read -r -d '' file; do
        rm "$file"
        ((deleted_count++))
    done < <(find "$CONFIG_BACKUP_DIR" -name "horilla_config_*.tar.gz" -mtime +$RETENTION_DAYS -print0 2>/dev/null)
    
    # Clean manifests
    while IFS= read -r -d '' file; do
        rm "$file"
        ((deleted_count++))
    done < <(find "$BACKUP_DIR" -name "manifest_*.json" -mtime +$RETENTION_DAYS -print0 2>/dev/null)
    
    # Clean old logs
    while IFS= read -r -d '' file; do
        rm "$file"
        ((deleted_count++))
    done < <(find "$BACKUP_DIR" -name "backup_*.log*" -mtime +$RETENTION_DAYS -print0 2>/dev/null)
    
    log "Cleanup completed - Removed $deleted_count old files"
}

# Verify backup integrity
verify_backups() {
    log "Verifying backup integrity..."
    
    local verification_failed=false
    
    # Verify database backup
    local db_backup="$DB_BACKUP_DIR/horilla_db_$DATE.sql.custom"
    if [ -f "$db_backup" ]; then
        if pg_restore --list "$db_backup" >/dev/null 2>&1; then
            log "Database backup verification: PASSED"
        else
            log "Database backup verification: FAILED"
            verification_failed=true
        fi
    fi
    
    # Verify file archives
    for archive in "$FILES_BACKUP_DIR"/horilla_files_$DATE.tar.gz "$CONFIG_BACKUP_DIR"/horilla_config_$DATE.tar.gz; do
        if [ -f "$archive" ]; then
            if tar -tzf "$archive" >/dev/null 2>&1; then
                log "Archive $(basename "$archive") verification: PASSED"
            else
                log "Archive $(basename "$archive") verification: FAILED"
                verification_failed=true
            fi
        fi
    done
    
    if [ "$verification_failed" = true ]; then
        error_exit "Backup verification failed"
    else
        log "All backup verifications passed"
    fi
}

# Send notification (placeholder for integration with monitoring systems)
send_notification() {
    local status=$1
    local message=$2
    
    log "Notification: $status - $message"
    
    # Here you can add integration with:
    # - Slack webhook
    # - Email notification
    # - PagerDuty
    # - Discord webhook
    # - etc.
    
    # Example Slack notification (uncomment and configure):
    # if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
    #     curl -X POST -H 'Content-type: application/json' \
    #         --data "{\"text\":\"Horilla Backup $status: $message\"}" \
    #         "$SLACK_WEBHOOK_URL"
    # fi
}

# Main backup function
main() {
    log "Starting Horilla HR System backup process..."
    
    local start_time=$(date +%s)
    
    # Run backup steps
    check_dependencies
    test_db_connection
    backup_database
    backup_files
    backup_config
    create_manifest
    verify_backups
    cleanup_old_backups
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log "Backup process completed successfully in ${duration} seconds"
    
    # Calculate total backup size
    local total_size=$(du -sh "$BACKUP_DIR" | cut -f1)
    log "Total backup size: $total_size"
    
    send_notification "SUCCESS" "Backup completed in ${duration}s, total size: $total_size"
}

# Error handling
trap 'send_notification "FAILED" "Backup process failed. Check logs for details."' ERR

# Run main function
main "$@"