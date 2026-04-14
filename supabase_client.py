import os
from supabase import create_client, Client
from supabase_config import (
    SUPABASE_URL, 
    SUPABASE_KEY, 
    SUPABASE_SERVICE_KEY,
    USERS_TABLE,
    ANIMAL_REPORTS_TABLE,
    PINNED_LOCATIONS_TABLE,
    REPORT_COMMENTS_TABLE,
    STORAGE_BUCKET
)

class SupabaseManager:
    def __init__(self):
        """Initialize Supabase client"""
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.service_client: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    
    def get_client(self, use_service_role=False):
        """Get appropriate Supabase client"""
        return self.service_client if use_service_role else self.supabase
    
    # User Management
    async def create_user(self, user_data):
        """Create a new user in Supabase"""
        try:
            client = self.get_client(use_service_role=True)
            result = client.table(USERS_TABLE).insert(user_data).execute()
            return result.data
        except Exception as e:
            print(f"Error creating user: {e}")
            return None
    
    async def get_user_by_email(self, email, use_service_role=False):
        """Get user by email"""
        try:
            client = self.get_client(use_service_role=use_service_role)
            result = client.table(USERS_TABLE).select('*').eq('email', email).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting user by email: {e}")
            return None
            
    async def get_user_by_id(self, user_id, use_service_role=False):
        """Get user by id"""
        try:
            client = self.get_client(use_service_role=use_service_role)
            result = client.table(USERS_TABLE).select('*').eq('id', user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting user by id: {e}")
            return None
            
    async def update_user(self, user_id, update_data):
        """Update user information"""
        try:
            client = self.get_client(use_service_role=True)
            result = client.table(USERS_TABLE).update(update_data).eq('id', user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error updating user: {e}")
            return None
    
    # Animal Reports Management
    async def create_animal_report(self, report_data):
        """Create a new animal report"""
        try:
            # Use service role to bypass RLS constraints
            # This is necessary because Django user IDs are integers but Supabase expects UUIDs
            client = self.get_client(use_service_role=True)
            result = client.table(ANIMAL_REPORTS_TABLE).insert(report_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error creating animal report: {e}")
            return None
    
    async def get_animal_reports(self, filters=None):
        """Get animal reports with optional filters"""
        try:
            # Use service role to bypass RLS and get all reports
            client = self.get_client(use_service_role=True)
            query = client.table(ANIMAL_REPORTS_TABLE).select('*')
            
            if filters:
                for key, value in filters.items():
                    if key == 'status':
                        query = query.eq('status', value)
                    elif key == 'animal_type':
                        query = query.eq('animal_type', value)
                    elif key == 'user_id':
                        query = query.eq('user_id', value)
                    elif key == 'reporter_email':
                        query = query.eq('reporter_email', value)
            
            result = query.order('created_at', desc=True).execute()
            return result.data
        except Exception as e:
            print(f"Error getting animal reports: {e}")
            return []
            
    async def get_report_by_id(self, report_id, use_service_role=True):
        """Get a single report by its ID"""
        try:
            client = self.get_client(use_service_role=use_service_role)
            result = client.table(ANIMAL_REPORTS_TABLE).select('*').eq('id', report_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting report by id: {e}")
            return None
    
    async def update_animal_report(self, report_id, update_data):
        """Update animal report"""
        try:
            client = self.get_client(use_service_role=True)
            result = client.table(ANIMAL_REPORTS_TABLE).update(update_data).eq('id', report_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error updating animal report (ID: {report_id}): {e}")
            print(f"Update data: {update_data}")
            import traceback
            traceback.print_exc()
            return None
    
    async def delete_animal_report(self, report_id):
        """Delete an animal report"""
        try:
            client = self.get_client(use_service_role=True)
            result = client.table(ANIMAL_REPORTS_TABLE).delete().eq('id', report_id).execute()
            return result.data
        except Exception as e:
            print(f"Error deleting animal report: {e}")
            return None
    
    async def hide_report_from_rescuer(self, report_id, rescuer_id):
        """Add rescuer to hidden_by_rescuers array without deleting the report"""
        try:
            client = self.get_client(use_service_role=True)
            # First get current hidden_by_rescuers array
            result = client.table(ANIMAL_REPORTS_TABLE).select('hidden_by_rescuers').eq('id', report_id).execute()
            if result.data:
                current_hidden = result.data[0].get('hidden_by_rescuers', []) or []
                if rescuer_id not in current_hidden:
                    current_hidden.append(rescuer_id)
                    update_result = client.table(ANIMAL_REPORTS_TABLE).update({'hidden_by_rescuers': current_hidden}).eq('id', report_id).execute()
                    return update_result.data[0] if update_result.data else None
                return result.data[0]  # Already hidden
            return None
        except Exception as e:
            print(f"Error hiding report from rescuer: {e}")
            return None
    
    # Pinned Locations Management
    async def create_pinned_location(self, location_data):
        """Create a new pinned location"""
        try:
            client = self.get_client()
            result = client.table(PINNED_LOCATIONS_TABLE).insert(location_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error creating pinned location: {e}")
            return None
    
    async def get_pinned_locations(self, user_id=None):
        """Get pinned locations, optionally filtered by user"""
        try:
            client = self.get_client()
            query = client.table(PINNED_LOCATIONS_TABLE).select('*')
            
            if user_id:
                query = query.eq('user_id', user_id)
            
            result = query.order('created_at', desc=True).execute()
            return result.data
        except Exception as e:
            print(f"Error getting pinned locations: {e}")
            return []
    
    async def delete_pinned_location(self, location_id):
        """Delete a pinned location"""
        try:
            client = self.get_client(use_service_role=True)
            result = client.table(PINNED_LOCATIONS_TABLE).delete().eq('id', location_id).execute()
            return result.data
        except Exception as e:
            print(f"Error deleting pinned location: {e}")
            return None

    # Report Comments Management
    async def get_report_comments(self, report_id):
        """Get comments for a specific report"""
        try:
            client = self.get_client(use_service_role=True)
            result = client.table(REPORT_COMMENTS_TABLE).select('*').eq('report_id', report_id).order('created_at', desc=False).execute()
            return result.data
        except Exception as e:
            print(f"Error getting report comments: {e}")
            return []

    async def create_report_comment(self, comment_data):
        """Create a new report comment"""
        try:
            client = self.get_client(use_service_role=True)
            result = client.table(REPORT_COMMENTS_TABLE).insert(comment_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error creating report comment: {e}")
            return None

    # Storage / Image Upload
    async def upload_image(self, file_data, file_name, content_type='image/jpeg'):
        """Upload an image to Supabase Storage"""
        try:
            client = self.get_client(use_service_role=True)
            
            # Upload to 'animal-images' bucket
            result = client.storage.from_(STORAGE_BUCKET).upload(
                file_name,
                file_data,
                file_options={
                    'content-type': content_type,
                    'upsert': 'true'
                }
            )
            
            if result:
                # Get public URL
                public_url = client.storage.from_(STORAGE_BUCKET).get_public_url(file_name)
                return {'success': True, 'url': public_url}
            else:
                return {'success': False, 'error': 'Upload failed'}
                
        except Exception as e:
            print(f"Error uploading image: {e}")
            return {'success': False, 'error': str(e)}
    
    async def delete_image(self, file_name):
        """Delete an image from Supabase Storage"""
        try:
            client = self.get_client(use_service_role=True)
            result = client.storage.from_(STORAGE_BUCKET).remove([file_name])
            return {'success': True, 'data': result}
        except Exception as e:
            print(f"Error deleting image: {e}")
            return {'success': False, 'error': str(e)}

    async def update_user_by_email(self, email, update_data):
        """Update user by email"""
        try:
            client = self.get_client(use_service_role=True)
            result = client.table(USERS_TABLE).update(update_data).eq('email', email).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error updating user by email: {e}")
            return None
    
    async def update_user_password(self, email, new_password):
        """Update user password in Supabase Auth"""
        try:
            # Get user by email first
            client = self.get_client(use_service_role=True)
            user_result = client.table(USERS_TABLE).select('id').eq('email', email).execute()
            
            if not user_result.data:
                print(f"User not found with email: {email}")
                return None
            
            user_id = user_result.data[0]['id']
            
            # Update password using Supabase Auth admin API
            auth_response = client.auth.admin.update_user_by_id(
                user_id,
                {'password': new_password}
            )
            
            return auth_response.user if auth_response else None
        except Exception as e:
            print(f"Error updating user password: {e}")
            return None

    async def delete_user(self, user_id):
        """Delete a user from the database and Supabase Auth, handling related records"""
        try:
            client = self.get_client(use_service_role=True)
            
            # 1. Delete user's pinned locations
            try:
                client.table(PINNED_LOCATIONS_TABLE).delete().eq('user_id', user_id).execute()
                print(f"Deleted pinned locations for user: {user_id}")
            except Exception as e:
                print(f"Error deleting pinned locations: {e}")
            
            # 2. Get user's reports and delete their comments first (due to FK constraints)
            try:
                reports = client.table(ANIMAL_REPORTS_TABLE).select('id').eq('user_id', user_id).execute()
                if reports.data:
                    for report in reports.data:
                        report_id = report['id']
                        # Delete comments on this report
                        client.table(REPORT_COMMENTS_TABLE).delete().eq('report_id', report_id).execute()
                        print(f"Deleted comments for report: {report_id}")
            except Exception as e:
                print(f"Error deleting comments: {e}")
            
            # 3. Delete comments made by this user on other reports
            try:
                client.table(REPORT_COMMENTS_TABLE).delete().eq('user_id', user_id).execute()
                print(f"Deleted user's comments: {user_id}")
            except Exception as e:
                print(f"Error deleting user comments: {e}")
            
            # 4. Delete user's animal reports
            try:
                client.table(ANIMAL_REPORTS_TABLE).delete().eq('user_id', user_id).execute()
                print(f"Deleted reports for user: {user_id}")
            except Exception as e:
                print(f"Error deleting reports: {e}")
            
            # 5. Delete from Supabase Auth (this prevents login)
            try:
                client.auth.admin.delete_user(user_id)
                print(f"Deleted user from Auth: {user_id}")
            except Exception as auth_error:
                print(f"Error deleting from Auth: {auth_error}")
            
            # 6. Finally, delete from the users table
            result = client.table(USERS_TABLE).delete().eq('id', user_id).execute()
            
            return result.data
        except Exception as e:
            print(f"Error deleting user: {e}")
            return None

    async def get_admin_stats(self):
        """Fetch aggregated stats for admin dashboard"""
        try:
            client = self.get_client(use_service_role=True)
            
            # 1. Total Users breakdown
            users_resp = client.table(USERS_TABLE).select('user_type').execute()
            users_data = users_resp.data or []
            total_users = len(users_data)
            num_rescuers = len([u for u in users_data if u.get('user_type') == 'rescuer'])
            num_regular_users = total_users - num_rescuers
            
            # 2. Reports breakdown by status
            reports_resp = client.table(ANIMAL_REPORTS_TABLE).select('status, animal_type, created_at').execute()
            reports_data = reports_resp.data or []
            total_reports = len(reports_data)
            
            status_counts = {}
            for r in reports_data:
                s = r.get('status', 'pending')
                status_counts[s] = status_counts.get(s, 0) + 1
            
            # 3. Reports by animal type
            animal_type_counts = {}
            for r in reports_data:
                at = r.get('animal_type', 'other')
                animal_type_counts[at] = animal_type_counts.get(at, 0) + 1
            
            # 4. Success Rate (Completed / Total)
            completed = status_counts.get('completed', 0)
            success_rate = (completed / total_reports * 100) if total_reports > 0 else 0
            
            return {
                'total_users': total_users,
                'num_rescuers': num_rescuers,
                'num_regular_users': num_regular_users,
                'total_reports': total_reports,
                'status_counts': status_counts,
                'animal_type_counts': animal_type_counts,
                'success_rate': round(success_rate, 1),
                'recent_reports': reports_data[:10]  # Just metadata for charts/lists
            }
        except Exception as e:
            print(f"Error getting admin stats: {e}")
            return None

    # Global instance
supabase_manager = SupabaseManager()
