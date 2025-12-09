"""
Authentication and Authorization System with JWT, RBAC, and API key management.
Provides comprehensive security for the Optimus API.
"""

import jwt
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Union, Set
from dataclasses import dataclass
from enum import Enum

from fastapi import HTTPException, Depends, Request, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from ..config import get_settings, redis_manager, logger


# Security configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class UserRole(str, Enum):
    """User roles for RBAC."""
    ADMIN = "admin"
    DEVELOPER = "developer"
    VIEWER = "viewer"
    API_USER = "api_user"
    GUEST = "guest"


class Permission(str, Enum):
    """Granular permissions."""
    # Project permissions
    PROJECTS_READ = "projects:read"
    PROJECTS_WRITE = "projects:write"
    PROJECTS_DELETE = "projects:delete"
    PROJECTS_EXECUTE = "projects:execute"
    
    # Council permissions
    COUNCIL_READ = "council:read"
    COUNCIL_WRITE = "council:write"
    COUNCIL_EXECUTE = "council:execute"
    
    # Orchestration permissions
    ORCHESTRATION_READ = "orchestration:read"
    ORCHESTRATION_WRITE = "orchestration:write"
    ORCHESTRATION_EXECUTE = "orchestration:execute"
    
    # Deployment permissions
    DEPLOYMENT_READ = "deployment:read"
    DEPLOYMENT_WRITE = "deployment:write"
    DEPLOYMENT_EXECUTE = "deployment:execute"
    
    # System permissions
    SYSTEM_READ = "system:read"
    SYSTEM_WRITE = "system:write"
    SYSTEM_ADMIN = "system:admin"
    
    # API permissions
    API_READ = "api:read"
    API_WRITE = "api:write"
    API_ADMIN = "api:admin"


@dataclass
class RolePermissions:
    """Role to permissions mapping."""
    role: UserRole
    permissions: Set[Permission]


# Default role permissions
DEFAULT_ROLE_PERMISSIONS = {
    UserRole.ADMIN: {
        Permission.PROJECTS_READ, Permission.PROJECTS_WRITE, Permission.PROJECTS_DELETE, Permission.PROJECTS_EXECUTE,
        Permission.COUNCIL_READ, Permission.COUNCIL_WRITE, Permission.COUNCIL_EXECUTE,
        Permission.ORCHESTRATION_READ, Permission.ORCHESTRATION_WRITE, Permission.ORCHESTRATION_EXECUTE,
        Permission.DEPLOYMENT_READ, Permission.DEPLOYMENT_WRITE, Permission.DEPLOYMENT_EXECUTE,
        Permission.SYSTEM_READ, Permission.SYSTEM_WRITE, Permission.SYSTEM_ADMIN,
        Permission.API_READ, Permission.API_WRITE, Permission.API_ADMIN
    },
    UserRole.DEVELOPER: {
        Permission.PROJECTS_READ, Permission.PROJECTS_WRITE, Permission.PROJECTS_EXECUTE,
        Permission.COUNCIL_READ, Permission.COUNCIL_WRITE, Permission.COUNCIL_EXECUTE,
        Permission.ORCHESTRATION_READ, Permission.ORCHESTRATION_WRITE, Permission.ORCHESTRATION_EXECUTE,
        Permission.DEPLOYMENT_READ, Permission.DEPLOYMENT_WRITE, Permission.DEPLOYMENT_EXECUTE,
        Permission.SYSTEM_READ, Permission.API_READ
    },
    UserRole.VIEWER: {
        Permission.PROJECTS_READ,
        Permission.COUNCIL_READ,
        Permission.ORCHESTRATION_READ,
        Permission.DEPLOYMENT_READ,
        Permission.SYSTEM_READ,
        Permission.API_READ
    },
    UserRole.API_USER: {
        Permission.PROJECTS_READ, Permission.PROJECTS_WRITE,
        Permission.COUNCIL_READ, Permission.COUNCIL_EXECUTE,
        Permission.ORCHESTRATION_READ,
        Permission.API_READ
    },
    UserRole.GUEST: {
        Permission.PROJECTS_READ,
        Permission.SYSTEM_READ
    }
}


