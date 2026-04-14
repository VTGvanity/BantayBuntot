import asyncio
import logging
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django_ratelimit.decorators import ratelimit  # STRIDE: DoS Protection
from .forms import CustomUserCreationForm
from .supabase_auth import supabase_auth
from logging_utils import log_audit_action, log_security_event, get_client_ip
from .captcha_utils import validate_request_captcha, add_captcha_context  # STRIDE: DoS Protection

logger = logging.getLogger('BantayBuntot')

@ratelimit(key='ip', rate='5/m', block=False)  # STRIDE: DoS Protection - 5 attempts per minute
@ratelimit(key='post:username', rate='3/m', block=False)  # Per-username rate limiting
def login_page(request):
    # Check if rate limited - show popup message instead of blocking
    if getattr(request, 'limited', False):
        log_security_event('RATE_LIMIT_EXCEEDED', request.POST.get('username', 'unknown'), 'Too many login attempts', get_client_ip(request), 'WARNING')
        messages.error(request, '⚠️ Rate limit exceeded! Too many login attempts. Please wait 1 minute before trying again.')
        context = {'form': AuthenticationForm()}
        add_captcha_context(context, action='login')
        return render(request, 'authentication/login.html', context)
    
    # Catch errors from URL parameters (e.g. from Google login role mismatch)
    error_msg = request.GET.get('error')
    if error_msg:
        messages.error(request, error_msg)

    if request.method == 'POST':
        # STRIDE: DoS/SPOOFING Protection - Validate CAPTCHA
        captcha_valid, captcha_error = validate_request_captcha(request, action='login', min_score=0.5)
        if not captcha_valid:
            log_security_event('CAPTCHA_FAILURE', request.POST.get('username'), captcha_error, get_client_ip(request), 'WARNING')
            messages.error(request, f"Security verification failed: {captcha_error}")
            context = {'form': AuthenticationForm()}
            add_captcha_context(context, action='login')
            return render(request, 'authentication/login.html', context)
        
        email = request.POST.get('username')  # Using username field for email
        password = request.POST.get('password')
        selected_role = request.POST.get('user_role', 'user')
        ip = get_client_ip(request)

        # Use Supabase authentication
        result = supabase_auth.sign_in(request, email, password)

        if result['success']:
            user_type = result.get('user_type', 'user')

            # Prevent logging in with wrong role selected
            if selected_role != user_type:
                supabase_auth.sign_out(request)
                log_security_event('LOGIN_ROLE_MISMATCH', email, f"Expected: {user_type}, Selected: {selected_role}", ip, 'WARNING')
                messages.error(request, f'This account is registered as {user_type}. Please select {user_type} and try again.')
            else:
                log_audit_action(email, 'User Login', f"Role: {user_type}", ip)
                messages.success(request, result['message'])
                if user_type == 'rescuer':
                    return redirect('rescuer_dashboard')
                return redirect('user_dashboard')
        else:
            # Check if this is a social-only account
            if result.get('social_only'):
                log_security_event('GOOGLE_ACCOUNT_LOGIN_ATTEMPT', email, 'Attempted password login on Google account', ip, 'WARNING')
            else:
                log_security_event('LOGIN_FAILURE', email, result.get('error'), ip)
            messages.error(request, result['error'])
    
    form = AuthenticationForm()
    context = {'form': form}
    add_captcha_context(context, action='login')  # STRIDE: DoS Protection
    return render(request, 'authentication/login.html', context)

@ratelimit(key='ip', rate='3/m', block=False)  # STRIDE: DoS Protection - 3 registrations per minute per IP
@ratelimit(key='post:email', rate='1/m', block=False)  # One registration per email per minute
def register_page(request):
    # Check if rate limited - show popup message
    if getattr(request, 'limited', False):
        log_security_event('RATE_LIMIT_EXCEEDED', request.POST.get('email', 'unknown'), 'Too many registration attempts', get_client_ip(request), 'WARNING')
        messages.error(request, '⚠️ Rate limit exceeded! Too many registration attempts. Please wait 1 minute.')
        form = CustomUserCreationForm(request.POST) if request.method == 'POST' else CustomUserCreationForm()
        context = {'form': form}
        add_captcha_context(context, action='register')
        return render(request, 'authentication/register.html', context)
    
    if request.method == 'POST':
        # STRIDE: DoS/SPOOFING Protection - Validate CAPTCHA
        captcha_valid, captcha_error = validate_request_captcha(request, action='register', min_score=0.5)
        if not captcha_valid:
            log_security_event('CAPTCHA_FAILURE', request.POST.get('email'), captcha_error, get_client_ip(request), 'WARNING')
            messages.error(request, f"Security verification failed: {captcha_error}")
            form = CustomUserCreationForm(request.POST)
            context = {'form': form}
            add_captcha_context(context, action='register')
            return render(request, 'authentication/register.html', context)
        
        email = request.POST.get('email')
        password = request.POST.get('password1')
        full_name = request.POST.get('full_name')
        username = request.POST.get('username')
        phone_raw = request.POST.get('phone')
        phone = phone_raw.strip() if phone_raw else None
        user_type = request.POST.get('user_type', 'user')
        ip = get_client_ip(request)

        # Use Supabase authentication
        redirect_to = request.build_absolute_uri('/auth/callback/')
        result = asyncio.run(supabase_auth.sign_up(
            email=email,
            password=password,
            full_name=full_name,
            username=username,
            phone=phone,
            user_type=user_type,
            redirect_to=redirect_to
        ))

        if result['success']:
            log_audit_action(email, 'User Registration', f"Username: {username}, Role: {user_type}", ip)
            messages.success(request, result['message'])
            # Redirect to verify email notice
            return redirect('verify_email')
        else:
            log_security_event('REGISTRATION_FAILURE', email, result.get('error'), ip)
            messages.error(request, result['error'])

    form = CustomUserCreationForm()
    context = {'form': form}
    add_captcha_context(context, action='register')  # STRIDE: DoS Protection
    return render(request, 'authentication/register.html', context)

