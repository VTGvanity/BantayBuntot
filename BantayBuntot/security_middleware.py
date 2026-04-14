"""
STRIDE Security Middleware Module
Implements Spoofing, Tampering, Repudiation, DoS protection
"""
import os
import time
import hashlib
import json
from datetime import datetime, timedelta
from collections import defaultdict
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.conf import settings
from django.core.cache import cache
from django.template.loader import render_to_string
import logging

logger = logging.getLogger('security')
audit_logger = logging.getLogger('audit')


class SecurityHeadersMiddleware:
    """
    STRIDE: Tampering Protection
    Adds security headers to all responses to prevent various attacks
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Content Security Policy - prevents XSS and data injection
        # Note: reCAPTCHA v2 requires 'unsafe-inline' for styles and specific Google domains
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://www.gstatic.com https://www.google.com https://www.recaptcha.net https://www.gstatic.com/recaptcha/; "
            "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://www.gstatic.com https://www.google.com; "
            "img-src 'self' data: https://*.tile.openstreetmap.org https://www.gstatic.com https://www.google.com https://www.recaptcha.net https://api.dicebear.com; "
            "connect-src 'self' https://*.supabase.co https://www.google.com https://www.recaptcha.net; "
            "font-src 'self' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://www.gstatic.com; "
            "frame-src 'self' https://www.google.com https://www.recaptcha.net https://www.gstatic.com/recaptcha/; "
            "frame-ancestors 'none'; "
            "base-uri 'self';"
        )
        
        # Additional security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(self), camera=(self), microphone=()'
        
        # Remove potentially dangerous headers
        if 'X-Powered-By' in response:
            del response['X-Powered-By']
        if 'Server' in response:
            del response['Server']
        
        return response


class RateLimitMiddleware:
    """
    STRIDE: Denial of Service (DoS) Protection
    Implements rate limiting per IP and per user
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # In-memory store for rate limiting (use Redis in production)
        self.requests = defaultdict(list)
        
    def __call__(self, request):
        # Skip rate limiting if disabled
        if not getattr(settings, 'RATELIMIT_ENABLE', False):
            return self.get_response(request)
        
        # Skip rate limiting for static files and admin
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return self.get_response(request)
        
        # Get client identifier (IP or user)
        client_ip = self._get_client_ip(request)
        client_id = request.user.username if request.user.is_authenticated else client_ip
        
        # Check rate limits
        if self._is_rate_limited(client_id, request.path):
            logger.warning(f"Rate limit exceeded for {client_id} on {request.path}")
            
            # Check if this is an API request
            is_api = request.path.startswith('/api/') or request.headers.get('Accept') == 'application/json'
            
            if is_api:
                # Return JSON for API requests
                return HttpResponseForbidden(
                    json.dumps({
                        'success': False,
                        'error': 'Rate limit exceeded. Please try again later.',
                        'retry_after': 60
                    }),
                    content_type='application/json'
                )
            else:
                # Return HTML error page for web requests
                html_content = render_to_string('errors/429.html', {
                    'retry_after': 60,
                    'error_message': 'Too many login attempts. Please wait a moment before trying again.'
                })
                return HttpResponseForbidden(html_content)
        
        # Track this request
        self._track_request(client_id)
        
        # Add rate limit headers to response
        response = self.get_response(request)
        response['X-RateLimit-Limit'] = '100'
        response['X-RateLimit-Remaining'] = str(max(0, 100 - len(self.requests.get(client_id, []))))
        
        return response
    
    def _get_client_ip(self, request):
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip or 'unknown'
    
    def _is_rate_limited(self, client_id, path):
        """Check if client has exceeded rate limit"""
        now = time.time()
        window = 60  # 1 minute window
        max_requests = self._get_max_requests_for_path(path)
        
        # Clean old requests
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if now - req_time < window
        ]
        
        return len(self.requests[client_id]) >= max_requests
    
    def _get_max_requests_for_path(self, path):
        """Get max requests allowed based on endpoint sensitivity"""
        sensitive_endpoints = ['/login', '/register', '/api/auth/', '/forgot-password']
        if any(path.startswith(ep) for ep in sensitive_endpoints):
            return 5  # Strict limit for auth endpoints
        elif path.startswith('/api/'):
            return 60  # Standard limit for API
        return 100  # Generous limit for regular pages
    
    def _track_request(self, client_id):
        """Track request timestamp"""
        self.requests[client_id].append(time.time())


