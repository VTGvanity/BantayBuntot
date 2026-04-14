from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_page, name='login'),
    path('register/', views.register_page, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('verify-email/', views.verify_email_page, name='verify_email'),
    path('google-login/', views.google_login, name='google_login'),
    path('auth/callback/', views.auth_callback, name='auth_callback'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/', views.reset_password_confirm, name='reset_password_confirm'),
    path('verification-success/', views.verification_success, name='verification_success'),
    path('check-field-uniqueness/', views.check_field_uniqueness, name='check_field_uniqueness'),
]
