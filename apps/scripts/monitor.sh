#!/bin/bash

# Horilla HR System Monitoring Script
# This script monitors system health and sends alerts
# Designed for continuous monitoring and SLA compliance

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="/var/log/horilla/monitor.log"
STATE_FILE="/tmp/horilla_monitor_state.json"

# Monitoring configuration
CHECK_INTERVAL=${MONITOR_CHECK_INTERVAL:-30}  # seconds
ALERT_COOLDOWN=${MONITOR_ALERT_COOLDOWN:-300}  # seconds
MAX_RESPONSE_TIME=${MONITOR_MAX_RESPONSE_TIME:-2000}  # milliseconds
MIN_DISK_SPACE=${MONITOR_MIN_DISK_SPACE:-10}  # percentage
MAX_CPU_USAGE=${MONITOR_MAX_CPU_USAGE:-80}  # percentage
MAX_MEMORY_USAGE=${MONITOR_MAX_MEMORY_USAGE:-85}  # percentage

# Service endpoints
WEB_ENDPOINT=${WEB_ENDPOINT:-"http://localhost:8000"}
HEALTH_ENDPOINT="$WEB_ENDPOINT/health/"
READY_ENDPOINT="$WEB_ENDPOINT/health/ready/"
METRICS_ENDPOINT="$WEB_ENDPOINT/metrics/"

# Alert configuration
SLACK_WEBHOOK_URL=${SLACK_WEBHOOK_URL:-""}
EMAIL_RECIPIENTS=${EMAIL_RECIPIENTS:-""}
PAGERDUTY_INTEGRATION_KEY=${PAGERDUTY_INTEGRATION_KEY:-""}
DISCORD_WEBHOOK_URL=${DISCORD_WEBHOOK_URL:-""}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create log directory
mkdir -p "$(dirname "$LOG_FILE")"

# Logging function
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        "INFO")
            echo -e "${GREEN}[INFO]${NC} $message"
            ;;
        "WARN")
            echo -e "${YELLOW}[WARN]${NC} $message"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} $message"
            ;;
        "DEBUG")
            echo -e "${BLUE}[DEBUG]${NC} $message"
            ;;
    esac
    
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

# Load monitoring state
load_state() {
    if [ -f "$STATE_FILE" ]; then
        cat "$STATE_FILE"
    else
        echo '{}'
    fi
}

# Save monitoring state
save_state() {
    local state="$1"
    echo "$state" > "$STATE_FILE"
}

# Get current timestamp
get_timestamp() {
    date +%s
}

# Check if alert cooldown has passed
can_send_alert() {
    local alert_type="$1"
    local current_time=$(get_timestamp)
    local state=$(load_state)
    
    local last_alert_time=$(echo "$state" | jq -r ".last_alerts.\"$alert_type\" // 0" 2>/dev/null || echo "0")
    local time_diff=$((current_time - last_alert_time))
    
    [ $time_diff -ge $ALERT_COOLDOWN ]
}

# Update alert timestamp
update_alert_timestamp() {
    local alert_type="$1"
    local current_time=$(get_timestamp)
    local state=$(load_state)
    
    local updated_state=$(echo "$state" | jq ".last_alerts.\"$alert_type\" = $current_time" 2>/dev/null || echo "{\"last_alerts\": {\"$alert_type\": $current_time}}")
    save_state "$updated_state"
}

# Send Slack notification
send_slack_alert() {
    local message="$1"
    local severity="$2"
    
    if [ -z "$SLACK_WEBHOOK_URL" ]; then
        return 0
    fi
    
    local color="good"
    case $severity in
        "critical") color="danger" ;;
        "warning") color="warning" ;;
        "info") color="good" ;;
    esac
    
    local payload=$(cat << EOF
{
    "attachments": [
        {
            "color": "$color",
            "title": "Horilla HR System Alert",
            "text": "$message",
            "footer": "Horilla Monitoring",
            "ts": $(date +%s)
        }
    ]
}
EOF
    )
    
    curl -X POST -H 'Content-type: application/json' \
        --data "$payload" \
        "$SLACK_WEBHOOK_URL" >/dev/null 2>&1 || log "WARN" "Failed to send Slack alert"
}