class AuditLogMiddleware:
    """
    STRIDE: Repudiation Protection
    Immutable audit logging for all critical actions
    Logs to append-only file and optionally to external SIEM
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.audit_file_path = os.path.join(settings.BASE_DIR, 'logs', 'immutable_audit.log')
        self._ensure_audit_file()
        
    def _ensure_audit_file(self):
        """Create audit file with restricted permissions (read-only for most users)"""
        if not os.path.exists(self.audit_file_path):
            # Create file with append-only permission simulation
            with open(self.audit_file_path, 'a') as f:
                f.write(f"# IMMUTABLE AUDIT LOG - Created {datetime.now().isoformat()}\n")
                f.write("# Format: TIMESTAMP | HASH | USER | IP | ACTION | DETAILS\n")
                f.write("# This file should be backed up to external SIEM\n\n")
            # Set restrictive permissions (Windows-compatible concept)
            try:
                os.chmod(self.audit_file_path, 0o644)
            except:
                pass
    
    def __call__(self, request):
        # Store request start time
        request._audit_start_time = time.time()
        
        response = self.get_response(request)
        
        # Log critical actions
        if self._should_log_request(request, response):
            self._log_audit_event(request, response)
        
        return response
    
    def _should_log_request(self, request, response):
        """Determine if request should be logged"""
        critical_paths = [
            '/login', '/logout', '/register', '/forgot-password', '/reset-password',
            '/admin', '/api/', '/auth/'
        ]
        
        path = request.path
        method = request.method
        
        # Log all POST/PUT/DELETE to critical paths
        if method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            return any(path.startswith(ep) for ep in critical_paths)
        
        # Log all admin access
        if '/admin' in path:
            return True
        
        # Log authentication events
        if any(path.startswith(ep) for ep in ['/login', '/logout', '/register']):
            return True
            
        # Log errors (4xx, 5xx)
        if response.status_code >= 400:
            return True
        
        return False
    
    def _log_audit_event(self, request, response):
        """Write immutable audit log entry"""
        timestamp = datetime.now().isoformat()
        user = request.user.username if request.user.is_authenticated else 'Anonymous'
        ip = self._get_client_ip(request)
        action = f"{request.method} {request.path}"
        status = response.status_code
        duration = time.time() - getattr(request, '_audit_start_time', time.time())
        
        # Create log entry
        entry = {
            'timestamp': timestamp,
            'user': user,
            'ip': ip,
            'action': action,
            'status': status,
            'duration_ms': round(duration * 1000, 2),
            'user_agent': request.META.get('HTTP_USER_AGENT', 'unknown')[:200]
        }
        
        # Calculate hash for integrity (simplified - use HMAC in production)
        entry_str = json.dumps(entry, sort_keys=True)
        entry_hash = hashlib.sha256(entry_str.encode()).hexdigest()[:16]
        
        # Format: TIMESTAMP | HASH | USER | IP | ACTION | DETAILS
        log_line = f"{timestamp} | {entry_hash} | {user} | {ip} | {action} | status={status} duration={duration*1000:.2f}ms\n"
        
        # Write to append-only file
        try:
            with open(self.audit_file_path, 'a') as f:
                f.write(log_line)
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
        
        # Also send to external SIEM if configured
        siem_endpoint = getattr(settings, 'AUDIT_LOG_SEPARATE_SERVER', '')
        if siem_endpoint:
            self._send_to_siem(entry, siem_endpoint)
        
        # Log to Django audit logger
        audit_logger.info(f"AUDIT: {user} from {ip} - {action} - Status {status}")
    
    def _get_client_ip(self, request):
        """Extract client IP"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')
    
    def _send_to_siem(self, entry, endpoint):
        """Send audit log to external SIEM (simplified)"""
        try:
            import requests
            requests.post(
                endpoint,
                json=entry,
                timeout=2,
                headers={'X-Audit-Source': 'BantayBuntot'}
            )
        except Exception as e:
            logger.warning(f"Failed to send audit log to SIEM: {e}")


class SecurityEventMonitor:
    """
    Utility class for monitoring security events and triggering alerts
    """
    def __init__(self):
        self.event_counts = defaultdict(lambda: defaultdict(int))
        self.last_reset = time.time()
    
    def record_event(self, event_type, user=None, ip=None):
        """Record a security event and check if alert threshold reached"""
        window = getattr(settings, 'SECURITY_ALERT_THRESHOLD', {}).get('TIME_WINDOW_MINUTES', 5) * 60
        
        # Reset counters if window expired
        if time.time() - self.last_reset > window:
            self.event_counts.clear()
            self.last_reset = time.time()
        
        key = ip or user or 'unknown'
        self.event_counts[event_type][key] += 1
        
        # Check thresholds
        thresholds = getattr(settings, 'SECURITY_ALERT_THRESHOLD', {})
        if event_type == 'LOGIN_FAILURE' and self.event_counts[event_type][key] >= thresholds.get('LOGIN_FAILURES', 5):
            logger.error(f"SECURITY ALERT: Multiple failed logins from {key} - Potential brute force attack")
            return True  # Threshold reached
        
        return False
