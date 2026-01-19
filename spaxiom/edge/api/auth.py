"""
Authentication and authorization for Spaxiom Edge API.

Provides:
- Token-based authentication
- Role-based access control (admin, operator, viewer)
- First-run setup flow
- API key management
"""

import hashlib
import hmac
import secrets
import time
from datetime import datetime
from enum import Enum
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel


class Role(str, Enum):
    """User roles for access control."""

    ADMIN = "admin"  # Full access
    OPERATOR = "operator"  # Start/stop agents, view config
    VIEWER = "viewer"  # Read-only access


class User(BaseModel):
    """Authenticated user info."""

    username: str
    role: Role
    token: str


class TokenData(BaseModel):
    """Token payload data."""

    username: str
    role: Role
    created_at: float
    expires_at: float


class AuthConfig(BaseModel):
    """Authentication configuration."""

    enabled: bool = False
    admin_password_hash: Optional[str] = None
    api_tokens: dict = (
        {}
    )  # {token: {"username": str, "role": str, "created_at": float}}
    session_timeout_hours: int = 24
    require_https: bool = False


# Security scheme
security = HTTPBearer(auto_error=False)


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """Hash a password with salt.

    Args:
        password: Plain text password
        salt: Optional salt (generated if not provided)

    Returns:
        Tuple of (hash, salt)
    """
    if salt is None:
        salt = secrets.token_hex(16)
    hash_input = f"{salt}{password}".encode()
    password_hash = hashlib.sha256(hash_input).hexdigest()
    return password_hash, salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """Verify a password against a hash.

    Args:
        password: Plain text password
        password_hash: Stored hash
        salt: Stored salt

    Returns:
        True if password matches
    """
    computed_hash, _ = hash_password(password, salt)
    return hmac.compare_digest(computed_hash, password_hash)


def generate_api_token() -> str:
    """Generate a secure API token.

    Returns:
        Random 32-character hex token
    """
    return secrets.token_hex(32)


