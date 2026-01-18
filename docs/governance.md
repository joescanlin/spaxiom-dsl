# Data Governance

The Governance module provides enforceable data governance primitives for Spaxiom applications, including data retention policies, consent management, authorization (RBAC/ABAC), and audit logging.

## Overview

The governance module includes four main components:

1. **RetentionPolicy** - Bounded storage with TTL-based cleanup
2. **ConsentManager** - Zone and entity opt-out controls
3. **Authorizer** - Role-based (RBAC) and attribute-based (ABAC) access control
4. **AuditLogger** - Structured, append-only event logging

## Retention Policy

Control how long data is retained in history buffers and temporal windows.

### Basic Usage

```python
from spaxiom.governance import RetentionPolicy

# Create a retention policy
policy = RetentionPolicy(
    default_days=30,         # Default retention: 30 days
    raw_events_days=7,       # Raw sensor data: 7 days
    exceptions=["SafetyIncident"],  # Keep safety incidents forever
    max_entries=10000        # Maximum 10,000 entries per buffer
)

# Check if an event should be retained
import time
event_time = time.time() - (8 * 24 * 60 * 60)  # 8 days ago
should_keep = policy.should_retain(event_time, "raw_sensor")  # False (> 7 days)

# Apply policy to a buffer
events = [
    {"timestamp": time.time() - 100, "event_type": "motion"},
    {"timestamp": time.time() - (40 * 24 * 60 * 60), "event_type": "motion"},  # Old
]
cleaned = policy.apply_to_buffer(events)  # Only keeps recent event
```

### Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `default_days` | Default retention period | 30 |
| `raw_events_days` | Retention for raw sensor events | 7 |
| `exceptions` | Event types retained indefinitely | `[]` |
| `max_entries` | Max entries per buffer (None = unlimited) | None |

## Consent Manager

Manage user and zone consent for data collection, supporting GDPR-style opt-out controls.

### Basic Usage

```python
from spaxiom.governance import ConsentManager

manager = ConsentManager()

# User opts out of specific zones
manager.opt_out("user123", ["bedroom", "bathroom"], reason="Privacy preference")

# Check if zone is opted out for a user
is_opted_out = manager.is_opted_out("bedroom", "user123")  # True

# User opts back in
manager.opt_in("user123", ["bedroom"])

# Globally suppress a zone (all users)
manager.suppress_zone("private_area")
```

### Filtering Events

```python
# Filter events based on consent
event = {"zone": "bedroom", "user_id": "user123", "data": "..."}
filtered = manager.filter_event(event)  # Returns None if suppressed

# Check before emitting events
if not manager.should_suppress_event("bedroom", "user123"):
    emit_event(event)
```

### Audit Summary

```python
summary = manager.get_consent_summary()
# {
#   "total_users": 5,
#   "zones_with_optouts": ["bedroom", "bathroom"],
#   "globally_suppressed": ["private_area"],
#   "optouts_by_zone": {"bedroom": 2, "bathroom": 3}
# }
```

## Authorization (RBAC + ABAC)

The Authorizer combines Role-Based Access Control (RBAC) with Attribute-Based Access Control (ABAC) for flexible authorization.

### Role-Based Access Control (RBAC)

```python
from spaxiom.governance import Authorizer, Role

authz = Authorizer()

# Define roles with permissions
operator_role = Role(
    name="operator",
    permissions={"read:occupancy", "read:temperature", "write:hvac"}
)
admin_role = Role(
    name="admin",
    permissions={"read:*", "write:*", "admin:*"}  # Wildcards supported
)

authz.add_role(operator_role)
authz.add_role(admin_role)

# Assign roles to users
authz.assign_user("alice", "operator")
authz.assign_user("bob", "admin")

# Check permissions
can_read = authz.check("alice", "read:occupancy")  # True
can_admin = authz.check("alice", "admin:users")    # False
can_admin = authz.check("bob", "admin:users")      # True (wildcard)
```

### Attribute-Based Access Control (ABAC)

For context-aware policies based on user, resource, action, and environment attributes:

