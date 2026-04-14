from django.shortcuts import render, redirect
import asyncio
from supabase_client import supabase_manager

def user_dashboard(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    user_type = getattr(request.user, 'user_type', 'user')
    if user_type == 'rescuer':
        return redirect('rescuer_dashboard')
    
    # Get Supabase UUID
    supabase_user = asyncio.run(supabase_manager.get_user_by_email(request.user.email, use_service_role=True))
    user_id = supabase_user.get('id') if supabase_user else str(request.user.id)
        
    return render(request, 'dashboard/user_dashboard.html', {
        'username': request.user.full_name or request.user.username,
        'user_type': user_type,
        'user_id': user_id
    })


def rescuer_dashboard(request):
    if not request.user.is_authenticated:
        return redirect('login')
        
    user_type = getattr(request.user, 'user_type', 'rescuer')
    if user_type == 'user':
        return redirect('user_dashboard')
    
    # Get Supabase UUID
    supabase_user = asyncio.run(supabase_manager.get_user_by_email(request.user.email, use_service_role=True))
    user_id = supabase_user.get('id') if supabase_user else str(request.user.id)
        
    return render(request, 'dashboard/rescuer_dashboard.html', {
        'username': request.user.full_name or request.user.username,
        'user_type': user_type,
        'user_id': user_id
    })
