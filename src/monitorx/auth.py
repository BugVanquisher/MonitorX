# Copyright 2025 MonitorX Team
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Authentication and authorization for MonitorX API."""
import os
from typing import Optional
from datetime import datetime, timedelta
from fastapi import Security, HTTPException, status, Depends
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from loguru import logger


# API Key Authentication
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


class APIKeyAuth:
    """API Key authentication handler."""

    def __init__(self):
        # Load API keys from environment
        self.api_keys = set(
            key.strip()
            for key in os.getenv("API_KEYS", "").split(",")
            if key.strip()
        )
        self.enabled = os.getenv("API_KEY_ENABLED", "false").lower() == "true"

    def verify_api_key(self, api_key: Optional[str] = Security(API_KEY_HEADER)) -> str:
        """Verify API key from header."""
        if not self.enabled:
            return "anonymous"  # Auth disabled

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required. Provide X-API-Key header."
            )

        if api_key not in self.api_keys:
            logger.warning(f"Invalid API key attempted: {api_key[:8]}...")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )

        logger.debug(f"Authenticated with API key: {api_key[:8]}...")
        return api_key


# JWT Authentication (for future user-based auth)
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "30"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


class Token(BaseModel):
    """JWT Token response."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token payload data."""
    username: Optional[str] = None
    scopes: list[str] = []


class User(BaseModel):
    """User model."""
    username: str
    email: Optional[str] = None
    disabled: bool = False
    scopes: list[str] = []


class JWTAuth:
    """JWT authentication handler."""

    def __init__(self):
        self.enabled = os.getenv("JWT_ENABLED", "false").lower() == "true"
        self.secret_key = SECRET_KEY
        self.algorithm = ALGORITHM

    def create_access_token(
        self, data: dict, expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token."""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

        return encoded_jwt

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Hash password."""
        return pwd_context.hash(password)

    async def get_current_user(
        self, credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
    ) -> User:
        """Get current user from JWT token."""
        if not self.enabled:
            return User(username="anonymous", scopes=["*"])

        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            payload = jwt.decode(
                credentials.credentials, self.secret_key, algorithms=[self.algorithm]
            )
            username: str = payload.get("sub")
            scopes: list = payload.get("scopes", [])

            if username is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            token_data = TokenData(username=username, scopes=scopes)

        except JWTError as e:
            logger.warning(f"JWT validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # In production, fetch user from database
        user = User(username=token_data.username, scopes=token_data.scopes)

        if user.disabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is disabled"
            )

        return user


# Global instances
api_key_auth = APIKeyAuth()
jwt_auth = JWTAuth()


# Dependency functions for FastAPI
def get_api_key(api_key: Optional[str] = Security(API_KEY_HEADER)) -> str:
    """FastAPI dependency for API key authentication."""
    return api_key_auth.verify_api_key(api_key)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> User:
    """FastAPI dependency for JWT authentication."""
    return await jwt_auth.get_current_user(credentials)


def check_scopes(required_scopes: list[str]):
    """Create a dependency that checks for required scopes."""
    async def scope_checker(user: User = Depends(get_current_user)) -> User:
        if "*" in user.scopes:
            return user  # Admin has all scopes

        for scope in required_scopes:
            if scope not in user.scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Not enough permissions. Required scope: {scope}"
                )

        return user

    return scope_checker
