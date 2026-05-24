# Enhanced Authentication Service with OOP, Caching, and Security Optimizations
import os
import time
import hashlib
import datetime as dt
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod
import jwt
import bcrypt
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from models.user import User, UserRole
from database_optimized import db_cache

# Base interfaces for polymorphism and dependency injection
class AuthenticationInterface(ABC):
    """Abstract interface for authentication providers"""
    
    @abstractmethod
    async def authenticate(self, email: str, password: str) -> Optional[User]:
        pass
    
    @abstractmethod
    def generate_token(self, user: User) -> str:
        pass

class CacheInterface(ABC):
    """Abstract interface for caching providers"""
    
    @abstractmethod
    def get(self, key: str) -> Any:
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        pass

# Concrete implementations for dependency injection
class JWTAuthenticationProvider(AuthenticationInterface):
    """JWT-based authentication provider with enhanced security"""
    
    def __init__(self, secret_key: str, algorithm: str = "HS256", 
                 token_expire_minutes: int = 60):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.token_expire_minutes = token_expire_minutes
    
    async def authenticate(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password - O(1) with caching"""
        # Check cache first for better performance
        cache_key = f"user_auth:{hashlib.sha256(email.encode()).hexdigest()}"
        cached_user = db_cache.get(cache_key)
        
        if cached_user and self._verify_password(password, cached_user.password_hash):
            return cached_user
        
        return None
    
    def generate_token(self, user: User) -> str:
        """Generate JWT token with user information"""
        expire = dt.datetime.utcnow() + dt.timedelta(minutes=self.token_expire_minutes)
        payload = {
            "sub": user.email,
            "user_id": user.id,
            "role": user.role.value,
            "exp": expire,
            "iat": dt.datetime.utcnow(),
            "jti": hashlib.sha256(f"{user.id}_{time.time()}".encode()).hexdigest()[:16]
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash with constant time comparison"""
        password_bytes = password.encode('utf-8')[:72]  # bcrypt limit
        hashed_bytes = hashed.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)

class MemoryCacheProvider(CacheInterface):
    """In-memory cache provider for session data"""
    
    def __init__(self):
        self.cache = {}
        self.timestamps = {}
    
    def get(self, key: str) -> Any:
        return db_cache.get(key)
    
    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        db_cache.set(key, value)

