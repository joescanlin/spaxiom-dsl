"""
Governance primitives for Spaxiom DSL.

Provides enforceable data governance:
- RetentionPolicy: bounded storage with TTL
- ConsentManager: zone/entity opt-out
- Authorizer: RBAC/ABAC for subscriptions/queries
- AuditLogger: structured event logging

Reference: Paper Section 5 "Privacy, Security, and Data Governance"
"""

from spaxiom.governance.retention import RetentionPolicy
from spaxiom.governance.consent import ConsentManager
from spaxiom.governance.authz import Authorizer, Role, Policy, RBAC, ABAC
from spaxiom.governance.audit import AuditLogger, AuditEntry

__all__ = [
    "RetentionPolicy",
    "ConsentManager",
    "Authorizer",
    "Role",
    "Policy",
    "RBAC",
    "ABAC",
    "AuditLogger",
    "AuditEntry",
]