# Send Discord notification
send_discord_alert() {
    local message="$1"
    local severity="$2"
    
    if [ -z "$DISCORD_WEBHOOK_URL" ]; then
        return 0
    fi
    
    local color=65280  # Green
    case $severity in
        "critical") color=16711680 ;;  # Red
        "warning") color=16776960 ;;   # Yellow
        "info") color=65280 ;;         # Green
    esac
    
    local payload=$(cat << EOF
{
    "embeds": [
        {
            "title": "Horilla HR System Alert",
            "description": "$message",
            "color": $color,
            "footer": {
                "text": "Horilla Monitoring"
            },
            "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%S.000Z)"
        }
    ]
}
EOF
    )
    
    curl -X POST -H 'Content-type: application/json' \
        --data "$payload" \
        "$DISCORD_WEBHOOK_URL" >/dev/null 2>&1 || log "WARN" "Failed to send Discord alert"
}

# Send email notification
send_email_alert() {
    local message="$1"
    local severity="$2"
    
    if [ -z "$EMAIL_RECIPIENTS" ]; then
        return 0
    fi
    
    local subject="Horilla HR System Alert - $severity"
    
    if command -v mail >/dev/null 2>&1; then
        echo "$message" | mail -s "$subject" "$EMAIL_RECIPIENTS" 2>/dev/null || log "WARN" "Failed to send email alert"
    elif command -v sendmail >/dev/null 2>&1; then
        {
            echo "To: $EMAIL_RECIPIENTS"
            echo "Subject: $subject"
            echo
            echo "$message"
        } | sendmail "$EMAIL_RECIPIENTS" 2>/dev/null || log "WARN" "Failed to send email alert"
    else
        log "WARN" "No email command available"
    fi
}

# Send PagerDuty alert
send_pagerduty_alert() {
    local message="$1"
    local severity="$2"
    
    if [ -z "$PAGERDUTY_INTEGRATION_KEY" ]; then
        return 0
    fi
    
    local event_action="trigger"
    case $severity in
        "critical") event_action="trigger" ;;
        "warning") event_action="trigger" ;;
        "info") event_action="resolve" ;;
    esac
    
    local payload=$(cat << EOF
{
    "routing_key": "$PAGERDUTY_INTEGRATION_KEY",
    "event_action": "$event_action",
    "payload": {
        "summary": "$message",
        "source": "horilla-monitoring",
        "severity": "$severity",
        "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%S.000Z)"
    }
}
EOF
    )
    
    curl -X POST -H 'Content-type: application/json' \
        --data "$payload" \
        "https://events.pagerduty.com/v2/enqueue" >/dev/null 2>&1 || log "WARN" "Failed to send PagerDuty alert"
}

# Send alert through all configured channels
send_alert() {
    local message="$1"
    local severity="$2"
    local alert_type="$3"
    
    if ! can_send_alert "$alert_type"; then
        log "DEBUG" "Alert cooldown active for $alert_type, skipping"
        return 0
    fi
    
    log "$severity" "ALERT: $message"
    
    send_slack_alert "$message" "$severity"
    send_discord_alert "$message" "$severity"
    send_email_alert "$message" "$severity"
    
    if [ "$severity" = "critical" ]; then
        send_pagerduty_alert "$message" "$severity"
    fi
    
    update_alert_timestamp "$alert_type"
}

# Check HTTP endpoint
check_http_endpoint() {
    local url="$1"
    local name="$2"
    local expected_status="${3:-200}"
    
    log "DEBUG" "Checking $name endpoint: $url"
    
    local start_time=$(date +%s%3N)
    local response=$(curl -s -w "HTTPSTATUS:%{http_code};TIME:%{time_total}" "$url" 2>/dev/null || echo "HTTPSTATUS:000;TIME:999")
    local end_time=$(date +%s%3N)
    
    local http_status=$(echo "$response" | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
    local response_time_seconds=$(echo "$response" | grep -o "TIME:[0-9.]*" | cut -d: -f2)
    local response_time_ms=$(echo "$response_time_seconds * 1000" | bc -l 2>/dev/null | cut -d. -f1)
    
    # Check HTTP status
    if [ "$http_status" != "$expected_status" ]; then
        send_alert "$name endpoint returned HTTP $http_status (expected $expected_status)" "critical" "http_$name"
        return 1
    fi
    
    # Check response time
    if [ "$response_time_ms" -gt "$MAX_RESPONSE_TIME" ]; then
        send_alert "$name endpoint response time is ${response_time_ms}ms (threshold: ${MAX_RESPONSE_TIME}ms)" "warning" "response_time_$name"
    fi
    
    log "DEBUG" "$name endpoint OK (${response_time_ms}ms)"
    return 0
}

# Check system resources
check_system_resources() {
    log "DEBUG" "Checking system resources"
    
    # Check CPU usage
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1 | cut -d',' -f1 2>/dev/null || echo "0")
    cpu_usage=${cpu_usage%.*}  # Remove decimal part
    
    if [ "$cpu_usage" -gt "$MAX_CPU_USAGE" ]; then
        send_alert "High CPU usage: ${cpu_usage}% (threshold: ${MAX_CPU_USAGE}%)" "warning" "cpu_usage"
    fi
    
    # Check memory usage
    local memory_info=$(free | grep Mem)
    local total_mem=$(echo "$memory_info" | awk '{print $2}')
    local used_mem=$(echo "$memory_info" | awk '{print $3}')
    local memory_usage=$((used_mem * 100 / total_mem))
    
    if [ "$memory_usage" -gt "$MAX_MEMORY_USAGE" ]; then
        send_alert "High memory usage: ${memory_usage}% (threshold: ${MAX_MEMORY_USAGE}%)" "warning" "memory_usage"
    fi
    
    # Check disk space
    local disk_usage=$(df / | tail -1 | awk '{print $5}' | cut -d'%' -f1)
    local disk_free=$((100 - disk_usage))
    
    if [ "$disk_free" -lt "$MIN_DISK_SPACE" ]; then
        send_alert "Low disk space: ${disk_free}% free (threshold: ${MIN_DISK_SPACE}%)" "critical" "disk_space"
    fi
    
    log "DEBUG" "System resources OK (CPU: ${cpu_usage}%, Memory: ${memory_usage}%, Disk: ${disk_usage}% used)"
}

