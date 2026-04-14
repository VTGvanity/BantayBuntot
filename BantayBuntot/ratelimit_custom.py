"""
Custom rate limit error handling for STRIDE DoS Protection
"""
from django.http import JsonResponse, HttpResponseForbidden
from django.template.response import TemplateResponse
import json


def ratelimit_error_view(request, exception=None):
    """
    Custom view called when rate limit is exceeded
    Returns JSON for API requests, HTML page for regular requests
    """
    is_api_request = request.path.startswith('/api/') or request.headers.get('Accept') == 'application/json'
    
    if is_api_request:
        return JsonResponse({
            'success': False,
            'error': 'Rate limit exceeded. Please try again later.',
            'retry_after': 60,
            'code': 'RATE_LIMIT_EXCEEDED'
        }, status=429)
    
    # For regular web requests, render an error page
    return TemplateResponse(
        request,
        'errors/429.html',  # Create this template
        status=429,
        context={
            'retry_after': 60,
            'error_message': 'Too many requests. Please wait a moment before trying again.'
        }
    )


def rate_limit_exceeded_handler(get_response):
    """
    Middleware-style handler for rate limiting
    Can be used as a decorator on specific views
    """
    def middleware(request):
        response = get_response(request)
        return response
    return middleware
