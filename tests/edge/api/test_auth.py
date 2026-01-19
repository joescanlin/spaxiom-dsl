"""Tests for authentication API."""

import pytest
from unittest.mock import AsyncMock

from spaxiom.edge.api.auth import (
    AuthManager,
    Role,
    User,
    hash_password,
    verify_password,
    generate_api_token,
)


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_hash_password_returns_hash_and_salt(self):
        """Test that hash_password returns both hash and salt."""
        password = "test_password"
        password_hash, salt = hash_password(password)

        assert password_hash is not None
        assert salt is not None
        assert len(password_hash) == 64  # SHA256 hex
        assert len(salt) == 32  # 16 bytes hex

    def test_hash_password_with_same_salt_produces_same_hash(self):
        """Test that same password + salt = same hash."""
        password = "test_password"
        salt = "fixed_salt_for_test"

        hash1, _ = hash_password(password, salt)
        hash2, _ = hash_password(password, salt)

        assert hash1 == hash2

    def test_hash_password_different_salts_produce_different_hashes(self):
        """Test that different salts produce different hashes."""
        password = "test_password"

        hash1, salt1 = hash_password(password)
        hash2, salt2 = hash_password(password)

        assert salt1 != salt2
        assert hash1 != hash2

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "test_password"
        password_hash, salt = hash_password(password)

        assert verify_password(password, password_hash, salt) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "test_password"
        password_hash, salt = hash_password(password)

        assert verify_password("wrong_password", password_hash, salt) is False


class TestApiToken:
    """Tests for API token generation."""

    def test_generate_api_token_length(self):
        """Test that generated tokens have correct length."""
        token = generate_api_token()
        assert len(token) == 64  # 32 bytes hex

    def test_generate_api_token_uniqueness(self):
        """Test that generated tokens are unique."""
        tokens = [generate_api_token() for _ in range(100)]
        assert len(set(tokens)) == 100


class TestAuthManager:
    """Tests for AuthManager class."""

    @pytest.fixture
    def mock_settings_repo(self):
        """Create mock settings repository."""
        repo = AsyncMock()
        repo.get = AsyncMock(return_value=None)
        repo.set = AsyncMock()
        return repo

    @pytest.fixture
    def auth_manager(self, mock_settings_repo):
        """Create auth manager with mock repo."""
        return AuthManager(mock_settings_repo)

    @pytest.mark.asyncio
    async def test_is_setup_required_true_when_no_config(self, auth_manager):
        """Test setup is required when no admin configured."""
        assert await auth_manager.is_setup_required() is True

    @pytest.mark.asyncio
    async def test_is_setup_required_false_after_setup(
        self, auth_manager, mock_settings_repo
    ):
        """Test setup is not required after admin is configured."""
        # Do setup
        await auth_manager.setup_admin("test_password")

        # Now should not be required
        assert await auth_manager.is_setup_required() is False

    @pytest.mark.asyncio
    async def test_setup_admin_returns_token(self, auth_manager):
        """Test that setup_admin returns a valid token."""
        token = await auth_manager.setup_admin("test_password")

        assert token is not None
        assert len(token) == 64

    @pytest.mark.asyncio
    async def test_setup_admin_enables_auth(self, auth_manager):
        """Test that setup_admin enables authentication."""
        await auth_manager.setup_admin("test_password")

        assert await auth_manager.is_auth_enabled() is True

    @pytest.mark.asyncio
    async def test_authenticate_success(self, auth_manager):
        """Test successful authentication."""
        password = "test_password"
        await auth_manager.setup_admin(password)

        result = await auth_manager.authenticate("admin", password)

        assert result is not None
        token, role = result
        assert len(token) == 64
        assert role == Role.ADMIN

    @pytest.mark.asyncio
    async def test_authenticate_wrong_password(self, auth_manager):
        """Test authentication with wrong password."""
        await auth_manager.setup_admin("test_password")

        result = await auth_manager.authenticate("admin", "wrong_password")

        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_wrong_username(self, auth_manager):
        """Test authentication with wrong username."""
        await auth_manager.setup_admin("test_password")

        result = await auth_manager.authenticate("not_admin", "test_password")

        assert result is None

    @pytest.mark.asyncio
    async def test_validate_token_valid(self, auth_manager):
        """Test token validation with valid token."""
        token = await auth_manager.setup_admin("test_password")

        user = await auth_manager.validate_token(token)

        assert user is not None
        assert user.username == "admin"
        assert user.role == Role.ADMIN

    @pytest.mark.asyncio
    async def test_validate_token_invalid(self, auth_manager):
        """Test token validation with invalid token."""
        await auth_manager.setup_admin("test_password")

        user = await auth_manager.validate_token("invalid_token")

        assert user is None

    @pytest.mark.asyncio
    async def test_revoke_token(self, auth_manager):
        """Test token revocation."""
        token = await auth_manager.setup_admin("test_password")

        # Token should be valid
        assert await auth_manager.validate_token(token) is not None

        # Revoke it
        await auth_manager.revoke_token(token)

        # Token should now be invalid
        assert await auth_manager.validate_token(token) is None

    @pytest.mark.asyncio
    async def test_create_api_token(self, auth_manager):
        """Test creating additional API tokens."""
        await auth_manager.setup_admin("test_password")

        token = await auth_manager.create_api_token("api_user", Role.OPERATOR)

        assert len(token) == 64

        user = await auth_manager.validate_token(token)
        assert user.username == "api_user"
        assert user.role == Role.OPERATOR

    @pytest.mark.asyncio
    async def test_list_tokens(self, auth_manager):
        """Test listing tokens."""
        await auth_manager.setup_admin("test_password")
        await auth_manager.create_api_token("user1", Role.VIEWER)
        await auth_manager.create_api_token("user2", Role.OPERATOR)

        tokens = await auth_manager.list_tokens()

        assert len(tokens) == 3  # admin + 2 created
        usernames = [t["username"] for t in tokens]
        assert "admin" in usernames
        assert "user1" in usernames
        assert "user2" in usernames

    @pytest.mark.asyncio
    async def test_change_password(self, auth_manager):
        """Test changing password."""
        old_password = "old_password"
        new_password = "new_password"

        await auth_manager.setup_admin(old_password)

        # Change password
        await auth_manager.change_password(old_password, new_password)

        # Old password should not work
        result = await auth_manager.authenticate("admin", old_password)
        assert result is None

        # New password should work
        result = await auth_manager.authenticate("admin", new_password)
        assert result is not None

    @pytest.mark.asyncio
    async def test_disable_enable_auth(self, auth_manager):
        """Test disabling and enabling authentication."""
        await auth_manager.setup_admin("test_password")

        assert await auth_manager.is_auth_enabled() is True

        await auth_manager.disable_auth()
        assert await auth_manager.is_auth_enabled() is False

        await auth_manager.enable_auth()
        assert await auth_manager.is_auth_enabled() is True


class TestRole:
    """Tests for Role enum."""

    def test_role_values(self):
        """Test role enum values."""
        assert Role.ADMIN.value == "admin"
        assert Role.OPERATOR.value == "operator"
        assert Role.VIEWER.value == "viewer"


class TestUser:
    """Tests for User model."""

    def test_user_creation(self):
        """Test creating a User."""
        user = User(username="test", role=Role.ADMIN, token="abc123")

        assert user.username == "test"
        assert user.role == Role.ADMIN
        assert user.token == "abc123"
