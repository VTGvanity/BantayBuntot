from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('', views.admin_dashboard, name='dashboard'),
    path('login/', views.admin_login, name='login'),
    path('logout/', views.admin_logout, name='logout'),
    path('users/', views.admin_users, name='users'),
    path('reports/', views.admin_reports, name='reports'),
    path('logs/', views.admin_logs, name='logs'),
    path('api/stats/', views.api_admin_stats, name='api_stats'),
    path('api/users/update/', views.api_update_user, name='api_update_user'),
    path('api/users/delete/', views.api_delete_user, name='api_delete_user'),
]
