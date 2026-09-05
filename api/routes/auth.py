"""
Authentication API Endpoints for User Registration and Login.
"""

import secrets
from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_db
from api.schemas import (
    AuthTokenResponseSchema,
    UserLoginRequestSchema,
    UserRegisterRequestSchema,
    UserResponseSchema,
)
from database.db_manager import DatabaseManager
from src.utils.logger import get_logger

logger = get_logger("AuthRoute")

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication & User Management"])


@router.post(
    "/register",
    response_model=UserResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Register New User Account",
    description="Registers a new user account with email, password, full name, and organization.",
)
async def register_user(
    payload: UserRegisterRequestSchema,
    db: DatabaseManager = Depends(get_db),
) -> UserResponseSchema:
    """Creates a new user profile with securely hashed credentials."""
    logger.info(f"Received registration request for email: {payload.email}")
    try:
        user = db.create_user(
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
            organization=payload.organization,
            role=payload.role or "MERCHANT_ADMIN",
        )
        return UserResponseSchema(**user)
    except ValueError as e:
        logger.warning(f"Registration validation failed for {payload.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Internal error during registration: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register user account.",
        )


@router.post(
    "/login",
    response_model=AuthTokenResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="User Login & Authentication",
    description="Validates email and password credentials and returns session token with user profile.",
)
async def login_user(
    payload: UserLoginRequestSchema,
    db: DatabaseManager = Depends(get_db),
) -> AuthTokenResponseSchema:
    """Authenticates user credentials and returns session auth token."""
    logger.info(f"Received login attempt for email: {payload.email}")
    user = db.authenticate_user(email=payload.email, password=payload.password)
    if not user:
        logger.warning(f"Invalid login credentials attempt for email: {payload.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    # Generate session access token
    session_token = f"tok_{secrets.token_hex(24)}"
    return AuthTokenResponseSchema(
        access_token=session_token,
        token_type="bearer",
        user=UserResponseSchema(**user),
    )


@router.get(
    "/me/{user_id}",
    response_model=UserResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Get User Profile",
    description="Retrieves public user profile by user ID.",
)
async def get_user_profile(
    user_id: str,
    db: DatabaseManager = Depends(get_db),
) -> UserResponseSchema:
    """Retrieves user profile details."""
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found.",
        )
    return UserResponseSchema(
        user_id=user["user_id"],
        email=user["email"],
        full_name=user["full_name"],
        organization=user.get("organization"),
        role=user.get("role", "MERCHANT_ADMIN"),
        created_at=user.get("created_at"),
    )