def verify_email_page(request):
    """Informational page about email verification"""
    return render(request, 'authentication/verify_email.html')

def verification_success(request):
    """Page shown after email verification is complete"""
    from supabase_config import SUPABASE_URL, SUPABASE_KEY
    context = {
        'SUPABASE_URL': SUPABASE_URL,
        'SUPABASE_ANON_KEY': SUPABASE_KEY,
    }
    return render(request, 'authentication/verification_success.html', context)

def google_login(request):
    """Render Google login initialization page (Critical for PKCE)"""
    from supabase_config import SUPABASE_URL, SUPABASE_KEY
    role = request.GET.get('role', 'user')
    context = {
        'SUPABASE_URL': SUPABASE_URL,
        'SUPABASE_ANON_KEY': SUPABASE_KEY,
        'role': role
    }
    return render(request, 'authentication/google_login.html', context)

def auth_callback(request):
    """Handle callback from Supabase/Google"""
    from supabase_config import SUPABASE_URL, SUPABASE_KEY
    context = {
        'SUPABASE_URL': SUPABASE_URL,
        'SUPABASE_ANON_KEY': SUPABASE_KEY
    }
    return render(request, 'authentication/auth_callback.html', context)

@ratelimit(key='ip', rate='3/m', block=True)  # STRIDE: DoS Protection
def forgot_password(request):
    """Initial forgot password request"""
    if request.method == 'POST':
        email = request.POST.get('email')
        ip = get_client_ip(request)
        
        # Check if user is a Google account
        try:
            from supabase_client import supabase_manager
            client = supabase_manager.get_client(use_service_role=True)
            user_result = client.table('users').select('id').eq('email', email).execute()
            
            if user_result.data:
                user_id = user_result.data[0]['id']
                auth_response = client.auth.admin.get_user_by_id(user_id)
                if auth_response and getattr(auth_response, 'user', None):
                    identities = getattr(auth_response.user, 'identities', [])
                    providers = []
                    for identity in identities:
                        p = getattr(identity, 'provider', None) or (identity.get('provider') if isinstance(identity, dict) else None)
                        if p: providers.append(p)
                    
                    if 'google' in providers:
                        log_security_event('GOOGLE_PASSWORD_RESET_ATTEMPT', email, 'Attempted password reset on Google account', ip, 'WARNING')
                        messages.error(request, 'Google accounts cannot use the forgot password feature. Please log in with Google directly.')
                        return redirect('login')
        except Exception as e:
            # Silently proceed to regular flow if check fails
            logger.warning(f"Error checking provider for forgot_password: {e}")

        redirect_to = request.build_absolute_uri('/reset-password/')
        result = asyncio.run(supabase_auth.reset_password(email, redirect_to))
        
        if result['success']:
            log_audit_action(email, 'Password Reset Requested', None, ip)
            messages.success(request, result['message'])
            return redirect('login')
        else:
            log_security_event('PASSWORD_RESET_FAILURE', email, result.get('error'), ip)
            messages.error(request, result['error'])
            
    # GET request: Show forgot password form
    return render(request, 'authentication/forgot_password.html')

def reset_password_confirm(request):
    """Update password after clicking email link"""
    from supabase_config import SUPABASE_URL, SUPABASE_KEY
    context = {
        'SUPABASE_URL': SUPABASE_URL,
        'SUPABASE_ANON_KEY': SUPABASE_KEY,
    }
    # GET request: Show the reset password form (JS will handle the actual update using the hash token)
    return render(request, 'authentication/reset_password_confirm.html', context)

@ratelimit(key='ip', rate='30/m', block=True)  # STRIDE: DoS Protection - Prevent enumeration attacks
def check_field_uniqueness(request):
    """AJAX view to check if a field (email, username, phone) is already taken"""
    field = request.GET.get('field')
    value = request.GET.get('value')
    
    if not field or not value:
        return JsonResponse({'available': True})
    
    if field not in ['email', 'username', 'phone']:
        return JsonResponse({'available': True})
        
    try:
        # We use service_role to check uniqueness across all users regardless of RLS
        # Using supabase_auth.supabase_service which is already initialized with service role
        response = supabase_auth.supabase_service.table('users').select('id').eq(field, value).execute()
        
        is_available = len(response.data) == 0
        return JsonResponse({'available': is_available})
    except Exception as e:
        return JsonResponse({'available': True, 'error': str(e)})

@require_http_methods(["GET", "POST"])
def logout_view(request):
    """Logout view"""
    user = request.user if request.user.is_authenticated else None
    ip = get_client_ip(request)
    result = supabase_auth.sign_out(request)
    
    if result['success']:
        log_audit_action(user, 'User Logout', None, ip)
        messages.success(request, result['message'])
    else:
        logger.warning(f"Logout failed for user {user}: {result.get('error')}")
        messages.error(request, result['error'])
    
    return redirect('login')
