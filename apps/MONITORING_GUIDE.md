# Horilla HR System Monitoring & Redundancy Guide

This guide provides comprehensive documentation for the monitoring and redundancy system implemented in Horilla HR to achieve 99.99% SLA uptime.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Monitoring Components](#monitoring-components)
4. [Redundancy & High Availability](#redundancy--high-availability)
5. [Installation & Setup](#installation--setup)
6. [Configuration](#configuration)
7. [Alerting](#alerting)
8. [Backup & Recovery](#backup--recovery)
9. [Troubleshooting](#troubleshooting)
10. [SLA Monitoring](#sla-monitoring)

## Overview

The Horilla HR monitoring and redundancy system provides:

- **Real-time monitoring** of all system components
- **Automated alerting** through multiple channels (Slack, Discord, Email, PagerDuty)
- **High availability** with load balancing and service redundancy
- **Automated backup** and recovery procedures
- **SLA tracking** with 99.99% uptime target
- **Performance metrics** and health checks
- **Proactive issue detection** and resolution

## Architecture

### Monitoring Stack

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Prometheus    │    │     Grafana     │    │   AlertManager  │
│   (Metrics)     │◄──►│  (Dashboards)   │◄──►│   (Alerting)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         ▲                        ▲                        │
         │                        │                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Node Exporter  │    │ Custom Monitors │    │ Alert Channels  │
│ (System Metrics)│    │ (App Health)    │    │ Slack/Email/etc │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### High Availability Architecture

```
                    ┌─────────────────┐
                    │     HAProxy     │
                    │ Load Balancer   │
                    └─────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼───────┐   ┌───────▼───────┐   ┌───────▼───────┐
│  Django App   │   │  Django App   │   │  Django App   │
│   Instance 1  │   │   Instance 2  │   │   Instance 3  │
└───────────────┘   └───────────────┘   └───────────────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼───────┐   ┌───────▼───────┐   ┌───────▼───────┐
│ PostgreSQL    │   │     Redis     │   │ Elasticsearch │
│   Primary     │   │   Primary     │   │   Cluster     │
│   + Replica   │   │   + Replica   │   │               │
└───────────────┘   └───────────────┘   └───────────────┘
```

## Monitoring Components

### 1. Health Check Endpoints

The system provides several health check endpoints:

- **`/health/`** - Basic health check
- **`/health/ready/`** - Readiness check (database, cache, migrations)
- **`/health/live/`** - Liveness check (application status)
- **`/health/detailed/`** - Detailed health metrics
- **`/metrics/`** - Prometheus-compatible metrics

### 2. System Monitors

#### Application Monitor (`monitor.sh`)

```bash
# Run monitoring cycle once
./scripts/monitor.sh --once

# Run as daemon
./scripts/monitor.sh --daemon

# Show current status
./scripts/monitor.sh --status
```

#### Monitored Components

- **HTTP Endpoints** - Response time and availability
- **System Resources** - CPU, memory, disk usage
- **Database** - PostgreSQL and Redis connectivity
- **Services** - Docker containers, Celery workers
- **External Services** - Elasticsearch, Ollama, N8N, ChromaDB

### 3. Prometheus Exporters

- **Node Exporter** (`:9100`) - System metrics
- **PostgreSQL Exporter** (`:9187`) - Database metrics
- **Redis Exporter** (`:9121`) - Cache metrics
- **Custom Django Exporter** (`:8000/metrics`) - Application metrics

### 4. Grafana Dashboards

Pre-configured dashboards for:
- System overview
- Application performance
- Database metrics
- Infrastructure health

## Redundancy & High Availability

### 1. Load Balancing

**HAProxy Configuration:**
- 3 Django application instances
- Health check integration
- Automatic failover
- Session persistence

### 2. Database Redundancy

**PostgreSQL:**
- Primary-replica setup
- Automatic failover
- Continuous replication
- Point-in-time recovery

**Redis:**
- Master-slave configuration
- Sentinel for automatic failover
- Data persistence

### 3. Service Redundancy

- **Multiple Celery workers**
- **Elasticsearch cluster**
- **Distributed file storage**
- **Container orchestration**

## Installation & Setup

### 1. Quick Setup

```bash
# Full monitoring setup (requires root)
sudo ./scripts/setup_monitoring.sh --full-setup

# Check status
./scripts/setup_monitoring.sh --status
```

### 2. Manual Setup

```bash
# Install dependencies
sudo ./scripts/setup_monitoring.sh --install-deps

# Setup logging
sudo ./scripts/setup_monitoring.sh --setup-logging

# Setup systemd services
sudo ./scripts/setup_monitoring.sh --setup-systemd

# Setup Prometheus exporters
sudo ./scripts/setup_monitoring.sh --setup-exporters

# Setup Django monitoring
./scripts/setup_monitoring.sh --setup-django

# Setup alerting
./scripts/setup_monitoring.sh --setup-alerting

# Start services
sudo ./scripts/setup_monitoring.sh --start-services
```

### 3. High Availability Deployment

```bash
# Deploy with Docker Compose HA
./scripts/deploy.sh --type ha

# Deploy with Kubernetes
./scripts/deploy.sh --type k8s
```

## Configuration

### 1. Monitoring Configuration

**Environment Variables:**

```bash
# Monitoring intervals
MONITOR_CHECK_INTERVAL=30          # seconds
MONITOR_ALERT_COOLDOWN=300         # seconds
MONITOR_MAX_RESPONSE_TIME=2000     # milliseconds

# Resource thresholds
MONITOR_MIN_DISK_SPACE=10          # percentage
MONITOR_MAX_CPU_USAGE=80           # percentage
MONITOR_MAX_MEMORY_USAGE=85        # percentage

# Service endpoints
WEB_ENDPOINT=http://localhost:8000
POSTGRES_HOST=localhost
REDIS_HOST=localhost
ELASTICSEARCH_HOST=localhost
```

### 2. Alert Configuration

Copy and configure the alert settings:

```bash
cp config/alerting/config.env.template config/alerting/config.env
```

Edit `config/alerting/config.env`:

```bash
# Slack Integration
SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"

# Email Alerts
EMAIL_RECIPIENTS="admin@yourcompany.com,ops@yourcompany.com"

# Discord Integration
DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/YOUR/DISCORD/WEBHOOK"

# PagerDuty (for critical alerts)
PAGERDUTY_INTEGRATION_KEY="your_pagerduty_integration_key"
```

### 3. Prometheus Configuration

The system includes pre-configured Prometheus settings in `prometheus/prometheus.yml`:

- Scrape intervals
- Target endpoints
- Alert rules
- Recording rules

## Alerting

### 1. Alert Channels

- **Slack** - Real-time team notifications
- **Discord** - Community/team chat integration
- **Email** - Traditional email alerts
- **PagerDuty** - Critical incident management
- **Microsoft Teams** - Enterprise collaboration

### 2. Alert Types

#### Critical Alerts
- Application down
- Database connectivity lost
- High error rates
- SLA breach
- Disk space critical

#### Warning Alerts
- High resource usage
- Slow response times
- Failed background tasks
- Service degradation

#### Info Alerts
- Service recovery
- Maintenance notifications
- Backup completion

### 3. Alert Testing

```bash
# Test all configured alert channels
./scripts/test_alerts.sh
```

### 4. Alert Cooldown

Alerts have a configurable cooldown period (default: 5 minutes) to prevent spam.

## Backup & Recovery

### 1. Automated Backups

**Daily Backups Include:**
- PostgreSQL database (custom format + SQL)
- Application files (media, static, logs)
- Configuration files
- Docker volumes

**Backup Schedule:**
```bash
# Manual backup
./scripts/backup.sh

# Automated daily backup (systemd timer)
sudo systemctl enable horilla-backup.timer
sudo systemctl start horilla-backup.timer
```

### 2. Backup Verification

```bash
# Verify backup integrity
./scripts/backup.sh --verify

# List available backups
./scripts/restore.sh --list
```

### 3. Recovery Procedures

```bash
# Full system restore
./scripts/restore.sh --backup-id BACKUP_ID

# Database only restore
./scripts/restore.sh --backup-id BACKUP_ID --database-only

# Files only restore
./scripts/restore.sh --backup-id BACKUP_ID --files-only
```

### 4. Disaster Recovery

1. **Identify the issue** using monitoring dashboards
2. **Check backup availability** and integrity
3. **Stop affected services** if necessary
4. **Restore from backup** using appropriate restore script
5. **Verify system functionality** using health checks
6. **Update monitoring** and alert stakeholders

## Troubleshooting

### 1. Common Issues

#### Monitoring Service Not Starting

```bash
# Check service status
sudo systemctl status horilla-monitor

# Check logs
sudo journalctl -u horilla-monitor -f

# Restart service
sudo systemctl restart horilla-monitor
```

#### High Resource Usage Alerts

```bash
# Check system resources
top
htop
iotop

# Check disk usage
df -h
du -sh /var/log/horilla/*

# Clean up logs if needed
sudo logrotate -f /etc/logrotate.d/horilla
```

#### Database Connection Issues

```bash
# Test PostgreSQL connection
pg_isready -h localhost -p 5432 -U horilla_user

# Test Redis connection
redis-cli ping

# Check database logs
sudo tail -f /var/log/postgresql/postgresql-*.log
```

### 2. Log Locations

- **Application logs:** `/var/log/horilla/`
- **Monitoring logs:** `/var/log/horilla/monitoring/`
- **Backup logs:** `/var/log/horilla/backup/`
- **System logs:** `/var/log/syslog`
- **Service logs:** `journalctl -u service-name`

### 3. Debug Mode

```bash
# Run monitoring with verbose output
./scripts/monitor.sh --once --verbose

# Check monitoring state
cat /tmp/horilla_monitor_state.json | jq .
```

## SLA Monitoring

### 1. SLA Targets

- **Availability:** 99.99% (52.56 minutes downtime/year)
- **Response Time:** < 2 seconds (95th percentile)
- **Error Rate:** < 0.1%
- **Recovery Time:** < 5 minutes

### 2. SLA Calculation

The monitoring system automatically calculates SLA metrics:

```bash
# View current SLA status
./scripts/monitor.sh --status

# SLA metrics are stored in monitoring state
cat /tmp/horilla_monitor_state.json | jq .sla
```

### 3. SLA Reporting

**Monthly SLA Report includes:**
- Uptime percentage
- Downtime incidents
- Performance metrics
- Alert summary
- Improvement recommendations

### 4. SLA Breach Handling

1. **Immediate notification** to all stakeholders
2. **Incident response** team activation
3. **Root cause analysis** and documentation
4. **Corrective actions** implementation
5. **Post-incident review** and process improvement

## Monitoring Dashboard

### 1. Web Dashboard

Access the monitoring dashboard at: `http://localhost:8080/`

**Features:**
- Real-time system status
- Resource utilization graphs
- Service health indicators
- Alert history
- Performance metrics

### 2. Grafana Dashboards

Access Grafana at: `http://localhost:3000/`

**Pre-configured dashboards:**
- System Overview
- Application Performance
- Database Metrics
- Infrastructure Health
- SLA Tracking

### 3. Prometheus Metrics

Access Prometheus at: `http://localhost:9090/`

**Available metrics:**
- System metrics (CPU, memory, disk, network)
- Application metrics (requests, errors, response times)
- Database metrics (connections, queries, performance)
- Custom business metrics

## Best Practices

### 1. Monitoring

- **Monitor everything** that can affect user experience
- **Set appropriate thresholds** based on historical data
- **Use multiple alert channels** for redundancy
- **Regularly test** monitoring and alerting systems
- **Document** all monitoring procedures

### 2. High Availability

- **Design for failure** at every level
- **Implement graceful degradation** when possible
- **Use health checks** for all services
- **Automate failover** procedures
- **Test disaster recovery** regularly

### 3. Performance

- **Optimize database queries** and indexes
- **Use caching** strategically
- **Monitor and tune** system resources
- **Implement rate limiting** for API endpoints
- **Use CDN** for static assets

### 4. Security

- **Secure monitoring endpoints** with authentication
- **Encrypt sensitive data** in transit and at rest
- **Regularly update** all system components
- **Monitor for security** events and anomalies
- **Implement access controls** for monitoring systems

## Maintenance

### 1. Regular Tasks

**Daily:**
- Check monitoring dashboard
- Review alert logs
- Verify backup completion

**Weekly:**
- Review performance trends
- Update system packages
- Test alert channels

**Monthly:**
- Generate SLA reports
- Review and tune thresholds
- Test disaster recovery procedures
- Update documentation

### 2. System Updates

```bash
# Update monitoring components
sudo ./scripts/setup_monitoring.sh --install-deps

# Restart monitoring services
sudo systemctl restart horilla-monitor
sudo systemctl restart node_exporter
```

### 3. Capacity Planning

- Monitor resource trends
- Plan for growth
- Scale infrastructure proactively
- Optimize resource usage

## Support

For issues with the monitoring system:

1. **Check this documentation** first
2. **Review system logs** for error messages
3. **Test individual components** to isolate issues
4. **Contact the development team** with detailed information

## Conclusion

This monitoring and redundancy system provides comprehensive coverage for achieving 99.99% SLA uptime. Regular maintenance, proper configuration, and proactive monitoring are key to maintaining high availability and performance.

For the latest updates and additional resources, refer to the project repository and documentation.