import asyncio
import logging
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django_ratelimit.decorators import ratelimit  # STRIDE: DoS Protection
from supabase_client import supabase_manager
from dashboard.api_views import enrich_reports_with_user_data
from logging_utils import log_audit_action, log_security_event, get_client_ip
from authentication.captcha_utils import validate_request_captcha, add_captcha_context  # STRIDE: DoS Protection

logger = logging.getLogger('BantayBuntot')

def admin_check(user):
    return user.is_authenticated and (user.is_staff or getattr(user, 'user_type', '') == 'admin')

@ratelimit(key='ip', rate='5/m', block=True)  # STRIDE: DoS Protection
@ratelimit(key='post:username', rate='3/m', block=True)
def admin_login(request):
    """Custom login view for the admin panel"""
    if request.user.is_authenticated and admin_check(request.user):
        return redirect('admin_panel:dashboard')
    
    if request.method == 'POST':
        # STRIDE: DoS/SPOOFING Protection - Validate CAPTCHA for admin login
        captcha_valid, captcha_error = validate_request_captcha(request, action='admin_login')
        if not captcha_valid:
            log_security_event('ADMIN_CAPTCHA_FAILURE', request.POST.get('username'), captcha_error, get_client_ip(request), 'WARNING')
            context = {'error': f'Security verification failed: {captcha_error}'}
            add_captcha_context(context, action='admin_login')
            return render(request, 'admin_panel/login.html', context)
        
        username = request.POST.get('username')
        password = request.POST.get('password')
        ip = get_client_ip(request)
        user = authenticate(request, username=username, password=password)
        
        if user is not None and admin_check(user):
            login(request, user)
            log_audit_action(username, 'Admin Login', 'Success', ip)
            return redirect('admin_panel:dashboard')
        else:
            if user is not None:
                log_security_event('ADMIN_ACCESS_DENIED', username, 'User is not staff/admin', ip, 'WARNING')
            else:
                log_security_event('ADMIN_LOGIN_FAILURE', username, 'Invalid credentials', ip)
            context = {'error': 'Invalid credentials or access denied.'}
            add_captcha_context(context, action='admin_login')
            return render(request, 'admin_panel/login.html', context)
            
    context = {}
    add_captcha_context(context, action='admin_login')
    return render(request, 'admin_panel/login.html', context)

def admin_logout(request):
    """Logout view for the admin panel"""
    user = request.user if request.user.is_authenticated else None
    ip = get_client_ip(request)
    log_audit_action(user, 'Admin Logout', None, ip)
    logout(request)
    return redirect('admin_panel:login')

@login_required(login_url='admin_panel:login')
@user_passes_test(admin_check, login_url='admin_panel:login')
def admin_dashboard(request):
    """Main admin dashboard overview"""
    stats = asyncio.run(supabase_manager.get_admin_stats())
    return render(request, 'admin_panel/dashboard.html', {'stats': stats})

@ratelimit(key='user', rate='30/m', block=True)  # STRIDE: DoS Protection
@login_required(login_url='admin_panel:login')
@user_passes_test(admin_check, login_url='admin_panel:login')
def admin_users(request):
    """User management view"""
    try:
        users = supabase_manager.get_client(use_service_role=True).table('users').select('*').order('created_at', desc=True).execute()
        log_audit_action(request.user, 'Viewed Users List', f"Count: {len(users.data or [])}", get_client_ip(request))
        return render(request, 'admin_panel/users_list.html', {'users': users.data or []})
    except Exception as e:
        logger.error(f"Error fetching users list: {e}", exc_info=True)
        return render(request, 'admin_panel/users_list.html', {'users': [], 'error': 'Failed to load users'})

@ratelimit(key='user', rate='30/m', block=True)  # STRIDE: DoS Protection
@login_required(login_url='admin_panel:login')
@user_passes_test(admin_check, login_url='admin_panel:login')
def admin_reports(request):
    """Global report management view"""
    try:
        reports = asyncio.run(supabase_manager.get_animal_reports())
        # Enrich reports with user data
        reports = enrich_reports_with_user_data(reports)
        
        # Serialize for JS modal
        import json
        class UUIDEncoder(json.JSONEncoder):
            def default(self, obj):
                import uuid
                if isinstance(obj, uuid.UUID):
                    return str(obj)
                return super().default(obj)
                
        reports_json = json.dumps(reports, cls=UUIDEncoder)
        
        log_audit_action(request.user, 'Viewed Reports List', f"Count: {len(reports)}", get_client_ip(request))
        
        return render(request, 'admin_panel/reports_list.html', {
            'reports': reports,
            'reports_json': reports_json
        })
    except Exception as e:
        logger.error(f"Error fetching reports list: {e}", exc_info=True)
        return render(request, 'admin_panel/reports_list.html', {
            'reports': [],
            'reports_json': '[]',
            'error': 'Failed to load reports'
        })

