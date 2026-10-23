from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from accounts.models import LoginTable, UserTable
from accounts.helpers import user_required, get_current_user_profile

class Login(View):
    def get(self, request):
        if request.session.get('user_id'):
            if request.session.get('usertype') == 'admin':
                return redirect('admin_home')
            return redirect('user_home')
        return render(request, 'auth/login.html')

    def post(self, request):
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        if not username or not password:
            messages.error(request, "Please enter both username and password.")
            return render(request, 'auth/login.html')

        try:
            login_obj = LoginTable.objects.get(username=username, password=password)
            if not login_obj.is_active:
                messages.error(request, "Your account is deactivated. Please contact support.")
                return render(request, 'auth/login.html')

            request.session['user_id'] = login_obj.id
            request.session['username'] = login_obj.username
            request.session['usertype'] = login_obj.usertype

            # Log into Django auth session as well
            django_user, _ = User.objects.get_or_create(
                username=login_obj.username,
                defaults={'email': f"{login_obj.username}@spotbook.local"}
            )
            auth_login(request, django_user)

            # Cache display name
            if login_obj.usertype == 'user':
                try:
                    profile = UserTable.objects.get(LOGINID=login_obj)
                    request.session['user_name'] = profile.name
                    django_user.first_name = profile.name
                    django_user.email = profile.email
                    django_user.save()
                except UserTable.DoesNotExist:
                    request.session['user_name'] = login_obj.username
            else:
                request.session['user_name'] = 'Administrator'
                django_user.is_staff = True
                django_user.is_superuser = True
                django_user.save()

            messages.success(request, f"Welcome back, {request.session.get('user_name')}!")

            if login_obj.usertype == 'admin':
                return redirect('admin_home')
            else:
                return redirect('user_home')

        except LoginTable.DoesNotExist:
            messages.error(request, "Invalid username or password. Please try again.")
            return render(request, 'auth/login.html', {'error': 'Invalid username or password.'})


class Register(View):
    def get(self, request):
        return render(request, 'auth/register.html')

    def post(self, request):
        name = request.POST.get('name', '').strip()
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        password = request.POST.get('password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        # Validation
        if not (name and username and email and phone and password):
            messages.error(request, "All required fields must be filled.")
            return render(request, 'auth/register.html', request.POST)

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'auth/register.html', request.POST)

        if len(password) < 6:
            messages.error(request, "Password must be at least 6 characters.")
            return render(request, 'auth/register.html', request.POST)

        if LoginTable.objects.filter(username=username).exists() or User.objects.filter(username=username).exists():
            messages.error(request, "Username is already taken. Please choose another.")
            return render(request, 'auth/register.html', request.POST)

        if UserTable.objects.filter(email=email).exists():
            messages.error(request, "An account with this email already exists.")
            return render(request, 'auth/register.html', request.POST)

        # Create Django User
        User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=name
        )

        # Create Login & User record
        login_obj = LoginTable.objects.create(
            username=username,
            password=password,
            usertype='user',
            is_active=True
        )

        UserTable.objects.create(
            LOGINID=login_obj,
            name=name,
            email=email,
            phone=phone,
            address=address
        )

        messages.success(request, "Registration successful! You can now log in.")
        return redirect('login')


class Logout(View):
    def get(self, request):
        auth_logout(request)
        request.session.flush()
        messages.info(request, "You have been logged out successfully.")
        return redirect('login')

    def post(self, request):
        auth_logout(request)
        request.session.flush()
        messages.info(request, "You have been logged out successfully.")
        return redirect('login')


class Profile(View):
    def get(self, request):
        user_id = request.session.get('user_id')
        if not user_id and not request.user.is_authenticated:
            return redirect('login')

        profile = get_current_user_profile(request)
        if not profile:
            messages.error(request, "User profile not found.")
            return redirect('login')

        return render(request, 'user/profile.html', {'profile': profile})

    def post(self, request):
        user_id = request.session.get('user_id')
        if not user_id and not request.user.is_authenticated:
            return redirect('login')

        profile = get_current_user_profile(request)
        if not profile:
            messages.error(request, "Profile not found.")
            return redirect('login')

        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        new_password = request.POST.get('new_password', '').strip()

        if name:
            profile.name = name
            request.session['user_name'] = name
        if email:
            profile.email = email
        if phone:
            profile.phone = phone
        if address:
            profile.address = address
        profile.save()

        if new_password:
            if len(new_password) >= 6:
                login_obj = profile.LOGINID
                login_obj.password = new_password
                login_obj.save()
                # Update django user password
                try:
                    d_user = User.objects.get(username=login_obj.username)
                    d_user.set_password(new_password)
                    d_user.save()
                except User.DoesNotExist:
                    pass
                messages.success(request, "Profile and password updated successfully!")
            else:
                messages.warning(request, "Profile updated, but password was too short (minimum 6 chars).")
        else:
            messages.success(request, "Profile updated successfully!")

        return redirect('profile')
