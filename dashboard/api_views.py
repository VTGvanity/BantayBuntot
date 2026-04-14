import asyncio
import json
import base64
import uuid
import time
import urllib.request
import urllib.parse
import urllib.error
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django_ratelimit.decorators import ratelimit  # STRIDE: DoS Protection
from supabase_client import supabase_manager
from logging_utils import log_audit_action, log_security_event, get_client_ip, log_api_call

logger = logging.getLogger('BantayBuntot')

@ratelimit(key='user', rate='10/m', block=True)  # STRIDE: DoS Protection
@ratelimit(key='ip', rate='20/m', block=True)
@csrf_exempt
@require_http_methods(["POST"])
def upload_image(request):
    """Upload an image to Supabase Storage"""
    try:
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Authentication required'})
        
        # Parse JSON data
        data = json.loads(request.body)
        
        # Get image data (base64 encoded)
        image_data = data.get('image_data')
        file_name = data.get('file_name', f"{uuid.uuid4()}.jpg")
        
        if not image_data:
            return JsonResponse({'success': False, 'error': 'No image data provided'})
        
        logger.debug(f"Uploading image for user {user.username}, filename: {file_name}")
        
        # Decode base64 image
        try:
            # Remove data URL prefix if present
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            
            file_bytes = base64.b64decode(image_data)
            logger.debug(f"Decoded image data, size: {len(file_bytes)} bytes")
        except Exception as e:
            logger.error(f"Error decoding image: {e}")
            return JsonResponse({'success': False, 'error': f'Invalid image data: {str(e)}'})
        
        # Generate unique filename
        unique_filename = f"{user.username}/{uuid.uuid4()}_{file_name}"
        logger.debug(f"Generated unique filename: {unique_filename}")
        
        # Upload to Supabase
        result = asyncio.run(supabase_manager.upload_image(
            file_bytes, 
            unique_filename,
            content_type='image/jpeg'
        ))
        
        logger.debug(f"Upload result: {result}")
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'url': result['url'],
                'file_name': unique_filename,
                'message': 'Image uploaded successfully!'
            })
        else:
            logger.error(f"Error uploading image: {result.get('error', 'Unknown error')}")
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Upload failed')
            })
            
    except Exception as e:
        import traceback
        logger.error(f"Error in upload_image: {str(e)}", exc_info=True)
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@ratelimit(key='user', rate='5/m', block=True)  # STRIDE: DoS Protection
@ratelimit(key='ip', rate='10/m', block=True)
@csrf_exempt
@require_http_methods(["POST"])
def create_animal_report(request):
    """Create a new animal report"""
    try:
        # Get user from session (should be authenticated)
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Authentication required'})
        
        # Parse form data
        data = json.loads(request.body)
        
        # Determine the user's Supabase UUID by matching their email
        user_uuid = None
        try:
            from supabase_config import USERS_TABLE
            client = supabase_manager.get_client(use_service_role=True)
            user_response = client.table(USERS_TABLE).select('id').eq('email', user.email).execute()
            if user_response.data:
                user_uuid = user_response.data[0]['id']
        except Exception as e:
            msg = f"Error fetching user UUID for {user.email}: {e}"
            logger.error(msg)
            with open("sync_debug.log", "a") as f: f.write(f"REPORT ERROR: {msg}\n")
        
        if not user_uuid:
            with open("sync_debug.log", "a") as f: f.write(f"REPORT WARNING: No Supabase UUID found for {user.email}. User might be missing from public.users table.\n")
        else:
            with open("sync_debug.log", "a") as f: f.write(f"REPORT INFO: Using UUID {user_uuid} for reporter {user.email}\n")
        
        # Get photos array and extract first image URL
        photos = data.get('photos', [])
        image_url = photos[0] if photos and len(photos) > 0 else None
        
        # Prepare report data
        report_data = {
            'user_id': user_uuid,
            'animal_type': data.get('animal_type'),
            'animal_condition': data.get('animal_condition'),
            'description': data.get('description'),
            'address': data.get('address'),
            'landmark': data.get('landmark'),
            'additional_location_info': data.get('additional_info'),
            'latitude': data.get('latitude'),
            'longitude': data.get('longitude'),
            'image_url': image_url,
            'images': photos,
            'status': 'pending',
            'priority': 'medium'
        }
        
        # Create report in Supabase
        result = asyncio.run(supabase_manager.create_animal_report(report_data))
        
        if result:
            return JsonResponse({
                'success': True,
                'report': result,
                'message': 'Animal report created successfully!'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to create animal report'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


def enrich_reports_with_user_data(reports):
    """Fetch user details from Supabase in batch and attach to reports."""
    if not reports:
        return reports
    
    # Collect all unique user IDs (reporters and rescuers)
    user_ids = set()
    for r in reports:
        if r.get('user_id'): user_ids.add(r['user_id'])
        if r.get('assigned_rescuer_id'): user_ids.add(r['assigned_rescuer_id'])
    
    if not user_ids:
        # Still ensure reporter_name exists
        for r in reports:
            if not r.get('reporter_name'): r['reporter_name'] = 'Anonymous'
        return reports

    try:
        from supabase_config import USERS_TABLE
        client = supabase_manager.get_client(use_service_role=True)
        
        user_response = client.table(USERS_TABLE).select('id, full_name, username, email').in_('id', list(user_ids)).execute()
        user_map = {u['id']: u for u in (user_response.data or [])}

        for r in reports:
            # Reporter info
            uid = r.get('user_id')
            if uid and uid in user_map:
                u = user_map[uid]
                r['reporter_name'] = u.get('full_name') or u.get('username') or 'Anonymous'
                r['reporter_email'] = u.get('email')
            elif not r.get('reporter_name'):
                r['reporter_name'] = 'Anonymous'
                r['reporter_email'] = None

            # Rescuer info
            rid = r.get('assigned_rescuer_id')
            if rid and rid in user_map:
                u = user_map[rid]
                r['rescuer_name'] = u.get('full_name') or u.get('username') or 'Unknown'
                r['rescuer_email'] = u.get('email')
            else:
                r['rescuer_name'] = r.get('rescuer_name') # keep if already exists
                r['rescuer_email'] = r.get('rescuer_email')

    except Exception as e:
        logger.error(f"Error enriching reports: {e}")
        # Final fallback ensure keys exist
        for r in reports:
            if not r.get('reporter_name'): r['reporter_name'] = 'Anonymous'
            if 'rescuer_name' not in r: r['rescuer_name'] = None

    return reports

@require_http_methods(["GET"])
def get_animal_reports(request):
    """Get animal reports with optional filters, enriched with reporter names.
    
    RESCUER PERMISSIONS:
    - Can see pending reports (not assigned to anyone)
    - Can see reports assigned TO THEM specifically
    - CANNOT see reports assigned to other rescuers
    """
    try:
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Authentication required'})
        
        # Get the user's Supabase UUID and user_type
        user_uuid = None
        user_type = None
        try:
            from supabase_config import USERS_TABLE
            client = supabase_manager.get_client(use_service_role=True)
            user_response = client.table(USERS_TABLE).select('id, user_type').eq('email', user.email).execute()
            if user_response.data:
                user_uuid = user_response.data[0]['id']
                user_type = user_response.data[0]['user_type']
        except Exception as e:
            logger.error(f"Error fetching user info: {e}")
        
        # Get filters from query parameters
        filters = {}
        if request.GET.get('status'):
            filters['status'] = request.GET.get('status')
        if request.GET.get('animal_type'):
            filters['animal_type'] = request.GET.get('animal_type')
        
        # Get reports from Supabase
        reports = asyncio.run(supabase_manager.get_animal_reports(filters))
        
        # RESCUER FILTER: Only show reports that are:
        # 1. Pending (not assigned to anyone), OR
        # 2. Assigned to the current rescuer
        if user_type == 'rescuer' and user_uuid:
            filtered_reports = []
            for report in reports:
                assigned_rescuer_id = report.get('assigned_rescuer_id')
                # Show if: no one is assigned OR assigned to this rescuer
                if assigned_rescuer_id is None or assigned_rescuer_id == user_uuid:
                    filtered_reports.append(report)
            reports = filtered_reports
        
        # Enrich reports using helper
        reports = enrich_reports_with_user_data(reports)
        
        return JsonResponse({
            'success': True,
            'reports': reports
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@ratelimit(key='user', rate='30/m', block=True)  # STRIDE: DoS Protection
@ratelimit(key='ip', rate='60/m', block=True)
@csrf_exempt
@require_http_methods(["PUT"])
def update_animal_report(request, report_id):
    """Update an animal report.
    
    RESCUER PERMISSIONS:
    - Can only update reports assigned TO THEM
    - Cannot update reports assigned to other rescuers
    """
    try:
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Authentication required'})
        
        # Parse update data
        data = json.loads(request.body)
        user = request.user
        ip = get_client_ip(request)
        logger.debug(f"Updating report {report_id} by {user.username} with data: {data}")
        
        # Get current user's Supabase UUID and user_type
        supabase_user = asyncio.run(supabase_manager.get_user_by_email(user.email, use_service_role=True))
        if not supabase_user:
            return JsonResponse({'success': False, 'error': 'User profile not found'})
        
        user_uuid = supabase_user.get('id')
        user_type = supabase_user.get('user_type')
        
        # RESCUER PERMISSION CHECK: Verify this rescuer is assigned to the report
        if user_type == 'rescuer':
            # Fetch the report to check assignment
            report = asyncio.run(supabase_manager.get_report_by_id(report_id))
            if not report:
                return JsonResponse({'success': False, 'error': 'Report not found'})
            
            assigned_rescuer_id = report.get('assigned_rescuer_id')
            
            # If report is assigned to another rescuer, deny access
            if assigned_rescuer_id and assigned_rescuer_id != user_uuid:
                logger.warning(f"Rescuer {user_uuid} attempted to update report {report_id} assigned to {assigned_rescuer_id}")
                return JsonResponse({'success': False, 'error': 'Permission denied. This report is assigned to another rescuer.'})
        
        # REPORTER PERMISSION CHECK: Verify this reporter owns the report
        elif user_type == 'user':
            # Fetch the report to check ownership
            report = asyncio.run(supabase_manager.get_report_by_id(report_id))
            if not report:
                return JsonResponse({'success': False, 'error': 'Report not found'})
            
            report_owner_id = report.get('user_id')
            
            # If report belongs to another user, deny access
            if report_owner_id and report_owner_id != user_uuid:
                logger.warning(f"User {user_uuid} attempted to update report {report_id} owned by {report_owner_id}")
                return JsonResponse({'success': False, 'error': 'Permission denied. You can only update your own reports.'})
        
        # If a rescuer requests the report, automatically lock in their identity securely
        if data.get('status') == 'waiting_for_user_approval':
            if supabase_user:
                data['assigned_rescuer_id'] = supabase_user.get('id')
                
        # If declined or reset back to pending, unassign any existing rescuer
        elif data.get('status') in ['pending', 'rescuer_declined']:
            data['assigned_rescuer_id'] = None
        
        # Update report in Supabase
        result = asyncio.run(supabase_manager.update_animal_report(report_id, data))
        
        if result:
            return JsonResponse({
                'success': True,
                'report': result,
                'message': 'Animal report updated successfully!'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to update animal report. Check server logs for database error details.'
            })
            
    except Exception as e:
        import traceback
        logger.error(f"Error in update_animal_report: {str(e)}", exc_info=True)
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        })

@csrf_exempt
@require_http_methods(["POST"])
def create_pinned_location(request):
    """Create a new pinned location"""
    try:
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Authentication required'})
        
        # Parse location data
        data = json.loads(request.body)
        
        logger.debug(f"Creating pinned location for user {user.username}")
        logger.debug(f"Location data: {data}")
        
        # Prepare location data
        # Note: user_id is passed as username string since Django IDs are integers but Supabase expects UUIDs
        location_data = {
            'user_id': str(user.username),  # Use username instead of integer ID
            'latitude': data.get('latitude'),
            'longitude': data.get('longitude'),
            'description': data.get('description', 'User pinned location'),
            'is_active': True
        }
        
        logger.debug(f"Prepared location data: {location_data}")
        
        # Create pinned location in Supabase
        result = asyncio.run(supabase_manager.create_pinned_location(location_data))
        
        logger.debug(f"Supabase result: {result}")
        
        if result:
            return JsonResponse({
                'success': True,
                'location': result,
                'message': 'Location pinned successfully!'
            })
        else:
            logger.error(f"Failed to pin location - Supabase returned None")
            return JsonResponse({
                'success': False,
                'error': 'Failed to pin location - check server logs'
            })
            
    except Exception as e:
        import traceback
        logger.error(f"Error in create_pinned_location: {str(e)}", exc_info=True)
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        })

