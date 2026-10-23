from django.urls import path
from accounts.views import Login, Register, Logout, Profile

urlpatterns = [
    path('', Login.as_view(), name='login'),
    path('register/', Register.as_view(), name='register'),
    path('logout/', Logout.as_view(), name='logout'),
    path('profile/', Profile.as_view(), name='profile'),
]
