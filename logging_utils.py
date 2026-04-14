"""
Logging utilities for BantayBuntot application.
Provides audit logging, security logging, and performance monitoring.
"""
import logging
import functools
import time
from django.http import JsonResponse

# Create loggers
audit_logger = logging.getLogger('audit')
security_logger = logging.getLogger('security')
app_logger = logging.getLogger('BantayBuntot')


def log_audit_action(user, action, details=None, ip_address=None):
    """
    Log an audit event for tracking user actions.
    
    Args:
        user: The user performing the action (User object or string)
        action: Description of the action performed
        details: Additional details (dict or string)
        ip_address: Client IP address
    """
    user_str = str(user) if user else 'Anonymous'
    details_str = str(details) if details else 'No details'
    ip_str = ip_address or 'Unknown IP'
    
    audit_logger.info(
        f"User: {user_str} | Action: {action} | IP: {ip_str} | Details: {details_str}"
    )


def log_security_event(event_type, user=None, details=None, ip_address=None, severity='INFO'):
    """
    Log a security-related event.
    
    Args:
        event_type: Type of security event (e.g., 'LOGIN_FAILURE', 'SUSPICIOUS_ACTIVITY')
        user: The user involved (optional)
        details: Additional details
        ip_address: Client IP address
        severity: Log level (INFO, WARNING, ERROR)
    """
    user_str = str(user) if user else 'Anonymous'
    details_str = str(details) if details else 'No details'
    ip_str = ip_address or 'Unknown IP'
    
    message = f"[{event_type}] User: {user_str} | IP: {ip_str} | Details: {details_str}"
    
    if severity == 'ERROR':
        security_logger.error(message)
    elif severity == 'WARNING':
        security_logger.warning(message)
    else:
        security_logger.info(message)


def log_performance(view_name, execution_time, user=None):
    """
    Log view performance metrics.
    
    Args:
        view_name: Name of the view/function
        execution_time: Time taken in seconds
        user: The user making the request
    """
    user_str = str(user) if user else 'Anonymous'
    app_logger.debug(f"[PERFORMANCE] {view_name} executed in {execution_time:.3f}s by {user_str}")


def get_client_ip(request):
    """Extract client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip or 'Unknown'


def audit_log(action_name):
    """
    Decorator to automatically log view function calls.
    
    Usage:
        @audit_log('User Login')
        def login_view(request):
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            start_time = time.time()
            user = request.user if request.user.is_authenticated else None
            ip = get_client_ip(request)
            
            try:
                result = func(request, *args, **kwargs)
                
                # Log successful execution
                execution_time = time.time() - start_time
                log_audit_action(
                    user=user,
                    action=action_name,
                    details=f"Success | Duration: {execution_time:.3f}s",
                    ip_address=ip
                )
                log_performance(func.__name__, execution_time, user)
                
                return result
                
            except Exception as e:
                # Log failure
                execution_time = time.time() - start_time
                log_audit_action(
                    user=user,
                    action=action_name,
                    details=f"Failed: {str(e)}",
                    ip_address=ip
                )
                app_logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
                raise
                
        return wrapper
    return decorator


def log_api_call(endpoint, method, user=None, status_code=None, error=None):
    """
    Log API endpoint calls.
    
    Args:
        endpoint: API endpoint path
        method: HTTP method (GET, POST, etc.)
        user: The user making the request
        status_code: HTTP response status code
        error: Error message if failed
    """
    user_str = str(user) if user else 'Anonymous'
    status_str = f"Status: {status_code}" if status_code else ""
    error_str = f"Error: {error}" if error else ""
    
    app_logger.info(f"[API] {method} {endpoint} | User: {user_str} {status_str} {error_str}")


class AuditLogMixin:
    """
    Mixin for class-based views to add automatic audit logging.
    """
    audit_action_name = None
    
    def dispatch(self, request, *args, **kwargs):
        if self.audit_action_name:
            start_time = time.time()
            user = request.user if request.user.is_authenticated else None
            ip = get_client_ip(request)
            
            try:
                response = super().dispatch(request, *args, **kwargs)
                execution_time = time.time() - start_time
                
                log_audit_action(
                    user=user,
                    action=self.audit_action_name,
                    details=f"Method: {request.method} | Status: {response.status_code} | Duration: {execution_time:.3f}s",
                    ip_address=ip
                )
                return response
                
            except Exception as e:
                log_audit_action(
                    user=user,
                    action=self.audit_action_name,
                    details=f"Method: {request.method} | Failed: {str(e)}",
                    ip_address=ip
                )
                raise
        else:
            return super().dispatch(request, *args, **kwargs)
