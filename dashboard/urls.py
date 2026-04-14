from django.urls import path
from . import views
from . import api_views

urlpatterns = [
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
    path('rescuer-dashboard/', views.rescuer_dashboard, name='rescuer_dashboard'),
    
    # API endpoints
    path('api/reports/', api_views.get_animal_reports, name='get_animal_reports'),
    path('api/reports/create/', api_views.create_animal_report, name='create_animal_report'),
    path('api/reports/<str:report_id>/update/', api_views.update_animal_report, name='update_animal_report'),
    path('api/reports/<str:report_id>/delete/', api_views.delete_animal_report, name='delete_animal_report'),
    path('api/reports/<str:report_id>/hide/', api_views.hide_report_from_rescuer, name='hide_report_from_rescuer'),
    
    path('api/pinned-locations/', api_views.get_pinned_locations, name='get_pinned_locations'),
    path('api/pinned-locations/create/', api_views.create_pinned_location, name='create_pinned_location'),
    path('api/pinned-locations/<int:location_id>/delete/', api_views.delete_pinned_location, name='delete_pinned_location'),
    
    # Image upload endpoint
    path('api/upload-image/', api_views.upload_image, name='upload_image'),
    
    # Profile management endpoints
    path('api/profile/', api_views.get_user_profile, name='get_user_profile'),
    path('api/profile/public/', api_views.get_public_profile, name='get_public_profile'),
    path('api/profile/update/', api_views.update_user_profile, name='update_user_profile'),
    path('api/profile/rescue-history/', api_views.get_rescue_history, name='get_rescue_history'),
    
    # Geocoding proxy
    path('api/reverse-geocode/', api_views.reverse_geocode, name='reverse_geocode'),
    # Authentication sync
    path('api/auth/sync-session/', api_views.sync_session, name='sync_session'),
    # Trash bin endpoints
    path('api/reports/<str:report_id>/trash/', api_views.trash_animal_report, name='trash_animal_report'),
    path('api/reports/<str:report_id>/recover/', api_views.recover_animal_report, name='recover_animal_report'),
    path('api/trash-bin/', api_views.get_trash_bin_reports, name='get_trash_bin_reports'),
    path('api/auth/finalize-verification/', api_views.finalize_verification, name='finalize_verification'),
    path('api/reports/<str:report_id>/comments/', api_views.get_report_comments, name='get_report_comments'),
    path('api/reports/<str:report_id>/comments/create/', api_views.create_report_comment, name='create_report_comment'),
]
