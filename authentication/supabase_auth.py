import asyncio
import os
from django.contrib.auth import login, logout
from django.contrib.auth.models import AnonymousUser
from django.http import JsonResponse
from django.shortcuts import redirect
from supabase import create_client, Client
from supabase_config import (
    SUPABASE_URL, 
    SUPABASE_KEY, 
    SUPABASE_SERVICE_KEY,
    USERS_TABLE,
    ANIMAL_REPORTS_TABLE,
    PINNED_LOCATIONS_TABLE
)
from .models import CustomUser

class SupabaseAuthManager:
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.supabase_service = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    def validate_password_strength(self, password):
        """
        Validate password strength: 8+ chars, upper, lower, digit, special symbol
        Returns (is_valid, error_message)
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters long."
        if not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter."
        if not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter."
        if not any(c.isdigit() for c in password):
            return False, "Password must contain at least one number."
        special_chars = "!@#$%^&*(),.?\":{}|<>"
        if not any(c in special_chars for c in password):
            return False, "Password must contain at least one special character (!@#$%^&* etc.)."
        return True, ""
    
    async def _admin_create_user(self, email, password, full_name, username, phone=None, user_type='user'):
        try:
            admin_response = self.supabase_service.auth.admin.create_user({
                'email': email,
                'password': password,
                'email_confirm': True,
                'user_metadata': {
                    'full_name': full_name,
                    'username': username,
                    'phone': phone,
                    'user_type': user_type
                }
            })
            if getattr(admin_response, 'user', None):
                return {
                    'success': True,
                    'user': admin_response.user,
                    'message': 'Registration successful! You can now log in.'
                }
            return {
                'success': False,
                'error': 'Could not create account via admin API.'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    async def sign_up(self, email, password, full_name, username, phone=None, user_type='user', redirect_to=None):
        """Sign up a new user with Supabase (Email Verification Required)"""
        if not redirect_to:
            redirect_to = "http://127.0.0.1:8000/verification-success/"
        try:
            # Check for email uniqueness in public.users
            email_check = self.supabase_service.table('users').select('id').eq('email', email).execute()
            if email_check.data:
                return {
                    'success': False,
                    'error': 'This email is already registered. Please use a different email or try logging in.'
                }

            # Check for username uniqueness in public.users
            username_check = self.supabase_service.table('users').select('id').eq('username', username).execute()
            if username_check.data:
                return {
                    'success': False,
                    'error': 'This username is already taken. Please choose a different username.'
                }

            # Check for phone uniqueness and format in public.users if provided
            if phone:
                # Basic format check: exactly 10 digits
                if not (len(phone) == 10 and phone.isdigit()):
                    return {
                        'success': False,
                        'error': 'Please enter exactly 10 digits for the contact number.'
                    }
                
                phone_check = self.supabase_service.table('users').select('id').eq('phone', phone).execute()
                if phone_check.data:
                    return {
                        'success': False,
                        'error': 'This contact number is already registered. Please use a different number.'
                    }

            # Enforce strict password policy
            is_valid, pwd_error = self.validate_password_strength(password)
            if not is_valid:
                return {
                    'success': False,
                    'error': pwd_error
                }

            # Prepare options
            options = {
                'data': {
                    'full_name': full_name,
                    'username': username,
                    'phone': phone,
                    'user_type': user_type
                }
            }
            if redirect_to:
                options['email_redirect_to'] = redirect_to

            # Use standard sign-up which triggers email verification
            response = self.supabase.auth.sign_up({
                'email': email,
                'password': password,
                'options': options
            })
            
            if response and getattr(response, 'user', None):
                return {
                    'success': True,
                    'user': response.user,
                    'message': 'Registration successful! Please check your email to verify your account.'
                }
            return {
                'success': False,
                'error': 'Could not create account.'
            }

        except Exception as e:
            error_message = str(e)
            return {
                'success': False,
                'error': self._parse_supabase_error(error_message)
            }
    
    def _parse_supabase_error(self, error_message):
        """Parse Supabase error messages into user-friendly messages"""
        if not isinstance(error_message, str):
            error_message = str(error_message)
        error_lower = error_message.lower()
        
        if 'email' in error_lower and 'already registered' in error_lower:
            return 'This email is already registered. Please use a different email or try logging in.'
        elif 'email' in error_lower and 'invalid' in error_lower:
            return 'Please enter a valid email address.'
        elif 'password' in error_lower and 'weak' in error_lower:
            return 'Password is too weak. Please use at least 8 characters with uppercase, lowercase, numbers, and special characters.'
        elif 'password' in error_lower and 'too short' in error_lower:
            return 'Password must be at least 8 characters long.'
        elif 'username' in error_lower and 'already' in error_lower:
            return 'This username is already taken. Please choose a different username.'
        elif 'phone' in error_lower and 'already' in error_lower:
            return 'This contact number is already registered. Please use a different number.'
        elif 'user_already_registered' in error_lower or ('already registered' in error_lower and 'email' in error_lower):
            return 'This email is already registered. Please log in or reset your password.'
        elif 'invalid_credentials' in error_lower:
            return 'Invalid email or password. Please check your credentials and try again.'
        elif 'signup_disabled' in error_lower:
            return 'Registration is currently disabled. Please contact support.'
        elif 'rate limit' in error_lower or 'too many' in error_lower:
            return 'Too many sign-up attempts right now. Please wait a few minutes or increase your Supabase email rate limit.'
        else:
            return f'Registration failed: {error_message}'
    
    def send_magic_link(self, email, redirect_to=None):
        """Send a Magic Link / Verification email manually"""
        if not redirect_to:
            # We add a 'confirmed=true' flag so we know the user actually clicked the link
            redirect_to = "http://127.0.0.1:8000/verification-success/?confirmed=true"
            
        try:
            return self.supabase.auth.sign_in_with_otp({
                'email': email,
                'options': {
                    'email_redirect_to': redirect_to
                }
            })
        except Exception as e:
            print(f"Error sending magic link: {e}")
            return None

    def update_user_metadata(self, user_id, metadata):
        """Update a user's metadata using the admin API (Service Role)"""
        try:
            return self.supabase_service.auth.admin.update_user_by_id(
                user_id,
                {'user_metadata': metadata}
            )
        except Exception as e:
            print(f"Error updating user metadata: {e}")
            return None
    def sign_in(self, request, email, password):
        """Sign in user with Supabase"""
        try:
            auth_response = self.supabase.auth.sign_in_with_password({
                'email': email,
                'password': password
            })

            if auth_response and getattr(auth_response, 'user', None):
                # Get user profile from our database
                user_profile = self.get_user_profile(auth_response.user.id)

                if not user_profile:
                    # If profile missing, try to create from auth user data
                    try:
                        profile_data = {
                            'id': auth_response.user.id,
                            'email': auth_response.user.email,
                            'full_name': auth_response.user.user_metadata.get('full_name', auth_response.user.email),
                            'username': auth_response.user.user_metadata.get('username', auth_response.user.email),
                            'phone': auth_response.user.user_metadata.get('phone') or None,
                            'user_type': auth_response.user.user_metadata.get('user_type', 'user')
                        }
                        self.supabase_service.table('users').insert(profile_data).execute()
                        user_profile = profile_data
                    except Exception:
                        pass

                if user_profile:
                    django_user = self.get_or_create_django_user(auth_response.user, user_profile)

                    # Login Django user
                    try:
                        login(request, django_user)
                    except Exception:
                        pass

                    return {
                        'success': True,
                        'user': django_user,
                        'user_type': user_profile.get('user_type', 'user'),
                        'message': f'Welcome back, {user_profile.get("full_name", email)}!'
                    }
                else:
                    return {
                        'success': False,
                        'error': 'User profile not found. Please contact support.'
                    }
            else:
                return {
                    'success': False,
                    'error': 'Invalid email or password.'
                }

        except Exception as e:
            error_message = str(e)
            print(f"DEBUG LOGIN ERROR: {error_message}")
            if 'invalid' in error_message.lower() or 'credentials' in error_message.lower():
                # IMPROVEMENT: Check if this is a Google-only user
                try:
                    # Using service role to check user identities
                    user_data = self.supabase_service.auth.admin.list_users()
                    if user_data and hasattr(user_data, 'users'):
                        target_user = next((u for u in user_data.users if u.email == email), None)
                        if target_user:
                            identities = getattr(target_user, 'identities', [])
                            providers = [getattr(i, 'provider', None) for i in identities]
                            if 'google' in providers and 'email' not in providers:
                                return {
                                    'success': False,
                                    'social_only': True,
                                    'error': 'This account is linked to Google. Please use the "Continue with Google" button below.'
                                }
                except Exception as lookup_err:
                    print(f"User identity lookup failed: {lookup_err}")

                error_msg = 'Invalid email or password.'
            else:
                error_msg = f'Login failed: {error_message}'

            return {
                'success': False,
                'error': error_msg
            }
    
    def sign_out(self, request):
        """Sign out user"""
        warning = None
        try:
            try:
                self.supabase.auth.sign_out()
            except Exception as supa_err:
                warning = f"Supabase sign out warning: {supa_err}"

            logout(request)

            if warning:
                return {
                    'success': True,
                    'message': 'Logged out successfully.',
                    'warning': warning
                }
            return {'success': True, 'message': 'Logged out successfully.'}
        except Exception as e:
            return {
                'success': False,
                'error': f'Logout failed: {str(e)}'
            }
    
    def get_user_profile(self, user_id):
        """Get user profile from Supabase database"""
        try:
            response = self.supabase_service.table('users').select('*').eq('id', user_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error getting user profile: {e}")
            return None

    def get_or_create_django_user(self, supabase_user, user_profile):
        """Get or create Django user for compatibility"""
        try:
            # Try to get existing Django user
            # Try to get existing Django user
            # Social logins should primarily map by email to avoid duplicate accounts
            email = user_profile.get('email') or supabase_user.email
            django_user = CustomUser.objects.filter(email=email).first()
            
            # If no user by email, try by username (if the user previously registered with a different email but same username - rare)
            if not django_user:
                username = user_profile.get('username') or email
                django_user = CustomUser.objects.filter(username=username).first()

            if not django_user:
                # Create new Django user
                django_user = CustomUser.objects.create_user(
                    username=user_profile.get('username') or email,
                    email=email,
                    password='supabase_managed',  # Placeholder password
                    full_name=user_profile.get('full_name', ''),
                    phone=user_profile.get('phone') or None,
                    user_type=user_profile.get('user_type', 'user')
                )
            else:
                # Update existing user info from Supabase profile
                # This ensures that even if they log in via Google, their existing Django name/type is updated
                django_user.email = email
                if user_profile.get('username'):
                    django_user.username = user_profile.get('username')
                if user_profile.get('full_name'):
                    django_user.full_name = user_profile.get('full_name')
                
                # Check explicitly to avoid '' failing UNIQUE constraint
                django_user.phone = user_profile.get('phone') or None
                
                django_user.user_type = user_profile.get('user_type', django_user.user_type)
                django_user.save()

            return django_user

        except Exception as e:
            print(f"Error creating Django user: {e}")
            raise
    
    async def reset_password(self, email, redirect_to):
        """Send password reset email"""
        try:
            response = self.supabase.auth.reset_password_for_email(email, {
                'redirect_to': redirect_to
            })
            return {
                'success': True,
                'message': 'Password reset email sent! Please check your inbox.'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to send password reset email: {str(e)}'
            }
    
    async def update_password(self, new_password):
        """Update current user's password"""
        try:
            # Enforce strict password policy
            is_valid, pwd_error = self.validate_password_strength(new_password)
            if not is_valid:
                return {
                    'success': False,
                    'error': pwd_error
                }
                
            response = self.supabase.auth.update_user({'password': new_password})
            return {
                'success': True,
                'message': 'Password updated successfully!'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to update password: {str(e)}'
            }

    def get_google_auth_url(self, redirect_to):
        """Get the URL for Google OAuth login"""
        try:
            auth_response = self.supabase.auth.sign_in_with_oauth({
                'provider': 'google',
                'options': {
                    'redirect_to': redirect_to,
                    'query_params': {
                        'prompt': 'select_account'
                    }
                }
            })
            return auth_response.url
        except Exception as e:
            print(f"Error getting Google auth URL: {e}")
            return None
    
    def get_current_user(self, request):
        """Get current authenticated user"""
        if request.user.is_authenticated:
            return request.user
        return None

# Global instance
supabase_auth = SupabaseAuthManager()
