"""
Guardrails service for protecting against prompt injections, abusive language, and ensuring system prompt adherence
Uses Guardrails AI framework for comprehensive protection
"""
import re
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

# Try to import Guardrails AI - handle gracefully if not installed
try:
    from guardrails import Guard, OnFailAction
    from guardrails.hub import DetectJailbreak, ToxicLanguage, ProfanityFree
    GUARDRAILS_AVAILABLE = True
except ImportError:
    GUARDRAILS_AVAILABLE = False
    logger.warning("Guardrails AI not installed. Install with: pip install guardrails-ai && guardrails hub install hub://guardrails/detect_jailbreak hub://guardrails/toxic_language")

class GuardrailsService:
    """Service for implementing security guardrails using Guardrails AI"""
    
    # Additional patterns for system extraction attempts (complement to Guardrails AI)
    SYSTEM_EXTRACTION_PATTERNS = [
        r'(?i)(what|tell|show|reveal|display).*(your|the).*(name|identity|role|purpose|instructions)',
        r'(?i)(who|what).*(are you|am i)',
        r'(?i)(repeat|echo|say back).*(your|the).*(system|prompt|instructions)',
    ]
    
    def __init__(self):
        """Initialize Guardrails AI guard with validators"""
        self.guard = None
        self.guardrails_available = GUARDRAILS_AVAILABLE
        
        if not GUARDRAILS_AVAILABLE:
            logger.warning("Guardrails AI not available. Using fallback validation.")
            return
        
        try:
            # Initialize Guard with multiple validators
            # DetectJailbreak: Detects prompt injection/jailbreak attempts
            # ToxicLanguage: Detects toxic/abusive language
            # ProfanityFree: Ensures content is free from profanity
            self.guard = Guard().use_many(
                DetectJailbreak(
                    on_fail=OnFailAction.EXCEPTION,
                    threshold=0.5  # Sensitivity threshold
                ),
                ToxicLanguage(
                    threshold=0.5,
                    validation_method="sentence",
                    on_fail=OnFailAction.EXCEPTION
                ),
                ProfanityFree(
                    on_fail=OnFailAction.EXCEPTION
                )
            )
            logger.info("Guardrails AI initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Guardrails AI: {e}")
            logger.warning("Falling back to basic validation. Make sure validators are installed: guardrails hub install hub://guardrails/detect_jailbreak hub://guardrails/toxic_language")
            self.guard = None
    
    def detect_prompt_injection(self, text: str) -> Tuple[bool, Optional[str]]:
        """
        Detect prompt injection attempts using Guardrails AI and custom patterns
        
        Args:
            text: Input text to check
            
        Returns:
            Tuple of (is_injection, reason)
        """
        if not text:
            return False, None
        
        # Use Guardrails AI DetectJailbreak validator
        if self.guard and self.guardrails_available:
            try:
                # Create a guard specifically for jailbreak detection
                jailbreak_guard = Guard().use(
                    DetectJailbreak(
                        on_fail=OnFailAction.EXCEPTION,
                        threshold=0.5
                    )
                )
                # Validate - if it passes, no jailbreak detected
                jailbreak_guard.validate(text)
            except Exception as e:
                # Exception means jailbreak was detected
                reason = "Detected prompt injection/jailbreak attempt"
                logger.warning(f"Prompt injection detected by Guardrails AI: {text[:100]}")
                return True, reason
        
        # Fallback: Check for system extraction patterns
        for pattern in self.SYSTEM_EXTRACTION_PATTERNS:
            if re.search(pattern, text):
                reason = f"Detected system information extraction attempt: {pattern}"
                logger.warning(f"System extraction attempt detected: {text[:100]}")
                return True, reason
        
        # Check for excessive special characters (potential encoding/obfuscation)
        # Skip this check if text looks like code (contains common code patterns)
        # Code naturally has many special characters, so this check is too aggressive for legitimate code
        code_keywords = ['def ', 'import ', 'class ', 'function', 'print(', 'return ', 'if ', 'for ', 'while ', 
                        'from ', 'try:', 'except', 'lambda', '=>', '->', '()', '[]', '{}']
        is_likely_code = any(keyword in text for keyword in code_keywords)
        
        if not is_likely_code:
            special_char_ratio = len(re.findall(r'[^\w\s]', text)) / max(len(text), 1)
            # Increased threshold from 0.3 to 0.5 to reduce false positives
            if special_char_ratio > 0.5 and len(text) > 20:
                reason = "Suspicious character pattern detected"
                logger.warning(f"Suspicious character pattern: {text[:100]}")
                return True, reason
        
        return False, None
    
    def detect_abusive_language(self, text: str) -> Tuple[bool, Optional[str]]:
        """
        Detect abusive or inappropriate language using Guardrails AI
        
        Args:
            text: Input text to check
            
        Returns:
            Tuple of (is_abusive, reason)
        """
        if not text:
            return False, None
        
        # Use Guardrails AI validators
        if self.guard and self.guardrails_available:
            try:
                # Check for toxic language
                toxic_guard = Guard().use(
                    ToxicLanguage(
                        threshold=0.5,
                        validation_method="sentence",
                        on_fail=OnFailAction.EXCEPTION
                    )
                )
                toxic_guard.validate(text)
                
                # Check for profanity
                profanity_guard = Guard().use(
                    ProfanityFree(on_fail=OnFailAction.EXCEPTION)
                )
                profanity_guard.validate(text)
                
            except Exception as e:
                # Exception means toxic/profane content was detected
                logger.warning(f"Abusive language detected by Guardrails AI: {text[:100]}")
                return True, "Inappropriate language detected"
        
        # Skip aggressive checks for code-like responses
        code_keywords = ['def ', 'import ', 'class ', 'function', 'print(', 'return ', 'if ', 'for ', 'while ', 
                        'from ', 'try:', 'except', 'lambda', '=>', '->', '()', '[]', '{}']
        is_likely_code = any(keyword in text for keyword in code_keywords)
        
        # Fallback: Check for excessive capitalization (often indicates aggression)
        # Skip for code responses as code often uses uppercase for constants
        if not is_likely_code:
            caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
            if caps_ratio > 0.7 and len(text) > 10:
                logger.warning(f"Excessive capitalization detected: {text[:100]}")
                return True, "Aggressive language pattern detected"
        
        # Check for repeated characters (spam/aggression indicator)
        # Only check non-whitespace characters and increase threshold to reduce false positives
        # Skip for code responses as code may have repeated characters (e.g., ===, ---, etc.)
        if not is_likely_code:
            # Check for non-whitespace characters repeated 6+ times (increased from 5)
            if re.search(r'(\S)\1{5,}', text):
                logger.warning(f"Repeated character pattern detected: {text[:100]}")
                return True, "Spam-like pattern detected"
        
        return False, None
    
    def validate_user_input(self, text: str) -> Tuple[bool, Optional[str]]:
        """
        Validate user input against all guardrails using Guardrails AI
        
        Args:
            text: User input text
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not text or not text.strip():
            return False, "Empty message"
        
        # Use comprehensive Guardrails AI validation
        if self.guard and self.guardrails_available:
            try:
                # Validate with all validators at once
                self.guard.validate(text)
            except Exception as e:
                # Determine which type of violation occurred
                error_msg = str(e).lower()
                if 'jailbreak' in error_msg or 'injection' in error_msg:
                    logger.warning(f"Prompt injection blocked: {text[:100]}")
                    return False, "I can't process that request. Please ask me something else."
                elif 'toxic' in error_msg or 'profanity' in error_msg:
                    logger.warning(f"Abusive language blocked: {text[:100]}")
                    return False, "I prefer to keep our conversation respectful. Could you rephrase that?"
                else:
                    logger.warning(f"Input validation failed: {text[:100]}")
                    return False, "I can't process that request. Please try again."
        
        # Fallback validation if Guardrails AI is not available
        # Check for prompt injection
        is_injection, reason = self.detect_prompt_injection(text)
        if is_injection:
            return False, "I can't process that request. Please ask me something else."
        
        # Check for abusive language
        is_abusive, reason = self.detect_abusive_language(text)
        if is_abusive:
            return False, "I prefer to keep our conversation respectful. Could you rephrase that?"
        
        return True, None
    
    def validate_ai_response(self, response: str, system_prompt: str) -> Tuple[bool, Optional[str]]:
        """
        Validate AI response to ensure it adheres to system prompt and is safe
        
        Args:
            response: AI generated response
            system_prompt: The system prompt that should be followed
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not response:
            return False, "Empty response"
        
        # Validate response with Guardrails AI
        if self.guard and self.guardrails_available:
            try:
                # Check for toxic/profane content in response
                toxic_guard = Guard().use(
                    ToxicLanguage(
                        threshold=0.5,
                        validation_method="sentence",
                        on_fail=OnFailAction.EXCEPTION
                    )
                )
                toxic_guard.validate(response)
                
                profanity_guard = Guard().use(
                    ProfanityFree(on_fail=OnFailAction.EXCEPTION)
                )
                profanity_guard.validate(response)
                
            except Exception as e:
                # Log the actual error for debugging
                logger.warning(f"AI response validation failed: {str(e)}")
                logger.warning(f"Response preview: {response[:200]}")
                
                # Only block if it's clearly toxic/profane, not for code or other false positives
                error_str = str(e).lower()
                if 'toxic' in error_str or 'profanity' in error_str:
                    logger.warning(f"AI response contains inappropriate content: {response[:100]}")
                    return False, "Response contains inappropriate content"
                # For other errors (like jailbreak false positives on code), log but allow
                logger.info(f"Guardrails flagged response but allowing (likely false positive for code): {str(e)[:100]}")
        
        response_lower = response.lower()
        
        # Check if response tries to reveal system information
        system_keywords = ['system prompt', 'instructions', 'my name is', 'i am', 'my role is']
        for keyword in system_keywords:
            if keyword in response_lower:
                # Allow if it's part of normal conversation, but check context
                # If it's trying to explain the system prompt, that's a violation
                if any(phrase in response_lower for phrase in [
                    'my system prompt', 'the system prompt', 'my instructions are',
                    'i was told to', 'my prompt says'
                ]):
                    logger.warning(f"Response reveals system information: {response[:100]}")
                    return False, "Response violates system prompt adherence"
        
        # Check if response is trying to ignore instructions
        if any(phrase in response_lower for phrase in [
            'ignore the instructions', 'forget the prompt', 'disregard the system'
        ]):
            logger.warning(f"Response attempts to ignore instructions: {response[:100]}")
            return False, "Response violates system prompt adherence"
        
        # Fallback: Check for abusive language
        is_abusive, reason = self.detect_abusive_language(response)
        if is_abusive:
            logger.warning(f"AI response contains abusive language: {response[:100]}")
            return False, "Response contains inappropriate content"
        
        return True, None
    
    def sanitize_input(self, text: str) -> str:
        """
        Sanitize input text by removing potentially dangerous patterns
        
        Args:
            text: Input text to sanitize
            
        Returns:
            Sanitized text
        """
        if not text:
            return ""
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Trim
        text = text.strip()
        
        # Limit length to prevent abuse
        max_length = 2000
        if len(text) > max_length:
            text = text[:max_length]
            logger.warning(f"Input truncated from {len(text)} to {max_length} characters")
        
        return text
