"""
test_governance_authorization.py - Paper Parity Test

Tests RBAC and ABAC authorization:
- RBAC class with roles and permissions
- ABAC class with policies
- Authorization checks

Reference: Paper Section 5 "Role-based access control (RBAC)" and "Attribute-based access control (ABAC)"
Proving Example: examples/paper/governance_demo.py
"""

from spaxiom.governance import RBAC, ABAC, Role, Policy, Authorizer


class TestRBACClass:
    """Tests for RBAC class."""

    def test_rbac_exists(self):
        """RBAC class must exist."""
        assert RBAC is not None

    def test_role_exists(self):
        """Role class must exist."""
        assert Role is not None

    def test_rbac_add_role(self):
        """RBAC must have add_role() method."""
        rbac = RBAC()
        role = Role(name="operator", permissions={"read:occupancy", "read:queue"})
        rbac.add_role(role)

        # Role should be added
        assert "operator" in rbac._roles

    def test_rbac_assign_user(self):
        """RBAC must have assign_user() method."""
        rbac = RBAC()
        role = Role(name="operator", permissions={"read:occupancy"})
        rbac.add_role(role)
        rbac.assign_user("user_123", role="operator")

        # User should have role
        assert "operator" in rbac.get_user_roles("user_123")

    def test_rbac_can(self):
        """RBAC must have can(user, action) method."""
        rbac = RBAC()
        role = Role(name="operator", permissions={"read:occupancy"})
        rbac.add_role(role)
        rbac.assign_user("user_123", role="operator")

        assert rbac.can("user_123", "read:occupancy") is True
        assert rbac.can("user_123", "write:config") is False

    def test_rbac_wildcard_permissions(self):
        """RBAC should support wildcard permissions."""
        rbac = RBAC()
        admin = Role(name="admin", permissions={"*"})
        reader = Role(name="reader", permissions={"read:*"})

        rbac.add_role(admin)
        rbac.add_role(reader)
        rbac.assign_user("admin_user", role="admin")
        rbac.assign_user("reader_user", role="reader")

        # Admin can do anything
        assert rbac.can("admin_user", "read:occupancy") is True
        assert rbac.can("admin_user", "write:config") is True

        # Reader can read anything
        assert rbac.can("reader_user", "read:occupancy") is True
        assert rbac.can("reader_user", "read:queue") is True
        assert rbac.can("reader_user", "write:config") is False


class TestABACClass:
    """Tests for ABAC class."""

    def test_abac_exists(self):
        """ABAC class must exist."""
        assert ABAC is not None

    def test_policy_exists(self):
        """Policy class must exist."""
        assert Policy is not None

    def test_abac_add_policy(self):
        """ABAC must have add_policy() method."""
        abac = ABAC()
        policy = Policy(
            name="office_hours_only",
            effect="allow",
            condition=lambda ctx: ctx.get("environment", {}).get("hour", 12) >= 9,
        )
        abac.add_policy(policy)

        assert len(abac._policies) == 1

    def test_abac_is_allowed(self):
        """ABAC must have is_allowed(user, action, resource) method."""
        abac = ABAC(default_effect="deny")

        # Policy: allow read during office hours
        policy = Policy(
            name="office_hours",
            effect="allow",
            condition=lambda ctx: 9 <= ctx["environment"].get("hour", 0) <= 17,
        )
        abac.add_policy(policy)

        # During office hours - allowed
        assert abac.is_allowed(
            user="user1",
            action="read",
            resource="data",
            environment={"hour": 10},
        )

        # Outside office hours - denied
        assert not abac.is_allowed(
            user="user1",
            action="read",
            resource="data",
            environment={"hour": 22},
        )

    def test_abac_deny_takes_precedence(self):
        """Deny policies should take precedence over allow."""
        abac = ABAC()

        allow_policy = Policy(name="allow_all", effect="allow")
        deny_policy = Policy(
            name="deny_sensitive",
            effect="deny",
            condition=lambda ctx: ctx["resource"] == "sensitive",
        )

        abac.add_policy(allow_policy)
        abac.add_policy(deny_policy)

        # Regular resource - allowed
        assert abac.is_allowed("user", "read", "normal")

        # Sensitive resource - denied (deny takes precedence)
        assert not abac.is_allowed("user", "read", "sensitive")


class TestAuthorizerClass:
    """Tests for combined Authorizer class."""

    def test_authorizer_exists(self):
        """Authorizer class must exist."""
        assert Authorizer is not None

    def test_authorizer_combines_rbac_abac(self):
        """Authorizer should combine RBAC and ABAC checks."""
        auth = Authorizer()

        # Set up RBAC role
        auth.add_role(Role(name="operator", permissions={"read:occupancy"}))
        auth.assign_user("user1", "operator")

        # User has RBAC permission
        assert auth.check("user1", "read:occupancy") is True
        assert auth.check("user1", "write:config") is False

    def test_runtime_accepts_authorizer(self):
        """Runtime must accept authorizer via set_authorizer()."""
        from spaxiom.tick import PhasedTickRunner

        runner = PhasedTickRunner()
        auth = Authorizer()

        runner.set_authorizer(auth)
        assert runner._authorizer is auth