class User(BaseModel):
    """User model."""
    id: str
    username: str
    email: Optional[EmailStr] = None
    role: UserRole
    permissions: Set[Permission]
    is_active: bool = True
    created_at: datetime
    last_login: Optional[datetime] = None
    metadata: Dict[str, Any] = {}


class UserCreate(BaseModel):
    """User creation model."""
    username: str
    email: Optional[EmailStr] = None
    password: str
    role: UserRole = UserRole.VIEWER


class UserUpdate(BaseModel):
    """User update model."""
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class TokenData(BaseModel):
    """JWT token data."""
    sub: str  # user_id
    username: str
    role: UserRole
    permissions: List[Permission]
    iat: int
    exp: int
    jti: str  # JWT ID for revocation


class APIKey(BaseModel):
    """API Key model."""
    id: str
    name: str
    key_hash: str
    user_id: str
    permissions: Set[Permission]
    is_active: bool = True
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    usage_count: int = 0
    rate_limit: Optional[int] = None  # requests per hour


class LoginRequest(BaseModel):
    """Login request model."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


class PasswordChangeRequest(BaseModel):
    """Password change request."""
    current_password: str
    new_password: str


class AuthenticationManager:
    """Authentication and authorization manager."""
    
    def __init__(self, redis_client: Optional[Redis] = None):
        self.redis = redis_client or redis_manager.client
        self.settings = get_settings()
        
        # JWT configuration
        self.secret_key = self.settings.secret_key
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        self.refresh_token_expire_days = 7
        
        # In-memory stores (in production, use proper database)
        self.users: Dict[str, User] = {}
        self.api_keys: Dict[str, APIKey] = {}
        self.revoked_tokens: Set[str] = set()
        
        # Initialize with default admin user
        self._create_default_admin()
    
    def _create_default_admin(self):
        """Create default admin user."""
        admin_id = "admin-001"
        if admin_id not in self.users:
            self.users[admin_id] = User(
                id=admin_id,
                username="admin",
                email="admin@optimus.local",
                role=UserRole.ADMIN,
                permissions=DEFAULT_ROLE_PERMISSIONS[UserRole.ADMIN],
                created_at=datetime.now(timezone.utc)
            )
            logger.info("Created default admin user")
    
    def hash_password(self, password: str) -> str:
        """Hash a password."""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password."""
        return pwd_context.verify(plain_password, hashed_password)
    
    def generate_api_key(self) -> str:
        """Generate a new API key."""
        return f"opt_{secrets.token_urlsafe(32)}"
    
    def hash_api_key(self, api_key: str) -> str:
        """Hash an API key."""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    async def create_user(self, user_data: UserCreate, password_hash: str = None) -> User:
        """Create a new user."""
        user_id = str(uuid.uuid4())
        
        # Check if username already exists
        for user in self.users.values():
            if user.username == user_data.username:
                raise HTTPException(
                    status_code=400,
                    detail="Username already exists"
                )
        
        # Get role permissions
        permissions = DEFAULT_ROLE_PERMISSIONS.get(user_data.role, set())
        
        user = User(
            id=user_id,
            username=user_data.username,
            email=user_data.email,
            role=user_data.role,
            permissions=permissions,
            created_at=datetime.now(timezone.utc)
        )
        
        self.users[user_id] = user
        
        # Store password hash
        if password_hash:
            await self.redis.set(f"user_password:{user_id}", password_hash)
        
        logger.info(f"Created user: {user.username} with role: {user.role}")
        return user
    
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password."""
        # Find user by username
        user = None
        for u in self.users.values():
            if u.username == username:
                user = u
                break
        
        if not user or not user.is_active:
            return None
        
        # Verify password
        password_hash = await self.redis.get(f"user_password:{user.id}")
        if not password_hash or not self.verify_password(password, password_hash.decode()):
            return None
        
        # Update last login
        user.last_login = datetime.now(timezone.utc)
        
        logger.info(f"User authenticated: {username}")
        return user
    
    async def authenticate_api_key(self, api_key: str) -> Optional[APIKey]:
        """Authenticate using API key."""
        key_hash = self.hash_api_key(api_key)
        
        # Find API key
        api_key_obj = None
        for key in self.api_keys.values():
            if key.key_hash == key_hash:
                api_key_obj = key
                break
        
        if not api_key_obj or not api_key_obj.is_active:
            return None
        
        # Check expiration
        if api_key_obj.expires_at and datetime.now(timezone.utc) > api_key_obj.expires_at:
            return None
        
        # Update usage
        api_key_obj.last_used = datetime.now(timezone.utc)
        api_key_obj.usage_count += 1
        
        logger.debug(f"API key authenticated: {api_key_obj.name}")
        return api_key_obj
    
    def create_access_token(self, user: User) -> str:
        """Create JWT access token."""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self.access_token_expire_minutes)
        
        token_data = TokenData(
            sub=user.id,
            username=user.username,
            role=user.role,
            permissions=list(user.permissions),
            iat=int(now.timestamp()),
            exp=int(expire.timestamp()),
            jti=str(uuid.uuid4())
        )
        
        return jwt.encode(
            token_data.model_dump(),
            self.secret_key,
            algorithm=self.algorithm
        )
    
    def create_refresh_token(self, user: User) -> str:
        """Create JWT refresh token."""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=self.refresh_token_expire_days)
        
        token_data = {
            "sub": user.id,
            "type": "refresh",
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "jti": str(uuid.uuid4())
        }
        
        return jwt.encode(token_data, self.secret_key, algorithm=self.algorithm)
    
    async def verify_token(self, token: str) -> Optional[TokenData]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check if token is revoked
            jti = payload.get("jti")
            if jti and await self.is_token_revoked(jti):
                return None
            
            # Check if it's a refresh token
            if payload.get("type") == "refresh":
                return None
            
            return TokenData(**payload)
            
        except jwt.ExpiredSignatureError:
            logger.debug("Token expired")
            return None
        except jwt.JWTError as e:
            logger.debug(f"Token validation error: {e}")
            return None
    
    async def verify_refresh_token(self, token: str) -> Optional[str]:
        """Verify refresh token and return user_id."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check if it's a refresh token
            if payload.get("type") != "refresh":
                return None
            
            # Check if token is revoked
            jti = payload.get("jti")
            if jti and await self.is_token_revoked(jti):
                return None
            
            return payload.get("sub")
            
        except jwt.JWTError:
            return None
    
    async def revoke_token(self, jti: str):
        """Revoke a token."""
        await self.redis.sadd("revoked_tokens", jti)
        await self.redis.expire("revoked_tokens", 86400 * 7)  # 7 days
        logger.info(f"Token revoked: {jti}")
    
    async def is_token_revoked(self, jti: str) -> bool:
        """Check if token is revoked."""
        return await self.redis.sismember("revoked_tokens", jti)
    
    async def create_api_key(self, user_id: str, name: str, permissions: Set[Permission] = None, 
                           expires_in_days: int = None) -> tuple[str, APIKey]:
        """Create a new API key."""
        api_key = self.generate_api_key()
        key_hash = self.hash_api_key(api_key)
        
        # Get user permissions if not specified
        user = self.users.get(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if permissions is None:
            permissions = user.permissions
        else:
            # Ensure user has the permissions they're granting
            if not permissions.issubset(user.permissions):
                raise HTTPException(
                    status_code=403,
                    detail="Cannot grant permissions you don't have"
                )
        
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
        
        api_key_obj = APIKey(
            id=str(uuid.uuid4()),
            name=name,
            key_hash=key_hash,
            user_id=user_id,
            permissions=permissions,
            created_at=datetime.now(timezone.utc),
            expires_at=expires_at
        )
        
        self.api_keys[api_key_obj.id] = api_key_obj
        
        logger.info(f"Created API key: {name} for user: {user.username}")
        return api_key, api_key_obj
    
    def has_permission(self, user_permissions: Set[Permission], required_permission: Permission) -> bool:
        """Check if user has required permission."""
        return required_permission in user_permissions
    
    def has_any_permission(self, user_permissions: Set[Permission], required_permissions: List[Permission]) -> bool:
        """Check if user has any of the required permissions."""
        return bool(user_permissions.intersection(required_permissions))
    
    def has_all_permissions(self, user_permissions: Set[Permission], required_permissions: List[Permission]) -> bool:
        """Check if user has all required permissions."""
        return set(required_permissions).issubset(user_permissions)


# Global auth manager
auth_manager = AuthenticationManager()


# Dependency functions
async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> User:
    """Get current authenticated user from JWT token."""
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token_data = await auth_manager.verify_token(credentials.credentials)
    if not token_data:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    user = auth_manager.users.get(token_data.sub)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    
    return user


async def get_current_user_from_api_key(api_key: str = Security(api_key_header)) -> User:
    """Get current user from API key."""
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    
    api_key_obj = await auth_manager.authenticate_api_key(api_key)
    if not api_key_obj:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired API key"
        )
    
    user = auth_manager.users.get(api_key_obj.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    
    # Override user permissions with API key permissions
    user.permissions = api_key_obj.permissions
    return user


async def get_current_user_flexible(
    request: Request,
    jwt_credentials: HTTPAuthorizationCredentials = Security(security),
    api_key: str = Security(api_key_header)
) -> User:
    """Get current user from either JWT token or API key."""
    # Try API key first
    if api_key:
        try:
            return await get_current_user_from_api_key(api_key)
        except HTTPException:
            pass
    
    # Try JWT token
    if jwt_credentials:
        try:
            return await get_current_user(jwt_credentials)
        except HTTPException:
            pass
    
    # No valid authentication
    raise HTTPException(
        status_code=401,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"}
    )


def require_permission(permission: Permission):
    """Dependency factory for permission checking."""
    async def check_permission(user: User = Depends(get_current_user_flexible)):
        if not auth_manager.has_permission(user.permissions, permission):
            raise HTTPException(
                status_code=403,
                detail=f"Permission required: {permission}"
            )
        return user
    
    return check_permission


def require_any_permission(permissions: List[Permission]):
    """Dependency factory for checking any of multiple permissions."""
    async def check_permissions(user: User = Depends(get_current_user_flexible)):
        if not auth_manager.has_any_permission(user.permissions, permissions):
            raise HTTPException(
                status_code=403,
                detail=f"One of these permissions required: {permissions}"
            )
        return user
    
    return check_permissions


def require_role(role: UserRole):
    """Dependency factory for role checking."""
    async def check_role(user: User = Depends(get_current_user_flexible)):
        if user.role != role:
            raise HTTPException(
                status_code=403,
                detail=f"Role required: {role}"
            )
        return user
    
    return check_role


# Admin-only dependency
RequireAdmin = Depends(require_role(UserRole.ADMIN))

# Common permission dependencies
RequireProjectsRead = Depends(require_permission(Permission.PROJECTS_READ))
RequireProjectsWrite = Depends(require_permission(Permission.PROJECTS_WRITE))
RequireCouncilExecute = Depends(require_permission(Permission.COUNCIL_EXECUTE))
RequireOrchestrationExecute = Depends(require_permission(Permission.ORCHESTRATION_EXECUTE))
RequireSystemAdmin = Depends(require_permission(Permission.SYSTEM_ADMIN))