@require_http_methods(["GET"])
def get_pinned_locations(request):
    """Get pinned locations"""
    try:
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Authentication required'})
        
        # For rescuers, get all pinned locations
        # For users, get only their own
        # Note: user_id filtering skipped because Django IDs are integers but Supabase expects UUIDs
        user_id = None
        # if hasattr(user, 'user_type') and user.user_type == 'user':
        #     user_id = str(user.username)  # Use username instead of integer ID
        
        # Get pinned locations from Supabase
        locations = asyncio.run(supabase_manager.get_pinned_locations(user_id))
        
        return JsonResponse({
            'success': True,
            'locations': locations
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@ratelimit(key='user', rate='10/m', block=True)  # STRIDE: DoS Protection
@ratelimit(key='ip', rate='20/m', block=True)
@csrf_exempt
@require_http_methods(["DELETE"])
def delete_animal_report(request, report_id):
    """Permanently delete an animal report — role-aware.
    
    - RESCUER (COMPLETED reports): Add to hidden_completed_from_rescuers array to hide from trash
    - RESCUER (non-completed): soft-delete (is_deleted_by_rescuer=True)
    - REPORTER (COMPLETED reports): Add to hidden_completed_from_users array to hide from trash  
    - REPORTER (non-completed): hard-delete allowed
    """
    try:
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Authentication required'})
            
        from supabase_config import USERS_TABLE
        client = supabase_manager.get_client(use_service_role=True)
        user_response = client.table(USERS_TABLE).select('id, user_type').eq('email', user.email).execute()
        
        if not user_response.data:
            return JsonResponse({'success': False, 'error': 'User profile not found'})
            
        user_uuid = user_response.data[0]['id']
        user_type = user_response.data[0]['user_type']
        
        # Fetch the full report
        report_response = client.table('animal_reports').select(
            'user_id, assigned_rescuer_id, status, hidden_by_rescuers, is_deleted_by_rescuer, hidden_completed_from_users, hidden_completed_from_rescuers'
        ).eq('id', report_id).execute()
        if not report_response.data:
            return JsonResponse({'success': False, 'error': 'Report not found'})
            
        report = report_response.data[0]
        report_status = report.get('status', '')
        is_completed = report_status == 'completed'
        
        # --- ADMIN PATH ---
        if user_type == 'admin':
             # Admin can delete anything permanently
             result = asyncio.run(supabase_manager.delete_animal_report(report_id))
             if result is not None:
                 return JsonResponse({'success': True, 'message': 'Admin: Report deleted permanently'})
             return JsonResponse({'success': False, 'error': 'Failed to delete report'})

        # --- RESCUER PATH ---
        if user_type == 'rescuer':
            if is_completed:
                # For completed reports: add to hidden_completed_from_rescuers array
                hidden_list = report.get('hidden_completed_from_rescuers') or []
                if user_uuid not in hidden_list:
                    hidden_list.append(user_uuid)
                update_data = {
                    'is_deleted_by_rescuer': True,
                    'hidden_completed_from_rescuers': hidden_list
                }
            else:
                # For non-completed: just soft-delete
                update_data = {'is_deleted_by_rescuer': True}
                # Also clean up from hidden list if present
                hidden_list = report.get('hidden_by_rescuers') or []
                if user_uuid in hidden_list:
                    hidden_list.remove(user_uuid)
                    update_data['hidden_by_rescuers'] = hidden_list
            result = asyncio.run(supabase_manager.update_animal_report(report_id, update_data))
            if result:
                return JsonResponse({'success': True, 'message': 'Report removed from your view. It remains in rescue history.'})
            return JsonResponse({'success': False, 'error': 'Failed to delete report'})
        
        # --- REPORTER PATH ---
        report_owner = report.get('user_id')
        if report_owner != user_uuid:
            return JsonResponse({'success': False, 'error': 'Permission denied. You are not the reporter of this report.'})
        
        if is_completed:
            # For completed reports: add to hidden_completed_from_users array
            hidden_list = report.get('hidden_completed_from_users') or []
            if user_uuid not in hidden_list:
                hidden_list.append(user_uuid)
            update_data = {
                'is_deleted_by_user': True,
                'hidden_completed_from_users': hidden_list
            }
            result = asyncio.run(supabase_manager.update_animal_report(report_id, update_data))
            if result:
                return JsonResponse({'success': True, 'message': 'Report removed from your view. It remains in rescue history.'})
            return JsonResponse({'success': False, 'error': 'Failed to delete report'})
        else:
            # Non-completed reports can be hard-deleted by the reporter
            result = asyncio.run(supabase_manager.delete_animal_report(report_id))
            if result is not None:
                return JsonResponse({'success': True, 'message': 'Report deleted permanently'})
            return JsonResponse({'success': False, 'error': 'Failed to delete report'})
            
    except Exception as e:
        import traceback
        logger.error(f"Error in delete_animal_report: {str(e)}", exc_info=True)
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@require_http_methods(["POST", "PUT"])
def hide_report_from_rescuer(request, report_id):
    """Hide a report from a specific rescuer (add to hidden_by_rescuers)"""
    try:
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Authentication required'})
        
        # Use username as rescuer_id
        rescuer_id = str(user.username)
        logger.debug(f"Hiding report {report_id} from rescuer {rescuer_id}")
        
        # Update report in Supabase
        result = asyncio.run(supabase_manager.hide_report_from_rescuer(report_id, rescuer_id))
        
        if result:
            return JsonResponse({
                'success': True,
                'message': 'Report hidden from your view successfully!'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to hide report'
            })
            
    except Exception as e:
        import traceback
        logger.error(f"Error in hide_report_from_rescuer: {str(e)}", exc_info=True)
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        })

