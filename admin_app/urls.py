"""
URL configuration for spotbook project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from admin_app.views import *

urlpatterns = [

    path('AdminHome', AdminHome.as_view(), name='admin_home'),

    path('users/', Users.as_view(), name='users'),
    path('parking/', ParkingManagement.as_view(), name='parking_management'),
    path('parking/locations/', ParkingLocations.as_view(), name='ParkingLocations'),
    path('parking/slots/', ParkingSlots.as_view(), name='ParkingSlots'),
    path('bookings/', Bookings.as_view(), name='Bookings'),
    path('parking-charges/',ParkingCharges.as_view(),name='ParkingCharges'),
    path('qr-verification/',QRVerification.as_view(),name='QRVerification'),
    path('vehicle-management/',VehicleManagement.as_view(),name='VehicleManagement'),
    path('vehicle/entry/',VehicleEntry.as_view(),name='VehicleEntry'),
    path('vehicle/exit/',VehicleExit.as_view(),name='VehicleExit'),
    path('reports/',Reports.as_view(),name='Reports'),
]