class AuthManager:
    """Manages authentication state and operations."""

    def __init__(self, settings_repo):
        """Initialize auth manager.

        Args:
            settings_repo: SettingsRepository for persisting auth config
        """
        self.settings_repo = settings_repo
        self._config: Optional[AuthConfig] = None

    async def load_config(self) -> AuthConfig:
        """Load auth config from settings."""
        if self._config is None:
            data = await self.settings_repo.get("auth_config")
            if data:
                self._config = AuthConfig(**data)
            else:
                self._config = AuthConfig()
        return self._config

    async def save_config(self) -> None:
        """Save auth config to settings."""
        if self._config:
            await self.settings_repo.set("auth_config", self._config.model_dump())

    async def is_setup_required(self) -> bool:
        """Check if first-time setup is required.

        Returns:
            True if no admin password has been set
        """
        config = await self.load_config()
        return config.admin_password_hash is None

    async def is_auth_enabled(self) -> bool:
        """Check if authentication is enabled.

        Returns:
            True if auth is enabled
        """
        config = await self.load_config()
        return config.enabled

    async def setup_admin(self, password: str) -> str:
        """Set up admin password on first run.

        Args:
            password: Admin password

        Returns:
            Generated API token for admin

        Raises:
            HTTPException: If setup already completed
        """
        config = await self.load_config()

        if config.admin_password_hash is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admin already configured. Use change password endpoint.",
            )

        # Hash and store password
        password_hash, salt = hash_password(password)
        config.admin_password_hash = f"{salt}:{password_hash}"
        config.enabled = True

        # Generate admin token
        token = generate_api_token()
        config.api_tokens[token] = {
            "username": "admin",
            "role": Role.ADMIN.value,
            "created_at": time.time(),
        }

        self._config = config
        await self.save_config()

        return token

    async def authenticate(
        self, username: str, password: str
    ) -> Optional[tuple[str, Role]]:
        """Authenticate with username and password.

        Args:
            username: Username (currently only "admin" supported)
            password: Password

        Returns:
            Tuple of (token, role) if successful, None otherwise
        """
        config = await self.load_config()

        if username != "admin" or not config.admin_password_hash:
            return None

        # Parse stored hash
        salt, stored_hash = config.admin_password_hash.split(":")

        if not verify_password(password, stored_hash, salt):
            return None

        # Generate new session token
        token = generate_api_token()
        expires_at = time.time() + (config.session_timeout_hours * 3600)

        config.api_tokens[token] = {
            "username": username,
            "role": Role.ADMIN.value,
            "created_at": time.time(),
            "expires_at": expires_at,
        }

        self._config = config
        await self.save_config()

        return token, Role.ADMIN

    async def validate_token(self, token: str) -> Optional[User]:
        """Validate an API token.

        Args:
            token: API token

        Returns:
            User if valid, None otherwise
        """
        config = await self.load_config()

        if token not in config.api_tokens:
            return None

        token_data = config.api_tokens[token]

        # Check expiration
        if "expires_at" in token_data and token_data["expires_at"] < time.time():
            # Remove expired token
            del config.api_tokens[token]
            await self.save_config()
            return None

        return User(
            username=token_data["username"],
            role=Role(token_data["role"]),
            token=token,
        )

    async def revoke_token(self, token: str) -> bool:
        """Revoke an API token.

        Args:
            token: Token to revoke

        Returns:
            True if token was revoked
        """
        config = await self.load_config()

        if token in config.api_tokens:
            del config.api_tokens[token]
            await self.save_config()
            return True
        return False

    async def create_api_token(
        self, username: str, role: Role, expires_days: Optional[int] = None
    ) -> str:
        """Create a new API token.

        Args:
            username: Username for token
            role: Role for token
            expires_days: Optional expiration in days

        Returns:
            New API token
        """
        config = await self.load_config()

        token = generate_api_token()
        token_data = {
            "username": username,
            "role": role.value,
            "created_at": time.time(),
        }

        if expires_days:
            token_data["expires_at"] = time.time() + (expires_days * 86400)

        config.api_tokens[token] = token_data
        await self.save_config()

        return token

    async def list_tokens(self) -> list[dict]:
        """List all API tokens (without the actual token values).

        Returns:
            List of token metadata
        """
        config = await self.load_config()

        tokens = []
        for token, data in config.api_tokens.items():
            tokens.append(
                {
                    "token_prefix": token[:8] + "...",
                    "username": data["username"],
                    "role": data["role"],
                    "created_at": datetime.fromtimestamp(
                        data["created_at"]
                    ).isoformat(),
                    "expires_at": (
                        datetime.fromtimestamp(data["expires_at"]).isoformat()
                        if "expires_at" in data
                        else None
                    ),
                }
            )
        return tokens

    async def change_password(self, old_password: str, new_password: str) -> bool:
        """Change admin password.

        Args:
            old_password: Current password
            new_password: New password

        Returns:
            True if password was changed

        Raises:
            HTTPException: If old password is incorrect
        """
        config = await self.load_config()

        if not config.admin_password_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Admin not configured"
            )

        # Verify old password
        salt, stored_hash = config.admin_password_hash.split(":")
        if not verify_password(old_password, stored_hash, salt):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password"
            )

        # Set new password
        new_hash, new_salt = hash_password(new_password)
        config.admin_password_hash = f"{new_salt}:{new_hash}"

        self._config = config
        await self.save_config()

        return True

    async def disable_auth(self) -> None:
        """Disable authentication (for development)."""
        config = await self.load_config()
        config.enabled = False
        self._config = config
        await self.save_config()

    async def enable_auth(self) -> None:
        """Enable authentication."""
        config = await self.load_config()
        config.enabled = True
        self._config = config
        await self.save_config()


# Global auth manager instance (set during app setup)
_auth_manager: Optional[AuthManager] = None


def get_auth_manager() -> AuthManager:
    """Get the global auth manager."""
    if _auth_manager is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Auth manager not initialized",
        )
    return _auth_manager


def set_auth_manager(manager: AuthManager) -> None:
    """Set the global auth manager."""
    global _auth_manager
    _auth_manager = manager


async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[User]:
    """Get current user if authenticated (optional).

    This dependency does not require authentication but returns
    the user if a valid token is provided.
    """
    auth_manager = get_auth_manager()

    # Check if auth is enabled
    if not await auth_manager.is_auth_enabled():
        return User(username="anonymous", role=Role.ADMIN, token="")

    if credentials is None:
        return None

    user = await auth_manager.validate_token(credentials.credentials)
    return user


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> User:
    """Get current authenticated user (required).

    This dependency requires authentication and raises 401 if not authenticated.
    """
    auth_manager = get_auth_manager()

    # Check if auth is enabled
    if not await auth_manager.is_auth_enabled():
        return User(username="anonymous", role=Role.ADMIN, token="")

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await auth_manager.validate_token(credentials.credentials)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_role(required_role: Role):
    """Dependency factory for role-based access control.

    Args:
        required_role: Minimum required role

    Returns:
        Dependency function
    """
    role_hierarchy = {Role.VIEWER: 0, Role.OPERATOR: 1, Role.ADMIN: 2}

    async def check_role(user: User = Depends(get_current_user)) -> User:
        if role_hierarchy[user.role] < role_hierarchy[required_role]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role.value}' or higher required",
            )
        return user

    return check_role


# Convenience dependencies
require_admin = require_role(Role.ADMIN)
require_operator = require_role(Role.OPERATOR)
require_viewer = require_role(Role.VIEWER)