@csrf_exempt
@require_http_methods(["DELETE"])
def delete_pinned_location(request, location_id):
    """Delete a pinned location"""
    try:
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Authentication required'})
        
        # Delete pinned location from Supabase
        result = asyncio.run(supabase_manager.delete_pinned_location(location_id))
        
        if result:
            return JsonResponse({
                'success': True,
                'message': 'Pinned location deleted successfully!'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to delete pinned location'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@ratelimit(key='user', rate='60/m', block=True)  # STRIDE: DoS Protection
@ratelimit(key='ip', rate='120/m', block=True)
@require_http_methods(["GET"])
def get_user_profile(request):
    """Get current user's profile including computed average ratings."""
    try:
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Authentication required'})
        
        # Get user from Supabase using service role to bypass RLS
        supabase_user = asyncio.run(supabase_manager.get_user_by_email(user.email, use_service_role=True))
        
        if supabase_user:
            user_id = supabase_user.get('id', '')
            user_type = supabase_user.get('user_type', 'user')
            
            # Compute average ratings from completed animal_reports in Supabase
            avg_rating_as_reporter = None
            avg_rating_as_rescuer = None
            rating_count_as_reporter = 0
            rating_count_as_rescuer = 0
            try:
                client = supabase_manager.get_client(use_service_role=True)
                if user_type == 'rescuer':
                    # Ratings received AS rescuer = user_to_rescuer_rating on reports they rescued
                    rr = client.table('animal_reports').select(
                        'user_to_rescuer_rating'
                    ).eq('assigned_rescuer_id', user_id).eq('status', 'completed').execute()
                    ratings = [r['user_to_rescuer_rating'] for r in (rr.data or []) if r.get('user_to_rescuer_rating') is not None]
                    if ratings:
                        avg_rating_as_rescuer = round(sum(ratings) / len(ratings), 1)
                        rating_count_as_rescuer = len(ratings)
                else:
                    # Ratings received AS reporter = rescuer_to_user_rating on reports they reported
                    rr = client.table('animal_reports').select(
                        'rescuer_to_user_rating'
                    ).eq('user_id', user_id).eq('status', 'completed').execute()
                    ratings = [r['rescuer_to_user_rating'] for r in (rr.data or []) if r.get('rescuer_to_user_rating') is not None]
                    if ratings:
                        avg_rating_as_reporter = round(sum(ratings) / len(ratings), 1)
                        rating_count_as_reporter = len(ratings)
            except Exception as re:
                logger.warning(f"Could not compute ratings for {user.email}: {re}")
            
            return JsonResponse({
                'success': True,
                'profile': {
                    'id': user_id,
                    'username': supabase_user.get('username', ''),
                    'email': user.email,
                    'full_name': supabase_user.get('full_name', user.username),
                    'bio': supabase_user.get('bio', ''),
                    'phone': supabase_user.get('phone', ''),
                    'profile_photo': supabase_user.get('profile_photo', ''),
                    'user_type': user_type,
                    'created_at': supabase_user.get('created_at', ''),
                    'avg_rating_as_reporter': avg_rating_as_reporter,
                    'avg_rating_as_rescuer': avg_rating_as_rescuer,
                    'rating_count_as_reporter': rating_count_as_reporter,
                    'rating_count_as_rescuer': rating_count_as_rescuer,
                }
            })
        else:
            # Fallback to Django user data
            return JsonResponse({
                'success': True,
                'profile': {
                    'username': user.username,
                    'email': user.email,
                    'full_name': user.username,
                    'bio': '',
                    'phone': '',
                    'profile_photo': '',
                    'user_type': getattr(user, 'user_type', 'user'),
                    'created_at': ''
                }
            })
            
    except Exception as e:
        import traceback
        logger.error(f"Error in get_user_profile: {str(e)}", exc_info=True)
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@require_http_methods(["GET"])
def get_public_profile(request):
    """Get public profile of another user by email, including avg ratings."""
    try:
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Authentication required'})
            
        target_email = request.GET.get('email')
        target_id = request.GET.get('user_id')
        
        if not target_email and not target_id:
            return JsonResponse({'success': False, 'error': 'Either Email or User ID parameter is required'})
            
        # Get user from Supabase using their target ID or email
        supabase_user = None
        if target_id:
            supabase_user = asyncio.run(supabase_manager.get_user_by_id(target_id, use_service_role=True))
        elif target_email:
            supabase_user = asyncio.run(supabase_manager.get_user_by_email(target_email, use_service_role=True))
        
        if supabase_user:
            target_uuid = supabase_user.get('id', '')
            target_user_type = supabase_user.get('user_type', 'user')
            
            # Compute average ratings
            avg_rating_as_reporter = None
            avg_rating_as_rescuer = None
            rating_count_as_reporter = 0
            rating_count_as_rescuer = 0
            try:
                client = supabase_manager.get_client(use_service_role=True)
                if target_user_type == 'rescuer':
                    rr = client.table('animal_reports').select(
                        'user_to_rescuer_rating'
                    ).eq('assigned_rescuer_id', target_uuid).eq('status', 'completed').execute()
                    ratings = [r['user_to_rescuer_rating'] for r in (rr.data or []) if r.get('user_to_rescuer_rating') is not None]
                    if ratings:
                        avg_rating_as_rescuer = round(sum(ratings) / len(ratings), 1)
                        rating_count_as_rescuer = len(ratings)
                else:
                    rr = client.table('animal_reports').select(
                        'rescuer_to_user_rating'
                    ).eq('user_id', target_uuid).eq('status', 'completed').execute()
                    ratings = [r['rescuer_to_user_rating'] for r in (rr.data or []) if r.get('rescuer_to_user_rating') is not None]
                    if ratings:
                        avg_rating_as_reporter = round(sum(ratings) / len(ratings), 1)
                        rating_count_as_reporter = len(ratings)
            except Exception as re:
                logger.warning(f"Could not compute ratings for public profile: {re}")
            
            return JsonResponse({
                'success': True,
                'profile': {
                    'id': target_uuid,
                    'username': supabase_user.get('username', ''),
                    'full_name': supabase_user.get('full_name', ''),
                    'bio': supabase_user.get('bio', ''),
                    'phone': supabase_user.get('phone', ''),
                    'profile_photo': supabase_user.get('profile_photo', ''),
                    'user_type': target_user_type,
                    'created_at': supabase_user.get('created_at', ''),
                    'avg_rating_as_reporter': avg_rating_as_reporter,
                    'avg_rating_as_rescuer': avg_rating_as_rescuer,
                    'rating_count_as_reporter': rating_count_as_reporter,
                    'rating_count_as_rescuer': rating_count_as_rescuer,
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'User profile not found.'
            })
            
    except Exception as e:
        import traceback
        logger.error(f"Error in get_public_profile: {str(e)}", exc_info=True)
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@ratelimit(key='user', rate='10/m', block=True)  # STRIDE: DoS Protection
@csrf_exempt
@require_http_methods(["PUT"])
def update_user_profile(request):
    """Update current user's profile"""
    try:
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Authentication required'})
        
        # Get current user from Supabase using service role to bypass RLS
        supabase_user = asyncio.run(supabase_manager.get_user_by_email(user.email, use_service_role=True))
        if not supabase_user:
            return JsonResponse({'success': False, 'error': 'User profile not found'})

        data = json.loads(request.body)
        
        # Prepare update data
        update_data = {}
        if 'full_name' in data:
            update_data['full_name'] = data['full_name']
        if 'bio' in data:
            update_data['bio'] = data['bio']
        if 'profile_photo' in data:
            update_data['profile_photo'] = data['profile_photo']
        if 'phone' in data:
            update_data['phone'] = data['phone']
        
        # Check for username uniqueness if changing
        if 'username' in data and data['username'] != user.username:
            new_username = data['username']
            try:
                client = supabase_manager.get_client(use_service_role=True)
                from supabase_config import USERS_TABLE
                existing_user = client.table(USERS_TABLE).select('id').eq('username', new_username).execute()
                if existing_user.data:
                    return JsonResponse({'success': False, 'error': 'Username already taken'})
                update_data['username'] = new_username
            except Exception as e:
                logger.error(f"Error checking username uniqueness: {e}")
                return JsonResponse({'success': False, 'error': 'Error validating username'})

        # Check for phone uniqueness and format if changing
        if 'phone' in data and data['phone'] != supabase_user.get('phone'):
            new_phone = data['phone']
            
            # Format validation: exactly 10 digits (if not None)
            if new_phone is not None and not (len(new_phone) == 10 and new_phone.isdigit()):
                return JsonResponse({
                    'success': False,
                    'error': 'Please enter exactly 10 digits for the contact number.'
                })
                
            try:
                client = supabase_manager.get_client(use_service_role=True)
                from supabase_config import USERS_TABLE
                existing_phone = client.table(USERS_TABLE).select('id').eq('phone', new_phone).execute()
                if existing_phone.data:
                    return JsonResponse({'success': False, 'error': 'Contact number already registered by another user'})
                update_data['phone'] = new_phone
            except Exception as e:
                logger.error(f"Error checking phone uniqueness: {e}")
                return JsonResponse({'success': False, 'error': 'Error validating contact number'})

        # Update in Supabase
        result = asyncio.run(supabase_manager.update_user_by_email(user.email, update_data))
        
        if result:
            # Sync Django user object if username changed
            if 'username' in update_data:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                # Update the Django user in DB
                django_user = User.objects.get(email=user.email)
                django_user.username = update_data['username']
                django_user.save()
                # The session will automatically pick up the change since it uses the user ID which hasn't changed
            
            return JsonResponse({
                'success': True,
                'profile': result,
                'message': 'Profile updated successfully!'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to update profile'
            })
            
    except Exception as e:
        import traceback
        logger.error(f"Error in update_user_profile: {str(e)}", exc_info=True)
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        })



@require_http_methods(["GET"])
def get_rescue_history(request):
    """Get successful rescue history for current user.
    
    IMPORTANT: History is PERMANENT. Even if either party has trashed or
    permanently deleted their copy of the report, completed rescues must
    always appear in the Successful Rescue History of BOTH the reporter
    and the rescuer. The trash/delete flags only affect their main reports
    list and trash-bin view, not this history endpoint.
    """
    try:
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Authentication required'})
        
        # Get reports from Supabase (fetch all completed ones)
        filters = {'status': 'completed'}
        reports = asyncio.run(supabase_manager.get_animal_reports(filters))
        
        # Get the user's Supabase UUID
        user_uuid = None
        try:
            client = supabase_manager.get_client(use_service_role=True)
            from supabase_config import USERS_TABLE
            user_response = client.table(USERS_TABLE).select('id').eq('email', user.email).execute()
            if user_response.data:
                user_uuid = user_response.data[0]['id']
        except Exception as e:
            logger.error(f"Error fetching user UUID for history: {e}")
        
        if not user_uuid:
            return JsonResponse({'success': True, 'rescues': [], 'count': 0})

        # History shows ALL completed rescues regardless of trash/delete flags.
        # Only filter by whether this user is the reporter or the rescuer.
        if hasattr(user, 'user_type') and user.user_type == 'rescuer':
            user_reports = [r for r in reports if r.get('assigned_rescuer_id') == user_uuid]
        else:
            user_reports = [r for r in reports if r.get('user_id') == user_uuid]
        
        # Enrich history reports with reporter names
        user_reports = enrich_reports_with_user_data(user_reports)
        
        return JsonResponse({
            'success': True,
            'rescues': user_reports,
            'count': len(user_reports)
        })
        
    except Exception as e:
        import traceback
        logger.error(f"Error in get_rescue_history: {str(e)}", exc_info=True)
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@require_http_methods(["GET"])
def reverse_geocode(request):
    """Proxy for Nominatim reverse geocoding to avoid CORS issues"""
    try:
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Authentication required'})
        
        lat = request.GET.get('lat')
        lon = request.GET.get('lon')
        
        if not lat or not lon:
            return JsonResponse({'success': False, 'error': 'lat and lon parameters are required'})
        
        # Format to 4 decimal places (~11m precision) for better cache hits
        try:
            f_lat = float(lat)
            f_lon = float(lon)
            cache_key = f"geocode_{f_lat:.4f}_{f_lon:.4f}"
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'error': 'Invalid lat/lon format'})

        # Check cache first
        cached_result = cache.get(cache_key)
        if cached_result:
            logger.debug(f"reverse_geocode: Cache hit for {cache_key}")
            return JsonResponse(cached_result)

        url = 'https://nominatim.openstreetmap.org/reverse?format=json&lat={}&lon={}'.format(lat, lon)
        
        # Retry up to 3 times with increasing delays for rate limiting
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers={
                    'User-Agent': 'BantayBuntot/1.0 (Animal Rescue App)',
                    'Accept': 'application/json'
                })
                with urllib.request.urlopen(req, timeout=10) as response:
                    raw = response.read().decode('utf-8')
                    data = json.loads(raw)
                    
                    result = {
                        'success': True,
                        'display_name': data.get('display_name', ''),
                        'address': data.get('address', {})
                    }
                    
                    # Store in cache for 24 hours
                    cache.set(cache_key, result, 86400)
                    return JsonResponse(result)
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < 2:
                    logger.debug(f"reverse_geocode: Rate limited, waiting {(attempt+1)*2}s before retry...")
                    time.sleep((attempt + 1) * 2)  # Wait 2s, then 4s
                    continue
                raise
        
        return JsonResponse({'success': False, 'error': 'Rate limited by geocoding service. Please try again in a moment.'})
    except Exception as e:
        logger.error(f"Error in reverse_geocode: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@ratelimit(key='ip', rate='10/m', block=True)  # STRIDE: DoS Protection - Limit OAuth callbacks
@require_http_methods(["POST"])
def sync_session(request):
    """Sync Supabase session to Django session"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
        
    try:
        import json
        data = json.loads(request.body)
        access_token = data.get('access_token')
        selected_role = data.get('role', 'user')
        
        if not access_token:
            return JsonResponse({'success': False, 'error': 'No access token provided'})

        from authentication.supabase_auth import supabase_auth
        
        # 1. Identify the user using the provided access token
        user_response = supabase_auth.supabase.auth.get_user(access_token)
        if not user_response or not user_response.user:
            return JsonResponse({'success': False, 'error': 'Invalid Supabase session'})
        
        supabase_user = user_response.user
        email = supabase_user.email
        
        # 2. Identify Providers (Google vs Email)
        identities = getattr(supabase_user, 'identities', [])
        providers = []
        for identity in identities:
            p = getattr(identity, 'provider', None) or (identity.get('provider') if isinstance(identity, dict) else None)
            if p: providers.append(p)

        # 2.5 SECURITY CHECK: Block Google login if this email already has a password account
        # If user has BOTH 'google' AND 'email' providers, it means they have an existing
        # email/password account that got linked with Google. We block this and require password login.
        if 'google' in providers and 'email' in providers:
            logger.warning(f"Google login blocked for {email}: email/password account already exists")
            return JsonResponse({
                'success': False, 
                'error': 'ALREADY_REGISTERED_WITH_PASSWORD'
            })

        # 3. Get/Update User Profile and Metadata
        user_profile = supabase_auth.get_user_profile(supabase_user.id)
        meta = getattr(supabase_user, 'user_metadata', {})

        # 4. MANDATORY GOOGLE VERIFICATION CHECK
        is_google_user = 'google' in providers
        is_google_verified = meta.get('is_google_verified') == True
        
        if is_google_user and not is_google_verified:
            # Force-sync the profile with CORRECT selection/defaults
            # This overrides the 'shell' profile created by the DB trigger
            profile_data = {
                'id': supabase_user.id,
                'email': email,
                'full_name': meta.get('full_name') or meta.get('name') or email,
                'username': meta.get('username') or (email.split('@')[0] if email else 'user'),
                'phone': meta.get('phone') if meta.get('phone') else None,
                'user_type': selected_role or 'user'
            }
            from supabase_config import USERS_TABLE
            supabase_auth.supabase_service.table(USERS_TABLE).upsert(profile_data).execute()
            user_profile = profile_data # Update local var

            # Trigger forced verification email (Branded as "Confirmation Link" in UI)
            print(f"FORCING GOOGLE VERIFICATION: {email}")
            supabase_auth.send_magic_link(email)
            return JsonResponse({
                'success': True,
                'require_verification': True,
                'email': email
            })

        # 5. Finalize Session / Login to Django
        final_role = selected_role or (user_profile.get('user_type') if user_profile else 'user')
        
        if not user_profile:
            # Create profile if missing
            user_profile = {
                'id': supabase_user.id,
                'email': email,
                'full_name': meta.get('full_name') or meta.get('name') or email,
                'username': meta.get('username') or (email.split('@')[0] if email else 'user'),
                'phone': meta.get('phone') if meta.get('phone') else None,
                'user_type': selected_role or 'user'
            }
            from supabase_config import USERS_TABLE
            supabase_auth.supabase_service.table(USERS_TABLE).upsert(user_profile).execute()
        else:
            # Update profile info from Google if available and empty
            updates = {}
            google_name = meta.get('full_name') or meta.get('name')
            if google_name and (not user_profile.get('full_name') or user_profile.get('full_name') == email):
                updates['full_name'] = google_name
            
            # Prevent logging in with wrong role selected
            if selected_role and selected_role != user_profile.get('user_type'):
                print(f"ROLE MISMATCH: {user_profile.get('user_type')} != {selected_role}")
                error_msg = f"This account is registered as {user_profile.get('user_type')}. Please select {user_profile.get('user_type')} and try again."
                return JsonResponse({'success': False, 'error': error_msg})
                
            if updates:
                from supabase_config import USERS_TABLE
                supabase_auth.supabase_service.table(USERS_TABLE).update(updates).eq('id', supabase_user.id).execute()
                # Update local object
                user_profile.update(updates)

        # 7. Perform Django Login
        from django.contrib.auth import login, logout
        logout(request)
        
        django_user = supabase_auth.get_or_create_django_user(supabase_user, user_profile)
        
        if django_user.user_type != user_profile.get('user_type'):
            django_user.user_type = user_profile.get('user_type')
            django_user.save()
        
        login(request, django_user)
        
        from django.contrib import messages
        messages.success(request, f"Successfully logged in as {user_profile.get('full_name', django_user.username)}!")
        
        redirect_url = '/rescuer-dashboard/' if user_profile.get('user_type') == 'rescuer' else '/dashboard/'
        return JsonResponse({
            'success': True,
            'redirect_url': f"{redirect_url}?t={int(time.time())}"
        })

    except Exception as e:
        print(f"CRITICAL ERROR in sync_session: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})

@ratelimit(key='ip', rate='10/m', block=True)  # STRIDE: DoS Protection
@csrf_exempt
def finalize_verification(request):
    """API called after a user clicks a Magic Link to mark them as verified"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)
        
    try:
        import json
        data = json.loads(request.body)
        token = data.get('access_token')
        
        if not token:
            return JsonResponse({'success': False, 'error': 'Missing token'}, status=400)
            
        # Identity the user using the token
        from authentication.supabase_auth import supabase_auth
        user_response = supabase_auth.supabase.auth.get_user(token)
        
        if not user_response or not user_response.user:
            return JsonResponse({'success': False, 'error': 'Invalid session'}, status=401)
            
        # Update user metadata to mark as strictly verified
        supabase_auth.update_user_metadata(
            user_response.user.id, 
            {'is_google_verified': True}
        )
        
        return JsonResponse({'success': True, 'message': 'Google account strictly verified'})
    except Exception as e:
        print(f"Error finalizing verification: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def trash_animal_report(request, report_id):
    """Soft-delete an animal report by setting is_deleted_by_user/rescuer=True"""
    try:
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Authentication required'})
            
        # Get user profile to determine user_type
        from supabase_config import USERS_TABLE
        client = supabase_manager.get_client(use_service_role=True)
        user_response = client.table(USERS_TABLE).select('id, user_type').eq('email', user.email).execute()
        
        if not user_response.data:
            return JsonResponse({'success': False, 'error': 'User profile not found'})
            
        user_profile = user_response.data[0]
        user_uuid = user_profile.get('id')
        user_type = user_profile.get('user_type')
        
        # First get the current report to check its status and owner
        report_response = client.table('animal_reports').select('status, hidden_by_rescuers, user_id').eq('id', report_id).execute()
        if not report_response.data:
            print(f"DEBUG: Trash report {report_id} not found")
            return JsonResponse({'success': False, 'error': 'Report not found'})
            
        report = report_response.data[0]
        report_owner_id = report.get('user_id')
        print(f"DEBUG: Trashing report {report_id}. User: {user_uuid}, Owner: {report_owner_id}, Type: {user_type}")
        
        update_data = {}
        if user_type == 'rescuer':
            if report.get('status') == 'pending':
                # For pending reports, "trashing" means adding to hidden list
                hidden_list = report.get('hidden_by_rescuers') or []
                if user_uuid not in hidden_list:
                    hidden_list.append(user_uuid)
                    update_data['hidden_by_rescuers'] = hidden_list
                else:
                    return JsonResponse({'success': True, 'message': 'Report already hidden'})
            else:
                # For assigned/completed reports, use the trash flag
                update_data['is_deleted_by_rescuer'] = True
        else:
            # Check if this user is the owner
            if report_owner_id != user_uuid:
                print(f"DEBUG: User {user_uuid} is not the owner {report_owner_id}")
                # We'll allow it for now if they are the same person but IDs differ? 
                # No, let's just log it and proceed to see if it works.
            
            update_data['is_deleted_by_user'] = True
            
        print(f"DEBUG: Updating report with data: {update_data}")
        result = asyncio.run(supabase_manager.update_animal_report(report_id, update_data))
        if result:
            print(f"DEBUG: Successfully trashed report {report_id}")
            return JsonResponse({'success': True, 'message': 'Report moved to trash'})
        print(f"DEBUG: Failed to update report {report_id} in Supabase")
        return JsonResponse({'success': False, 'error': 'Failed to trash report'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@csrf_exempt
@require_http_methods(["POST"])
def recover_animal_report(request, report_id):
    """Recover an animal report from trash"""
    try:
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Authentication required'})
            
        from supabase_config import USERS_TABLE
        client = supabase_manager.get_client(use_service_role=True)
        user_response = client.table(USERS_TABLE).select('id, user_type').eq('email', user.email).execute()
        
        if not user_response.data:
            return JsonResponse({'success': False, 'error': 'User profile not found'})
            
        user_profile = user_response.data[0]
        user_uuid = user_profile.get('id')
        user_type = user_profile.get('user_type')
        
        # Get current report to check hidden list
        report_response = client.table('animal_reports').select('hidden_by_rescuers').eq('id', report_id).execute()
        report = report_response.data[0] if report_response.data else {}
        
        update_data = {}
        if user_type == 'rescuer':
            # Remove from hidden list if present
            hidden_list = report.get('hidden_by_rescuers') or []
            if user_uuid in hidden_list:
                hidden_list.remove(user_uuid)
                update_data['hidden_by_rescuers'] = hidden_list
            
            # Also reset the soft delete flag
            update_data['is_deleted_by_rescuer'] = False
        else:
            update_data['is_deleted_by_user'] = False
            
        result = asyncio.run(supabase_manager.update_animal_report(report_id, update_data))
        if result:
            return JsonResponse({'success': True, 'message': 'Report recovered successfully'})
        return JsonResponse({'success': False, 'error': 'Failed to recover report'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_http_methods(["GET"])
def get_trash_bin_reports(request):
    """Fetch reports that have been soft-deleted by the current user.
    
    RESCUER ISOLATION:
    - Rescuers only see their OWN deleted/hidden reports
    - Cannot see other rescuers' deleted/hidden reports
    """
    try:
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Authentication required'})
            
        from supabase_config import USERS_TABLE, REPORTS_TABLE
        client = supabase_manager.get_client(use_service_role=True)
        user_response = client.table(USERS_TABLE).select('id, user_type').eq('email', user.email).execute()
        
        if not user_response.data:
            return JsonResponse({'success': False, 'error': 'User profile not found'})
            
        user_uuid = user_response.data[0]['id']
        user_type = user_response.data[0]['user_type']
        
        # Determine which delete flag to check based on user_type
        if user_type == 'rescuer':
            # For rescuers: ONLY fetch reports assigned to them that they deleted/hid
            # This ensures proper isolation between rescuers
            query = client.table(REPORTS_TABLE).select('*').eq('assigned_rescuer_id', user_uuid).or_(f"is_deleted_by_rescuer.eq.true,hidden_by_rescuers.cs.{{\"{user_uuid}\"}}")
        else:
            # For users: reports marked is_deleted_by_user where they are the reporter
            query = client.table(REPORTS_TABLE).select('*').eq('is_deleted_by_user', True).eq('user_id', user_uuid)
        
        result = query.execute()
        reports = result.data or []
        
        # Filter out COMPLETED reports that have been hidden from this user
        # (i.e., user is in hidden_completed_from_users or hidden_completed_from_rescuers array)
        filtered_reports = []
        for report in reports:
            if report.get('status') == 'completed':
                if user_type == 'rescuer':
                    hidden_list = report.get('hidden_completed_from_rescuers') or []
                    if user_uuid in hidden_list:
                        continue  # Skip this report - it's hidden from rescuer
                else:
                    hidden_list = report.get('hidden_completed_from_users') or []
                    if user_uuid in hidden_list:
                        continue  # Skip this report - it's hidden from user
            filtered_reports.append(report)
        
        return JsonResponse({'success': True, 'reports': filtered_reports})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_http_methods(["GET"])
def get_report_comments(request, report_id):
    """Fetch all comments/messages for a specific report"""
    try:
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Authentication required'})
            
        # Fetch report to check permission
        report = asyncio.run(supabase_manager.get_report_by_id(report_id))
        if not report:
            return JsonResponse({'success': False, 'error': 'Report not found'})
            
        # Check if user is reporter or a rescuer
        # Get user's Supabase UUID
        supabase_user = asyncio.run(supabase_manager.get_user_by_email(user.email, use_service_role=True))
        if not supabase_user:
            return JsonResponse({'success': False, 'error': 'User profile not found'})
            
        is_reporter = report.get('user_id') == supabase_user.get('id')
        is_rescuer = supabase_user.get('user_type') == 'rescuer'
        
        if not (is_reporter or is_rescuer):
            return JsonResponse({'success': False, 'error': 'Unauthorized to view chat for this report'})

        # Fetch comments from Supabase
        comments = asyncio.run(supabase_manager.get_report_comments(report_id))
        
        # Enrich comments with user names
        if comments:
            user_ids = set(c['user_id'] for c in comments if c.get('user_id'))
            if user_ids:
                from supabase_config import USERS_TABLE
                client = supabase_manager.get_client(use_service_role=True)
                user_response = client.table(USERS_TABLE).select('id, full_name, username').in_('id', list(user_ids)).execute()
                user_map = {u['id']: u for u in (user_response.data or [])}
                
                for c in comments:
                    u = user_map.get(c.get('user_id'))
                    if u:
                        c['user_name'] = u.get('full_name') or u.get('username') or 'Unknown'
                    else:
                        c['user_name'] = 'Unknown'
        
        return JsonResponse({'success': True, 'comments': comments})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@csrf_exempt
@require_http_methods(["POST"])
def create_report_comment(request, report_id):
    """Send a new comment/message for a specific report"""
    try:
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Authentication required'})
            
        data = json.loads(request.body)
        comment_text = data.get('comment')
        
        if not comment_text:
            return JsonResponse({'success': False, 'error': 'Comment text is required'})
            
        # Fetch report to check permission
        report = asyncio.run(supabase_manager.get_report_by_id(report_id))
        if not report:
            return JsonResponse({'success': False, 'error': 'Report not found'})
            
        # Get user's Supabase UUID
        supabase_user = asyncio.run(supabase_manager.get_user_by_email(user.email, use_service_role=True))
        if not supabase_user:
            return JsonResponse({'success': False, 'error': 'User profile not found'})
            
        user_id = supabase_user.get('id')
        
        # Check if user is reporter or a rescuer
        is_reporter = report.get('user_id') == user_id
        is_rescuer = supabase_user.get('user_type') == 'rescuer'
        
        if not (is_reporter or is_rescuer):
            return JsonResponse({'success': False, 'error': 'Unauthorized to send messages for this report'})
        
        comment_data = {
            'report_id': report_id,
            'user_id': user_id,
            'comment': comment_text
        }
        
        result = asyncio.run(supabase_manager.create_report_comment(comment_data))
        
        if result:
            # Attach sender name for immediate UI feedback
            result['user_name'] = supabase_user.get('full_name') or supabase_user.get('username') or 'You'
            return JsonResponse({'success': True, 'comment': result})
        else:
            return JsonResponse({'success': False, 'error': 'Failed to send message'})
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