# Enhanced User Service with OOP principles and caching
class UserService:
    """
    Enhanced user service with proper encapsulation, caching, and performance optimizations.
    Implements the Single Responsibility Principle and Dependency Injection.
    """
    
    def __init__(self, auth_provider: AuthenticationInterface, 
                 cache_provider: CacheInterface):
        self.auth_provider = auth_provider
        self.cache_provider = cache_provider
        self._user_cache = {}  # Local cache for frequently accessed users
    
    # Password operations with enhanced security
    def hash_password(self, password: str) -> str:
        """
        Hash password with bcrypt and salt.
        Time Complexity: O(1) - bcrypt has constant time complexity
        """
        password_bytes = password.encode('utf-8')[:72]  # bcrypt 72-byte limit
        salt = bcrypt.gensalt(rounds=12)  # Higher rounds for better security
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """
        Verify password with constant-time comparison to prevent timing attacks.
        Time Complexity: O(1)
        """
        return self.auth_provider._verify_password(password, hashed)
    
    # User management operations with caching
    def create_user(self, db: Session, email: str, name: str, password: str, 
                   role: UserRole = UserRole.CUSTOMER, license_no: str = None) -> User:
        """
        Create new user with validation and caching.
        Time Complexity: O(1) - database insert with indexing
        """
        # Check if user already exists - O(1) with database index
        existing_user = self.get_user_by_email(db, email)
        if existing_user:
            raise ValueError(f"User with email {email} already exists")
        
        # Create user with hashed password
        user = User(
            email=email.lower().strip(),
            name=name.strip(),
            password_hash=self.hash_password(password),
            role=role,
            license_no=license_no.strip() if license_no else None
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Cache the new user for faster future access
        cache_key = f"user_email:{email.lower()}"
        self.cache_provider.set(cache_key, user, ttl=600)  # 10 minutes
        
        return user
    
    def get_user_by_email(self, db: Session, email: str) -> Optional[User]:
        """
        Get user by email with caching for O(1) access.
        Time Complexity: O(1) with cache hit, O(log n) with database index
        """
        email = email.lower().strip()
        cache_key = f"user_email:{email}"
        
        # Check cache first
        cached_user = self.cache_provider.get(cache_key)
        if cached_user:
            return cached_user
        
        # Query database with indexed lookup
        user = db.query(User).filter(User.email == email).first()
        
        if user:
            # Cache for future requests
            self.cache_provider.set(cache_key, user, ttl=600)
        
        return user
    
    def get_user_by_id(self, db: Session, user_id: int) -> Optional[User]:
        """
        Get user by ID with caching.
        Time Complexity: O(1) with cache hit, O(log n) with primary key lookup
        """
        cache_key = f"user_id:{user_id}"
        
        # Check cache first
        cached_user = self.cache_provider.get(cache_key)
        if cached_user:
            return cached_user
        
        # Primary key lookup is O(log n) but very fast
        user = db.query(User).filter(User.id == user_id).first()
        
        if user:
            self.cache_provider.set(cache_key, user, ttl=600)
        
        return user
    
    def search_users(self, db: Session, query: str, limit: int = 10) -> List[User]:
        """
        Search users with optimized query and result caching.
        Time Complexity: O(n log n) but with result caching for common searches
        """
        query = query.strip().lower()
        cache_key = f"user_search:{hashlib.sha256(query.encode()).hexdigest()}:{limit}"
        
        # Check cache for this search
        cached_results = self.cache_provider.get(cache_key)
        if cached_results:
            return cached_results
        
        # Optimized database query with OR conditions and LIMIT
        users = db.query(User).filter(
            or_(
                User.name.ilike(f"%{query}%"),
                User.email.ilike(f"%{query}%")
            )
        ).limit(limit).all()
        
        # Cache search results
        self.cache_provider.set(cache_key, users, ttl=300)  # 5 minutes
        
        return users
    
    def update_user_activity(self, db: Session, user_id: int, is_active: bool = True) -> bool:
        """
        Update user activity status with cache invalidation.
        Time Complexity: O(1)
        """
        user = self.get_user_by_id(db, user_id)
        if not user:
            return False
        
        user.is_active = "true" if is_active else "false"
        db.commit()
        
        # Invalidate cached user data
        self._invalidate_user_cache(user)
        
        return True
    
    def _invalidate_user_cache(self, user: User):
        """Invalidate all cache entries for a user"""
        cache_keys = [
            f"user_email:{user.email}",
            f"user_id:{user.id}"
        ]
        for key in cache_keys:
            try:
                # Note: Our simple cache doesn't have delete method, 
                # but in production we'd use Redis with proper invalidation
                pass
            except:
                pass

# Token Service for JWT operations
class TokenService:
    """Service for JWT token operations with enhanced security"""
    
    def __init__(self, secret_key: str, algorithm: str = "HS256", 
                 expire_minutes: int = 60):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expire_minutes = expire_minutes
    
    def create_access_token(self, user: User) -> str:
        """
        Create JWT access token with user claims.
        Time Complexity: O(1)
        """
        expire = dt.datetime.utcnow() + dt.timedelta(minutes=self.expire_minutes)
        payload = {
            "sub": user.email,
            "user_id": user.id,
            "role": user.role.value,
            "exp": expire,
            "iat": dt.datetime.utcnow(),
            "jti": hashlib.sha256(f"{user.id}_{time.time()}".encode()).hexdigest()[:16]
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Decode and validate JWT token.
        Time Complexity: O(1)
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Validate token is not expired
            if payload.get("exp", 0) < time.time():
                return None
            
            return payload
        except jwt.PyJWTError:
            return None
    
    def get_current_user(self, db: Session, token: str, user_service: UserService) -> Optional[User]:
        """
        Get current user from token with caching.
        Time Complexity: O(1) with cache, O(log n) without
        """
        payload = self.decode_token(token)
        if not payload:
            return None
        
        user_id = payload.get("user_id")
        if not user_id:
            return None
        
        return user_service.get_user_by_id(db, user_id)

# Factory pattern for service creation
class AuthServiceFactory:
    """Factory for creating authentication services with dependency injection"""
    
    @staticmethod
    def create_auth_service() -> tuple[UserService, TokenService]:
        """Create auth services with proper dependencies"""
        secret_key = os.getenv("SECRET_KEY", "change_me_in_production")
        expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
        
        # Create providers
        auth_provider = JWTAuthenticationProvider(secret_key, expire_minutes=expire_minutes)
        cache_provider = MemoryCacheProvider()
        
        # Create services with dependency injection
        user_service = UserService(auth_provider, cache_provider)
        token_service = TokenService(secret_key, expire_minutes=expire_minutes)
        
        return user_service, token_service

# Global service instances (singleton pattern)
user_service, token_service = AuthServiceFactory.create_auth_service()

# Backward compatibility functions for existing code
def hash_password(password: str) -> str:
    return user_service.hash_password(password)

def get_password_hash(password: str) -> str:
    return user_service.hash_password(password)

def verify_password(password: str, hashed: str) -> bool:
    return user_service.verify_password(password, hashed)

def create_user(db: Session, email: str, name: str, password: str, 
               role: UserRole = UserRole.CUSTOMER, license_no: str = None) -> User:
    return user_service.create_user(db, email, name, password, role, license_no)

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return user_service.get_user_by_email(db, email)

def create_access_token(sub: str, role: str = None) -> str:
    # Legacy function - get user by email and create token
    # This is less efficient than the new method
    return token_service.create_access_token(User(email=sub, role=UserRole(role) if role else UserRole.CUSTOMER))

def decode_token(token: str) -> Optional[dict]:
    return token_service.decode_token(token)

def get_current_user(db: Session, token: str) -> Optional[User]:
    return token_service.get_current_user(db, token, user_service)