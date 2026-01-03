"""
Image utility functions for processing images before sending to LLM
"""
import io
import logging
from typing import Optional
from PIL import Image

logger = logging.getLogger(__name__)

def resize_image_for_llm(image_bytes: bytes, max_dimension: int = 768) -> bytes:
    """
    Resize image to reduce token consumption while maintaining quality
    
    For Gemini 2.5, images ≤384px = 258 tokens, larger images are tiled.
    Resizing to max 768px ensures reasonable token usage while maintaining detail.
    
    Args:
        image_bytes: Original image bytes
        max_dimension: Maximum width or height (default 768)
        
    Returns:
        Resized image bytes, or original bytes if resize failed
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        original_format = img.format or 'JPEG'
        
        # Get original dimensions
        width, height = img.size
        logger.info(f"Original image dimensions: {width}x{height}, format: {original_format}")
        
        # Check if resizing is needed
        if width <= max_dimension and height <= max_dimension:
            logger.info(f"Image already within size limit, no resizing needed")
            return image_bytes
        
        # Calculate new dimensions maintaining aspect ratio
        if width > height:
            new_width = max_dimension
            new_height = int(height * (max_dimension / width))
        else:
            new_height = max_dimension
            new_width = int(width * (max_dimension / height))
        
        logger.info(f"Resizing image to: {new_width}x{new_height}")
        
        # Resize with high-quality resampling
        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Convert back to bytes
        output = io.BytesIO()
        
        # Preserve format, use JPEG for photos, PNG for transparency
        if original_format == 'PNG' and img.mode in ('RGBA', 'LA'):
            # Keep PNG for images with transparency
            img_resized.save(output, format='PNG', optimize=True)
        else:
            # Use JPEG for photos (smaller file size)
            if img_resized.mode in ('RGBA', 'LA', 'P'):
                # Convert to RGB if needed
                rgb_img = Image.new('RGB', img_resized.size, (255, 255, 255))
                if img_resized.mode == 'P':
                    img_resized = img_resized.convert('RGBA')
                rgb_img.paste(img_resized, mask=img_resized.split()[-1] if img_resized.mode == 'RGBA' else None)
                img_resized = rgb_img
            
            img_resized.save(output, format='JPEG', quality=85, optimize=True)
        
        resized_bytes = output.getvalue()
        logger.info(f"Image resized: {len(image_bytes)} bytes -> {len(resized_bytes)} bytes")
        
        return resized_bytes
        
    except Exception as e:
        logger.error(f"Error resizing image: {e}", exc_info=True)
        # Return original bytes if resize fails
        return image_bytes

def get_image_mime_type(image_bytes: bytes) -> str:
    """
    Detect MIME type from image bytes
    
    Args:
        image_bytes: Image file bytes
        
    Returns:
        MIME type string (e.g., 'image/jpeg', 'image/png')
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        format_to_mime = {
            'JPEG': 'image/jpeg',
            'PNG': 'image/png',
            'GIF': 'image/gif',
            'WEBP': 'image/webp',
        }
        return format_to_mime.get(img.format, 'image/jpeg')
    except Exception as e:
        logger.warning(f"Could not detect image format: {e}, defaulting to image/jpeg")
        return 'image/jpeg'