# Check Docker services
check_docker_services() {
    if ! command -v docker >/dev/null 2>&1; then
        log "DEBUG" "Docker not available, skipping Docker service checks"
        return 0
    fi
    
    log "DEBUG" "Checking Docker services"
    
    # Check if Docker daemon is running
    if ! docker info >/dev/null 2>&1; then
        send_alert "Docker daemon is not running" "critical" "docker_daemon"
        return 1
    fi
    
    # Check critical services
    local critical_services=("web" "postgres" "redis")
    
    for service in "${critical_services[@]}"; do
        local container_status=$(docker-compose ps -q "$service" 2>/dev/null | xargs docker inspect --format='{{.State.Status}}' 2>/dev/null || echo "not_found")
        
        if [ "$container_status" != "running" ]; then
            send_alert "Docker service '$service' is not running (status: $container_status)" "critical" "docker_$service"
        else
            log "DEBUG" "Docker service '$service' is running"
        fi
    done
}

# Check database connectivity
check_database() {
    log "DEBUG" "Checking database connectivity"
    
    # Try to connect to PostgreSQL
    if command -v pg_isready >/dev/null 2>&1; then
        local pg_host=${POSTGRES_HOST:-"localhost"}
        local pg_port=${POSTGRES_PORT:-"5432"}
        local pg_user=${POSTGRES_USER:-"horilla_user"}
        
        if ! pg_isready -h "$pg_host" -p "$pg_port" -U "$pg_user" >/dev/null 2>&1; then
            send_alert "PostgreSQL database is not accessible" "critical" "database_postgres"
        else
            log "DEBUG" "PostgreSQL database is accessible"
        fi
    fi
    
    # Try to connect to Redis
    if command -v redis-cli >/dev/null 2>&1; then
        local redis_host=${REDIS_HOST:-"localhost"}
        local redis_port=${REDIS_PORT:-"6379"}
        
        if ! redis-cli -h "$redis_host" -p "$redis_port" ping >/dev/null 2>&1; then
            send_alert "Redis is not accessible" "critical" "database_redis"
        else
            log "DEBUG" "Redis is accessible"
        fi
    fi
}

# Check Celery workers
check_celery_workers() {
    log "DEBUG" "Checking Celery workers"
    
    if command -v celery >/dev/null 2>&1; then
        cd "$PROJECT_DIR"
        
        # Check if any workers are active
        local active_workers=$(celery -A horilla inspect active 2>/dev/null | grep -c "celery@" || echo "0")
        
        if [ "$active_workers" -eq 0 ]; then
            send_alert "No active Celery workers found" "warning" "celery_workers"
        else
            log "DEBUG" "Celery workers are active ($active_workers workers)"
        fi
        
        # Check for failed tasks
        local failed_tasks=$(celery -A horilla inspect reserved 2>/dev/null | grep -c "failed" || echo "0")
        
        if [ "$failed_tasks" -gt 0 ]; then
            send_alert "Celery has $failed_tasks failed tasks" "warning" "celery_failed_tasks"
        fi
    fi
}