@login_required
@user_passes_test(admin_check)
def api_admin_stats(request):
    """API endpoint for admin analytics"""
    stats = asyncio.run(supabase_manager.get_admin_stats())
    if stats:
        return JsonResponse({'success': True, 'stats': stats})
    return JsonResponse({'success': False, 'error': 'Failed to fetch stats'})

@login_required
@user_passes_test(admin_check)
def api_update_user(request):
    """Update user metadata (e.g., change type)"""
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        user_id = data.get('id')
        update_data = data.get('update_data')
        ip = get_client_ip(request)
        
        if user_id and update_data:
            result = asyncio.run(supabase_manager.update_user(user_id, update_data))
            if result:
                log_audit_action(request.user, 'Updated User', f"User ID: {user_id}, Data: {update_data}", ip)
                return JsonResponse({'success': True})
            else:
                logger.error(f"Failed to update user {user_id}")
        else:
            log_security_event('INVALID_ADMIN_ACTION', request.user, 'Missing user_id or update_data', ip, 'WARNING')
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@ratelimit(key='user', rate='10/m', block=True)  # STRIDE: DoS Protection - Prevent mass deletion
@login_required
@user_passes_test(admin_check)
def api_delete_user(request):
    """Delete a user from the system"""
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        user_id = data.get('id')
        ip = get_client_ip(request)
        
        if user_id:
            # Prevent self-deletion
            if str(user_id) == str(request.user.id):
                log_security_event('ADMIN_SELF_DELETE_ATTEMPT', request.user, 'Attempted to delete own account', ip, 'WARNING')
                return JsonResponse({'success': False, 'error': 'Cannot delete your own account'})
            
            result = asyncio.run(supabase_manager.delete_user(user_id))
            if result is not None:
                log_audit_action(request.user, 'Deleted User', f"User ID: {user_id}", ip)
                return JsonResponse({'success': True})
            else:
                logger.error(f"Failed to delete user {user_id}")
        else:
            log_security_event('INVALID_ADMIN_ACTION', request.user, 'Missing user_id for deletion', ip, 'WARNING')
    return JsonResponse({'success': False, 'error': 'Invalid request'})


import os
from pathlib import Path
from django.conf import settings

@login_required(login_url='admin_panel:login')
@user_passes_test(admin_check, login_url='admin_panel:login')
def admin_logs(request):
    """View application logs"""
    log_type = request.GET.get('type', 'application')
    lines = int(request.GET.get('lines', 500))
    
    # Security: restrict log types
    allowed_types = ['application', 'audit', 'error']
    if log_type not in allowed_types:
        log_type = 'application'
    
    # Build log file path
    logs_dir = Path(settings.BASE_DIR) / 'logs'
    log_file = logs_dir / f"{log_type}.log"
    
    log_content = []
    error_message = None
    
    try:
        if log_file.exists():
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                # Read last N lines
                all_lines = f.readlines()
                log_content = all_lines[-lines:] if len(all_lines) > lines else all_lines
        else:
            error_message = f"Log file not found: {log_file.name}"
    except Exception as e:
        logger.error(f"Error reading log file {log_file}: {e}")
        error_message = f"Error reading log file: {str(e)}"
    
    # Get file stats
    file_stats = {}
    for lt in allowed_types:
        lf = logs_dir / f"{lt}.log"
        if lf.exists():
            size = lf.stat().st_size
            file_stats[lt] = {
                'size': f"{size / 1024:.1f} KB" if size < 1024*1024 else f"{size / (1024*1024):.1f} MB",
                'exists': True
            }
        else:
            file_stats[lt] = {'size': '0 KB', 'exists': False}
    
    log_audit_action(request.user, 'Viewed Logs', f"Type: {log_type}, Lines: {len(log_content)}", get_client_ip(request))
    
    return render(request, 'admin_panel/logs.html', {
        'log_type': log_type,
        'log_content': log_content,
        'error_message': error_message,
        'file_stats': file_stats,
        'lines': lines
    })
