import json
import redis
from typing import Optional, Any
from functools import wraps

from app.config import get_settings

settings = get_settings()

# Create Redis client
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


class CacheService:
    """
    Redis cache service for caching product details and other data.
    
    This service provides methods for:
    - Setting cache with TTL
    - Getting cached values
    - Invalidating cache
    - Cache decorator for functions
    """
    
    def __init__(self, client: redis.Redis = None, ttl: int = None):
        self.client = client or redis_client
        self.ttl = ttl or settings.CACHE_TTL
    
    def _make_key(self, prefix: str, key: str) -> str:
        """Create a namespaced cache key."""
        return f"{prefix}:{key}"
    
    def get(self, prefix: str, key: str) -> Optional[Any]:
        """
        Get a value from cache.
        
        Args:
            prefix: Cache key prefix (e.g., 'product')
            key: Unique identifier
            
        Returns:
            Cached value or None if not found
        """
        cache_key = self._make_key(prefix, key)
        try:
            value = self.client.get(cache_key)
            if value:
                return json.loads(value)
            return None
        except (redis.RedisError, json.JSONDecodeError):
            return None
    
    def set(self, prefix: str, key: str, value: Any, ttl: int = None) -> bool:
        """
        Set a value in cache with TTL.
        
        Args:
            prefix: Cache key prefix
            key: Unique identifier
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds (optional, uses default if not provided)
            
        Returns:
            True if successful, False otherwise
        """
        cache_key = self._make_key(prefix, key)
        ttl = ttl or self.ttl
        try:
            serialized = json.dumps(value, default=str)
            self.client.setex(cache_key, ttl, serialized)
            return True
        except (redis.RedisError, TypeError):
            return False
    
    def delete(self, prefix: str, key: str) -> bool:
        """
        Delete a value from cache.
        
        Args:
            prefix: Cache key prefix
            key: Unique identifier
            
        Returns:
            True if deleted, False otherwise
        """
        cache_key = self._make_key(prefix, key)
        try:
            self.client.delete(cache_key)
            return True
        except redis.RedisError:
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.
        
        Args:
            pattern: Redis key pattern (e.g., 'product:*')
            
        Returns:
            Number of keys deleted
        """
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except redis.RedisError:
            return 0


# Singleton cache service instance
cache_service = CacheService()


def cached(prefix: str, key_arg: str = None, ttl: int = None):
    """
    Decorator for caching function results.
    
    Args:
        prefix: Cache key prefix
        key_arg: Name of the argument to use as cache key
        ttl: Cache TTL in seconds
        
    Example:
        @cached("product", key_arg="product_id")
        def get_product(product_id: int):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract key from arguments
            if key_arg:
                key = str(kwargs.get(key_arg, args[0] if args else "default"))
            else:
                key = "default"
            
            # Try to get from cache
            cached_value = cache_service.get(prefix, key)
            if cached_value is not None:
                return cached_value
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            if result is not None:
                cache_service.set(prefix, key, result, ttl)
            
            return result
        return wrapper
    return decorator