# Check external services
check_external_services() {
    log "DEBUG" "Checking external services"
    
    # Check Elasticsearch
    local es_host=${ELASTICSEARCH_HOST:-"localhost"}
    local es_port=${ELASTICSEARCH_PORT:-"9200"}
    check_http_endpoint "http://$es_host:$es_port/_cluster/health" "Elasticsearch"
    
    # Check Ollama
    local ollama_host=${OLLAMA_HOST:-"localhost"}
    local ollama_port=${OLLAMA_PORT:-"11434"}
    check_http_endpoint "http://$ollama_host:$ollama_port/api/tags" "Ollama"
    
    # Check N8N
    local n8n_host=${N8N_HOST:-"localhost"}
    local n8n_port=${N8N_PORT:-"5678"}
    check_http_endpoint "http://$n8n_host:$n8n_port/healthz" "N8N"
    
    # Check ChromaDB
    local chromadb_host=${CHROMADB_HOST:-"localhost"}
    local chromadb_port=${CHROMADB_PORT:-"8000"}
    check_http_endpoint "http://$chromadb_host:$chromadb_port/api/v1/heartbeat" "ChromaDB"
}

# Calculate SLA metrics
calculate_sla_metrics() {
    log "DEBUG" "Calculating SLA metrics"
    
    local state=$(load_state)
    local current_time=$(get_timestamp)
    
    # Get uptime data
    local total_checks=$(echo "$state" | jq -r '.sla.total_checks // 0')
    local successful_checks=$(echo "$state" | jq -r '.sla.successful_checks // 0')
    local last_downtime=$(echo "$state" | jq -r '.sla.last_downtime // 0')
    
    # Increment total checks
    total_checks=$((total_checks + 1))
    
    # Check if main endpoint is up
    if check_http_endpoint "$HEALTH_ENDPOINT" "Health" >/dev/null 2>&1; then
        successful_checks=$((successful_checks + 1))
    else
        last_downtime=$current_time
    fi
    
    # Calculate availability percentage
    local availability=0
    if [ $total_checks -gt 0 ]; then
        availability=$(echo "scale=4; $successful_checks * 100 / $total_checks" | bc -l)
    fi
    
    # Update state
    local updated_state=$(echo "$state" | jq "
        .sla.total_checks = $total_checks |
        .sla.successful_checks = $successful_checks |
        .sla.last_downtime = $last_downtime |
        .sla.availability = $availability
    ")
    save_state "$updated_state"
    
    # Alert if SLA is breached (below 99.99%)
    local sla_threshold=99.99
    if [ "$(echo "$availability < $sla_threshold" | bc -l)" -eq 1 ] && [ $total_checks -gt 100 ]; then
        send_alert "SLA breach: Current availability is ${availability}% (target: ${sla_threshold}%)" "critical" "sla_breach"
    fi
    
    log "DEBUG" "SLA metrics: ${availability}% availability ($successful_checks/$total_checks checks)"
}

# Main monitoring function
run_monitoring_cycle() {
    log "INFO" "Starting monitoring cycle"
    
    # Core application checks
    check_http_endpoint "$HEALTH_ENDPOINT" "Health"
    check_http_endpoint "$READY_ENDPOINT" "Readiness"
    
    # System resource checks
    check_system_resources
    
    # Service checks
    check_docker_services
    check_database
    check_celery_workers
    check_external_services
    
    # SLA calculation
    calculate_sla_metrics
    
    log "INFO" "Monitoring cycle completed"
}

# Show monitoring status
show_status() {
    local state=$(load_state)
    
    echo "Horilla HR System Monitoring Status"
    echo "==================================="
    echo
    
    # SLA metrics
    local availability=$(echo "$state" | jq -r '.sla.availability // "N/A"')
    local total_checks=$(echo "$state" | jq -r '.sla.total_checks // 0')
    local successful_checks=$(echo "$state" | jq -r '.sla.successful_checks // 0')
    
    echo "SLA Metrics:"
    echo "  Availability: ${availability}%"
    echo "  Total Checks: $total_checks"
    echo "  Successful Checks: $successful_checks"
    echo
    
    # Recent alerts
    echo "Recent Alert Timestamps:"
    echo "$state" | jq -r '.last_alerts // {} | to_entries[] | "  \(.key): \(.value)"' 2>/dev/null || echo "  No recent alerts"
    echo
    
    # Current system status
    echo "Current System Status:"
    
    # Check main endpoint
    if curl -f "$HEALTH_ENDPOINT" >/dev/null 2>&1; then
        echo -e "  Main Application: ${GREEN}UP${NC}"
    else
        echo -e "  Main Application: ${RED}DOWN${NC}"
    fi
    
    # Check system resources
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1 | cut -d',' -f1 2>/dev/null || echo "0")
    local memory_usage=$(free | awk 'NR==2{printf "%.1f", $3*100/$2 }')
    local disk_usage=$(df / | tail -1 | awk '{print $5}')
    
    echo "  CPU Usage: ${cpu_usage%.*}%"
    echo "  Memory Usage: ${memory_usage}%"
    echo "  Disk Usage: $disk_usage"
    echo
}

