"""
Authentication API endpoints.

Provides:
- First-run setup
- Login/logout
- Token management
- Password change
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from spaxiom.edge.api.auth import (
    AuthManager,
    Role,
    User,
    get_auth_manager,
    get_current_user,
    require_admin,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# Request/Response models
class SetupRequest(BaseModel):
    """First-time setup request."""

    password: str = Field(..., min_length=8, description="Admin password (min 8 chars)")


class SetupResponse(BaseModel):
    """First-time setup response."""

    message: str
    token: str
    username: str = "admin"


class LoginRequest(BaseModel):
    """Login request."""

    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response."""

    token: str
    username: str
    role: str
    expires_in_hours: int


class ChangePasswordRequest(BaseModel):
    """Change password request."""

    old_password: str
    new_password: str = Field(..., min_length=8)


class CreateTokenRequest(BaseModel):
    """Create API token request."""

    username: str
    role: Role = Role.VIEWER
    expires_days: Optional[int] = None


class CreateTokenResponse(BaseModel):
    """Create API token response."""

    token: str
    username: str
    role: str


class AuthStatusResponse(BaseModel):
    """Authentication status response."""

    enabled: bool
    setup_required: bool
    current_user: Optional[str] = None
    current_role: Optional[str] = None


@router.get("/status", response_model=AuthStatusResponse)
async def get_auth_status(
    auth_manager: AuthManager = Depends(get_auth_manager),
    user: Optional[User] = Depends(lambda: None),  # Don't require auth for status check
):
    """Get authentication status.

    Returns whether auth is enabled, if setup is required,
    and current user info if authenticated.
    """
    enabled = await auth_manager.is_auth_enabled()
    setup_required = await auth_manager.is_setup_required()

    return AuthStatusResponse(
        enabled=enabled,
        setup_required=setup_required,
        current_user=user.username if user else None,
        current_role=user.role.value if user else None,
    )


@router.post("/setup", response_model=SetupResponse)
async def setup_admin(
    request: SetupRequest,
    auth_manager: AuthManager = Depends(get_auth_manager),
):
    """First-time admin setup.

    Sets the admin password and enables authentication.
    Only works if no admin has been configured.
    """
    if not await auth_manager.is_setup_required():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Setup already completed",
        )

    token = await auth_manager.setup_admin(request.password)

    return SetupResponse(
        message="Admin setup complete. Authentication is now enabled.",
        token=token,
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    auth_manager: AuthManager = Depends(get_auth_manager),
):
    """Login with username and password.

    Returns a session token valid for 24 hours.
    """
    result = await auth_manager.authenticate(request.username, request.password)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token, role = result
    config = await auth_manager.load_config()

    return LoginResponse(
        token=token,
        username=request.username,
        role=role.value,
        expires_in_hours=config.session_timeout_hours,
    )


@router.post("/logout")
async def logout(
    user: User = Depends(get_current_user),
    auth_manager: AuthManager = Depends(get_auth_manager),
):
    """Logout and revoke current token."""
    await auth_manager.revoke_token(user.token)
    return {"message": "Logged out successfully"}


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    user: User = Depends(require_admin),
    auth_manager: AuthManager = Depends(get_auth_manager),
):
    """Change admin password.

    Requires current password for verification.
    """
    await auth_manager.change_password(request.old_password, request.new_password)
    return {"message": "Password changed successfully"}


@router.post("/tokens", response_model=CreateTokenResponse)
async def create_token(
    request: CreateTokenRequest,
    user: User = Depends(require_admin),
    auth_manager: AuthManager = Depends(get_auth_manager),
):
    """Create a new API token.

    Admin only. Can create tokens for any role.
    """
    token = await auth_manager.create_api_token(
        request.username, request.role, request.expires_days
    )

    return CreateTokenResponse(
        token=token,
        username=request.username,
        role=request.role.value,
    )


@router.get("/tokens")
async def list_tokens(
    user: User = Depends(require_admin),
    auth_manager: AuthManager = Depends(get_auth_manager),
):
    """List all API tokens.

    Admin only. Returns token metadata (not actual tokens).
    """
    tokens = await auth_manager.list_tokens()
    return {"tokens": tokens}


@router.delete("/tokens/{token_prefix}")
async def revoke_token(
    token_prefix: str,
    user: User = Depends(require_admin),
    auth_manager: AuthManager = Depends(get_auth_manager),
):
    """Revoke an API token by prefix.

    Admin only. Token prefix is the first 8 characters.
    """
    config = await auth_manager.load_config()

    # Find token by prefix
    for token in list(config.api_tokens.keys()):
        if token.startswith(token_prefix):
            await auth_manager.revoke_token(token)
            return {"message": f"Token {token_prefix}... revoked"}

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Token with prefix {token_prefix} not found",
    )


@router.post("/enable")
async def enable_auth(
    user: User = Depends(require_admin),
    auth_manager: AuthManager = Depends(get_auth_manager),
):
    """Enable authentication."""
    await auth_manager.enable_auth()
    return {"message": "Authentication enabled"}


@router.post("/disable")
async def disable_auth(
    user: User = Depends(require_admin),
    auth_manager: AuthManager = Depends(get_auth_manager),
):
    """Disable authentication (development only).

    Warning: This allows unauthenticated access to all endpoints.
    """
    await auth_manager.disable_auth()
    return {"message": "Authentication disabled. All endpoints are now public."}
