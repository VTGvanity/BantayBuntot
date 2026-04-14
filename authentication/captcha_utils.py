"""
STRIDE: Spoofing/DoS Protection - CAPTCHA Validation Utilities
Supports Google reCAPTCHA v2 and v3
"""
import os
import requests
from django.conf import settings
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger('security')


def verify_recaptcha(token, action=None, min_score=0.7):
    """
    Verify Google reCAPTCHA v3 token
    
    Args:
        token: The reCAPTCHA token from the client
        action: Expected action name (for v3)
        min_score: Minimum score required (0.0 - 1.0)
    
    Returns:
        tuple: (is_valid, score, error_message)
    """
    secret_key = getattr(settings, 'RECAPTCHA_PRIVATE_KEY', '')
    
    # Skip verification if no key configured (development mode)
    if not secret_key:
        logger.debug("reCAPTCHA skipped - no secret key configured")
        return True, 1.0, None
    
    if not token:
        return False, 0.0, "CAPTCHA verification required"
    
    try:
        response = requests.post(
            'https://www.google.com/recaptcha/api/siteverify',
            data={
                'secret': secret_key,
                'response': token,
                'remoteip': None  # Optional, can be added if needed
            },
            timeout=5
        )
        
        result = response.json()
        
        if not result.get('success'):
            error_codes = result.get('error-codes', [])
            logger.warning(f"reCAPTCHA validation failed: {error_codes}")
            return False, 0.0, f"CAPTCHA validation failed: {', '.join(error_codes)}"
        
        # For v3, check the score (v2 doesn't have score)
        score = result.get('score', 1.0)  # Default to 1.0 for v2 (which has no score)
        
        # Only check score for v3 (when score is present and not default)
        if 'score' in result and score < min_score:
            logger.warning(f"reCAPTCHA score too low: {score} (min: {min_score})")
            return False, score, "CAPTCHA score too low - possible bot detected"
        
        # Check action if specified (v3 only - v2 doesn't have action)
        if action and result.get('action') and result.get('action') != action:
            logger.warning(f"reCAPTCHA action mismatch: {result.get('action')} != {action}")
            return False, score, "CAPTCHA action mismatch"
        
        logger.debug(f"reCAPTCHA validation successful with score: {score}")
        return True, score, None
        
    except requests.RequestException as e:
        logger.error(f"reCAPTCHA verification request failed: {e}")
        # In case of network issues, we might want to be lenient in development
        if settings.DEBUG:
            return True, 0.5, None
        return False, 0.0, "CAPTCHA verification service unavailable"
    except Exception as e:
        logger.error(f"Unexpected error during reCAPTCHA verification: {e}")
        return False, 0.0, "CAPTCHA verification error"


class CaptchaValidatorMixin:
    """
    Mixin to add CAPTCHA validation to forms
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.captcha_token = None
        self.captcha_action = None
        self.captcha_min_score = 0.7
    
    def clean_captcha(self):
        """Validate the CAPTCHA token"""
        token = self.cleaned_data.get('captcha_token')
        
        if not token:
            # Check if reCAPTCHA is configured
            if getattr(settings, 'RECAPTCHA_PRIVATE_KEY', ''):
                raise ValidationError("Please complete the CAPTCHA verification.")
            # If no key configured, skip in development
            return token
        
        is_valid, score, error = verify_recaptcha(
            token, 
            action=self.captcha_action,
            min_score=self.captcha_min_score
        )
        
        if not is_valid:
            raise ValidationError(error or "CAPTCHA verification failed. Please try again.")
        
        return token


def add_captcha_context(context, action='login'):
    """
    Add reCAPTCHA site key to template context
    
    Args:
        context: The template context dictionary
        action: The reCAPTCHA action name (v3)
    
    Returns:
        Updated context with CAPTCHA settings
    """
    site_key = getattr(settings, 'RECAPTCHA_PUBLIC_KEY', '')
    context.update({
        'recaptcha_site_key': site_key,
        'recaptcha_enabled': bool(site_key),
        'recaptcha_action': action,
    })
    return context


def validate_request_captcha(request, action='submit', min_score=0.7):
    """
    Validate CAPTCHA from request data (for API endpoints)
    
    Args:
        request: Django request object
        action: Expected action
        min_score: Minimum score required
    
    Returns:
        tuple: (is_valid, error_message)
    """
    # Get token from POST data or JSON body
    token = None
    if request.method == 'POST':
        token = request.POST.get('captcha_token') or request.POST.get('g-recaptcha-response')
        
        # Also check JSON body
        if not token and request.content_type == 'application/json':
            try:
                import json
                body = json.loads(request.body)
                token = body.get('captcha_token') or body.get('g-recaptcha-response')
            except:
                pass
    
    if not token:
        # Check if reCAPTCHA is configured
        if getattr(settings, 'RECAPTCHA_PRIVATE_KEY', ''):
            return False, "CAPTCHA verification required - Please check the 'I'm not a robot' box"
        return True, None  # Skip if not configured
    
    is_valid, score, error = verify_recaptcha(token, action=action, min_score=min_score)
    return is_valid, error
