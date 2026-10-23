from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.models import User
from accounts.models import LoginTable, UserTable

def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user_id = request.session.get('user_id')
        usertype = request.session.get('usertype')
        if not user_id or usertype != 'admin':
            messages.error(request, "Access restricted to administrators. Please login.")
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def user_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user_id = request.session.get('user_id')
        usertype = request.session.get('usertype')
        if not user_id or usertype != 'user':
            messages.error(request, "Please login to access your account.")
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def get_current_django_user(request):
    if request.user and request.user.is_authenticated:
        return request.user
    user_id = request.session.get('user_id')
    if user_id:
        try:
            login_obj = LoginTable.objects.get(id=user_id)
            user_obj, _ = User.objects.get_or_create(
                username=login_obj.username,
                defaults={'email': f"{login_obj.username}@spotbook.local"}
            )
            return user_obj
        except LoginTable.DoesNotExist:
            pass
    return None

def get_current_user_profile(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return None
    try:
        login_obj = LoginTable.objects.get(id=user_id)
        return UserTable.objects.get(LOGINID=login_obj)
    except (LoginTable.DoesNotExist, UserTable.DoesNotExist):
        return None