# Show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Monitor Horilla HR System health and send alerts

OPTIONS:
    -d, --daemon           Run as daemon (continuous monitoring)
    -o, --once             Run monitoring cycle once and exit
    -s, --status           Show current monitoring status
    -i, --interval SEC     Set check interval in seconds (default: $CHECK_INTERVAL)
    -v, --verbose          Enable verbose output
    -h, --help             Show this help message

ENVIRONMENT VARIABLES:
    MONITOR_CHECK_INTERVAL      Check interval in seconds (default: 30)
    MONITOR_ALERT_COOLDOWN      Alert cooldown in seconds (default: 300)
    MONITOR_MAX_RESPONSE_TIME   Max response time in ms (default: 2000)
    MONITOR_MIN_DISK_SPACE      Min disk space percentage (default: 10)
    MONITOR_MAX_CPU_USAGE       Max CPU usage percentage (default: 80)
    MONITOR_MAX_MEMORY_USAGE    Max memory usage percentage (default: 85)
    
    WEB_ENDPOINT               Web application endpoint (default: http://localhost:8000)
    
    SLACK_WEBHOOK_URL          Slack webhook URL for alerts
    EMAIL_RECIPIENTS           Email recipients for alerts
    PAGERDUTY_INTEGRATION_KEY  PagerDuty integration key
    DISCORD_WEBHOOK_URL        Discord webhook URL for alerts

Examples:
    $0 -o                      # Run once and exit
    $0 -d                      # Run as daemon
    $0 -s                      # Show status
    $0 -d -i 60 -v             # Run as daemon with 60s interval and verbose output

EOF
}

# Main function
main() {
    local daemon_mode=false
    local run_once=false
    local show_status_only=false
    local verbose=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -d|--daemon)
                daemon_mode=true
                shift
                ;;
            -o|--once)
                run_once=true
                shift
                ;;
            -s|--status)
                show_status_only=true
                shift
                ;;
            -i|--interval)
                CHECK_INTERVAL="$2"
                shift 2
                ;;
            -v|--verbose)
                verbose=true
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            -*)
                echo "Unknown option: $1" >&2
                exit 1
                ;;
            *)
                echo "Unexpected argument: $1" >&2
                exit 1
                ;;
        esac
    done
    
    # Show status and exit
    if [ "$show_status_only" = true ]; then
        show_status
        exit 0
    fi
    
    # Validate check interval
    if ! [[ "$CHECK_INTERVAL" =~ ^[0-9]+$ ]] || [ "$CHECK_INTERVAL" -lt 5 ]; then
        echo "Invalid check interval: $CHECK_INTERVAL (minimum: 5 seconds)" >&2
        exit 1
    fi
    
    log "INFO" "Starting Horilla HR System monitoring"
    log "INFO" "Check interval: ${CHECK_INTERVAL} seconds"
    log "INFO" "Log file: $LOG_FILE"
    
    # Run once and exit
    if [ "$run_once" = true ]; then
        run_monitoring_cycle
        exit 0
    fi
    
    # Daemon mode
    if [ "$daemon_mode" = true ]; then
        log "INFO" "Running in daemon mode (PID: $$)"
        
        # Create PID file
        echo $$ > "/tmp/horilla_monitor.pid"
        
        # Trap signals for graceful shutdown
        trap 'log "INFO" "Monitoring daemon stopped"; rm -f "/tmp/horilla_monitor.pid"; exit 0' INT TERM
        
        # Main monitoring loop
        while true; do
            run_monitoring_cycle
            sleep "$CHECK_INTERVAL"
        done
    else
        # Default: run once
        run_monitoring_cycle
    fi
}

# Check for required tools
if ! command -v jq >/dev/null 2>&1; then
    echo "Error: jq is required but not installed" >&2
    exit 1
fi

if ! command -v bc >/dev/null 2>&1; then
    echo "Error: bc is required but not installed" >&2
    exit 1
fi

# Run main function
main "$@"