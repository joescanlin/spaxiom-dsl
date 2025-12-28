"""
Authorization for subscriptions and queries.

Provides RBAC (Role-Based Access Control) and ABAC (Attribute-Based Access Control).

Reference: Paper Section 5 "Role-based access control (RBAC)" and
"Attribute-based access control (ABAC)"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set


@dataclass
class Role:
    """A role with associated permissions.

    Attributes:
        name: Role name (e.g., "operator", "admin")
        permissions: Set of permission strings (e.g., "read:occupancy")
    """

    name: str
    permissions: Set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        """Convert permissions to set if list provided."""
        if isinstance(self.permissions, list):
            self.permissions = set(self.permissions)

    def has_permission(self, permission: str) -> bool:
        """Check if role has a specific permission.

        Args:
            permission: Permission string to check

        Returns:
            True if role has permission
        """
        # Check exact match
        if permission in self.permissions:
            return True
        # Check wildcard (e.g., "read:*" matches "read:occupancy")
        action = permission.split(":")[0] if ":" in permission else permission
        if f"{action}:*" in self.permissions:
            return True
        if "*" in self.permissions:
            return True
        return False


class RBAC:
    """Role-Based Access Control.

    Manages roles and user-role assignments.
    """

    def __init__(self) -> None:
        """Initialize RBAC."""
        self._roles: Dict[str, Role] = {}
        self._user_roles: Dict[str, Set[str]] = {}

    def add_role(self, role: Role) -> None:
        """Add a role to the RBAC system.

        Args:
            role: Role to add
        """
        self._roles[role.name] = role

    def remove_role(self, role_name: str) -> None:
        """Remove a role from the RBAC system.

        Args:
            role_name: Name of role to remove
        """
        if role_name in self._roles:
            del self._roles[role_name]
            # Remove role from all users
            for user_id in self._user_roles:
                self._user_roles[user_id].discard(role_name)

    def assign_user(self, user_id: str, role: str) -> None:
        """Assign a role to a user.

        Args:
            user_id: User identifier
            role: Role name to assign
        """
        if user_id not in self._user_roles:
            self._user_roles[user_id] = set()
        self._user_roles[user_id].add(role)

    def unassign_user(self, user_id: str, role: str) -> None:
        """Remove a role from a user.

        Args:
            user_id: User identifier
            role: Role name to remove
        """
        if user_id in self._user_roles:
            self._user_roles[user_id].discard(role)

    def get_user_roles(self, user_id: str) -> Set[str]:
        """Get all roles assigned to a user.

        Args:
            user_id: User identifier

        Returns:
            Set of role names
        """
        return self._user_roles.get(user_id, set()).copy()

    def can(self, user_id: str, permission: str) -> bool:
        """Check if user has a permission.

        Args:
            user_id: User identifier
            permission: Permission string (e.g., "read:occupancy")

        Returns:
            True if user has permission through any role
        """
        user_roles = self._user_roles.get(user_id, set())
        for role_name in user_roles:
            role = self._roles.get(role_name)
            if role and role.has_permission(permission):
                return True
        return False

    def get_permissions(self, user_id: str) -> Set[str]:
        """Get all permissions for a user.

        Args:
            user_id: User identifier

        Returns:
            Set of all permissions from all assigned roles
        """
        permissions: Set[str] = set()
        user_roles = self._user_roles.get(user_id, set())
        for role_name in user_roles:
            role = self._roles.get(role_name)
            if role:
                permissions.update(role.permissions)
        return permissions


@dataclass
class Policy:
    """An ABAC policy rule.

    Attributes:
        name: Policy name
        effect: "allow" or "deny"
        condition: Function that evaluates the policy
    """

    name: str
    effect: str = "allow"  # "allow" or "deny"
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate the policy against a context.

        Args:
            context: Dict with user, action, resource, environment

        Returns:
            True if condition is met
        """
        if self.condition is None:
            return True
        return self.condition(context)


class ABAC:
    """Attribute-Based Access Control.

    Evaluates access decisions based on attributes of subject,
    resource, action, and environment.
    """

    def __init__(self, default_effect: str = "deny") -> None:
        """Initialize ABAC.

        Args:
            default_effect: Default decision when no policies match ("allow" or "deny")
        """
        self._policies: List[Policy] = []
        self._default_effect = default_effect

    def add_policy(self, policy: Policy) -> None:
        """Add a policy to the ABAC system.

        Args:
            policy: Policy to add
        """
        self._policies.append(policy)

    def remove_policy(self, policy_name: str) -> None:
        """Remove a policy by name.

        Args:
            policy_name: Name of policy to remove
        """
        self._policies = [p for p in self._policies if p.name != policy_name]

    def is_allowed(
        self,
        user: str,
        action: str,
        resource: str,
        environment: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Check if an action is allowed.

        Args:
            user: User identifier
            action: Action being performed
            resource: Resource being accessed
            environment: Optional environmental context

        Returns:
            True if action is allowed
        """
        context = {
            "user": user,
            "action": action,
            "resource": resource,
            "environment": environment or {},
        }

        # Evaluate all policies
        allow_matched = False
        deny_matched = False

        for policy in self._policies:
            if policy.evaluate(context):
                if policy.effect == "deny":
                    deny_matched = True
                elif policy.effect == "allow":
                    allow_matched = True

        # Deny takes precedence
        if deny_matched:
            return False
        if allow_matched:
            return True

        # No policies matched, use default
        return self._default_effect == "allow"


class Authorizer:
    """Combined RBAC + ABAC authorizer.

    Provides a unified interface for authorization checks,
    using RBAC for role-based permissions and ABAC for
    context-aware policies.
    """

    def __init__(self) -> None:
        """Initialize the authorizer."""
        self.rbac = RBAC()
        self.abac = ABAC()

    def check(
        self,
        user_id: str,
        action: str,
        resource: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Check if user is authorized for an action.

        First checks RBAC permissions, then ABAC policies.

        Args:
            user_id: User identifier
            action: Action being performed (e.g., "read:occupancy")
            resource: Optional specific resource
            context: Optional additional context

        Returns:
            True if authorized
        """
        # Check RBAC first
        if self.rbac.can(user_id, action):
            # If RBAC allows, also check ABAC (may deny)
            if resource:
                return self.abac.is_allowed(user_id, action, resource, context)
            return True

        # RBAC denied, check if ABAC explicitly allows
        if resource:
            return self.abac.is_allowed(user_id, action, resource, context)

        return False

    def add_role(self, role: Role) -> None:
        """Add a role to RBAC."""
        self.rbac.add_role(role)

    def assign_user(self, user_id: str, role: str) -> None:
        """Assign a role to a user."""
        self.rbac.assign_user(user_id, role)

    def add_policy(self, policy: Policy) -> None:
        """Add a policy to ABAC."""
        self.abac.add_policy(policy)