```python
from spaxiom.governance import Policy

# Policy: Only allow access during business hours
def business_hours_only(ctx):
    import datetime
    hour = datetime.datetime.now().hour
    return 9 <= hour < 17

business_policy = Policy(
    name="business_hours",
    effect="allow",
    condition=business_hours_only
)
authz.add_policy(business_policy)

# Policy: Deny access to sensitive resources from external IPs
def deny_external_sensitive(ctx):
    is_external = ctx["environment"].get("ip_type") == "external"
    is_sensitive = "sensitive" in ctx["resource"]
    return is_external and is_sensitive

deny_policy = Policy(
    name="deny_external_sensitive",
    effect="deny",
    condition=deny_external_sensitive
)
authz.add_policy(deny_policy)

# Check with context
context = {"ip_type": "internal"}
allowed = authz.check("alice", "read:data", "sensor_data", context)
```

### Permission Format

Permissions follow the format `action:resource`:

- `read:occupancy` - Read occupancy data
- `write:hvac` - Control HVAC systems
- `admin:users` - Administer users
- `read:*` - Read any resource (wildcard)
- `*` - All permissions

## Audit Logger

Append-only audit logging with optional cryptographic signing for tamper-evidence.

### Basic Usage

```python
from spaxiom.governance import AuditLogger

# Create logger (in-memory for demo)
logger = AuditLogger(backend="memory")

# Log events
logger.log_event(
    event_type="data_access",
    actor="alice",
    action="read",
    resource="occupancy_zone_1",
    outcome="success",
    details={"reason": "Dashboard view"}
)

# Log authorization failures
logger.log_event(
    event_type="authz_failure",
    actor="mallory",
    action="write",
    resource="admin_config",
    outcome="denied",
    details={"reason": "Insufficient permissions"}
)
```

### Signed Audit Logs

For tamper-evident logging, provide a signing key:

```python
import os

signing_key = os.urandom(32)  # Keep this secret!
logger = AuditLogger(signing_key=signing_key)

# Entries are automatically signed
logger.log_event(
    event_type="config_change",
    actor="admin",
    action="update",
    resource="system_settings"
)

# Verify integrity of all entries
is_valid = logger.verify_integrity()  # True if no tampering
```

### Querying Logs

```python
# Get all entries for a specific actor
entries = logger.get_entries(actor="alice")

# Get entries in a time range
import time
one_hour_ago = time.time() - 3600
entries = logger.get_entries(since=one_hour_ago)

# Get entries by type
entries = logger.get_entries(event_type="authz_failure")

# Export all entries as JSON-serializable dicts
all_entries = logger.export()
```

### Sealing the Log

For forensic preservation, seal the log to prevent further writes:

```python
logger.seal()  # No more entries can be added
logger.is_sealed()  # True
logger.log_event(...)  # Raises RuntimeError
```

## Integration Example

Combining all governance primitives:

```python
from spaxiom.governance import (
    RetentionPolicy,
    ConsentManager,
    Authorizer,
    AuditLogger,
    Role,
)

# Setup governance
retention = RetentionPolicy(default_days=30, raw_events_days=7)
consent = ConsentManager()
authz = Authorizer()
audit = AuditLogger()

# Configure roles
authz.add_role(Role("viewer", {"read:*"}))
authz.add_role(Role("operator", {"read:*", "write:controls"}))
authz.assign_user("alice", "viewer")

def process_request(user_id, action, resource, zone, event_data):
    # Check authorization
    if not authz.check(user_id, action, resource):
        audit.log_event("authz_failure", user_id, action, resource, "denied")
        return {"error": "Unauthorized"}
    
    # Check consent
    if consent.should_suppress_event(zone, user_id):
        audit.log_event("consent_suppression", user_id, action, resource, "suppressed")
        return {"error": "Data collection not consented"}
    
    # Process request...
    audit.log_event("data_access", user_id, action, resource, "success")
    
    # Apply retention to any stored data
    stored_events = get_stored_events(zone)
    cleaned = retention.apply_to_buffer(stored_events)
    
    return {"success": True}
```
