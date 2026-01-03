"""
Rate limiting service using Redis
"""
import redis
import time
import logging
from typing import Tuple, Dict, Optional
from app.utils.config import (
    REDIS_HOST,
    REDIS_PORT,
    REDIS_PASSWORD,
    REDIS_DB,
    RATE_LIMIT_ENABLED,
    RATE_LIMIT_PER_MINUTE,
    RATE_LIMIT_PER_HOUR
)

logger = logging.getLogger(__name__)


class RateLimitService:
    """Service for managing rate limits using Redis"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.enabled = RATE_LIMIT_ENABLED
        self._connect_redis()
    
    def _connect_redis(self):
        """Initialize Redis connection"""
        if not self.enabled:
            logger.info("Rate limiting is disabled")
            return
        
        try:
            self.redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_PASSWORD,
                db=REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            # Test connection
            self.redis_client.ping()
            logger.info(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
        except redis.ConnectionError as e:
            logger.warning(f"Failed to connect to Redis: {e}. Rate limiting will be disabled.")
            self.redis_client = None
            self.enabled = False
        except Exception as e:
            logger.error(f"Unexpected error connecting to Redis: {e}")
            self.redis_client = None
            self.enabled = False
    
    def check_rate_limit(
        self,
        identifier: str,
        limit_per_minute: Optional[int] = None,
        limit_per_hour: Optional[int] = None
    ) -> Tuple[bool, Dict]:
        """
        Check if request is within rate limits using sliding window algorithm
        
        Args:
            identifier: Unique identifier (phone number, IP address, or combination)
            limit_per_minute: Requests allowed per minute (defaults to config value)
            limit_per_hour: Requests allowed per hour (defaults to config value)
        
        Returns:
            Tuple of (is_allowed, rate_limit_info)
            rate_limit_info contains:
                - allowed: bool
                - remaining_minute: int
                - remaining_hour: int
                - reset_time_minute: int (Unix timestamp)
                - reset_time_hour: int (Unix timestamp)
        """
        if not self.enabled or not self.redis_client:
            # Fail-open: if Redis is unavailable, allow the request
            logger.debug("Rate limiting disabled or Redis unavailable, allowing request")
            return True, {
                "allowed": True,
                "remaining_minute": limit_per_minute or RATE_LIMIT_PER_MINUTE,
                "remaining_hour": limit_per_hour or RATE_LIMIT_PER_HOUR,
                "reset_time_minute": int(time.time()) + 60,
                "reset_time_hour": int(time.time()) + 3600
            }
        
        limit_per_minute = limit_per_minute or RATE_LIMIT_PER_MINUTE
        limit_per_hour = limit_per_hour or RATE_LIMIT_PER_HOUR
        
        current_time = time.time()
        
        try:
            # Check per-minute limit
            minute_key = f"rate_limit:minute:{identifier}"
            minute_allowed, minute_remaining, minute_reset = self._check_window(
                minute_key, limit_per_minute, 60, current_time
            )
            
            # Check per-hour limit
            hour_key = f"rate_limit:hour:{identifier}"
            hour_allowed, hour_remaining, hour_reset = self._check_window(
                hour_key, limit_per_hour, 3600, current_time
            )
            
            # Request is allowed only if both limits are not exceeded
            is_allowed = minute_allowed and hour_allowed
            
            if not is_allowed:
                logger.warning(
                    f"Rate limit exceeded for {identifier}: "
                    f"minute={minute_remaining}/{limit_per_minute}, "
                    f"hour={hour_remaining}/{limit_per_hour}"
                )
            
            return is_allowed, {
                "allowed": is_allowed,
                "remaining_minute": minute_remaining,
                "remaining_hour": hour_remaining,
                "reset_time_minute": minute_reset,
                "reset_time_hour": hour_reset
            }
        
        except redis.RedisError as e:
            logger.error(f"Redis error during rate limit check: {e}")
            # Fail-open: allow request if Redis fails
            return True, {
                "allowed": True,
                "remaining_minute": limit_per_minute,
                "remaining_hour": limit_per_hour,
                "reset_time_minute": int(current_time) + 60,
                "reset_time_hour": int(current_time) + 3600
            }
        except Exception as e:
            logger.error(f"Unexpected error during rate limit check: {e}")
            # Fail-open: allow request on unexpected errors
            return True, {
                "allowed": True,
                "remaining_minute": limit_per_minute,
                "remaining_hour": limit_per_hour,
                "reset_time_minute": int(current_time) + 60,
                "reset_time_hour": int(current_time) + 3600
            }
    
    def _check_window(
        self,
        key: str,
        limit: int,
        window_seconds: int,
        current_time: float
    ) -> Tuple[bool, int, int]:
        """
        Check rate limit for a specific time window using sliding window algorithm
        
        Args:
            key: Redis key for this window
            limit: Maximum requests allowed
            window_seconds: Size of time window in seconds
            current_time: Current Unix timestamp
        
        Returns:
            Tuple of (is_allowed, remaining_requests, reset_timestamp)
        """
        window_start = current_time - window_seconds
        
        # Use Redis sorted set to track requests in sliding window
        # Score is the timestamp, value is also timestamp (for uniqueness)
        
        # Remove old entries outside the window
        self.redis_client.zremrangebyscore(key, 0, window_start)
        
        # Count current requests in window
        current_count = self.redis_client.zcard(key)
        
        # Check if limit is exceeded
        if current_count >= limit:
            # Calculate reset time (when oldest request expires)
            oldest = self.redis_client.zrange(key, 0, 0, withscores=True)
            if oldest:
                reset_time = int(oldest[0][1]) + window_seconds
            else:
                reset_time = int(current_time) + window_seconds
            return False, 0, reset_time
        
        # Add current request
        self.redis_client.zadd(key, {str(current_time): current_time})
        # Set expiration on the key (window_seconds + small buffer)
        self.redis_client.expire(key, window_seconds + 60)
        
        remaining = limit - current_count - 1
        reset_time = int(current_time) + window_seconds
        
        return True, remaining, reset_time
    
    def reset_rate_limit(self, identifier: str):
        """
        Reset rate limit for an identifier (useful for testing or admin actions)
        
        Args:
            identifier: Identifier to reset
        """
        if not self.enabled or not self.redis_client:
            return
        
        try:
            minute_key = f"rate_limit:minute:{identifier}"
            hour_key = f"rate_limit:hour:{identifier}"
            self.redis_client.delete(minute_key, hour_key)
            logger.info(f"Rate limit reset for {identifier}")
        except Exception as e:
            logger.error(f"Error resetting rate limit: {e}")


