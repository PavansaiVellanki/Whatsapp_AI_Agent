"""
Rate limiting middleware and dependencies for FastAPI
"""
from fastapi import Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Optional
import logging
import time
from app.services.rate_limit_service import RateLimitService
from app.utils.config import RATE_LIMIT_PER_MINUTE, RATE_LIMIT_PER_HOUR

logger = logging.getLogger(__name__)

# Global rate limit service instance
_rate_limit_service: Optional[RateLimitService] = None


def get_rate_limit_service() -> RateLimitService:
    """Get or create rate limit service instance"""
    global _rate_limit_service
    if _rate_limit_service is None:
        _rate_limit_service = RateLimitService()
    return _rate_limit_service


def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request
    
    Args:
        request: FastAPI request object
    
    Returns:
        Client IP address as string
    """
    # Check for forwarded headers (if behind proxy/load balancer)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP in the chain
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # Fallback to direct client IP
    if request.client:
        return request.client.host
    
    return "unknown"


async def rate_limit_dependency(
    request: Request,
    phone_number: Optional[str] = None,
    rate_limit_service: RateLimitService = Depends(get_rate_limit_service)
) -> None:
    """
    FastAPI dependency to enforce rate limiting
    
    Checks both phone number and IP address limits.
    Raises HTTPException with 429 status if limit is exceeded.
    
    Args:
        request: FastAPI request object
        phone_number: Optional phone number identifier
        rate_limit_service: Rate limit service instance
    
    Raises:
        HTTPException: 429 Too Many Requests if rate limit exceeded
    """
    # Extract identifiers
    ip_address = get_client_ip(request)
    
    # Check rate limit for phone number if provided
    if phone_number:
        phone_allowed, phone_info = rate_limit_service.check_rate_limit(phone_number)
        if not phone_allowed:
            reset_time = min(phone_info["reset_time_minute"], phone_info["reset_time_hour"])
            retry_after = max(0, reset_time - int(time.time()))
            
            logger.warning(f"Rate limit exceeded for phone number: {phone_number}")
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later.",
                headers={
                    "X-RateLimit-Limit-Minute": str(RATE_LIMIT_PER_MINUTE),
                    "X-RateLimit-Limit-Hour": str(RATE_LIMIT_PER_HOUR),
                    "X-RateLimit-Remaining-Minute": str(phone_info["remaining_minute"]),
                    "X-RateLimit-Remaining-Hour": str(phone_info["remaining_hour"]),
                    "X-RateLimit-Reset-Minute": str(phone_info["reset_time_minute"]),
                    "X-RateLimit-Reset-Hour": str(phone_info["reset_time_hour"]),
                    "Retry-After": str(retry_after)
                }
            )
    
    # Check rate limit for IP address
    ip_allowed, ip_info = rate_limit_service.check_rate_limit(ip_address)
    if not ip_allowed:
        reset_time = min(ip_info["reset_time_minute"], ip_info["reset_time_hour"])
        retry_after = max(0, reset_time - int(time.time()))
        
        logger.warning(f"Rate limit exceeded for IP address: {ip_address}")
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later.",
            headers={
                "X-RateLimit-Limit-Minute": str(RATE_LIMIT_PER_MINUTE),
                "X-RateLimit-Limit-Hour": str(RATE_LIMIT_PER_HOUR),
                "X-RateLimit-Remaining-Minute": str(ip_info["remaining_minute"]),
                "X-RateLimit-Remaining-Hour": str(ip_info["remaining_hour"]),
                "X-RateLimit-Reset-Minute": str(ip_info["reset_time_minute"]),
                "X-RateLimit-Reset-Hour": str(ip_info["reset_time_hour"]),
                "Retry-After": str(retry_after)
            }
        )


async def rate_limit_by_phone(
    request: Request,
    phone_number: str,
    rate_limit_service: RateLimitService = Depends(get_rate_limit_service)
) -> None:
    """
    Rate limit dependency that requires a phone number
    
    Args:
        request: FastAPI request object
        phone_number: Phone number to check
        rate_limit_service: Rate limit service instance
    
    Raises:
        HTTPException: 429 Too Many Requests if rate limit exceeded
    """
    await rate_limit_dependency(request, phone_number, rate_limit_service)


async def rate_limit_by_ip(
    request: Request,
    rate_limit_service: RateLimitService = Depends(get_rate_limit_service)
) -> None:
    """
    Rate limit dependency that only checks IP address
    
    Args:
        request: FastAPI request object
        rate_limit_service: Rate limit service instance
    
    Raises:
        HTTPException: 429 Too Many Requests if rate limit exceeded
    """
    await rate_limit_dependency(request, None, rate_limit_service)

