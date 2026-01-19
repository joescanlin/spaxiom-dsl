# Edge Security Guide

This guide covers security features for production Spaxiom Edge deployments, including authentication, HTTPS, monitoring, and backup/restore.

## Authentication

### First-Time Setup

On first access, you'll be prompted to create an admin account:

```bash
curl -X POST http://localhost:8080/api/auth/setup \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "your-secure-password"
  }'
```

Or via the web UI at `http://localhost:8080/setup`.

### Logging In

```bash
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "your-password"
  }'
```

**Response:**

```json
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "expires_at": "2024-01-16T10:30:00Z",
  "user": {
    "username": "admin",
    "role": "admin"
  }
}
```

### Using Tokens

Include the token in subsequent requests:

```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8080/api/sensors
```

### Role-Based Access Control

Three roles are available:

| Role | Permissions |
|------|-------------|
| `admin` | Full access: create users, manage system, all operations |
| `operator` | Manage sensors, zones, agents; cannot manage users |
| `viewer` | Read-only access to all resources |

### Managing Users

**Create User (admin only):**

```bash
curl -X POST http://localhost:8080/api/auth/users \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "operator1",
    "password": "secure-password",
    "role": "operator"
  }'
```

**Change Password:**

```bash
curl -X POST http://localhost:8080/api/auth/password \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "current_password": "old-password",
    "new_password": "new-secure-password"
  }'
```

## HTTPS/TLS

### Self-Signed Certificates

Generate certificates for development/testing:

```bash
spax edge start --ssl --ssl-cert ./certs/cert.pem --ssl-key ./certs/key.pem
```

If certificates don't exist, they'll be auto-generated.

### Using Let's Encrypt

For production with a domain name:

1. Install certbot:
   ```bash
   sudo apt install certbot
   ```

2. Obtain certificates:
   ```bash
   sudo certbot certonly --standalone -d edge.yourdomain.com
   ```

3. Start with certificates:
   ```bash
   spax edge start \
     --ssl \
     --ssl-cert /etc/letsencrypt/live/edge.yourdomain.com/fullchain.pem \
     --ssl-key /etc/letsencrypt/live/edge.yourdomain.com/privkey.pem
   ```

### Reverse Proxy (nginx)

For production, use nginx as a reverse proxy:

```nginx
server {
    listen 443 ssl;
    server_name edge.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/edge.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/edge.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Health Monitoring

### System Health Checks

The edge server monitors:

- **Disk usage**: Alert at 90% (warning) or 95% (critical)
- **Memory usage**: Alert at 85% (warning) or 95% (critical)
- **CPU usage**: Alert on sustained high usage (>90% for 3+ checks)

### Viewing Health Status

```bash
curl http://localhost:8080/api/system/health
```

**Response:**

```json
{
  "healthy": true,
  "checks": {
    "disk": {
      "healthy": true,
      "value": 45.2,
      "threshold": 90.0,
      "message": "Disk usage: 45.2%"
    },
    "memory": {
      "healthy": true,
      "value": 62.1,
      "threshold": 85.0,
      "message": "Memory usage: 62.1%"
    },
    "cpu": {
      "healthy": true,
      "value": 12.5,
      "threshold": 90.0,
      "message": "CPU usage: 12.5%"
    }
  },
  "active_alerts": 0,
  "uptime_seconds": 86432
}
```

### Alerts

**List Active Alerts:**

```bash
curl http://localhost:8080/api/system/alerts
```

**Alert Severities:**

- `info`: Informational notice
- `warning`: Potential issue, monitor closely
- `critical`: Immediate attention required

**Acknowledge Alert:**

```bash
curl -X POST http://localhost:8080/api/system/alerts/{alert_id}/acknowledge \
  -H "Authorization: Bearer <token>"
```

## Backup & Restore

### Creating Backups

**Manual Backup:**

```bash
curl -X POST http://localhost:8080/api/system/backup \
  -H "Authorization: Bearer <admin-token>"
```

**Response:**

```json
{
  "path": "/var/lib/spaxiom/backups/backup_20240115_143022_123456.tar.gz",
  "size": 1048576,
  "contents": [
    {"type": "database", "name": "spaxiom.db"},
    {"type": "config", "name": "config"}
  ]
}
```

### Listing Backups

```bash
curl http://localhost:8080/api/system/backups \
  -H "Authorization: Bearer <token>"
```

### Restoring from Backup

```bash
curl -X POST http://localhost:8080/api/system/restore \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "backup_path": "/var/lib/spaxiom/backups/backup_20240115_143022_123456.tar.gz"
  }'
```

!!! warning
    Restore will overwrite current data. A pre-restore backup is automatically created.

### Automated Backups

Configure scheduled backups via environment variables:

```bash
export SPAXIOM_BACKUP_ENABLED=true
export SPAXIOM_BACKUP_INTERVAL_HOURS=24
export SPAXIOM_BACKUP_MAX_COUNT=7
export SPAXIOM_BACKUP_DIR=/var/lib/spaxiom/backups
```

### Backup Contents

Backups include:

- SQLite database (sensors, zones, agents, readings)
- Configuration files
- Optionally: log files

## Remote Access (Optional)

For cloud-based monitoring, configure the remote connector:

```bash
export SPAXIOM_CLOUD_URL=https://cloud.spaxiom.ai
export SPAXIOM_DEVICE_ID=edge-001
export SPAXIOM_API_KEY=your-api-key
export SPAXIOM_API_SECRET=your-api-secret
```

Remote access enables:

- Heartbeat monitoring
- Telemetry upload
- Remote command execution
- Centralized alerting

## Software Updates

### Checking for Updates

```bash
curl http://localhost:8080/api/system/updates/check \
  -H "Authorization: Bearer <admin-token>"
```

### Installing Updates

```bash
curl -X POST http://localhost:8080/api/system/updates/install \
  -H "Authorization: Bearer <admin-token>"
```

### Rollback

If an update causes issues:

```bash
curl -X POST http://localhost:8080/api/system/updates/rollback \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"version": "0.1.0"}'
```

## Security Checklist

Before deploying to production:

- [ ] Change default credentials
- [ ] Enable HTTPS with valid certificates
- [ ] Configure firewall (allow only necessary ports)
- [ ] Set up automated backups
- [ ] Configure log rotation
- [ ] Review user permissions
- [ ] Enable health monitoring alerts
- [ ] Test restore procedure
- [ ] Document recovery procedures

## Firewall Configuration

Recommended iptables rules:

```bash
# Allow SSH
iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# Allow HTTPS
iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# Allow local connections
iptables -A INPUT -i lo -j ACCEPT

# Drop other incoming
iptables -A INPUT -j DROP
```

For Raspberry Pi with ufw:

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 443/tcp
sudo ufw enable
```
